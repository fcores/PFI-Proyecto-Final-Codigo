#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# createChannel.sh — Crea el canal de aplicación y une orderer + peers.
#
#   1. osnadmin channel join   -> el orderer arranca el canal con su bloque génesis
#   2. peer channel join       -> cada peer (Org1, Org2) se une al canal
#
# Requiere que la red esté levantada (./network.sh up) y que exista el bloque
# de génesis (generado por generateArtifacts.sh).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FABRIC_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
NETWORK_DIR="${FABRIC_DIR}/network"
source "${SCRIPT_DIR}/utils.sh"

export PATH="${FABRIC_DIR}/bin:${PATH}"
export FABRIC_CFG_PATH="${FABRIC_DIR}/config"

CHANNEL_NAME="${1:-mychannel}"
MAX_RETRY=5
DELAY=3

cd "${NETWORK_DIR}"
export ORG_DIR="${NETWORK_DIR}/organizations"
source "${SCRIPT_DIR}/envVar.sh"

BLOCKFILE="./channel-artifacts/${CHANNEL_NAME}.block"
[ -f "${BLOCKFILE}" ] || fatalln "No existe ${BLOCKFILE}. Corré: ./network.sh generate"

# ── 1. El orderer se une al canal (Channel Participation API) ────────────────
infoln "Uniendo el orderer al canal '${CHANNEL_NAME}'..."
osnadmin channel join \
  --channelID "${CHANNEL_NAME}" \
  --config-block "${BLOCKFILE}" \
  -o localhost:7053 \
  --ca-file "${ORDERER_CA}" \
  --client-cert "${ORDERER_ADMIN_TLS_SIGN_CERT}" \
  --client-key "${ORDERER_ADMIN_TLS_PRIVATE_KEY}"
verifyResult $? "osnadmin: el orderer no pudo unirse al canal"
successln "Orderer unido al canal."

# ── 2. Cada peer se une al canal ─────────────────────────────────────────────
joinChannel() {
  local org=$1
  setGlobals "${org}"
  local rc=1 attempt=1
  while [ ${attempt} -le ${MAX_RETRY} ]; do
    infoln "Org${org}: peer channel join (intento ${attempt}/${MAX_RETRY})..."
    set +e
    peer channel join -b "${BLOCKFILE}" >/dev/null 2>&1
    rc=$?
    set -e
    [ ${rc} -eq 0 ] && break
    sleep ${DELAY}
    attempt=$((attempt + 1))
  done
  verifyResult ${rc} "Org${org}: el peer no pudo unirse al canal"
  successln "Org${org}: peer unido al canal '${CHANNEL_NAME}'."
}

joinChannel 1
joinChannel 2

# ── 3. (opcional) Verificación ───────────────────────────────────────────────
setGlobals 1
infoln "Canales del peer0.org1:"
peer channel list

successln "Canal '${CHANNEL_NAME}' creado y con ambos peers unidos."
