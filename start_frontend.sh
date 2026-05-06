#!/usr/bin/env bash
set -euo pipefail

exec npm --prefix /data4/baihexiang/NanoScaner/frontend run dev -- --host 0.0.0.0 --strictPort --port 5173
