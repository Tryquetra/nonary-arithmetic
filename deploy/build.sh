#!/usr/bin/env bash
# Build the Cloudflare Pages bundle for papers.robsoncassiano.software.
#
# Layout of the deployed site:
#   /                                          papers index
#   /nonary-ternary-bridge-conversion/         the article (Tailwind and math
#                                              compiled at build time)
#   /nonary-ternary-bridge-conversion/paper.md Markdown version
#   /robots.txt, /sitemap.xml, /llms.txt       crawler and LLM entry points
#
# Usage: deploy/build.sh [outdir]   (default: dist)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$ROOT/dist}"
SLUG="nonary-ternary-bridge-conversion"

cd "$ROOT"

rm -rf "$OUT"
mkdir -p "$OUT/$SLUG"

# Article: prerender math and compile Tailwind, so the page ships no JS.
bun deploy/prerender.mjs "$OUT/$SLUG"
rm -f "$OUT/$SLUG/.prerendered.html" "$OUT/$SLUG/.tailwind.css"

cp "$ROOT/paper.md"              "$OUT/$SLUG/paper.md"
cp "$ROOT/og-nonary-bridges.png" "$OUT/$SLUG/og-nonary-bridges.png"
cp "$ROOT/robots.txt"            "$OUT/robots.txt"
cp "$ROOT/sitemap.xml"           "$OUT/sitemap.xml"
cp "$ROOT/llms.txt"              "$OUT/llms.txt"

cp "$ROOT/deploy/_headers"       "$OUT/_headers"
cp "$ROOT/deploy/_redirects"     "$OUT/_redirects"
cp "$ROOT/deploy/index.html"     "$OUT/index.html"

echo "built $OUT"
find "$OUT" -type f -printf '%8s  %P\n' | sort -k2 | head -20
echo "files: $(find "$OUT" -type f | wc -l)"
