#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip install -r requirements.txt
if [ -f ui/package-lock.json ]; then
  npm --prefix ui ci
  npm --prefix ui run build
fi
