#!/usr/bin/env bash
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Paso 7: Crear instancia RDS PostgreSQL 16 en subredes privadas.
# - Single-AZ db.t4g.micro (optimizado para costo academico)
# - storage_encrypted con clave por defecto de RDS
# - Backups automaticos 7 dias + PITR
# - Security Group que solo acepta trafico desde SG de ECS
# - Credenciales en Secrets Manager
# - TLS obligatorio (rds.force_ssl = 1)
# Prerequisito: pasos 01, 03 ejecutados (.env.deploy con SUBNET_A, SUBNET_B, SG_ECS)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/00-variables.sh"
source "${SCRIPT_DIR}/.env.deploy"

DB_INSTANCE_ID="${PROJECT}-db"
DB_NAME="medchain"
DB_USERNAME="medchain_app"
DB_PORT=5432
DB_SECRET_NAME="${PROJECT}/database-credentials"
SUBNET_GROUP_NAME="${PROJECT}-db-subnet-group"
SG_DB_NAME="${PROJECT}-db-sg"
PARAM_GROUP_NAME="${PROJECT}-pg16-params"

echo "=== Generando password aleatoria ==="
DB_PASSWORD=$(python3 -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(32)))")

echo "=== Creando Security Group para RDS ==="
SG_DB=$(aws ec2 create-security-group \
  --group-name "${SG_DB_NAME}" \
  --description "SG para RDS ${PROJECT} - solo acepta ECS" \
  --vpc-id "${VPC_ID}" \
  --region "${AWS_REGION}" \
  --query 'GroupId' --output text 2>/dev/null || \
  aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=${SG_DB_NAME}" "Name=vpc-id,Values=${VPC_ID}" \
    --region "${AWS_REGION}" \
    --query 'SecurityGroups[0].GroupId' --output text)

aws ec2 authorize-security-group-ingress \
  --group-id "${SG_DB}" \
  --protocol tcp --port ${DB_PORT} \
  --source-group "${SG_ECS}" \
  --region "${AWS_REGION}" 2>/dev/null || true

echo "SG_DB=${SG_DB}"

echo "=== Creando subnet group ==="
aws rds create-db-subnet-group \
  --db-subnet-group-name "${SUBNET_GROUP_NAME}" \
  --db-subnet-group-description "Subnets para RDS ${PROJECT}" \
  --subnet-ids "${SUBNET_A}" "${SUBNET_B}" \
  --region "${AWS_REGION}" 2>/dev/null || true

echo "=== Creando parameter group (force SSL) ==="
aws rds create-db-parameter-group \
  --db-parameter-group-name "${PARAM_GROUP_NAME}" \
  --db-parameter-group-family "postgres16" \
  --description "Parametros ${PROJECT}: SSL obligatorio" \
  --region "${AWS_REGION}" 2>/dev/null || true

aws rds modify-db-parameter-group \
  --db-parameter-group-name "${PARAM_GROUP_NAME}" \
  --parameters "ParameterName=rds.force_ssl,ParameterValue=1,ApplyMethod=pending-reboot" \
  --region "${AWS_REGION}"

echo "=== Creando instancia RDS ==="
aws rds create-db-instance \
  --db-instance-identifier "${DB_INSTANCE_ID}" \
  --db-instance-class "db.t4g.micro" \
  --engine "postgres" \
  --engine-version "16" \
  --master-username "${DB_USERNAME}" \
  --master-user-password "${DB_PASSWORD}" \
  --db-name "${DB_NAME}" \
  --allocated-storage 20 \
  --storage-type gp3 \
  --storage-encrypted \
  --db-subnet-group-name "${SUBNET_GROUP_NAME}" \
  --vpc-security-group-ids "${SG_DB}" \
  --db-parameter-group-name "${PARAM_GROUP_NAME}" \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --no-publicly-accessible \
  --no-multi-az \
  --port ${DB_PORT} \
  --region "${AWS_REGION}" \
  --tags "Key=Project,Value=${PROJECT}" \
  --query 'DBInstance.DBInstanceIdentifier' --output text

echo "Esperando a que la instancia estÃ© disponible (puede tardar 5-10 min)..."
aws rds wait db-instance-available \
  --db-instance-identifier "${DB_INSTANCE_ID}" \
  --region "${AWS_REGION}"

DB_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier "${DB_INSTANCE_ID}" \
  --region "${AWS_REGION}" \
  --query 'DBInstances[0].Endpoint.Address' --output text)

echo "RDS Endpoint: ${DB_ENDPOINT}"

DATABASE_URL="postgresql://${DB_USERNAME}:${DB_PASSWORD}@${DB_ENDPOINT}:${DB_PORT}/${DB_NAME}?sslmode=verify-full&sslrootcert=/usr/local/share/aws/rds-combined-ca-bundle.pem"

echo "=== Guardando credenciales en Secrets Manager ==="
aws secretsmanager create-secret \
  --name "${DB_SECRET_NAME}" \
  --description "Credenciales RDS para ${PROJECT}" \
  --secret-string "{\"username\":\"${DB_USERNAME}\",\"password\":\"${DB_PASSWORD}\",\"host\":\"${DB_ENDPOINT}\",\"port\":${DB_PORT},\"dbname\":\"${DB_NAME}\",\"DATABASE_URL\":\"${DATABASE_URL}\"}" \
  --region "${AWS_REGION}" 2>/dev/null || \
aws secretsmanager update-secret \
  --secret-id "${DB_SECRET_NAME}" \
  --secret-string "{\"username\":\"${DB_USERNAME}\",\"password\":\"${DB_PASSWORD}\",\"host\":\"${DB_ENDPOINT}\",\"port\":${DB_PORT},\"dbname\":\"${DB_NAME}\",\"DATABASE_URL\":\"${DATABASE_URL}\"}" \
  --region "${AWS_REGION}"

DB_SECRET_ARN=$(aws secretsmanager describe-secret \
  --secret-id "${DB_SECRET_NAME}" \
  --region "${AWS_REGION}" \
  --query 'ARN' --output text)

echo "DB_SECRET_ARN=${DB_SECRET_ARN}"

cat >> "${SCRIPT_DIR}/.env.deploy" <<EOF
SG_DB=${SG_DB}
DB_INSTANCE_ID=${DB_INSTANCE_ID}
DB_ENDPOINT=${DB_ENDPOINT}
DB_SECRET_ARN=${DB_SECRET_ARN}
DATABASE_URL=${DATABASE_URL}
EOF

echo ""
echo "=== RDS listo ==="
echo "Endpoint: ${DB_ENDPOINT}"
echo "Secret ARN: ${DB_SECRET_ARN}"
echo ""
echo "Para inyectar DATABASE_URL en ECS, actualizar la task definition con:"
echo '  {"name": "DATABASE_URL", "valueFrom": "'${DB_SECRET_ARN}':DATABASE_URL::"}'
