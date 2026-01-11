#!/usr/bin/env bash
set -euo pipefail

# Railway injects PORT as an integer at runtime. Do NOT override it in Railway Variables.
RAW_PORT="${PORT:-8000}"
if [[ ! "${RAW_PORT}" =~ ^[0-9]+$ ]]; then
  echo "FATAL: PORT env var must be an integer. Got: '${RAW_PORT}'."
  echo "Fix: Railway → Service → Variables → remove any custom PORT value (Railway sets it automatically)."
  exit 1
fi

exec uvicorn main:app --host 0.0.0.0 --port "${RAW_PORT}"
