#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
python -m venv .venv
.venv/bin/pip install -r requirements.txt
echo 'Ready. Launch with ./run.sh; use ./install.sh to add the launcher entry.'
