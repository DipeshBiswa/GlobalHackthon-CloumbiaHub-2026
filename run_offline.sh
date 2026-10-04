#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

exec "$PROJECT_DIR/myenv/bin/uvicorn" \
    --app-dir "$PROJECT_DIR" \
    api:app \
    --host 127.0.0.1 \
    --port 8000
