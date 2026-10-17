#!/usr/bin/env bash
# Paso 8: Dominio propio en CloudFront (app.<DOMINIO>).
# Prerequisito: dominio registrado con zona publica en Route 53 y la
# distribucion de 06-s3-cloudfront.sh (CF_DIST_ID en .env.deploy o en el entorno).
#
#   DOMAIN=midominio.com ./deploy/08-dominio.sh
#
# Emite un certificado ACM para APP_HOSTNAME (gratis; CloudFront lo exige en
# us-east-1), lo valida por DNS, agrega el alias a la distribucion con TLS 1.2
# como minimo y crea los registros alias en Route 53. Es idempotente: reutiliza
# el certificado y hace UPSERT de los registros.
#
# El certificado del tramo API Gateway -> tarea (API_TLS_HOSTNAME) NO sale de
# aca: ACM no exporta claves sin costo, asi que lo emite Let's Encrypt desde
# .github/workflows/renew-backend-cert.yml.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/00-variables.sh"
[ -f "${SCRIPT_DIR}/.env.deploy" ] && source "${SCRIPT_DIR}/.env.deploy"

: "${DOMAIN:?Definir DOMAIN (ej: DOMAIN=midominio.com ./deploy/08-dominio.sh)}"
: "${CF_DIST_ID:?Definir CF_DIST_ID (id de la distribucion de CloudFront)}"
# Zona fija de CloudFront para registros alias (documentada por AWS).
CLOUDFRONT_ZONE_ID="Z2FDTNDATAQYW2"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "=== Zona publica de ${DOMAIN} ==="
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones-by-name --dns-name "${DOMAIN}." \
  --query "HostedZones[?Name=='${DOMAIN}.' && Config.PrivateZone==\`false\`].Id | [0]" \
  --output text | sed 's|/hostedzone/||')
if [ -z "${HOSTED_ZONE_ID}" ] || [ "${HOSTED_ZONE_ID}" = "None" ]; then
  echo "ERROR: no hay zona publica para ${DOMAIN} en Route 53." >&2
  exit 1
fi
echo "Zona: ${HOSTED_ZONE_ID}"

echo "=== Certificado ACM para ${APP_HOSTNAME} (us-east-1) ==="
APP_CERT_ARN=$(aws acm list-certificates --region us-east-1 \
  --certificate-statuses ISSUED PENDING_VALIDATION \
  --query "CertificateSummaryList[?DomainName=='${APP_HOSTNAME}'].CertificateArn | [0]" \
  --output text)
if [ -z "${APP_CERT_ARN}" ] || [ "${APP_CERT_ARN}" = "None" ]; then
  APP_CERT_ARN=$(aws acm request-certificate --region us-east-1 \
    --domain-name "${APP_HOSTNAME}" --validation-method DNS \
    --key-algorithm RSA_2048 \
    --query 'CertificateArn' --output text)
fi
echo "Certificado: ${APP_CERT_ARN}"

# El registro de validacion tarda unos segundos en aparecer tras el request.
for _ in $(seq 1 12); do
  VALIDATION=$(aws acm describe-certificate --region us-east-1 --certificate-arn "${APP_CERT_ARN}" \
    --query 'Certificate.DomainValidationOptions[0].ResourceRecord.[Name,Value]' --output text)
  [ -n "${VALIDATION}" ] && [ "${VALIDATION}" != "None" ] && break
  sleep 5
done
read -r VAL_NAME VAL_VALUE <<<"${VALIDATION}"
cat > "${TMP_DIR}/validation.json" <<EOF
{"Changes":[{"Action":"UPSERT","ResourceRecordSet":{
  "Name":"${VAL_NAME}","Type":"CNAME","TTL":300,
  "ResourceRecords":[{"Value":"${VAL_VALUE}"}]}}]}
EOF
aws route53 change-resource-record-sets --hosted-zone-id "${HOSTED_ZONE_ID}" \
  --change-batch "file://${TMP_DIR}/validation.json" --query 'ChangeInfo.Status' --output text
echo "Esperando la validacion del certificado (puede tardar unos minutos)..."
aws acm wait certificate-validated --region us-east-1 --certificate-arn "${APP_CERT_ARN}"

echo "=== Alias ${APP_HOSTNAME} en la distribucion ${CF_DIST_ID} ==="
aws cloudfront get-distribution-config --id "${CF_DIST_ID}" --output json > "${TMP_DIR}/cf.json"
ETAG=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['ETag'])" "${TMP_DIR}/cf.json")
python3 - "${TMP_DIR}/cf.json" "${TMP_DIR}/cf-new.json" "${APP_HOSTNAME}" "${APP_CERT_ARN}" <<'PY'
import json, sys
src, dst, host, cert = sys.argv[1:5]
cfg = json.load(open(src))["DistributionConfig"]
aliases = set(cfg.get("Aliases", {}).get("Items", []) or [])
aliases.add(host)
cfg["Aliases"] = {"Quantity": len(aliases), "Items": sorted(aliases)}
cfg["ViewerCertificate"] = {
    "ACMCertificateArn": cert,
    "SSLSupportMethod": "sni-only",
    "MinimumProtocolVersion": "TLSv1.2_2021",
    "CloudFrontDefaultCertificate": False,
}
json.dump(cfg, open(dst, "w"))
print("ipv6" if cfg.get("IsIPV6Enabled") else "ipv4")
PY
aws cloudfront update-distribution --id "${CF_DIST_ID}" --if-match "${ETAG}" \
  --distribution-config "file://${TMP_DIR}/cf-new.json" --query 'Distribution.Status' --output text
CF_DOMAIN=$(aws cloudfront get-distribution --id "${CF_DIST_ID}" --query 'Distribution.DomainName' --output text)
IPV6=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('IsIPV6Enabled', False))" "${TMP_DIR}/cf-new.json")

echo "=== Registros alias en Route 53 ==="
RECORD_TYPES="A"
[ "${IPV6}" = "True" ] && RECORD_TYPES="A AAAA"
for TYPE in ${RECORD_TYPES}; do
  cat > "${TMP_DIR}/alias-${TYPE}.json" <<EOF
{"Changes":[{"Action":"UPSERT","ResourceRecordSet":{
  "Name":"${APP_HOSTNAME}","Type":"${TYPE}",
  "AliasTarget":{"HostedZoneId":"${CLOUDFRONT_ZONE_ID}","DNSName":"${CF_DOMAIN}","EvaluateTargetHealth":false}}}]}
EOF
  aws route53 change-resource-record-sets --hosted-zone-id "${HOSTED_ZONE_ID}" \
    --change-batch "file://${TMP_DIR}/alias-${TYPE}.json" --query 'ChangeInfo.Status' --output text
done

cat >> "${SCRIPT_DIR}/.env.deploy" <<EOF
HOSTED_ZONE_ID=${HOSTED_ZONE_ID}
APP_CERT_ARN=${APP_CERT_ARN}
EOF

echo ""
echo "Listo: https://${APP_HOSTNAME} (la distribucion tarda unos minutos en propagar)."
echo "La URL https://${CF_DOMAIN} sigue funcionando."
