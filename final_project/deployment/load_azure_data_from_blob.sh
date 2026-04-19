#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-cs5165-retail-rg}"
STORAGE_ACCOUNT="${STORAGE_ACCOUNT:?Set STORAGE_ACCOUNT before running.}"
CONTAINER_NAME="${CONTAINER_NAME:-retail-datasets}"

export AZURE_BLOB_CONNECTION_STRING="$(
  az storage account show-connection-string \
    --resource-group "$RESOURCE_GROUP" \
    --name "$STORAGE_ACCOUNT" \
    --query connectionString \
    -o tsv
)"
export AZURE_BLOB_CONTAINER="$CONTAINER_NAME"

python3 scripts/upload_dataset_to_blob.py
python3 scripts/load_blob_to_db.py

echo "Azure Blob upload and managed database load completed."
