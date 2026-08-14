#!/usr/bin/env bash
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Crea el proveedor OIDC de GitHub y el rol IAM para GitHub Actions.
# Ejecutar una sola vez por cuenta AWS.
# Reemplaza el uso de access keys permanentes (AWS_ACCESS_KEY_ID/SECRET).
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/00-variables.sh"

GITHUB_ORG_REPO="fcores/PFI-Proyecto-Final"
ROLE_NAME="github-actions-deploy"

echo "=== Creando OIDC Provider de GitHub ==="
OIDC_ARN=$(aws iam list-open-id-connect-providers \
  --query "OpenIDConnectProviderList[?ends_with(Arn,'token.actions.githubusercontent.com')].Arn" \
  --output text 2>/dev/null || true)

if [ -z "$OIDC_ARN" ]; then
  THUMBPRINT="6938fd4d98bab03faadb97b34396831e3780aea1"
  OIDC_ARN=$(aws iam create-open-id-connect-provider \
    --url "https://token.actions.githubusercontent.com" \
    --client-id-list "sts.amazonaws.com" \
    --thumbprint-list "$THUMBPRINT" \
    --query "OpenIDConnectProviderArn" \
    --output text)
  echo "OIDC Provider creado: $OIDC_ARN"
else
  echo "OIDC Provider ya existe: $OIDC_ARN"
fi

echo "=== Creando rol IAM: $ROLE_NAME ==="
TRUST_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "$OIDC_ARN"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_ORG_REPO}:ref:refs/heads/desarrollo"
        }
      }
    }
  ]
}
EOF
)

if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  echo "Rol ya existe, actualizando trust policy..."
  aws iam update-assume-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-document "$TRUST_POLICY"
else
  aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document "$TRUST_POLICY" \
    --description "Rol para GitHub Actions deploy via OIDC"
  echo "Rol creado."
fi

echo "=== Adjuntando politicas necesarias ==="
POLICIES=(
  "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser"
  "arn:aws:iam::aws:policy/AmazonECS_FullAccess"
  "arn:aws:iam::aws:policy/AmazonS3FullAccess"
  "arn:aws:iam::aws:policy/CloudFrontFullAccess"
  "arn:aws:iam::aws:policy/AmazonSSMFullAccess"
  "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
)

for POLICY_ARN in "${POLICIES[@]}"; do
  aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn "$POLICY_ARN" 2>/dev/null || true
  echo "  Attached: $(basename "$POLICY_ARN")"
done

echo ""
echo "=== Listo ==="
echo "ARN del rol: arn:aws:iam::${AWS_ACCOUNT_ID:-007072540405}:role/$ROLE_NAME"
echo ""
echo "Proximos pasos:"
echo "  1. Ajustar GITHUB_ORG_REPO en este script al nombre real del repositorio."
echo "  2. Eliminar los secretos AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY de GitHub."
echo "  3. Rotar/eliminar las access keys IAM del usuario medchain-admin."
