#!/usr/bin/env bash
set -e

if [[ "$1" == "backend" ]]; then
    WORKERS=${BACKEND_WORKERS:-1}
    echo "[ENTRYPOINT] Starting FastAPI server with $WORKERS workers..."
    exec fastapi run --workers "$WORKERS" app/main.py
else
    echo "[ENTRYPOINT] Skipping backend startup for argument: $1"
    exec "$@"
fi