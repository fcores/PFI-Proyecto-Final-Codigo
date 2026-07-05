#!/usr/bin/env bash
# Paso 3: Crear secreto en Secrets Manager y roles IAM para ECS.
# Prerequisito: pasos 01 y 02 ejecutados.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/00-variables.sh"
source "${SCRIPT_DIR}/.env.deploy"

echo "=== Creando secreto en Secrets Manager ==="
SECRET_ARN=$(aws secretsmanager create-secret \
  --name "${SECRET_NAME}" \
  --description "Credenciales de auth para MedChain" \
  --secret-string "{\"AUTH_USERNAME\":\"${AUTH_USERNAME}\",\"AUTH_PASSWORD\":\"${AUTH_PASSWORD}\",\"AUTH_DISPLAY_NAME\":\"${AUTH_DISPLAY_NAME}\"}" \
  --region "${AWS_REGION}" \
  --query 'ARN' --output text 2>/dev/null || \
  aws secretsmanager describe-secret \
    --secret-id "${SECRET_NAME}" \
    --region "${AWS_REGION}" \
    --query 'ARN' --output text)
echo "SECRET_ARN=${SECRET_ARN}"

echo "=== Creando execution role (pull ECR + leer secrets + logs) ==="
EXEC_ROLE_NAME="${PROJECT}-ecs-execution-role"

cat > /tmp/trust-policy.json <<'TRUST'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ecs-tasks.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
TRUST

EXEC_ROLE_ARN=$(aws iam create-role \
  --role-name "${EXEC_ROLE_NAME}" \
  --assume-role-policy-document file:///tmp/trust-policy.json \
  --query 'Role.Arn' --output text 2>/dev/null || \
  aws iam get-role --role-name "${EXEC_ROLE_NAME}" --query 'Role.Arn' --output text)

aws iam attach-role-policy --role-name "${EXEC_ROLE_NAME}" \
  --policy-arn "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"

cat > /tmp/secrets-policy.json <<SECRETS
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "secretsmanager:GetSecretValue"
    ],
    "Resource": "${SECRET_ARN}"
  }]
}
SECRETS

aws iam put-role-policy \
  --role-name "${EXEC_ROLE_NAME}" \
  --policy-name "${PROJECT}-read-secrets" \
  --policy-document file:///tmp/secrets-policy.json

echo "EXEC_ROLE_ARN=${EXEC_ROLE_ARN}"

echo "=== Creando task role (permisos de la app, vacio por ahora) ==="
TASK_ROLE_NAME="${PROJECT}-ecs-task-role"
TASK_ROLE_ARN=$(aws iam create-role \
  --role-name "${TASK_ROLE_NAME}" \
  --assume-role-policy-document file:///tmp/trust-policy.json \
  --query 'Role.Arn' --output text 2>/dev/null || \
  aws iam get-role --role-name "${TASK_ROLE_NAME}" --query 'Role.Arn' --output text)
echo "TASK_ROLE_ARN=${TASK_ROLE_ARN}"

cat >> "${SCRIPT_DIR}/.env.deploy" <<EOF
SECRET_ARN=${SECRET_ARN}
EXEC_ROLE_ARN=${EXEC_ROLE_ARN}
TASK_ROLE_ARN=${TASK_ROLE_ARN}
EOF
echo "ARNs guardados en deploy/.env.deploy"

rm -f /tmp/trust-policy.json /tmp/secrets-policy.json
