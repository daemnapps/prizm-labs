#!/bin/zsh
# Rebuild the board's data every 30s so the page is never stale.
# The board reads board.json; nothing rebuilt it, so "the page hasn't
# updated in a minute" was literally true — 2026-08-31.
cd "$(dirname "$0")"
while true; do python3 build_ui.py >/dev/null 2>&1; sleep 30; done
