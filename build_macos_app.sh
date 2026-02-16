#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN=".venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install pyinstaller -r requirements.txt
"$PYTHON_BIN" tools/generate_app_icons.py

ICON_PATH="build/icons/app_icon.icns"
if [[ ! -f "$ICON_PATH" ]]; then
  ICON_PATH="build/icons/app_icon.png"
fi

"$PYTHON_BIN" -m PyInstaller --noconfirm --clean --windowed \
  --name SRCMediaDrop \
  --icon "$ICON_PATH" \
  --osx-bundle-identifier "com.src.mediadrop" \
  --hidden-import pystray \
  --hidden-import PIL.Image \
  --hidden-import PIL.ImageDraw \
  --add-data "templates:templates" \
  --add-data "static:static" \
  --add-data "app_meta.py:." \
  launcher_gui.py

echo "Build release concluido. App em: dist/SRCMediaDrop.app"
