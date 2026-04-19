#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-cs5165-retail-rg}"

az group delete --name "$RESOURCE_GROUP" --yes --no-wait
echo "Requested deletion for $RESOURCE_GROUP"
