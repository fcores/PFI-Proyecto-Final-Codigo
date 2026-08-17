#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# network.sh — Punto de entrada para operar la red Hyperledger Fabric de MedChain.
#
# Uso:
#   ./network.sh install                 Descarga binarios + imágenes Docker
#   ./network.sh generate                Genera cripto + bloque de génesis
#   ./network.sh up                      Genera artefactos (si faltan) y levanta contenedores
#   ./network.sh createChannel [nombre]  Crea el canal y une los peers (default: mychannel)
#   ./network.sh deployCC [nombre]       Despliega el chaincode de prescripciones
#   ./network.sh down                    Apaga la red y limpia artefactos
#   ./network.sh restart                 down + up
#
# Flujo típico:
#   ./network.sh install && ./network.sh up && ./network.sh createChannel && ./network.sh deployCC
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NETWORK_DIR="${SCRIPT_DIR}/network"
SCRIPTS="${SCRIPT_DIR}/scripts"
COMPOSE_FILE="${NETWORK_DIR}/compose/compose-net.yaml"
ENV_FILE="${NETWORK_DIR}/.env"

source "${SCRIPTS}/utils.sh"

CHANNEL_NAME="mychannel"

# Detecta `docker compose` (v2) vs `docker-compose` (v1).
dockerCompose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
  else
    fatalln "No se encontró Docker Compose. Instalá Docker Desktop / docker compose."
  fi
}

checkPrereqs() {
  command -v docker >/dev/null 2>&1 || fatalln "Docker no está instalado o no está en el PATH."
  docker info >/dev/null 2>&1 || fatalln "El daemon de Docker no está corriendo."
}

networkUp() {
  checkPrereqs
  # Generar artefactos si aún no existen
  if [ ! -d "${NETWORK_DIR}/organizations/peerOrganizations" ]; then
    "${SCRIPTS}/generateArtifacts.sh" "${CHANNEL_NAME}"
  else
    infoln "Artefactos ya presentes — se omite generación."
  fi
  infoln "Levantando contenedores..."
  dockerCompose up -d
  successln "Red levantada. Contenedores:"
  docker ps --filter "label=service=hyperledger-fabric" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

networkDown() {
  infoln "Apagando contenedores y limpiando volúmenes..."
  dockerCompose down --volumes --remove-orphans 2>/dev/null || true

  # Limpiar contenedores de chaincode (dev-peer*)
  local cc
  cc=$(docker ps -aq --filter "name=dev-peer" 2>/dev/null || true)
  [ -n "${cc}" ] && docker rm -f ${cc} >/dev/null 2>&1 || true

  infoln "Limpiando artefactos generados..."
  rm -rf "${NETWORK_DIR}/organizations" \
         "${NETWORK_DIR}/channel-artifacts" \
         "${NETWORK_DIR}/system-genesis-block"
  rm -f "${NETWORK_DIR}"/*.tar.gz
  successln "Red apagada y limpia."
}

case "${1:-}" in
  install)       "${SCRIPTS}/install-fabric.sh" ;;
  generate)      "${SCRIPTS}/generateArtifacts.sh" "${2:-$CHANNEL_NAME}" ;;
  up)            networkUp ;;
  createChannel) "${SCRIPTS}/createChannel.sh" "${2:-$CHANNEL_NAME}" ;;
  deployCC)      "${SCRIPTS}/deployChaincode.sh" "${2:-$CHANNEL_NAME}" ;;
  down)          networkDown ;;
  restart)       networkDown; networkUp ;;
  *)
    grep -E '^#( |$)' "$0" | sed -E 's/^# ?//' | head -n 22
    exit 1
    ;;
esac
