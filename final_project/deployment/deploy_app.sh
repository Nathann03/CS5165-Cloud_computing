#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-cs5165-retail-rg}"
WEBAPP_NAME="${WEBAPP_NAME:?Set WEBAPP_NAME before running.}"
PACKAGE_PATH="${PACKAGE_PATH:-deployment/app.zip}"

if [[ ! -f "$PACKAGE_PATH" ]]; then
  echo "Package not found at $PACKAGE_PATH"
  exit 1
fi

az webapp deploy \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEBAPP_NAME" \
  --src-path "$PACKAGE_PATH" \
  --type zip

az webapp restart \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEBAPP_NAME"

echo "Deployment submitted for $WEBAPP_NAME"
