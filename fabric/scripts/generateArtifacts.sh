#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# generateArtifacts.sh — Genera material criptográfico y el bloque de génesis.
#
#   1. cryptogen     -> organizations/  (certificados x509 + MSP + TLS)
#   2. configtxgen   -> channel-artifacts/<channel>.block  (génesis del canal)
#
# Idempotente: si organizations/ ya existe, no regenera el cripto (usar
# `network.sh down` para limpiar primero).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FABRIC_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
NETWORK_DIR="${FABRIC_DIR}/network"
source "${SCRIPT_DIR}/utils.sh"

export PATH="${FABRIC_DIR}/bin:${PATH}"
export FABRIC_CFG_PATH="${NETWORK_DIR}"

CHANNEL_NAME="${1:-mychannel}"

command -v cryptogen   >/dev/null || fatalln "No se encontró 'cryptogen'. Corré primero: ./network.sh install"
command -v configtxgen >/dev/null || fatalln "No se encontró 'configtxgen'. Corré primero: ./network.sh install"

cd "${NETWORK_DIR}"

# ── 1. Material criptográfico ────────────────────────────────────────────────
if [ -d "organizations/peerOrganizations" ]; then
  warnln "organizations/ ya existe — se omite cryptogen."
else
  infoln "Generando certificados con cryptogen..."
  cryptogen generate --config=./crypto-config.yaml --output="organizations"
  verifyResult $? "cryptogen falló"
  successln "Certificados generados en organizations/"
fi

# ── 2. Bloque de génesis del canal ───────────────────────────────────────────
mkdir -p channel-artifacts
infoln "Generando bloque de génesis para el canal '${CHANNEL_NAME}'..."
configtxgen \
  -profile ChannelGenesis \
  -channelID "${CHANNEL_NAME}" \
  -outputBlock "./channel-artifacts/${CHANNEL_NAME}.block"
verifyResult $? "configtxgen falló al generar el bloque de génesis"

successln "Bloque de génesis: channel-artifacts/${CHANNEL_NAME}.block"
