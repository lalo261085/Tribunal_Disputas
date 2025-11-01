#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VENV_DIR="$PROJECT_ROOT/.venv-build"

python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_ROOT/requirements.txt" pyinstaller

pyinstaller \
  "$PROJECT_ROOT/run.py" \
  --name TribunalServer \
  --onefile \
  --distpath "$PROJECT_ROOT/dist" \
  --workpath "$PROJECT_ROOT/build" \
  --specpath "$PROJECT_ROOT/build"

echo "Build completado en $PROJECT_ROOT/dist/TribunalServer"
