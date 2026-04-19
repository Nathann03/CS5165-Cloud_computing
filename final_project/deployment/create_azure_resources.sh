#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-cs5165-retail-rg}"
LOCATION="${LOCATION:-eastus}"
APP_SERVICE_PLAN="${APP_SERVICE_PLAN:-cs5165-retail-plan}"
WEBAPP_NAME="${WEBAPP_NAME:-cs5165-retail-app-$RANDOM}"
POSTGRES_SERVER="${POSTGRES_SERVER:-cs5165-retail-pg-$RANDOM}"
POSTGRES_DB="${POSTGRES_DB:-retailanalytics}"
POSTGRES_ADMIN_USER="${POSTGRES_ADMIN_USER:-retailadmin}"
POSTGRES_ADMIN_PASSWORD="${POSTGRES_ADMIN_PASSWORD:?Set POSTGRES_ADMIN_PASSWORD before running.}"
STORAGE_ACCOUNT="${STORAGE_ACCOUNT:-cs5165retail$RANDOM}"
BLOB_CONTAINER="${BLOB_CONTAINER:-retail-datasets}"

echo "Creating resource group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

echo "Creating PostgreSQL Flexible Server..."
az postgres flexible-server create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$POSTGRES_SERVER" \
  --location "$LOCATION" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 16 \
  --admin-user "$POSTGRES_ADMIN_USER" \
  --admin-password "$POSTGRES_ADMIN_PASSWORD" \
  --public-access 0.0.0.0-255.255.255.255

echo "Creating storage account..."
az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2

echo "Creating blob container..."
az storage container create \
  --account-name "$STORAGE_ACCOUNT" \
  --name "$BLOB_CONTAINER" \
  --auth-mode login

echo "Creating application database..."
az postgres flexible-server db create \
  --resource-group "$RESOURCE_GROUP" \
  --server-name "$POSTGRES_SERVER" \
  --database-name "$POSTGRES_DB"

echo "Creating App Service plan..."
az appservice plan create \
  --name "$APP_SERVICE_PLAN" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --is-linux \
  --sku B1

echo "Creating Web App..."
az webapp create \
  --resource-group "$RESOURCE_GROUP" \
  --plan "$APP_SERVICE_PLAN" \
  --name "$WEBAPP_NAME" \
  --runtime "PYTHON|3.12"

POSTGRES_URL="postgresql+psycopg://${POSTGRES_ADMIN_USER}:${POSTGRES_ADMIN_PASSWORD}@${POSTGRES_SERVER}.postgres.database.azure.com:5432/${POSTGRES_DB}?sslmode=require"

echo "Configuring app settings..."
az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEBAPP_NAME" \
  --settings \
    DATABASE_URL="$POSTGRES_URL" \
    AUTO_LOAD_ON_STARTUP=0 \
    ENVIRONMENT=production \
    AZURE_BLOB_CONTAINER="$BLOB_CONTAINER" \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true

az webapp config set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEBAPP_NAME" \
  --startup-file "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo "Created WEBAPP_NAME=$WEBAPP_NAME"
echo "Created POSTGRES_SERVER=$POSTGRES_SERVER"
echo "Created STORAGE_ACCOUNT=$STORAGE_ACCOUNT"
