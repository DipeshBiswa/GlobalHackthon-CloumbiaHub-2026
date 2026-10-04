#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ ! -x "$PROJECT_DIR/.venv/bin/python" ]; then
    echo "No .venv found. Run ./setup.sh first." >&2
    exit 1
fi

"$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/download_opus.py"
