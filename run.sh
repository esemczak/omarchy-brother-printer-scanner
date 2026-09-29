#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
if [[ ! -x .venv/bin/python ]]; then
  echo 'Run ./setup.sh first to install Qt dependencies.' >&2
  exit 1
fi
exec .venv/bin/python -m brother_studio "$@"
