#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deployChaincode.sh — Despliega un chaincode usando el lifecycle de Fabric 2.x:
#
#   1. peer lifecycle chaincode package
#   2. install   (en los peers de Prescriptor, MedChain y Prepaga)
#   3. approveformyorg  (las tres orgs)
#   4. checkcommitreadiness
#   5. commit  (con --signature-policy AND de las tres orgs)
#   6. invoke de inicialización + query de prueba
#
# La política de endorsement es explícita: ninguna transacción entra al ledger
# sin la firma de las tres organizaciones (garantía de no adulteración).
#
# Variables:
#   CC_NAME     nombre lógico del chaincode      (default: prescriptions)
#   CC_SRC_PATH ruta al código fuente (Go)       (default: ../../chaincode/prescription-contract)
#   CC_VERSION  versión                          (default: 1.0)
#   CC_SEQUENCE secuencia de definición          (default: 1)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FABRIC_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
NETWORK_DIR="${FABRIC_DIR}/network"
ROOT_DIR="$(cd "${FABRIC_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

export PATH="${FABRIC_DIR}/bin:${PATH}"
export FABRIC_CFG_PATH="${FABRIC_DIR}/config"

CHANNEL_NAME="${1:-mychannel}"
CC_NAME="${CC_NAME:-prescriptions}"
CC_SRC_PATH="${CC_SRC_PATH:-${ROOT_DIR}/chaincode/prescription-contract}"
CC_LANG="golang"
CC_ENDORSEMENT_POLICY="${CC_ENDORSEMENT_POLICY:-AND('PrescriptorMSP.peer','MedChainMSP.peer','PrepagaMSP.peer')}"

cd "${NETWORK_DIR}"
export ORG_DIR="${NETWORK_DIR}/organizations"
source "${SCRIPT_DIR}/envVar.sh"

# Secuencia automatica: si CC_SEQUENCE no viene dado, consulta la definicion
# commiteada y usa la siguiente (primer deploy => 1).
if [ -z "${CC_SEQUENCE:-}" ]; then
  setGlobals 1
  CURRENT_SEQ=$(peer lifecycle chaincode querycommitted \
      --channelID "${CHANNEL_NAME}" --name "${CC_NAME}" --output json 2>/dev/null \
    | python3 -c 'import sys,json; print(json.load(sys.stdin).get("sequence",0))' 2>/dev/null \
    || echo 0)
  CC_SEQUENCE=$((CURRENT_SEQ + 1))
  infoln "Secuencia autodetectada: ${CC_SEQUENCE} (commiteada: ${CURRENT_SEQ})"
fi
CC_VERSION="${CC_VERSION:-1.${CC_SEQUENCE}}"
CC_LABEL="${CC_NAME}_${CC_VERSION}"
CC_PKG="${NETWORK_DIR}/${CC_LABEL}.tar.gz"

# ── 0. Resolver dependencias Go (vendor) para que el peer pueda compilar ─────
if command -v go >/dev/null 2>&1; then
  infoln "Resolviendo dependencias Go (go mod vendor)..."
  ( cd "${CC_SRC_PATH}" && GO111MODULE=on go mod vendor ) || warnln "go mod vendor falló; continúo igual"
else
  warnln "Go no está instalado en el host; se asume que el chaincode ya tiene vendor/."
fi

# ── 1. Empaquetar ────────────────────────────────────────────────────────────
infoln "Empaquetando chaincode '${CC_NAME}'..."
peer lifecycle chaincode package "${CC_PKG}" \
  --path "${CC_SRC_PATH}" \
  --lang "${CC_LANG}" \
  --label "${CC_LABEL}"
verifyResult $? "Falló el package del chaincode"
successln "Paquete creado: ${CC_PKG}"

# ── 2. Instalar en los tres peers ────────────────────────────────────────────
installChaincode() {
  local org=$1
  setGlobals "${org}"
  infoln "${CORE_PEER_LOCALMSPID}: instalando chaincode..."
  set +e
  peer lifecycle chaincode install "${CC_PKG}"
  local rc=$?
  set -e
  verifyResult ${rc} "${CORE_PEER_LOCALMSPID}: falló el install"
  successln "${CORE_PEER_LOCALMSPID}: chaincode instalado."
}
installChaincode 1
installChaincode 2
installChaincode 3

# ── 3. Obtener el package ID ─────────────────────────────────────────────────
setGlobals 1
PACKAGE_ID=$(peer lifecycle chaincode calculatepackageid "${CC_PKG}")
infoln "Package ID: ${PACKAGE_ID}"

# ── 4. Aprobar por cada org (con la política de endorsement explícita) ───────
approveForOrg() {
  local org=$1
  setGlobals "${org}"
  infoln "${CORE_PEER_LOCALMSPID}: aprobando definición del chaincode..."
  peer lifecycle chaincode approveformyorg \
    -o localhost:7050 --ordererTLSHostnameOverride orderer.medchain.com \
    --tls --cafile "${ORDERER_CA}" \
    --channelID "${CHANNEL_NAME}" \
    --name "${CC_NAME}" \
    --version "${CC_VERSION}" \
    --package-id "${PACKAGE_ID}" \
    --sequence "${CC_SEQUENCE}" \
    --signature-policy "${CC_ENDORSEMENT_POLICY}"
  verifyResult $? "${CORE_PEER_LOCALMSPID}: falló approveformyorg"
  successln "${CORE_PEER_LOCALMSPID}: definición aprobada."
}
approveForOrg 1
approveForOrg 2
approveForOrg 3

# ── 5. Verificar readiness ───────────────────────────────────────────────────
setGlobals 1
infoln "Verificando commit readiness..."
peer lifecycle chaincode checkcommitreadiness \
  --channelID "${CHANNEL_NAME}" \
  --name "${CC_NAME}" \
  --version "${CC_VERSION}" \
  --sequence "${CC_SEQUENCE}" \
  --signature-policy "${CC_ENDORSEMENT_POLICY}" \
  --output json

# ── 6. Commit de la definición ───────────────────────────────────────────────
setGlobalsCLI
infoln "Realizando commit de la definición del chaincode..."
peer lifecycle chaincode commit \
  -o localhost:7050 --ordererTLSHostnameOverride orderer.medchain.com \
  --tls --cafile "${ORDERER_CA}" \
  --channelID "${CHANNEL_NAME}" \
  --name "${CC_NAME}" \
  --version "${CC_VERSION}" \
  --sequence "${CC_SEQUENCE}" \
  --signature-policy "${CC_ENDORSEMENT_POLICY}" \
  "${PEER_CONN_PARMS[@]}"
verifyResult $? "Falló el commit del chaincode"
successln "Chaincode '${CC_NAME}' commiteado en el canal '${CHANNEL_NAME}'."

# ── 7. Inicialización (InitLedger es no-op) + smoke test ─────────────────────
setGlobalsCLI
setGlobals 1
infoln "Invocando InitLedger..."
peer chaincode invoke \
  -o localhost:7050 --ordererTLSHostnameOverride orderer.medchain.com \
  --tls --cafile "${ORDERER_CA}" \
  -C "${CHANNEL_NAME}" -n "${CC_NAME}" \
  "${PEER_CONN_PARMS[@]}" \
  -c '{"function":"InitLedger","Args":[]}'
verifyResult $? "Falló InitLedger"
sleep 3

infoln "Query de prueba (ListPrescriptions):"
setGlobals 2
peer chaincode query -C "${CHANNEL_NAME}" -n "${CC_NAME}" -c '{"Args":["ListPrescriptions","5",""]}'
verifyResult $? "Falló el query de prueba ListPrescriptions"

successln "Despliegue del chaincode completo."
