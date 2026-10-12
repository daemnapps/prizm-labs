#!/bin/zsh
# The daily language pull (components/research-gatherer/daily.py) — installed
# at ~/.local/bin/daemn-language-daily.sh, run by launchd
# (com.daemn.language-daily). It runs daily.py as it is on origin/main, so the
# newest code always runs even when the main checkout is behind or mid-edit;
# daily.py makes its own throwaway checkout, pulls, files, commits and pushes.
# Free sources only — Apify is fenced off inside the run.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN
WS="${AI_WORKSPACE_MAIN:-$HOME/Projects/workspace}"
LOG="$HOME/Library/Logs/daemn/language-daily.log"
mkdir -p "$(dirname "$LOG")"
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
if ! git -C "$WS" fetch -q origin 2>>"$LOG" || \
   ! git -C "$WS" show origin/main:components/research-gatherer/daily.py > "$T/daily.py" 2>>"$LOG"; then
  echo "$(date '+%Y-%m-%d %H:%M:%S')  FAILED — could not read daily.py from origin/main" >> "$LOG"
  exit 1
fi
python3 "$T/daily.py" --repo "$WS" "$@"
