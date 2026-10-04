#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
    echo "No .venv found. Run ./setup.sh first." >&2
    exit 1
fi

"$VENV_PYTHON" "$PROJECT_DIR/download_insight_model.py"
