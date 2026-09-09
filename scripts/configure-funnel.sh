#!/usr/bin/env bash
set -euo pipefail

config_file=${FACTORY_MCP_ENV_FILE:-"$HOME/.config/touhou-reconstruction-factory-mcp.env"}
if [[ ! -f "$config_file" ]]; then
  echo "missing environment file: $config_file" >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "$config_file"
set +a

: "${FACTORY_MCP_HOST:?}"
: "${FACTORY_MCP_PORT:?}"
: "${FACTORY_MCP_PATH:?}"
: "${FACTORY_FUNNEL_HTTPS_PORT:?}"

if [[ "$FACTORY_MCP_HOST" != "127.0.0.1" ]]; then
  echo "Funnel upstream must remain bound to 127.0.0.1" >&2
  exit 2
fi
if [[ "$FACTORY_MCP_PATH" != /* || "$FACTORY_MCP_PATH" == "/" ]]; then
  echo "FACTORY_MCP_PATH must be an absolute, non-root path" >&2
  exit 2
fi

# Funnel strips its public mount prefix before proxying, so the upstream URL
# includes the same MCP route and preserves the request path seen by the app.
tailscale funnel \
  --bg \
  --https="$FACTORY_FUNNEL_HTTPS_PORT" \
  --set-path="$FACTORY_MCP_PATH" \
  "http://${FACTORY_MCP_HOST}:${FACTORY_MCP_PORT}${FACTORY_MCP_PATH}"
tailscale funnel status
