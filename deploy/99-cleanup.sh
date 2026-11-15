#!/usr/bin/env bash
# Limpieza: eliminar todos los recursos AWS creados por los scripts de deploy.
# Ejecutar SOLO si queres borrar todo.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/00-variables.sh"
source "${SCRIPT_DIR}/.env.deploy" 2>/dev/null || true

echo "=== ATENCION: Esto eliminara TODOS los recursos de ${PROJECT} en AWS ==="
read -p "Escribi 'BORRAR' para continuar: " CONFIRM
if [ "${CONFIRM}" != "BORRAR" ]; then echo "Cancelado."; exit 1; fi

echo "--- Deshabilitando CloudFront ---"
if [ -n "${CF_DIST_ID:-}" ]; then
  ETAG=$(aws cloudfront get-distribution-config --id "${CF_DIST_ID}" --query 'ETag' --output text)
  aws cloudfront get-distribution-config --id "${CF_DIST_ID}" --output json | \
    python3 -c "import sys,json; c=json.load(sys.stdin)['DistributionConfig']; c['Enabled']=False; json.dump(c,sys.stdout)" > /tmp/cf-disable.json
  aws cloudfront update-distribution --id "${CF_DIST_ID}" --if-match "${ETAG}" \
    --distribution-config file:///tmp/cf-disable.json 2>/dev/null || true
  echo "Esperando a que se deshabilite (puede tardar minutos)..."
  aws cloudfront wait distribution-deployed --id "${CF_DIST_ID}" 2>/dev/null || true
  ETAG=$(aws cloudfront get-distribution-config --id "${CF_DIST_ID}" --query 'ETag' --output text)
  aws cloudfront delete-distribution --id "${CF_DIST_ID}" --if-match "${ETAG}" 2>/dev/null || true
  rm -f /tmp/cf-disable.json
fi

echo "--- Vaciando y eliminando S3 ---"
aws s3 rm "s3://${S3_BUCKET:-noop}" --recursive 2>/dev/null || true
aws s3api delete-bucket --bucket "${S3_BUCKET:-noop}" --region "${AWS_REGION}" 2>/dev/null || true

echo "--- Eliminando servicio ECS ---"
aws ecs update-service --cluster "${ECS_CLUSTER}" --service "${ECS_SERVICE}" \
  --desired-count 0 --region "${AWS_REGION}" 2>/dev/null || true
aws ecs delete-service --cluster "${ECS_CLUSTER}" --service "${ECS_SERVICE}" \
  --force --region "${AWS_REGION}" 2>/dev/null || true

echo "--- Eliminando cluster ECS ---"
aws ecs delete-cluster --cluster "${ECS_CLUSTER}" --region "${AWS_REGION}" 2>/dev/null || true

echo "--- Eliminando API Gateway ---"
if [ -n "${API_ID:-}" ]; then
  aws apigatewayv2 delete-api --api-id "${API_ID}" --region "${AWS_REGION}" 2>/dev/null || true
fi

echo "--- Eliminando VPC Link ---"
if [ -n "${VPCLINK_ID:-}" ]; then
  aws apigatewayv2 delete-vpc-link --vpc-link-id "${VPCLINK_ID}" --region "${AWS_REGION}" 2>/dev/null || true
fi

echo "--- Eliminando Cloud Map ---"
CLOUDMAP_SVC_ID=$(aws servicediscovery list-services --region "${AWS_REGION}" \
  --query "Services[?Name=='${CLOUDMAP_SERVICE}'].Id" --output text 2>/dev/null || echo "")
if [ -n "${CLOUDMAP_SVC_ID}" ]; then
  aws servicediscovery delete-service --id "${CLOUDMAP_SVC_ID}" --region "${AWS_REGION}" 2>/dev/null || true
fi
if [ -n "${NAMESPACE_ID:-}" ]; then
  aws servicediscovery delete-namespace --id "${NAMESPACE_ID}" --region "${AWS_REGION}" 2>/dev/null || true
fi

echo "--- Eliminando secreto ---"
aws secretsmanager delete-secret --secret-id "${SECRET_NAME}" \
  --force-delete-without-recovery --region "${AWS_REGION}" 2>/dev/null || true

echo "--- Eliminando roles IAM ---"
for ROLE in "${PROJECT}-ecs-execution-role" "${PROJECT}-ecs-task-role"; do
  for POLICY_ARN in $(aws iam list-attached-role-policies --role-name "${ROLE}" \
    --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null); do
    aws iam detach-role-policy --role-name "${ROLE}" --policy-arn "${POLICY_ARN}" 2>/dev/null || true
  done
  for POLICY_NAME in $(aws iam list-role-policies --role-name "${ROLE}" \
    --query 'PolicyNames[]' --output text 2>/dev/null); do
    aws iam delete-role-policy --role-name "${ROLE}" --policy-name "${POLICY_NAME}" 2>/dev/null || true
  done
  aws iam delete-role --role-name "${ROLE}" 2>/dev/null || true
done

echo "--- Eliminando repositorio ECR ---"
aws ecr delete-repository --repository-name "${ECR_REPO}" --force --region "${AWS_REGION}" 2>/dev/null || true

echo "--- Eliminando VPC y componentes ---"
if [ -n "${SG_ECS:-}" ]; then
  aws ec2 delete-security-group --group-id "${SG_ECS}" --region "${AWS_REGION}" 2>/dev/null || true
fi
if [ -n "${SUBNET_A:-}" ]; then
  aws ec2 delete-subnet --subnet-id "${SUBNET_A}" --region "${AWS_REGION}" 2>/dev/null || true
fi
if [ -n "${SUBNET_B:-}" ]; then
  aws ec2 delete-subnet --subnet-id "${SUBNET_B}" --region "${AWS_REGION}" 2>/dev/null || true
fi
if [ -n "${IGW_ID:-}" ] && [ -n "${VPC_ID:-}" ]; then
  aws ec2 detach-internet-gateway --internet-gateway-id "${IGW_ID}" --vpc-id "${VPC_ID}" --region "${AWS_REGION}" 2>/dev/null || true
  aws ec2 delete-internet-gateway --internet-gateway-id "${IGW_ID}" --region "${AWS_REGION}" 2>/dev/null || true
fi
if [ -n "${VPC_ID:-}" ]; then
  aws ec2 delete-vpc --vpc-id "${VPC_ID}" --region "${AWS_REGION}" 2>/dev/null || true
fi

echo ""
echo "=== Limpieza completada ==="
rm -f "${SCRIPT_DIR}/.env.deploy"
