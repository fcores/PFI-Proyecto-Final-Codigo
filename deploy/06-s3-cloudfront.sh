#!/usr/bin/env bash
# Paso 6: Subir SPA a S3 y crear distribucion CloudFront con dos origenes.
# Prerequisito: pasos 01-05 ejecutados, frontend buildeado (npm run build).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/00-variables.sh"
source "${SCRIPT_DIR}/.env.deploy"

PROJECT_ROOT="${SCRIPT_DIR}/.."

echo "=== Construyendo frontend ==="
cd "${PROJECT_ROOT}/frontend"
npm run build
cd "${PROJECT_ROOT}"

echo "=== Creando bucket S3 ==="
if [ "${AWS_REGION}" = "us-east-1" ]; then
  aws s3api create-bucket --bucket "${S3_BUCKET}" --region "${AWS_REGION}" 2>/dev/null || true
else
  aws s3api create-bucket --bucket "${S3_BUCKET}" --region "${AWS_REGION}" \
    --create-bucket-configuration "LocationConstraint=${AWS_REGION}" 2>/dev/null || true
fi

aws s3api put-public-access-block --bucket "${S3_BUCKET}" \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
echo "Bucket: ${S3_BUCKET}"

echo "=== Subiendo dist/ a S3 ==="
aws s3 sync frontend/dist/ "s3://${S3_BUCKET}/" --delete

echo "=== Creando Origin Access Control (OAC) ==="
OAC_ID=$(aws cloudfront create-origin-access-control \
  --origin-access-control-config "{
    \"Name\": \"${PROJECT}-oac\",
    \"Description\": \"OAC para S3 SPA\",
    \"SigningProtocol\": \"sigv4\",
    \"SigningBehavior\": \"always\",
    \"OriginAccessControlOriginType\": \"s3\"
  }" \
  --query 'OriginAccessControl.Id' --output text 2>/dev/null || echo "")

if [ -z "${OAC_ID}" ]; then
  OAC_ID=$(aws cloudfront list-origin-access-controls \
    --query "OriginAccessControlList.Items[?Name=='${PROJECT}-oac'].Id" --output text)
fi
echo "OAC: ${OAC_ID}"

APIGW_DOMAIN=$(echo "${APIGW_ENDPOINT}" | sed 's|https://||')

echo "=== Creando distribucion CloudFront ==="
CALLER_REF="deploy-$(date +%s)"

cat > /tmp/cf-config.json <<CFCONFIG
{
  "CallerReference": "${CALLER_REF}",
  "Comment": "MedChain AI - SPA + API",
  "Enabled": true,
  "DefaultRootObject": "index.html",
  "Origins": {
    "Quantity": 2,
    "Items": [
      {
        "Id": "s3-spa",
        "DomainName": "${S3_BUCKET}.s3.${AWS_REGION}.amazonaws.com",
        "OriginAccessControlId": "${OAC_ID}",
        "S3OriginConfig": {
          "OriginAccessIdentity": ""
        }
      },
      {
        "Id": "api-gateway",
        "DomainName": "${APIGW_DOMAIN}",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "https-only",
          "OriginSslProtocols": {"Quantity": 1, "Items": ["TLSv1.2"]}
        }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "s3-spa",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
    "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
    "Compress": true,
    "ForwardedValues": {
      "QueryString": false,
      "Cookies": {"Forward": "none"}
    },
    "MinTTL": 0,
    "DefaultTTL": 86400,
    "MaxTTL": 31536000
  },
  "CacheBehaviors": {
    "Quantity": 1,
    "Items": [
      {
        "PathPattern": "/api/*",
        "TargetOriginId": "api-gateway",
        "ViewerProtocolPolicy": "redirect-to-https",
        "AllowedMethods": {"Quantity": 7, "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]},
        "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
        "Compress": true,
        "ForwardedValues": {
          "QueryString": true,
          "Cookies": {"Forward": "none"},
          "Headers": {"Quantity": 2, "Items": ["Authorization", "Content-Type"]}
        },
        "MinTTL": 0,
        "DefaultTTL": 0,
        "MaxTTL": 0
      }
    ]
  },
  "CustomErrorResponses": {
    "Quantity": 2,
    "Items": [
      {
        "ErrorCode": 403,
        "ResponsePagePath": "/index.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 10
      },
      {
        "ErrorCode": 404,
        "ResponsePagePath": "/index.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 10
      }
    ]
  },
  "PriceClass": "PriceClass_100"
}
CFCONFIG

CF_DIST_ID=$(aws cloudfront create-distribution \
  --distribution-config file:///tmp/cf-config.json \
  --query 'Distribution.Id' --output text)
CF_DOMAIN=$(aws cloudfront get-distribution --id "${CF_DIST_ID}" \
  --query 'Distribution.DomainName' --output text)
echo "CloudFront Distribution: ${CF_DIST_ID}"
echo "CloudFront Domain: ${CF_DOMAIN}"

echo "=== Agregando bucket policy para OAC ==="
cat > /tmp/bucket-policy.json <<BPOLICY
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowCloudFrontOAC",
    "Effect": "Allow",
    "Principal": {"Service": "cloudfront.amazonaws.com"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::${S3_BUCKET}/*",
    "Condition": {
      "StringEquals": {
        "AWS:SourceArn": "arn:aws:cloudfront::${ACCOUNT_ID}:distribution/${CF_DIST_ID}"
      }
    }
  }]
}
BPOLICY
aws s3api put-bucket-policy --bucket "${S3_BUCKET}" --policy file:///tmp/bucket-policy.json

echo ""
echo "============================================"
echo " DESPLIEGUE COMPLETADO"
echo "============================================"
echo "URL de la aplicacion: https://${CF_DOMAIN}"
echo ""
echo "La distribucion puede tardar 5-15 minutos en propagarse."
echo "============================================"

cat >> "${SCRIPT_DIR}/.env.deploy" <<EOF
S3_BUCKET=${S3_BUCKET}
CF_DIST_ID=${CF_DIST_ID}
CF_DOMAIN=${CF_DOMAIN}
EOF

rm -f /tmp/cf-config.json /tmp/bucket-policy.json
