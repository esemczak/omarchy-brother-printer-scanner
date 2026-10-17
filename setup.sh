#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
# Build on the system Python, not a version-manager alias that can move underneath the venv.
/usr/bin/python3 -m venv --clear --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
echo 'Ready. Launch with ./run.sh; use ./install.sh to add the launcher entry.'
