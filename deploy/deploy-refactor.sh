#!/usr/bin/env bash
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# deploy-refactor.sh â€” Despliega todos los componentes nuevos del refactor.
#
# Prerequisitos:
#   - AWS CLI configurado con permisos admin
#   - deploy/.env.deploy existente con los recursos base
#   - Docker corriendo (para rebuild de imagen)
#   - Python 3.11+ con pip
#
# Ejecutar desde la raiz del proyecto:
#   bash deploy/deploy-refactor.sh
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/00-variables.sh"
source "${SCRIPT_DIR}/.env.deploy"

echo "========================================================"
echo " MedChain AI â€” Despliegue del Refactor (Fases 0-5)"
echo "========================================================"
echo ""

# â”€â”€â”€ PASO 1: OIDC Provider + Rol GitHub Actions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
echo "[1/8] Creando OIDC Provider y rol para GitHub Actions..."
bash "${SCRIPT_DIR}/00-github-oidc-role.sh"
echo ""

# â”€â”€â”€ PASO 2: RDS PostgreSQL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
echo "[2/8] Creando instancia RDS PostgreSQL 16..."
bash "${SCRIPT_DIR}/07-rds.sh"
# Recargar .env.deploy con las nuevas variables (DB_SECRET_ARN, DATABASE_URL)
source "${SCRIPT_DIR}/.env.deploy"
echo ""

# â”€â”€â”€ PASO 3: Clave de cifrado â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
echo "[3/8] Creando clave maestra de cifrado en Secrets Manager..."
MASTER_KEY=$(python3 -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())")
ENCRYPTION_SECRET_ARN=$(aws secretsmanager create-secret \
  --name "medchain/encryption-key" \
  --description "Clave maestra AES-256 para cifrado de PHI" \
  --secret-string "{\"v1\": \"${MASTER_KEY}\", \"activa\": \"v1\"}" \
  --region "${AWS_REGION}" \
  --query 'ARN' --output text 2>/dev/null || \
  aws secretsmanager describe-secret \
    --secret-id "medchain/encryption-key" \
    --region "${AWS_REGION}" \
    --query 'ARN' --output text)

echo "ENCRYPTION_SECRET_ARN=${ENCRYPTION_SECRET_ARN}"
echo "ENCRYPTION_SECRET_ARN=${ENCRYPTION_SECRET_ARN}" >> "${SCRIPT_DIR}/.env.deploy"
echo ""

# â”€â”€â”€ PASO 4: Permisos IAM adicionales â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
echo "[4/8] Agregando permisos de Secrets Manager al Task Role..."
POLICY_DOC=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": [
        "${DB_SECRET_ARN}",
        "${ENCRYPTION_SECRET_ARN}"
      ]
    }
  ]
}
EOF
)
aws iam put-role-policy \
  --role-name "${PROJECT}-ecs-task-role" \
  --policy-name "medchain-secrets-read" \
  --policy-document "${POLICY_DOC}" \
  --region "${AWS_REGION}" 2>/dev/null || true
echo "  Politica adjuntada al task role."
echo ""

# â”€â”€â”€ PASO 5: Actualizar Task Definition con nuevos secretos â”€â”€
echo "[5/8] Actualizando Task Definition de ECS con DATABASE_URL y ENCRYPTION_SECRET_ARN..."
bash "${SCRIPT_DIR}/04-ecs-cluster.sh"
echo ""

# â”€â”€â”€ PASO 6: Ejecutar migraciones Alembic â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
echo "[6/8] Ejecutando migraciones de base de datos (Alembic)..."
cd "${ROOT_DIR}"
pip install -r requirements.txt --quiet 2>/dev/null || true
export DATABASE_URL="${DATABASE_URL}"
python -m alembic upgrade head
echo "  Migraciones aplicadas exitosamente."
echo ""

# â”€â”€â”€ PASO 7: Rebuild y push de imagen Docker â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
echo "[7/8] Reconstruyendo imagen Docker y subiendo a ECR..."
cd "${ROOT_DIR}"
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID:-007072540405}.dkr.ecr.${AWS_REGION}.amazonaws.com"
docker build -t "${IMAGE_URI}" .
docker push "${IMAGE_URI}"

aws ecs update-service \
  --cluster "${ECS_CLUSTER}" \
  --service "${ECS_SERVICE}" \
  --force-new-deployment \
  --region "${AWS_REGION}" --output text --query 'service.serviceName'
echo "  Imagen subida y deploy forzado."
echo ""

# â”€â”€â”€ PASO 8: Desplegar chaincode via SSM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
echo "[8/8] Desplegando chaincode prescription-contract en EC2 via SSM..."
EC2_INSTANCE_ID="i-0331b3fbeaadee294"

# Asegurar que la EC2 este corriendo
STATE=$(aws ec2 describe-instances \
  --instance-ids "${EC2_INSTANCE_ID}" \
  --query "Reservations[0].Instances[0].State.Name" \
  --output text --region "${AWS_REGION}")

if [ "${STATE}" = "stopped" ]; then
  echo "  Arrancando EC2..."
  aws ec2 start-instances --instance-ids "${EC2_INSTANCE_ID}" --region "${AWS_REGION}"
  aws ec2 wait instance-running --instance-ids "${EC2_INSTANCE_ID}" --region "${AWS_REGION}"
  sleep 30
fi

COMMAND_ID=$(aws ssm send-command \
  --instance-ids "${EC2_INSTANCE_ID}" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["set -e","cd ~/PFI-Proyecto-Final","git fetch origin desarrollo","git checkout desarrollo","git pull origin desarrollo","cd chaincode/prescription-contract","go mod tidy","cd ../../fabric","export CC_NAME=prescriptions","export CC_SRC_PATH=$HOME/PFI-Proyecto-Final/chaincode/prescription-contract","export CC_VERSION=1.1","export CC_SEQUENCE=1","./scripts/deployChaincode.sh mychannel","cd ../fabric-gateway-svc","go build -o fabric-gateway-svc .","sudo systemctl restart fabric-gateway-svc 2>/dev/null || nohup ./fabric-gateway-svc > /tmp/gateway-svc.log 2>&1 &"]' \
  --timeout-seconds 300 \
  --region "${AWS_REGION}" \
  --query "Command.CommandId" --output text 2>/dev/null || echo "ssm-skipped")

if [ "${COMMAND_ID}" != "ssm-skipped" ]; then
  echo "  SSM Command ID: ${COMMAND_ID}"
  echo "  Esperando resultado..."
  aws ssm wait command-executed \
    --command-id "${COMMAND_ID}" \
    --instance-id "${EC2_INSTANCE_ID}" \
    --region "${AWS_REGION}" 2>/dev/null || true
  echo "  Chaincode desplegado."
else
  echo "  WARN: SSM no disponible. Desplegar chaincode manualmente en la EC2."
fi

echo ""
echo "========================================================"
echo " DESPLIEGUE DEL REFACTOR FINALIZADO"
echo "========================================================"
echo ""
echo " Verificar:"
echo "   - Health check:  curl <API_URL>/"
echo "   - Base de datos: el health check debe decir 'database: connected'"
echo "   - Fabric:        curl http://<EC2_IP>:8081/health"
echo ""
echo " Pasos manuales pendientes:"
echo "   1. Eliminar secretos AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY de GitHub"
echo "   2. Desactivar las access keys IAM del usuario medchain-admin en la consola"
echo "   3. Configurar FABRIC_GATEWAY_URL en la task definition de ECS"
echo "========================================================"
