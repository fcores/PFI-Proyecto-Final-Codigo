# ──────────────────────────────────────────────────────────────
# deploy-refactor.ps1 — Despliega todos los componentes nuevos del refactor.
# Ejecutar desde PowerShell en la raiz del proyecto:
#   .\deploy\deploy-refactor.ps1
# ──────────────────────────────────────────────────────────────
$ErrorActionPreference = "Continue"
$ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ROOT

$AWS_REGION = "us-east-1"
$PROJECT = "medchain"
$AWS_ACCOUNT_ID = "007072540405"
$EC2_INSTANCE_ID = "i-0331b3fbeaadee294"

# Leer variables existentes
$VPC_ID = "vpc-0c98e7d7f299bf5e8"
$SUBNET_A = "subnet-0752770229746744b"
$SUBNET_B = "subnet-0d27ce970f3922eda"
$SG_ECS = "sg-08518301fe0009809"
$SECRET_ARN = "arn:aws:secretsmanager:us-east-1:007072540405:secret:medchain/auth-credentials-nOXEVU"
$EXEC_ROLE_ARN = "arn:aws:iam::007072540405:role/medchain-ecs-execution-role"
$TASK_ROLE_ARN = "arn:aws:iam::007072540405:role/medchain-ecs-task-role"
$IMAGE_URI = "007072540405.dkr.ecr.us-east-1.amazonaws.com/medchain-backend:latest"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " MedChain AI - Despliegue del Refactor (Fases 0-5)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# ─── PASO 1: OIDC Provider ───────────────────────────────────
Write-Host "[1/8] Creando OIDC Provider y rol para GitHub Actions..." -ForegroundColor Yellow

$OIDC_ARN = (aws iam list-open-id-connect-providers `
  --query "OpenIDConnectProviderList[?ends_with(Arn,'token.actions.githubusercontent.com')].Arn" `
  --output text 2>&1) | Where-Object { $_ -notmatch "^aws" -and $_.Trim() -ne "" } | Select-Object -First 1

if (-not $OIDC_ARN -or $OIDC_ARN -match "None") {
    $OIDC_ARN = aws iam create-open-id-connect-provider `
      --url "https://token.actions.githubusercontent.com" `
      --client-id-list "sts.amazonaws.com" `
      --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" `
      --query "OpenIDConnectProviderArn" --output text 2>&1
    Write-Host "  OIDC Provider creado: $OIDC_ARN"
} else {
    Write-Host "  OIDC Provider ya existe: $OIDC_ARN"
}

$TRUST_POLICY = @"
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "$OIDC_ARN"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
      "StringLike": {"token.actions.githubusercontent.com:sub": ["repo:fcores/PFI-Proyecto-Final:ref:refs/heads/main", "repo:fcores/PFI-Proyecto-Final:ref:refs/heads/desarrollo"]}
    }
  }]
}
"@

$ROLE_NAME = "github-actions-deploy"
$TRUST_POLICY | Out-File -Encoding utf8 "$env:TEMP\trust.json"
$roleCheck = aws iam get-role --role-name $ROLE_NAME 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Rol ya existe, actualizando trust policy..."
    aws iam update-assume-role-policy --role-name $ROLE_NAME --policy-document "file://$env:TEMP\trust.json" 2>&1 | Out-Null
} else {
    aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document "file://$env:TEMP\trust.json" --description "Rol para GitHub Actions deploy via OIDC" 2>&1 | Out-Null
    Write-Host "  Rol creado."
}

$policies = @(
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser",
    "arn:aws:iam::aws:policy/AmazonECS_FullAccess",
    "arn:aws:iam::aws:policy/AmazonS3FullAccess",
    "arn:aws:iam::aws:policy/CloudFrontFullAccess",
    "arn:aws:iam::aws:policy/AmazonSSMFullAccess",
    "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
)
foreach ($p in $policies) {
    aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn $p 2>&1 | Out-Null
}
Write-Host "  Politicas adjuntadas." -ForegroundColor Green
Write-Host ""

# ─── PASO 2: RDS PostgreSQL ──────────────────────────────────
Write-Host "[2/8] Creando instancia RDS PostgreSQL 16..." -ForegroundColor Yellow

$DB_INSTANCE_ID = "$PROJECT-db"
$DB_NAME = "medchain"
$DB_USERNAME = "medchain_app"
$DB_PORT = 5432
$DB_SECRET_NAME = "$PROJECT/database-credentials"
$SUBNET_GROUP = "$PROJECT-db-subnet-group"
$SG_DB_NAME = "$PROJECT-db-sg"
$PARAM_GROUP = "$PROJECT-pg16-params"

# Generar password
$DB_PASSWORD = python -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(32)))"

