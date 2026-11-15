#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# envVar.sh — Helpers para fijar las variables de entorno de `peer` según la org.
#
# Se debe ejecutar dentro del contexto donde ${NETWORK_DIR} apunta a fabric/network
# (rutas locales en el host) o, si se corre dentro del contenedor CLI, las rutas
# de organizations/.
#
# Uso:  source envVar.sh   y luego:
#   setGlobals 1   -> PrescriptorMSP (peer0.prescriptor.medchain.com:7051)
#   setGlobals 2   -> MedChainMSP    (peer0.auditoria.medchain.com:9051)
#   setGlobals 3   -> PrepagaMSP     (peer0.prepaga.medchain.com:11051)
# ─────────────────────────────────────────────────────────────────────────────

# Directorio raíz de organizations (montado igual en host y en el CLI).
: "${ORG_DIR:=${PWD}/organizations}"

ORDERER_CA="${ORG_DIR}/ordererOrganizations/medchain.com/orderers/orderer.medchain.com/msp/tlscacerts/tlsca.medchain.com-cert.pem"
ORDERER_ADMIN_TLS_SIGN_CERT="${ORG_DIR}/ordererOrganizations/medchain.com/orderers/orderer.medchain.com/tls/server.crt"
ORDERER_ADMIN_TLS_PRIVATE_KEY="${ORG_DIR}/ordererOrganizations/medchain.com/orderers/orderer.medchain.com/tls/server.key"

PEER0_PRESCRIPTOR_CA="${ORG_DIR}/peerOrganizations/prescriptor.medchain.com/peers/peer0.prescriptor.medchain.com/tls/ca.crt"
PEER0_MEDCHAIN_CA="${ORG_DIR}/peerOrganizations/auditoria.medchain.com/peers/peer0.auditoria.medchain.com/tls/ca.crt"
PEER0_PREPAGA_CA="${ORG_DIR}/peerOrganizations/prepaga.medchain.com/peers/peer0.prepaga.medchain.com/tls/ca.crt"

# Fija CORE_PEER_* para operar como la org indicada (1, 2 ó 3).
setGlobals() {
  local org=$1
  export CORE_PEER_TLS_ENABLED=true
  if [ "$org" -eq 1 ]; then
    export CORE_PEER_LOCALMSPID=PrescriptorMSP
    export CORE_PEER_TLS_ROOTCERT_FILE=$PEER0_PRESCRIPTOR_CA
    export CORE_PEER_MSPCONFIGPATH=${ORG_DIR}/peerOrganizations/prescriptor.medchain.com/users/Admin@prescriptor.medchain.com/msp
    export CORE_PEER_ADDRESS=localhost:7051
  elif [ "$org" -eq 2 ]; then
    export CORE_PEER_LOCALMSPID=MedChainMSP
    export CORE_PEER_TLS_ROOTCERT_FILE=$PEER0_MEDCHAIN_CA
    export CORE_PEER_MSPCONFIGPATH=${ORG_DIR}/peerOrganizations/auditoria.medchain.com/users/Admin@auditoria.medchain.com/msp
    export CORE_PEER_ADDRESS=localhost:9051
  elif [ "$org" -eq 3 ]; then
    export CORE_PEER_LOCALMSPID=PrepagaMSP
    export CORE_PEER_TLS_ROOTCERT_FILE=$PEER0_PREPAGA_CA
    export CORE_PEER_MSPCONFIGPATH=${ORG_DIR}/peerOrganizations/prepaga.medchain.com/users/Admin@prepaga.medchain.com/msp
    export CORE_PEER_ADDRESS=localhost:11051
  else
    echo "Org desconocida: $org (usar 1, 2 ó 3)" >&2
    return 1
  fi
}

# Construye los flags --peerAddresses para invocar chaincode con endorsement de
# las tres orgs. Deja el resultado en la variable PEER_CONN_PARMS (array).
setGlobalsCLI() {
  PEER_CONN_PARMS=(
    --peerAddresses localhost:7051 --tlsRootCertFiles "$PEER0_PRESCRIPTOR_CA"
    --peerAddresses localhost:9051 --tlsRootCertFiles "$PEER0_MEDCHAIN_CA"
    --peerAddresses localhost:11051 --tlsRootCertFiles "$PEER0_PREPAGA_CA"
  )
}
