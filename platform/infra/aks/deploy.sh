#!/usr/bin/env bash
# Create (or update) the AKS cluster and its registry, then hand over to
# platformctl. Everything here is idempotent; run it again after editing
# main.bicep.
#
#   RESOURCE_GROUP=poc-platform-rg ./deploy.sh
set -euo pipefail
cd "$(dirname "$0")"

RESOURCE_GROUP="${RESOURCE_GROUP:-poc-platform-rg}"
LOCATION="${LOCATION:-westeurope}"
NAME="${NAME:-pocplatform}"

az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

outputs=$(az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file main.bicep \
  --parameters name="$NAME" location="$LOCATION" \
  --query properties.outputs --output json)

cluster=$(echo "$outputs" | python3 -c 'import json,sys; print(json.load(sys.stdin)["clusterName"]["value"])')
registry=$(echo "$outputs" | python3 -c 'import json,sys; print(json.load(sys.stdin)["registryLoginServer"]["value"])')

az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$cluster" --overwrite-existing

cat <<EOF

Cluster ready: $cluster
Registry:      $registry

Next, from ../../ (the platform directory):

  1. point platform.yaml at the registry and the internal DNS zone:
       registry: $registry
       domain:   <the zone that resolves to the ingress load balancer>
  2. ./platformctl bootstrap --target aks
  3. build and push each project image to $registry, then
     ./platformctl deploy
EOF