# Verificar si RDS ya existe
$existingDB = aws rds describe-db-instances --db-instance-identifier $DB_INSTANCE_ID --region $AWS_REGION 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  RDS ya existe, saltando creacion..."
    $DB_ENDPOINT = aws rds describe-db-instances --db-instance-identifier $DB_INSTANCE_ID --region $AWS_REGION `
      --query "DBInstances[0].Endpoint.Address" --output text
} else {
    # Security Group para RDS
    $SG_DB = aws ec2 create-security-group --group-name $SG_DB_NAME `
      --description "SG para RDS medchain" --vpc-id $VPC_ID --region $AWS_REGION `
      --query "GroupId" --output text 2>&1
    if ($LASTEXITCODE -ne 0) {
        $SG_DB = aws ec2 describe-security-groups --filters "Name=group-name,Values=$SG_DB_NAME" "Name=vpc-id,Values=$VPC_ID" `
          --region $AWS_REGION --query "SecurityGroups[0].GroupId" --output text 2>&1
    }
    aws ec2 authorize-security-group-ingress --group-id $SG_DB --protocol tcp --port $DB_PORT `
      --source-group $SG_ECS --region $AWS_REGION 2>&1 | Out-Null

    # Subnet group
    aws rds create-db-subnet-group --db-subnet-group-name $SUBNET_GROUP `
      --db-subnet-group-description "Subnets para RDS" `
      --subnet-ids $SUBNET_A $SUBNET_B --region $AWS_REGION 2>&1 | Out-Null

    # Parameter group
    aws rds create-db-parameter-group --db-parameter-group-name $PARAM_GROUP `
      --db-parameter-group-family "postgres16" `
      --description "Force SSL" --region $AWS_REGION 2>&1 | Out-Null
    aws rds modify-db-parameter-group --db-parameter-group-name $PARAM_GROUP `
      --parameters "ParameterName=rds.force_ssl,ParameterValue=1,ApplyMethod=pending-reboot" `
      --region $AWS_REGION | Out-Null

    # Crear instancia
    Write-Host "  Creando instancia (tarda 5-10 min)..."
    aws rds create-db-instance `
      --db-instance-identifier $DB_INSTANCE_ID `
      --db-instance-class "db.t4g.micro" `
      --engine "postgres" --engine-version "16" `
      --master-username $DB_USERNAME --master-user-password $DB_PASSWORD `
      --db-name $DB_NAME --allocated-storage 20 --storage-type gp3 `
      --storage-encrypted --db-subnet-group-name $SUBNET_GROUP `
      --vpc-security-group-ids $SG_DB --db-parameter-group-name $PARAM_GROUP `
      --backup-retention-period 7 --no-publicly-accessible --no-multi-az `
      --port $DB_PORT --region $AWS_REGION `
      --tags "Key=Project,Value=$PROJECT" | Out-Null

    Write-Host "  Esperando a que la instancia este disponible..."
    aws rds wait db-instance-available --db-instance-identifier $DB_INSTANCE_ID --region $AWS_REGION

    $DB_ENDPOINT = aws rds describe-db-instances --db-instance-identifier $DB_INSTANCE_ID `
      --region $AWS_REGION --query "DBInstances[0].Endpoint.Address" --output text
}

$DATABASE_URL = "postgresql://${DB_USERNAME}:${DB_PASSWORD}@${DB_ENDPOINT}:${DB_PORT}/${DB_NAME}?sslmode=require"
Write-Host "  RDS Endpoint: $DB_ENDPOINT" -ForegroundColor Green

# Guardar en Secrets Manager
$secretJson = @{username=$DB_USERNAME; password=$DB_PASSWORD; host=$DB_ENDPOINT; port=$DB_PORT; dbname=$DB_NAME; DATABASE_URL=$DATABASE_URL} | ConvertTo-Json -Compress
aws secretsmanager create-secret --name $DB_SECRET_NAME --description "Credenciales RDS" `
  --secret-string $secretJson --region $AWS_REGION 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    aws secretsmanager update-secret --secret-id $DB_SECRET_NAME --secret-string $secretJson --region $AWS_REGION 2>&1 | Out-Null
}
$DB_SECRET_ARN = aws secretsmanager describe-secret --secret-id $DB_SECRET_NAME --region $AWS_REGION --query "ARN" --output text 2>&1
Write-Host "  DB Secret ARN: $DB_SECRET_ARN" -ForegroundColor Green
Write-Host ""

# ─── PASO 3: Clave de cifrado ────────────────────────────────
Write-Host "[3/8] Creando clave maestra de cifrado..." -ForegroundColor Yellow
$MASTER_KEY = python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
$encSecretJson = "{`"v1`": `"$MASTER_KEY`", `"activa`": `"v1`"}"

$ENCRYPTION_SECRET_ARN = aws secretsmanager create-secret --name "medchain/encryption-key" `
  --description "Clave maestra AES-256" --secret-string $encSecretJson `
  --region $AWS_REGION --query "ARN" --output text 2>&1
