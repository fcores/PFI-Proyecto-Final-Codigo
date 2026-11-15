#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# install-fabric.sh — Descarga binarios de Fabric, archivos de config base e
# imágenes Docker en las versiones definidas en network/.env
#
# Genera (dentro de fabric/):
#   bin/      -> peer, orderer, configtxgen, cryptogen, osnadmin, discover...
#   config/   -> core.yaml, orderer.yaml, configtx.yaml (de muestra)
#
# Usa el instalador oficial de Hyperledger por debajo.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FABRIC_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

# Cargar versiones desde network/.env
set -a
# shellcheck disable=SC1091
source "${FABRIC_DIR}/network/.env"
set +a

FABRIC_VERSION="${IMAGE_TAG}"
CA_VERSION="${CA_IMAGE_TAG}"

infoln "Instalando Hyperledger Fabric v${FABRIC_VERSION} (CA v${CA_VERSION})"
infoln "Destino: ${FABRIC_DIR}"

cd "${FABRIC_DIR}"

# Descargar el instalador oficial si no está presente.
if [ ! -f "install-fabric.sh.upstream" ]; then
  infoln "Descargando instalador oficial de Hyperledger..."
  curl -fsSL https://raw.githubusercontent.com/hyperledger/fabric/main/scripts/install-fabric.sh \
    -o install-fabric.sh.upstream
  chmod +x install-fabric.sh.upstream
fi

# Componentes:
#   docker  -> baja imágenes Docker
#   binary  -> baja binarios + config/
infoln "Descargando binarios, config e imágenes Docker..."
./install-fabric.sh.upstream --fabric-version "${FABRIC_VERSION}" --ca-version "${CA_VERSION}" docker binary

successln "Instalación completa."
infoln "Binarios en:  ${FABRIC_DIR}/bin"
infoln "Config en:    ${FABRIC_DIR}/config"
warnln "Agregá ${FABRIC_DIR}/bin al PATH o los scripts lo harán automáticamente."
