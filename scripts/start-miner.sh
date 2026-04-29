#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -n "${ENV_FILE:-}" ]]; then
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "ENV_FILE does not exist: $ENV_FILE" >&2
    exit 1
  fi
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

# websockets / substrate clients may honor proxy-related variables and route
# chain traffic through a proxy unintentionally. Clear them for miner startup.
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy NO_PROXY no_proxy

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "Missing virtualenv at $ROOT_DIR/.venv" >&2
  exit 1
fi

source .venv/bin/activate
export PYTHONUNBUFFERED=1

exec aurelius-miner
