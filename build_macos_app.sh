#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

FFMPEG_STAGE_DIR="build/runtime_ffmpeg"
FFMPEG_DATA_SOURCE="ffmpeg"

if command -v ffmpeg >/dev/null 2>&1; then
  mkdir -p "$FFMPEG_STAGE_DIR"
  cp "$(command -v ffmpeg)" "$FFMPEG_STAGE_DIR/ffmpeg"
  chmod +x "$FFMPEG_STAGE_DIR/ffmpeg"
  if command -v ffprobe >/dev/null 2>&1; then
    cp "$(command -v ffprobe)" "$FFMPEG_STAGE_DIR/ffprobe"
    chmod +x "$FFMPEG_STAGE_DIR/ffprobe"
  fi
  FFMPEG_DATA_SOURCE="$FFMPEG_STAGE_DIR"
fi

if [[ ! -f "$FFMPEG_DATA_SOURCE/ffmpeg" && ! -f "$FFMPEG_DATA_SOURCE/ffmpeg.exe" ]]; then
  echo "Erro: FFmpeg nao encontrado para empacotamento. Instale com: brew install ffmpeg"
  exit 1
fi

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
  --add-data "$FFMPEG_DATA_SOURCE:ffmpeg" \
  --add-data "app_meta.py:." \
  launcher_gui.py

echo "Build release concluido. App em: dist/SRCMediaDrop.app"
