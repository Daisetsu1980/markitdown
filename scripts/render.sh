#!/usr/bin/env bash
# pptx を全ページ画像（1280x720）にする。
# 使い方: scripts/render.sh <file.pptx> [出力フォルダ]
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "使い方: render.sh <file.pptx> [出力フォルダ]" >&2
  exit 2
fi

pptx="$1"
dir="${2:-$(dirname "$pptx")/render}"
mkdir -p "$dir"
rm -f "$dir"/slide-*.png "$dir"/*.pdf

soffice --headless --convert-to pdf --outdir "$dir" "$pptx" >/dev/null 2>&1
pdf="$dir/$(basename "${pptx%.*}").pdf"
[ -f "$pdf" ] || { echo "PDF への変換に失敗した: $pptx" >&2; exit 1; }

pdftoppm -r 96 -png "$pdf" "$dir/slide"
ls "$dir"/slide-*.png
echo "注意: LibreOffice による描画。PowerPoint とは、フォント置換や折り返しの位置が異なることがある。" >&2
