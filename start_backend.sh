#!/usr/bin/env bash
set -euo pipefail

cd /data4/baihexiang/NanoScaner

# Ensure imports work regardless of launch directory.
export PYTHONPATH="/data4/baihexiang/NanoScaner:${PYTHONPATH:-}"

exec /data3/baihexiang/.conda/envs/ace/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
