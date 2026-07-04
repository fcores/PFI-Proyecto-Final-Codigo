#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# envVar.sh — Helpers para fijar las variables de entorno de `peer` según la org.
#
# Se debe ejecutar dentro del contexto donde ${NETWORK_DIR} apunta a fabric/network
# (rutas locales en el host) o, si se corre dentro del contenedor CLI, las rutas
# de organizations/.
#
# Uso:  source envVar.sh   y luego   setGlobals 1   (para Org1) ó  setGlobals 2.
# ─────────────────────────────────────────────────────────────────────────────

# Directorio raíz de organizations (montado igual en host y en el CLI).
: "${ORG_DIR:=${PWD}/organizations}"

ORDERER_CA="${ORG_DIR}/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem"
ORDERER_ADMIN_TLS_SIGN_CERT="${ORG_DIR}/ordererOrganizations/example.com/orderers/orderer.example.com/tls/server.crt"
ORDERER_ADMIN_TLS_PRIVATE_KEY="${ORG_DIR}/ordererOrganizations/example.com/orderers/orderer.example.com/tls/server.key"

PEER0_ORG1_CA="${ORG_DIR}/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt"
PEER0_ORG2_CA="${ORG_DIR}/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt"

# Fija CORE_PEER_* para operar como la org indicada (1 ó 2).
setGlobals() {
  local org=$1
  export CORE_PEER_TLS_ENABLED=true
  if [ "$org" -eq 1 ]; then
    export CORE_PEER_LOCALMSPID=Org1MSP
    export CORE_PEER_TLS_ROOTCERT_FILE=$PEER0_ORG1_CA
    export CORE_PEER_MSPCONFIGPATH=${ORG_DIR}/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp
    export CORE_PEER_ADDRESS=localhost:7051
  elif [ "$org" -eq 2 ]; then
    export CORE_PEER_LOCALMSPID=Org2MSP
    export CORE_PEER_TLS_ROOTCERT_FILE=$PEER0_ORG2_CA
    export CORE_PEER_MSPCONFIGPATH=${ORG_DIR}/peerOrganizations/org2.example.com/users/Admin@org2.example.com/msp
    export CORE_PEER_ADDRESS=localhost:9051
  else
    echo "Org desconocida: $org (usar 1 ó 2)" >&2
    return 1
  fi
}

# Construye los flags --peerAddresses para invocar chaincode con endorsement de
# ambas orgs. Deja el resultado en la variable PEER_CONN_PARMS (array).
setGlobalsCLI() {
  PEER_CONN_PARMS=(
    --peerAddresses localhost:7051 --tlsRootCertFiles "$PEER0_ORG1_CA"
    --peerAddresses localhost:9051 --tlsRootCertFiles "$PEER0_ORG2_CA"
  )
}
