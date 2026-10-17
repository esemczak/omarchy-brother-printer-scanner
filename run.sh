#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
# Prefer Arch's Python: pacman upgrades it in step with pyside6 and python-pillow.
if /usr/bin/python3 -c 'import PySide6, PIL' 2>/dev/null; then
  exec /usr/bin/python3 -m brother_studio "$@"
fi
# Otherwise use the venv, rebuilding it if a Python upgrade has broken it.
if ! .venv/bin/python -c 'import PySide6, PIL' 2>/dev/null; then
  echo 'Qt dependencies missing or stale; rebuilding .venv...' >&2
  ./setup.sh >&2
fi
exec .venv/bin/python -m brother_studio "$@"
