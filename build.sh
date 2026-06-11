#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

rm -rf build dist
python -m PyInstaller --clean --noconfirm sessionchrono.spec

cat <<'MSG'

Build complete.
Generated output: dist/SessionChrono/

Do not commit build/, dist/, executables, shared libraries, bytecode, or other
PyInstaller-generated artifacts. They are local release outputs only.
MSG
