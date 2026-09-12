#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Charge le Client ID / Secret de la Machine Identity dédiée
set -a
source .infisical-identity.env
set +a

INFISICAL_DOMAIN="http://caesura.tailb8daf5.ts.net:8090/api"
INFISICAL_PROJECT_ID="db436bc3-c41c-4439-a385-1a547f7c4846"
INFISICAL_ENV="prod"

INFISICAL_TOKEN=$(infisical login \
  --method=universal-auth \
  --client-id="$INFISICAL_UNIVERSAL_AUTH_CLIENT_ID" \
  --client-secret="$INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET" \
  --domain="$INFISICAL_DOMAIN" \
  --silent --plain)

infisical run \
  --token="$INFISICAL_TOKEN" \
  --domain="$INFISICAL_DOMAIN" \
  --projectId="$INFISICAL_PROJECT_ID" \
  --env="$INFISICAL_ENV" \
  -- docker compose up -d