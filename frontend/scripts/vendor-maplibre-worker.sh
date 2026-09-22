#!/usr/bin/env bash
# maplibre-gl 워커를 public/에 원본 파일명으로 벤더링 (Turbopack 해시 리네임 회피).
# package.json postinstall에서 호출. maplibre-gl 업그레이드 후 재실행.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/node_modules/maplibre-gl/dist"
DEST="$ROOT/public/maplibre-gl"
if [ ! -d "$SRC" ]; then
  echo "skip vendor-maplibre-worker: maplibre-gl not installed"
  exit 0
fi
mkdir -p "$DEST"
cp -f "$SRC/maplibre-gl-worker.mjs" "$DEST/maplibre-gl-worker.mjs"
cp -f "$SRC/maplibre-gl-shared.mjs" "$DEST/maplibre-gl-shared.mjs"
echo "vendored maplibre worker → $DEST"