if ($LASTEXITCODE -ne 0) {
    $ENCRYPTION_SECRET_ARN = aws secretsmanager describe-secret --secret-id "medchain/encryption-key" `
      --region $AWS_REGION --query "ARN" --output text 2>&1
}
Write-Host "  Encryption Secret ARN: $ENCRYPTION_SECRET_ARN" -ForegroundColor Green
Write-Host ""

# ─── PASO 4: Permisos IAM ────────────────────────────────────
Write-Host "[4/8] Agregando permisos de Secrets Manager al Task Role..." -ForegroundColor Yellow
$policyDoc = @"
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"secretsmanager:GetSecretValue","Resource":["$DB_SECRET_ARN","$ENCRYPTION_SECRET_ARN"]}]}
"@
$policyDoc | Out-File -Encoding utf8 "$env:TEMP\secrets-policy.json"
aws iam put-role-policy --role-name "$PROJECT-ecs-task-role" `
  --policy-name "medchain-secrets-read" `
  --policy-document "file://$env:TEMP\secrets-policy.json" 2>&1 | Out-Null
Write-Host "  Politica adjuntada." -ForegroundColor Green
Write-Host ""

# ─── PASO 5: Migraciones Alembic ─────────────────────────────
Write-Host "[5/8] Ejecutando migraciones Alembic..." -ForegroundColor Yellow
$env:DATABASE_URL = $DATABASE_URL
$env:ENVIRONMENT = "local"
pip install -r requirements.txt --quiet 2>$null
python -m alembic upgrade head
Write-Host "  Migraciones aplicadas." -ForegroundColor Green
Write-Host ""

# ─── PASO 6: Rebuild Docker ──────────────────────────────────
Write-Host "[6/8] Reconstruyendo imagen Docker..." -ForegroundColor Yellow
$loginCmd = aws ecr get-login-password --region $AWS_REGION
$loginCmd | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
docker build -t $IMAGE_URI .
docker push $IMAGE_URI
Write-Host "  Imagen subida." -ForegroundColor Green
Write-Host ""

# ─── PASO 7: Force ECS deploy ────────────────────────────────
Write-Host "[7/8] Forzando nuevo deploy en ECS..." -ForegroundColor Yellow
aws ecs update-service --cluster "$PROJECT-cluster" --service "$PROJECT-backend-svc" `
  --force-new-deployment --region $AWS_REGION | Out-Null
Write-Host "  Deploy forzado." -ForegroundColor Green
Write-Host ""

# ─── PASO 8: Chaincode via SSM ───────────────────────────────
Write-Host "[8/8] Desplegando chaincode en EC2 via SSM..." -ForegroundColor Yellow
$STATE = aws ec2 describe-instances --instance-ids $EC2_INSTANCE_ID `
  --query "Reservations[0].Instances[0].State.Name" --output text --region $AWS_REGION
if ($STATE -eq "stopped") {
    Write-Host "  Arrancando EC2..."
    aws ec2 start-instances --instance-ids $EC2_INSTANCE_ID --region $AWS_REGION | Out-Null
    aws ec2 wait instance-running --instance-ids $EC2_INSTANCE_ID --region $AWS_REGION
    Start-Sleep -Seconds 30
}

$commands = @(
    "set -e",
    "cd ~/PFI-Proyecto-Final",
    "git fetch origin desarrollo",
    "git checkout desarrollo",
    "git pull origin desarrollo",
    "cd chaincode/prescription-contract && go mod tidy && cd ../..",
    "cd fabric",
    "export CC_NAME=prescriptions",
    "export CC_SRC_PATH=`$HOME/PFI-Proyecto-Final/chaincode/prescription-contract",
    "export CC_VERSION=1.1",
    "export CC_SEQUENCE=1",
    "./scripts/deployChaincode.sh mychannel"
)
$cmdJson = $commands | ConvertTo-Json -Compress

try {
    $COMMAND_ID = aws ssm send-command --instance-ids $EC2_INSTANCE_ID `
      --document-name "AWS-RunShellScript" `
      --parameters "{`"commands`":$cmdJson}" `
      --timeout-seconds 300 --region $AWS_REGION `
      --query "Command.CommandId" --output text
    Write-Host "  SSM Command: $COMMAND_ID"
    Write-Host "  Esperando resultado (puede tardar unos minutos)..."
    aws ssm wait command-executed --command-id $COMMAND_ID --instance-id $EC2_INSTANCE_ID --region $AWS_REGION 2>$null
    Write-Host "  Chaincode desplegado." -ForegroundColor Green
} catch {
    Write-Host "  WARN: SSM fallo. Puede que el agente no este instalado." -ForegroundColor DarkYellow
    Write-Host "  Desplegar chaincode manualmente en la EC2." -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " DESPLIEGUE FINALIZADO" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host " RDS Endpoint:  $DB_ENDPOINT"
Write-Host " DATABASE_URL guardada en Secrets Manager"
Write-Host ""
Write-Host " Pasos manuales:"
Write-Host "   1. Eliminar AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY de GitHub Secrets"
Write-Host "   2. Desactivar access keys de medchain-admin en IAM"
Write-Host "   3. Agregar FABRIC_GATEWAY_URL a la task definition"
Write-Host ""
