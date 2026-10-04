#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

if [ -x "$PROJECT_DIR/.venv/bin/uvicorn" ]; then
    UVICORN="$PROJECT_DIR/.venv/bin/uvicorn"
elif [ -x "$PROJECT_DIR/../.venv/bin/uvicorn" ]; then
    UVICORN="$PROJECT_DIR/../.venv/bin/uvicorn"
elif [ -x "$PROJECT_DIR/myenv/bin/uvicorn" ]; then
    UVICORN="$PROJECT_DIR/myenv/bin/uvicorn"
elif [ -x "$PROJECT_DIR/../myenv/bin/uvicorn" ]; then
    UVICORN="$PROJECT_DIR/../myenv/bin/uvicorn"
else
    echo "No virtual environment found. Run ./setup.sh first." >&2
    exit 1
fi

exec "$UVICORN" \
    --app-dir "$PROJECT_DIR" \
    api:app \
    --host 127.0.0.1 \
    --port 8000
