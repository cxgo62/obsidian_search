#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_CONFIG_FILE="${PROJECT_ROOT}/config.json"
EXAMPLE_CONFIG_FILE="${PROJECT_ROOT}/config.example.json"

if [[ -z "${OBS_CONFIG_FILE:-}" ]]; then
  export OBS_CONFIG_FILE="${DEFAULT_CONFIG_FILE}"
fi

if [[ -f "${PROJECT_ROOT}/.env.local" ]]; then
  # shellcheck disable=SC1091
  source "${PROJECT_ROOT}/.env.local"
fi

if [[ ! -f "${OBS_CONFIG_FILE}" ]]; then
  cp "${EXAMPLE_CONFIG_FILE}" "${OBS_CONFIG_FILE}"
  echo "Created config file: ${OBS_CONFIG_FILE}"
  echo "Edit vault_path and embedding provider api_key in config before starting the service."
fi

export PYTHONPATH="${PROJECT_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
export OBS_BIND_HOST="${OBS_BIND_HOST:-127.0.0.1}"
export OBS_BIND_PORT="${OBS_BIND_PORT:-8000}"
export OBS_AUTO_BOOTSTRAP="${OBS_AUTO_BOOTSTRAP:-1}"

if [[ -d "${PROJECT_ROOT}/.venv" ]]; then
  export OBS_PYTHON_BIN="${PROJECT_ROOT}/.venv/bin/python"
else
  export OBS_PYTHON_BIN="${OBS_PYTHON_BIN:-python3}"
fi

echo "Using config: ${OBS_CONFIG_FILE}"
echo "Using python: ${OBS_PYTHON_BIN}"
echo "Auto bootstrap: ${OBS_AUTO_BOOTSTRAP}"
