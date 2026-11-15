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

# El execution role es el que resuelve el bloque "secrets" de la task definition
# AL ARRANCAR la task. 04-ecs-cluster.sh toma DATABASE_URL de ${DB_SECRET_ARN},
# que es un secreto DISTINTO de ${SECRET_ARN}: si no esta en esta policy, la task
# no arranca ("ResourceInitializationError: unable to pull secrets").
# DB_SECRET_ARN lo escribe 07-rds.sh, que corre despues que este script; por eso
# se agrega solo si ya existe y hay que RE-EJECUTAR 03 despues de 07.
SECRET_RESOURCES="\"${SECRET_ARN}\""
if [ -n "${DB_SECRET_ARN:-}" ]; then
  SECRET_RESOURCES="${SECRET_RESOURCES}, \"${DB_SECRET_ARN}\""
else
  echo "AVISO: DB_SECRET_ARN no esta en .env.deploy todavia."
  echo "       Volve a correr 03-secrets-iam.sh DESPUES de 07-rds.sh,"
  echo "       o la task ECS no va a poder resolver DATABASE_URL."
fi
# Secreto TLS (FABRIC_GATEWAY_CA_PEM y, con dominio, TLS_CERT_PEM/TLS_KEY_PEM):
# tambien lo resuelve el execution role al arrancar la task.
TLS_SECRET_ARN=$(aws secretsmanager describe-secret --secret-id "${TLS_SECRET_NAME}" \
  --region "${AWS_REGION}" --query 'ARN' --output text 2>/dev/null || echo "")
if [ -n "${TLS_SECRET_ARN}" ]; then
  SECRET_RESOURCES="${SECRET_RESOURCES}, \"${TLS_SECRET_ARN}\""
else
  echo "AVISO: no existe ${TLS_SECRET_NAME}; crearlo con la CA del puente"
  echo "       (fabric/network/gateway-tls/ca.crt) y re-ejecutar este script."
fi

cat > /tmp/secrets-policy.json <<SECRETS
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "secretsmanager:GetSecretValue"
    ],
    "Resource": [${SECRET_RESOURCES}]
  }]
}
SECRETS

aws iam put-role-policy \
  --role-name "${EXEC_ROLE_NAME}" \
  --policy-name "${PROJECT}-read-secrets" \
  --policy-document file:///tmp/secrets-policy.json

echo "EXEC_ROLE_ARN=${EXEC_ROLE_ARN}"

echo "=== Creando task role (permisos de la app en runtime) ==="
TASK_ROLE_NAME="${PROJECT}-ecs-task-role"
TASK_ROLE_ARN=$(aws iam create-role \
  --role-name "${TASK_ROLE_NAME}" \
  --assume-role-policy-document file:///tmp/trust-policy.json \
  --query 'Role.Arn' --output text 2>/dev/null || \
  aws iam get-role --role-name "${TASK_ROLE_NAME}" --query 'Role.Arn' --output text)
echo "TASK_ROLE_ARN=${TASK_ROLE_ARN}"

# A diferencia de los demas secretos, ENCRYPTION_SECRET_ARN NO se inyecta como
# "secrets" de la task definition: se pasa como env var y la app lo lee sola en
# runtime (backend/security/key_manager.py). Por eso el permiso va al TASK role,
# no al execution role.
if [ -n "${ENCRYPTION_SECRET_ARN:-}" ]; then
  cat > /tmp/encryption-policy.json <<ENCPOL
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["secretsmanager:GetSecretValue"],
    "Resource": "${ENCRYPTION_SECRET_ARN}"
  }]
}
ENCPOL
  aws iam put-role-policy \
    --role-name "${TASK_ROLE_NAME}" \
    --policy-name "AllowEncryptionKeyRead" \
    --policy-document file:///tmp/encryption-policy.json
  echo "Task role con acceso a ${ENCRYPTION_SECRET_ARN}"
else
  echo "AVISO: ENCRYPTION_SECRET_ARN no definido: el cifrado de PHI va a fallar"
  echo "       en la primera operacion con pacientes (falla lazy, no al arrancar)."
fi

cat >> "${SCRIPT_DIR}/.env.deploy" <<EOF
SECRET_ARN=${SECRET_ARN}
TLS_SECRET_ARN=${TLS_SECRET_ARN}
EXEC_ROLE_ARN=${EXEC_ROLE_ARN}
TASK_ROLE_ARN=${TASK_ROLE_ARN}
EOF
echo "ARNs guardados en deploy/.env.deploy"

rm -f /tmp/trust-policy.json /tmp/secrets-policy.json /tmp/encryption-policy.json
