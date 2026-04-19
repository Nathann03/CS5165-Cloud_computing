#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-cs5165-retail-rg}"
POSTGRES_SERVER="${POSTGRES_SERVER:?Set POSTGRES_SERVER before running.}"
RULE_NAME="${RULE_NAME:-AllowCurrentIpTemporary}"

az postgres flexible-server firewall-rule delete \
  --resource-group "$RESOURCE_GROUP" \
  --name "$POSTGRES_SERVER" \
  --rule-name "$RULE_NAME" \
  --yes

echo "Removed firewall rule $RULE_NAME"
