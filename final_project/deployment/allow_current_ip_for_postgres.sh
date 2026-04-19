#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-cs5165-retail-rg}"
POSTGRES_SERVER="${POSTGRES_SERVER:?Set POSTGRES_SERVER before running.}"
RULE_NAME="${RULE_NAME:-AllowCurrentIpTemporary}"

CURRENT_IP="$(curl -sS https://api.ipify.org)"

az postgres flexible-server firewall-rule create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$POSTGRES_SERVER" \
  --rule-name "$RULE_NAME" \
  --start-ip-address "$CURRENT_IP" \
  --end-ip-address "$CURRENT_IP"

echo "Allowed current IP $CURRENT_IP with rule $RULE_NAME"
