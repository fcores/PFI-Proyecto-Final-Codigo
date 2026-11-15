#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# utils.sh — Funciones de logging y utilidades compartidas por los scripts.
# ─────────────────────────────────────────────────────────────────────────────

C_RESET='\033[0m'
C_RED='\033[0;31m'
C_GREEN='\033[0;32m'
C_YELLOW='\033[1;33m'
C_BLUE='\033[0;34m'

infoln()    { echo -e "${C_BLUE}[INFO]${C_RESET}  $1"; }
successln() { echo -e "${C_GREEN}[OK]${C_RESET}    $1"; }
warnln()    { echo -e "${C_YELLOW}[WARN]${C_RESET}  $1"; }
errorln()   { echo -e "${C_RED}[ERROR]${C_RESET} $1" >&2; }

# Aborta el script mostrando un mensaje de error.
fatalln() {
  errorln "$1"
  exit 1
}

# Verifica el código de salida del último comando; aborta si fue != 0.
verifyResult() {
  if [ "$1" -ne 0 ]; then
    fatalln "$2"
  fi
}
