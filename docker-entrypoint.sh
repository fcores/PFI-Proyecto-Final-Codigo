#!/bin/sh
# Arranque del contenedor del backend.
#
# 1. El bootstrap aplica sql/schema.sql y luego 'alembic upgrade head'. Si
#    falla, el contenedor sale != 0 a proposito: preferimos un crash loop
#    visible antes que una app sirviendo trafico contra un esquema roto.
# 2. Con TLS_CERT_PEM y TLS_KEY_PEM (secreto medchain/backend-tls, inyectado por
#    la task definition) uvicorn sirve HTTPS: API Gateway valida ese
#    certificado contra el nombre de tlsConfig.serverNameToVerify. Sin ellas
#    sirve HTTP, para que la imagen siga funcionando con una task definition
#    que todavia no las define.
set -e

python -m backend.db_bootstrap

if [ -n "${TLS_CERT_PEM:-}" ] && [ -n "${TLS_KEY_PEM:-}" ]; then
  umask 077
  mkdir -p /tmp/tls
  printf '%s\n' "${TLS_CERT_PEM}" > /tmp/tls/cert.pem
  printf '%s\n' "${TLS_KEY_PEM}" > /tmp/tls/key.pem
  # La clave ya esta en disco; la aplicacion no necesita verla en su entorno.
  unset TLS_KEY_PEM
  exec uvicorn backend.main:app --host 0.0.0.0 --port 8000 \
    --ssl-certfile /tmp/tls/cert.pem --ssl-keyfile /tmp/tls/key.pem
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
