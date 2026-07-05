#!/usr/bin/env bash
# Paso 2: Crear repositorio ECR, construir la imagen Docker y subirla.
# Prerequisito: Docker corriendo, paso 01 ejecutado.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/00-variables.sh"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "=== Creando repositorio ECR ==="
aws ecr create-repository \
  --repository-name "${ECR_REPO}" \
  --region "${AWS_REGION}" 2>/dev/null || echo "Repositorio ya existe."

echo "=== Login en ECR ==="
aws ecr get-login-password --region "${AWS_REGION}" | \
  docker login --username AWS --password-stdin "${ECR_URI}"

echo "=== Construyendo imagen Docker ==="
cd "${SCRIPT_DIR}/.."
docker build -t "${ECR_REPO}:latest" .

echo "=== Tagueando y subiendo ==="
docker tag "${ECR_REPO}:latest" "${ECR_URI}/${ECR_REPO}:latest"
docker push "${ECR_URI}/${ECR_REPO}:latest"

IMAGE_URI="${ECR_URI}/${ECR_REPO}:latest"
echo ""
echo "=== Imagen subida ==="
echo "IMAGE_URI=${IMAGE_URI}"

echo "IMAGE_URI=${IMAGE_URI}" >> "${SCRIPT_DIR}/.env.deploy"
echo "ACCOUNT_ID=${ACCOUNT_ID}" >> "${SCRIPT_DIR}/.env.deploy"
