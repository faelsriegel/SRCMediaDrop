#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

APP_NAME="SRCMediaDrop"
APP_BUNDLE="dist/${APP_NAME}.app"
DMG_PATH="dist/${APP_NAME}-macos.dmg"
STAGE_DIR="build/dmg_stage"

if ! command -v hdiutil >/dev/null 2>&1; then
  echo "Erro: hdiutil nao encontrado. Este script deve ser executado no macOS."
  exit 1
fi

if [[ ! -d "$APP_BUNDLE" ]]; then
  echo "App nao encontrado em $APP_BUNDLE. Gerando app primeiro..."
  chmod +x build_macos_app.sh
  ./build_macos_app.sh
fi

rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"

cp -R "$APP_BUNDLE" "$STAGE_DIR/"
ln -sfn /Applications "$STAGE_DIR/Applications"

rm -f "$DMG_PATH"
hdiutil create \
  -volname "SRC MediaDrop" \
  -srcfolder "$STAGE_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

echo "DMG criado com sucesso em: $DMG_PATH"
