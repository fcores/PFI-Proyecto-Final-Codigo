#!/usr/bin/env bash
# Variables compartidas entre los scripts de despliegue.
# Editar los valores antes de ejecutar los scripts.

export AWS_REGION="us-east-1"
export PROJECT="medchain"

# VPC / Red
export VPC_CIDR="10.0.0.0/16"
export SUBNET_A_CIDR="10.0.1.0/24"
export SUBNET_B_CIDR="10.0.2.0/24"

# ECR
export ECR_REPO="${PROJECT}-backend"

# ECS
export ECS_CLUSTER="${PROJECT}-cluster"
export ECS_SERVICE="${PROJECT}-backend-svc"
export ECS_TASK_FAMILY="${PROJECT}-backend"
export CONTAINER_PORT=8000
export TASK_CPU=256
export TASK_MEMORY=512

# Cloud Map
export CLOUDMAP_NAMESPACE="${PROJECT}.local"
export CLOUDMAP_SERVICE="${PROJECT}-backend"

# API Gateway
export APIGW_NAME="${PROJECT}-api"

# S3 / CloudFront
export S3_BUCKET="${PROJECT}-frontend-$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo 'ACCOUNT_ID')"

# Secrets Manager
export SECRET_NAME="${PROJECT}/auth-credentials"

# Auth credentials (se suben a Secrets Manager, NO al contenedor directamente)
export AUTH_USERNAME="admin"
export AUTH_PASSWORD="admin123"
export AUTH_DISPLAY_NAME="Administrador"
