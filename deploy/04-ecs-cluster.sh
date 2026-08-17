#!/usr/bin/env bash
# Paso 4: Crear cluster ECS, Cloud Map namespace, task definition y service.
# Prerequisito: pasos 01-03 ejecutados.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/00-variables.sh"
source "${SCRIPT_DIR}/.env.deploy"

# Las prescripciones viven exclusivamente en Fabric: el backend exige estas
# variables en production (fail-fast). FABRIC_GATEWAY_URL apunta al puente en
# la EC2 (IP privada, puerto 8081); GATEWAY_AUTH_TOKEN debe existir como clave
# dentro del secreto ${SECRET_ARN} y coincidir con fabric/network/.env de la EC2.
: "${FABRIC_GATEWAY_URL:?Definir FABRIC_GATEWAY_URL en .env.deploy (ej: http://10.0.x.x:8081)}"

echo "=== Creando Cloud Map namespace ==="
NAMESPACE_OP=$(aws servicediscovery create-http-namespace \
  --name "${CLOUDMAP_NAMESPACE}" \
  --region "${AWS_REGION}" \
  --query 'OperationId' --output text 2>/dev/null || echo "exists")

if [ "${NAMESPACE_OP}" != "exists" ]; then
  echo "Esperando a que se cree el namespace..."
  sleep 10
fi

NAMESPACE_ID=$(aws servicediscovery list-namespaces --region "${AWS_REGION}" \
  --query "Namespaces[?Name=='${CLOUDMAP_NAMESPACE}'].Id" --output text)
echo "NAMESPACE_ID=${NAMESPACE_ID}"

echo "=== Creando cluster ECS ==="
aws ecs create-cluster --cluster-name "${ECS_CLUSTER}" --region "${AWS_REGION}" \
  --query 'cluster.clusterArn' --output text

echo "=== Creando log group ==="
aws logs create-log-group --log-group-name "/ecs/${ECS_TASK_FAMILY}" \
  --region "${AWS_REGION}" 2>/dev/null || true

echo "=== Registrando task definition ==="
cat > /tmp/task-def.json <<TASKDEF
{
  "family": "${ECS_TASK_FAMILY}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "${TASK_CPU}",
  "memory": "${TASK_MEMORY}",
  "executionRoleArn": "${EXEC_ROLE_ARN}",
  "taskRoleArn": "${TASK_ROLE_ARN}",
  "containerDefinitions": [
    {
      "name": "${PROJECT}-backend",
      "image": "${IMAGE_URI}",
      "essential": true,
      "portMappings": [
        {
          "containerPort": ${CONTAINER_PORT},
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "FABRIC_GATEWAY_URL", "value": "${FABRIC_GATEWAY_URL}"}
      ],
      "secrets": [
        {"name": "AUTH_USERNAME",     "valueFrom": "${SECRET_ARN}:AUTH_USERNAME::"},
        {"name": "AUTH_PASSWORD",     "valueFrom": "${SECRET_ARN}:AUTH_PASSWORD::"},
        {"name": "AUTH_DISPLAY_NAME", "valueFrom": "${SECRET_ARN}:AUTH_DISPLAY_NAME::"},
        {"name": "DATABASE_URL",     "valueFrom": "${DB_SECRET_ARN}:DATABASE_URL::"},
        {"name": "GATEWAY_AUTH_TOKEN", "valueFrom": "${SECRET_ARN}:GATEWAY_AUTH_TOKEN::"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/${ECS_TASK_FAMILY}",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "backend"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/')\""],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 90
      }
    }
  ]
}
TASKDEF

TASK_DEF_ARN=$(aws ecs register-task-definition \
  --cli-input-json file:///tmp/task-def.json \
  --region "${AWS_REGION}" \
  --query 'taskDefinition.taskDefinitionArn' --output text)
echo "TASK_DEF_ARN=${TASK_DEF_ARN}"

echo "=== Creando servicio ECS con Cloud Map ==="
aws ecs create-service \
  --cluster "${ECS_CLUSTER}" \
  --service-name "${ECS_SERVICE}" \
  --task-definition "${TASK_DEF_ARN}" \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_A},${SUBNET_B}],securityGroups=[${SG_ECS}],assignPublicIp=ENABLED}" \
  --service-registries "registryArn=$(aws servicediscovery create-service \
    --name "${CLOUDMAP_SERVICE}" \
    --namespace-id "${NAMESPACE_ID}" \
    --dns-config "NamespaceId=${NAMESPACE_ID},DnsRecords=[{Type=A,TTL=10}]" \
    --region "${AWS_REGION}" \
    --query 'Service.Arn' --output text 2>/dev/null || \
    aws servicediscovery list-services --region "${AWS_REGION}" \
    --query \"Services[?Name=='${CLOUDMAP_SERVICE}'].Arn\" --output text)" \
  --region "${AWS_REGION}" \
  --query 'service.serviceArn' --output text

echo ""
echo "=== Servicio ECS creado. Esperando a que la task inicie... ==="
aws ecs wait services-stable --cluster "${ECS_CLUSTER}" --services "${ECS_SERVICE}" --region "${AWS_REGION}" || true

TASK_ARN=$(aws ecs list-tasks --cluster "${ECS_CLUSTER}" --service-name "${ECS_SERVICE}" \
  --region "${AWS_REGION}" --query 'taskArns[0]' --output text)
echo "Task corriendo: ${TASK_ARN}"

cat >> "${SCRIPT_DIR}/.env.deploy" <<EOF
NAMESPACE_ID=${NAMESPACE_ID}
TASK_DEF_ARN=${TASK_DEF_ARN}
EOF

rm -f /tmp/task-def.json
