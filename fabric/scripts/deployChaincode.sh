#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deployChaincode.sh — Despliega un chaincode usando el lifecycle de Fabric 2.x:
#
#   1. peer lifecycle chaincode package
#   2. install   (en peer0.org1 y peer0.org2)
#   3. approveformyorg  (Org1 y Org2)
#   4. checkcommitreadiness
#   5. commit
#   6. (opcional) invoke de inicialización + query de prueba
#
# Variables:
#   CC_NAME     nombre lógico del chaincode      (default: basic)
#   CC_SRC_PATH ruta al código fuente (Go)       (default: ../../chaincode/asset-transfer-basic)
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
CC_VERSION="${CC_VERSION:-1.0}"
CC_SEQUENCE="${CC_SEQUENCE:-1}"
CC_LANG="golang"
CC_LABEL="${CC_NAME}_${CC_VERSION}"
CC_PKG="${NETWORK_DIR}/${CC_LABEL}.tar.gz"

cd "${NETWORK_DIR}"
export ORG_DIR="${NETWORK_DIR}/organizations"
source "${SCRIPT_DIR}/envVar.sh"

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

# ── 2. Instalar en ambos peers ───────────────────────────────────────────────
installChaincode() {
  local org=$1
  setGlobals "${org}"
  infoln "Org${org}: instalando chaincode..."
  set +e
  peer lifecycle chaincode install "${CC_PKG}"
  local rc=$?
  set -e
  verifyResult ${rc} "Org${org}: falló el install"
  successln "Org${org}: chaincode instalado."
}
installChaincode 1
installChaincode 2

# ── 3. Obtener el package ID ─────────────────────────────────────────────────
setGlobals 1
PACKAGE_ID=$(peer lifecycle chaincode calculatepackageid "${CC_PKG}")
infoln "Package ID: ${PACKAGE_ID}"

# ── 4. Aprobar por cada org ──────────────────────────────────────────────────
approveForOrg() {
  local org=$1
  setGlobals "${org}"
  infoln "Org${org}: aprobando definición del chaincode..."
  peer lifecycle chaincode approveformyorg \
    -o localhost:7050 --ordererTLSHostnameOverride orderer.example.com \
    --tls --cafile "${ORDERER_CA}" \
    --channelID "${CHANNEL_NAME}" \
    --name "${CC_NAME}" \
    --version "${CC_VERSION}" \
    --package-id "${PACKAGE_ID}" \
    --sequence "${CC_SEQUENCE}"
  verifyResult $? "Org${org}: falló approveformyorg"
  successln "Org${org}: definición aprobada."
}
approveForOrg 1
approveForOrg 2

# ── 5. Verificar readiness ───────────────────────────────────────────────────
setGlobals 1
infoln "Verificando commit readiness..."
peer lifecycle chaincode checkcommitreadiness \
  --channelID "${CHANNEL_NAME}" \
  --name "${CC_NAME}" \
  --version "${CC_VERSION}" \
  --sequence "${CC_SEQUENCE}" \
  --output json

# ── 6. Commit de la definición ───────────────────────────────────────────────
setGlobalsCLI
infoln "Realizando commit de la definición del chaincode..."
peer lifecycle chaincode commit \
  -o localhost:7050 --ordererTLSHostnameOverride orderer.example.com \
  --tls --cafile "${ORDERER_CA}" \
  --channelID "${CHANNEL_NAME}" \
  --name "${CC_NAME}" \
  --version "${CC_VERSION}" \
  --sequence "${CC_SEQUENCE}" \
  "${PEER_CONN_PARMS[@]}"
verifyResult $? "Falló el commit del chaincode"
successln "Chaincode '${CC_NAME}' commiteado en el canal '${CHANNEL_NAME}'."

# ── 7. Inicialización de datos de prueba (InitLedger) ────────────────────────
setGlobalsCLI
infoln "Invocando InitLedger..."
peer chaincode invoke \
  -o localhost:7050 --ordererTLSHostnameOverride orderer.example.com \
  --tls --cafile "${ORDERER_CA}" \
  -C "${CHANNEL_NAME}" -n "${CC_NAME}" \
  "${PEER_CONN_PARMS[@]}" \
  -c '{"function":"InitLedger","Args":[]}'
verifyResult $? "Falló InitLedger"
sleep 3

infoln "Query de prueba (GetAllAssets):"
setGlobals 1
peer chaincode query -C "${CHANNEL_NAME}" -n "${CC_NAME}" -c '{"Args":["GetAllAssets"]}'

successln "Despliegue del chaincode completo."
