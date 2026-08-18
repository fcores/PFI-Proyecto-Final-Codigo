#!/usr/bin/env bash
# Paso 5: Crear API Gateway HTTP API + VPC Link apuntando al Cloud Map service.
# Prerequisito: pasos 01-04 ejecutados.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/00-variables.sh"
source "${SCRIPT_DIR}/.env.deploy"

echo "=== Creando VPC Link para API Gateway ==="
VPCLINK_ID=$(aws apigatewayv2 create-vpc-link \
  --name "${PROJECT}-vpclink" \
  --subnet-ids "${SUBNET_A}" "${SUBNET_B}" \
  --security-group-ids "${SG_ECS}" \
  --region "${AWS_REGION}" \
  --query 'VpcLinkId' --output text)
echo "VPC Link: ${VPCLINK_ID}"

echo "Esperando a que el VPC Link este disponible..."
while true; do
  STATUS=$(aws apigatewayv2 get-vpc-link --vpc-link-id "${VPCLINK_ID}" \
    --region "${AWS_REGION}" --query 'VpcLinkStatus' --output text)
  echo "  Status: ${STATUS}"
  if [ "${STATUS}" = "AVAILABLE" ]; then break; fi
  sleep 10
done

echo "=== Obteniendo Cloud Map service ARN ==="
# CRITICO: tiene que ser EXACTAMENTE el service donde ECS auto-registra las
# tasks (el que 04-ecs-cluster.sh pasa en --service-registries). Si apunta a
# otro, API Gateway resuelve IPs muertas y devuelve 503 en TODAS las rutas.
#
# list-services SIN filtro de namespace devuelve servicios homonimos de otros
# namespaces; con --output text salen separados por tab y el ARN queda corrupto.
# Por eso: filtrar por NAMESPACE_ID y tomar | [0].
if [ -n "${CLOUDMAP_SVC_ARN:-}" ]; then
  echo "Reutilizando CLOUDMAP_SVC_ARN de .env.deploy"
else
  NS_ID="${NAMESPACE_ID:-$(aws servicediscovery list-namespaces --region "${AWS_REGION}" \
    --query "Namespaces[?Name=='${CLOUDMAP_NAMESPACE}'].Id | [0]" --output text)}"
  CLOUDMAP_SVC_ARN=$(aws servicediscovery list-services --region "${AWS_REGION}" \
    --filters "Name=NAMESPACE_ID,Values=${NS_ID},Condition=EQ" \
    --query "Services[?Name=='${CLOUDMAP_SERVICE}'].Arn | [0]" --output text)
fi

if [ -z "${CLOUDMAP_SVC_ARN}" ] || [ "${CLOUDMAP_SVC_ARN}" = "None" ]; then
  echo "ERROR: no se encontro el Cloud Map service '${CLOUDMAP_SERVICE}'." >&2
  echo "       Corre 04-ecs-cluster.sh primero." >&2
  exit 1
fi
echo "Cloud Map Service: ${CLOUDMAP_SVC_ARN}"

# Chequeo de coherencia: el service elegido debe ser el mismo que usa el ECS
# service. Si divergen, el API Gateway queda roto de entrada.
ECS_REGISTRY_ARN=$(aws ecs describe-services --cluster "${ECS_CLUSTER}" \
  --services "${ECS_SERVICE}" --region "${AWS_REGION}" \
  --query 'services[0].serviceRegistries[0].registryArn' --output text 2>/dev/null || echo "")
if [ -n "${ECS_REGISTRY_ARN}" ] && [ "${ECS_REGISTRY_ARN}" != "None" ] \
   && [ "${ECS_REGISTRY_ARN}" != "${CLOUDMAP_SVC_ARN}" ]; then
  echo "ERROR: el Cloud Map service no coincide con el que usa ECS." >&2
  echo "  ECS registra en: ${ECS_REGISTRY_ARN}" >&2
  echo "  API GW usaria:   ${CLOUDMAP_SVC_ARN}" >&2
  exit 1
fi

echo "=== Creando HTTP API ==="
API_ID=$(aws apigatewayv2 create-api \
  --name "${APIGW_NAME}" \
  --protocol-type HTTP \
  --region "${AWS_REGION}" \
  --query 'ApiId' --output text)
echo "API ID: ${API_ID}"

echo "=== Creando integracion VPC Link -> Cloud Map ==="
INTEGRATION_ID=$(aws apigatewayv2 create-integration \
  --api-id "${API_ID}" \
  --integration-type HTTP_PROXY \
  --integration-method ANY \
  --integration-uri "${CLOUDMAP_SVC_ARN}" \
  --connection-type VPC_LINK \
  --connection-id "${VPCLINK_ID}" \
  --payload-format-version "1.0" \
  --region "${AWS_REGION}" \
  --query 'IntegrationId' --output text)
echo "Integration: ${INTEGRATION_ID}"

echo "=== Creando ruta catch-all ==="
aws apigatewayv2 create-route \
  --api-id "${API_ID}" \
  --route-key 'ANY /{proxy+}' \
  --target "integrations/${INTEGRATION_ID}" \
  --region "${AWS_REGION}" \
  --query 'RouteId' --output text

aws apigatewayv2 create-route \
  --api-id "${API_ID}" \
  --route-key 'ANY /' \
  --target "integrations/${INTEGRATION_ID}" \
  --region "${AWS_REGION}" \
  --query 'RouteId' --output text

echo "=== Creando stage \$default con auto-deploy ==="
aws apigatewayv2 create-stage \
  --api-id "${API_ID}" \
  --stage-name '$default' \
  --auto-deploy \
  --region "${AWS_REGION}"

APIGW_ENDPOINT=$(aws apigatewayv2 get-api --api-id "${API_ID}" \
  --region "${AWS_REGION}" --query 'ApiEndpoint' --output text)
echo ""
echo "=== API Gateway disponible ==="
echo "APIGW_ENDPOINT=${APIGW_ENDPOINT}"
echo "Probar: curl ${APIGW_ENDPOINT}/"

cat >> "${SCRIPT_DIR}/.env.deploy" <<EOF
VPCLINK_ID=${VPCLINK_ID}
API_ID=${API_ID}
APIGW_ENDPOINT=${APIGW_ENDPOINT}
EOF
