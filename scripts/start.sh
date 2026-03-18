#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck disable=SC1091
source "${PROJECT_ROOT}/scripts/env.sh"

if ! command -v "${OBS_PYTHON_BIN}" >/dev/null 2>&1 && [[ "${OBS_PYTHON_BIN}" != */python ]]; then
  echo "Python executable not found: ${OBS_PYTHON_BIN}" >&2
  exit 1
fi

if [[ ! -f "${OBS_CONFIG_FILE}" ]]; then
  echo "Config file not found: ${OBS_CONFIG_FILE}" >&2
  exit 1
fi

ensure_runtime() {
  if "${OBS_PYTHON_BIN}" -m uvicorn --version >/dev/null 2>&1; then
    return 0
  fi

  if [[ "${OBS_AUTO_BOOTSTRAP}" != "1" ]]; then
    echo "uvicorn is not installed in ${OBS_PYTHON_BIN}" >&2
    echo "Set OBS_AUTO_BOOTSTRAP=1 or install dependencies manually." >&2
    exit 1
  fi

  if [[ ! -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
    echo "Creating virtual environment at ${PROJECT_ROOT}/.venv"
    python3 -m venv "${PROJECT_ROOT}/.venv"
  fi

  OBS_PYTHON_BIN="${PROJECT_ROOT}/.venv/bin/python"
  export OBS_PYTHON_BIN

  if ! "${OBS_PYTHON_BIN}" -m uvicorn --version >/dev/null 2>&1; then
    echo "Installing project dependencies into .venv"
    if ! (
      cd "${PROJECT_ROOT}" &&
      "${OBS_PYTHON_BIN}" -m pip install -e ".[dev]"
    ); then
      echo "Failed to install dependencies automatically." >&2
      echo "If you hit SSL/certificate issues, fix pip connectivity and rerun scripts/start.sh." >&2
      exit 1
    fi
  fi
}

ensure_runtime

echo "Starting Obsidian Search API on ${OBS_BIND_HOST}:${OBS_BIND_PORT}"
exec "${OBS_PYTHON_BIN}" -m uvicorn app.main:app \
  --app-dir "${PROJECT_ROOT}/src" \
  --host "${OBS_BIND_HOST}" \
  --port "${OBS_BIND_PORT}"
