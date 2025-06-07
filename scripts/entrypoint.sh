#!/usr/bin/env bash
set -e

if [[ "$1" == "backend" ]]; then
    echo "[ENTRYPOINT] Starting FastAPI server..."
    exec fastapi run --workers 4 app/main.py
else
    echo "[ENTRYPOINT] Skipping backend startup for argument: $1"
    exec "$@"
fi