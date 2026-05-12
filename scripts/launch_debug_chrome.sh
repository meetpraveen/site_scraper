#!/usr/bin/env bash
set -euo pipefail
URL="${1:?usage: launch_debug_chrome.sh URL [PORT]}"
PORT="${2:-9222}"
PROFILE="${SITE_SCRAPER_CHROME_PROFILE:-$PWD/secrets/chrome-profile}"
mkdir -p "$PROFILE"
exec google-chrome --remote-debugging-port="$PORT" --user-data-dir="$PROFILE" --no-first-run --no-default-browser-check "$URL"
