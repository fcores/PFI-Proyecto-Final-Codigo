#!/usr/bin/env bash
# Paso 1: Crear VPC, subredes publicas, Internet Gateway y Security Groups.
# Prerequisito: AWS CLI configurado (aws configure) y 00-variables.sh editado.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/00-variables.sh"

echo "=== Creando VPC ==="
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block "${VPC_CIDR}" \
  --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=${PROJECT}-vpc}]" \
  --query 'Vpc.VpcId' --output text --region "${AWS_REGION}")
echo "VPC: ${VPC_ID}"

aws ec2 modify-vpc-attribute --vpc-id "${VPC_ID}" --enable-dns-support --region "${AWS_REGION}"
aws ec2 modify-vpc-attribute --vpc-id "${VPC_ID}" --enable-dns-hostnames --region "${AWS_REGION}"

echo "=== Creando Internet Gateway ==="
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=${PROJECT}-igw}]" \
  --query 'InternetGateway.InternetGatewayId' --output text --region "${AWS_REGION}")
aws ec2 attach-internet-gateway --internet-gateway-id "${IGW_ID}" --vpc-id "${VPC_ID}" --region "${AWS_REGION}"
echo "IGW: ${IGW_ID}"

echo "=== Creando subredes publicas (2 AZs) ==="
AZS=($(aws ec2 describe-availability-zones --region "${AWS_REGION}" \
  --query 'AvailabilityZones[?State==`available`].ZoneName' --output text | head -c 50))
AZ_A="${AZS[0]}"
AZ_B="${AZS[1]}"

SUBNET_A=$(aws ec2 create-subnet \
  --vpc-id "${VPC_ID}" --cidr-block "${SUBNET_A_CIDR}" --availability-zone "${AZ_A}" \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${PROJECT}-public-a}]" \
  --query 'Subnet.SubnetId' --output text --region "${AWS_REGION}")

SUBNET_B=$(aws ec2 create-subnet \
  --vpc-id "${VPC_ID}" --cidr-block "${SUBNET_B_CIDR}" --availability-zone "${AZ_B}" \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${PROJECT}-public-b}]" \
  --query 'Subnet.SubnetId' --output text --region "${AWS_REGION}")

aws ec2 modify-subnet-attribute --subnet-id "${SUBNET_A}" --map-public-ip-on-launch --region "${AWS_REGION}"
aws ec2 modify-subnet-attribute --subnet-id "${SUBNET_B}" --map-public-ip-on-launch --region "${AWS_REGION}"
echo "Subnets: ${SUBNET_A}, ${SUBNET_B}"

echo "=== Ruta por defecto al IGW ==="
RTB_ID=$(aws ec2 describe-route-tables --filters "Name=vpc-id,Values=${VPC_ID}" \
  --query 'RouteTables[0].RouteTableId' --output text --region "${AWS_REGION}")
aws ec2 create-route --route-table-id "${RTB_ID}" --destination-cidr-block "0.0.0.0/0" \
  --gateway-id "${IGW_ID}" --region "${AWS_REGION}"

aws ec2 associate-route-table --route-table-id "${RTB_ID}" --subnet-id "${SUBNET_A}" --region "${AWS_REGION}" 2>/dev/null || true
aws ec2 associate-route-table --route-table-id "${RTB_ID}" --subnet-id "${SUBNET_B}" --region "${AWS_REGION}" 2>/dev/null || true

echo "=== Security Group para ECS ==="
SG_ECS=$(aws ec2 create-security-group \
  --group-name "${PROJECT}-ecs-sg" \
  --description "SG para tareas Fargate del backend" \
  --vpc-id "${VPC_ID}" \
  --query 'GroupId' --output text --region "${AWS_REGION}")

# Entrada al puerto de la app SOLO desde el propio SG: el VPC Link de API
# Gateway (05-api-gateway.sh) se crea con este mismo SG, asi que la regla
# autorreferenciada admite exactamente sus ENIs y nada mas. Nunca 0.0.0.0/0:
# las tareas tienen IP publica (assignPublicIp=ENABLED, para salir a ECR,
# Secrets Manager y CloudWatch sin NAT) y una regla abierta las expone a
# Internet salteando CloudFront y API Gateway.
aws ec2 authorize-security-group-ingress --group-id "${SG_ECS}" --region "${AWS_REGION}" \
  --ip-permissions "IpProtocol=tcp,FromPort=${CONTAINER_PORT},ToPort=${CONTAINER_PORT},UserIdGroupPairs=[{GroupId=${SG_ECS},Description='Solo desde el VPC Link de API Gateway'}]"

aws ec2 authorize-security-group-egress --group-id "${SG_ECS}" \
  --protocol "-1" --cidr "0.0.0.0/0" --region "${AWS_REGION}" 2>/dev/null || true
echo "SG ECS: ${SG_ECS}"

echo ""
echo "=== Guardar estos IDs para los siguientes pasos ==="
echo "VPC_ID=${VPC_ID}"
echo "SUBNET_A=${SUBNET_A}"
echo "SUBNET_B=${SUBNET_B}"
echo "SG_ECS=${SG_ECS}"

cat > "${SCRIPT_DIR}/.env.deploy" <<EOF
VPC_ID=${VPC_ID}
SUBNET_A=${SUBNET_A}
SUBNET_B=${SUBNET_B}
SG_ECS=${SG_ECS}
IGW_ID=${IGW_ID}
EOF
echo "IDs guardados en deploy/.env.deploy"
