#!/usr/bin/env bash
# Script maestro: ejecuta todos los pasos de despliegue en orden.
# Prerequisitos:
#   - AWS CLI instalado y configurado (aws configure)
#   - Docker corriendo
#   - Node.js y npm instalados
#   - Haber editado 00-variables.sh con tus valores
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo " MedChain AI — Despliegue completo en AWS"
echo "============================================"
echo ""

echo "[1/6] Creando VPC, subredes y Security Groups..."
bash "${SCRIPT_DIR}/01-vpc-network.sh"
echo ""

echo "[2/6] Construyendo imagen Docker y subiendo a ECR..."
bash "${SCRIPT_DIR}/02-ecr-push.sh"
echo ""

echo "[3/6] Creando secretos y roles IAM..."
bash "${SCRIPT_DIR}/03-secrets-iam.sh"
echo ""

echo "[4/6] Creando cluster ECS, task definition y servicio..."
bash "${SCRIPT_DIR}/04-ecs-cluster.sh"
echo ""

echo "[5/6] Creando API Gateway HTTP API + VPC Link..."
bash "${SCRIPT_DIR}/05-api-gateway.sh"
echo ""

echo "[6/6] Subiendo frontend a S3 y creando CloudFront..."
bash "${SCRIPT_DIR}/06-s3-cloudfront.sh"
echo ""

echo "============================================"
echo " DESPLIEGUE FINALIZADO"
echo "============================================"
source "${SCRIPT_DIR}/.env.deploy"
echo ""
echo "  App URL:     https://${CF_DOMAIN}"
echo "  API directo: ${APIGW_ENDPOINT}"
echo "  Health:      ${APIGW_ENDPOINT}/"
echo "  Swagger:     ${APIGW_ENDPOINT}/docs"
echo ""
echo "  La distribucion CloudFront puede tardar"
echo "  5-15 minutos en propagarse."
echo ""
echo "  Para limpiar todo: bash deploy/99-cleanup.sh"
echo "============================================"
