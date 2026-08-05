#!/usr/bin/env bash
# Render an HTML file to a PNG at a fixed geometry using the cached Playwright
# Chromium (no node dependency). Output PNG is (cssW*scale) x (cssH*scale).
#
#   ./render.sh input.html out.png [cssW=1440] [cssH=900] [scale=2]
#
# Defaults are a generic 2x desktop viewport; the orchestrator (vdiff.py)
# normally computes these from the mockup's own dimensions and passes them in.
set -euo pipefail
HTML="${1:?usage: render.sh input.html out.png [cssW cssH scale]}"
OUT="${2:?output png path required}"
CW="${3:-1440}"; CH="${4:-900}"; SCALE="${5:-2}"

# Locate a chrome-headless-shell binary from the Playwright browser cache.
BIN="${CHROME_HEADLESS_SHELL:-}"
if [[ -z "$BIN" ]]; then
  BIN="$(find "${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}" \
        -type f -name 'chrome-headless-shell' 2>/dev/null | sort | tail -1)"
fi
[[ -x "$BIN" ]] || { echo "no chrome-headless-shell found; set CHROME_HEADLESS_SHELL" >&2; exit 1; }

ABS="$(cd "$(dirname "$HTML")" && pwd)/$(basename "$HTML")"
"$BIN" --headless --no-sandbox --hide-scrollbars \
  --force-device-scale-factor="$SCALE" --window-size="${CW},${CH}" \
  --default-background-color=FFFFFFFF \
  --screenshot="$OUT" "file://$ABS" 2>/dev/null
echo "rendered $OUT @ $((CW*SCALE))x$((CH*SCALE))"
