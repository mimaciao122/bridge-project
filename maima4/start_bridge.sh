#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

python3 -m pip install -r requirements.txt
export BRIDGE_AGENTS_JSON='{"chiave-super-segreta-1":"assistente-locale-1"}'
exec python3 -m uvicorn bridge.http_server:app --host 127.0.0.1 --port 8787
