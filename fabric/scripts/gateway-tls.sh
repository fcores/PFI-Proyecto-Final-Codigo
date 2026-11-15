#!/usr/bin/env bash
# gateway-tls.sh — Material TLS del puente fabric-gateway-svc.
#
# Genera una CA propia del proyecto y un certificado de servidor para el
# listener HTTPS del gateway (TLS_LISTEN_ADDR). El backend valida contra esa CA
# (FABRIC_GATEWAY_CA_PEM): no hace falta una CA publica porque el unico cliente
# es nuestro.
#
# Uso:
#   ./fabric/scripts/gateway-tls.sh [IP_PRIVADA]        # crea lo que falte
#   ./fabric/scripts/gateway-tls.sh [IP_PRIVADA] --renew # reemite el de servidor
#
# Sin IP, la toma del servicio de metadatos de la EC2 (IMDSv2). La IP privada va
# como SAN porque el backend llama por IP literal: el VPC peering no propaga la
# resolucion DNS. Si la instancia se recrea y cambia de IP, hay que reemitir con
# --renew y actualizar FABRIC_GATEWAY_URL.
#
# Salida en fabric/network/gateway-tls/ (gitignored). Queda FUERA de
# organizations/ a proposito: `network.sh down` borra organizations/ y esto no
# debe rotar con cada recreacion de la red.
#
# La clave de la CA (ca.key) solo se usa para firmar; no la lee ningun proceso.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="${SCRIPT_DIR}/../network/gateway-tls"
GATEWAY_UID=10001
CA_DAYS=3650
SERVER_DAYS=730

IP="${1:-}"
RENEW="${2:-}"
if [ "${IP}" = "--renew" ]; then IP=""; RENEW="--renew"; fi

if [ -z "${IP}" ]; then
  TOKEN=$(curl -sf -X PUT "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 60" || true)
  IP=$(curl -sf -H "X-aws-ec2-metadata-token: ${TOKEN}" \
    http://169.254.169.254/latest/meta-data/local-ipv4 || true)
fi
if [ -z "${IP}" ]; then
  echo "ERROR: no se pudo determinar la IP privada; pasala como primer argumento." >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"
cd "${OUT_DIR}"

# Los archivos pueden haber quedado a nombre del uid del gateway en una corrida
# anterior; se recuperan para poder reescribirlos.
if [ -e server.key ] && [ ! -w server.key ]; then
  sudo chown "$(id -u):$(id -g)" server.key server.crt 2>/dev/null || true
fi

if [ ! -f ca.key ]; then
  echo "=== Generando CA del proyecto (${CA_DAYS} dias) ==="
  openssl req -x509 -newkey rsa:4096 -sha256 -nodes -days "${CA_DAYS}" \
    -keyout ca.key -out ca.crt \
    -subj "/O=MedChain/CN=MedChain Fabric Gateway CA" \
    -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
    -addext "keyUsage=critical,keyCertSign,cRLSign"
  chmod 600 ca.key
else
  echo "CA existente: se reutiliza (${OUT_DIR}/ca.crt)"
fi

if [ ! -f server.crt ] || [ "${RENEW}" = "--renew" ]; then
  echo "=== Emitiendo certificado de servidor para ${IP} (${SERVER_DAYS} dias) ==="
  openssl req -newkey rsa:2048 -sha256 -nodes \
    -keyout server.key -out server.csr \
    -subj "/O=MedChain/CN=fabric-gateway"
  cat > server.ext <<EOF
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=IP:${IP},IP:127.0.0.1,DNS:localhost
EOF
  openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -days "${SERVER_DAYS}" -sha256 -extfile server.ext -out server.crt
  rm -f server.csr server.ext
else
  echo "Certificado de servidor existente: se conserva (usar --renew para reemitir)"
fi

# El contenedor del gateway corre como uid 10001 (ver fabric-gateway-svc/Dockerfile).
chmod 644 ca.crt server.crt
chmod 600 server.key
chown "${GATEWAY_UID}:${GATEWAY_UID}" server.key server.crt 2>/dev/null \
  || sudo chown "${GATEWAY_UID}:${GATEWAY_UID}" server.key server.crt

openssl x509 -in server.crt -noout -subject -enddate -ext subjectAltName
echo ""
echo "CA para el backend (FABRIC_GATEWAY_CA_PEM): ${OUT_DIR}/ca.crt"
