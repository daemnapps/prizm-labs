#!/bin/bash
# Take a key off the clipboard into this repo's .env, without it ever being displayed.
# Pasting a secret into a chat puts it in a transcript forever (workspace rule 6);
# the clipboard keeps it out of everything but the file it belongs in.
# Prizm reads keys only from the environment and its own .env (never this repo's .env).
set -euo pipefail
NAME="${1:?usage: add-key.sh KEY_NAME}"
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
VAULT="$REPO/.env"
VAL="$(pbpaste | tr -d '\r\n[:space:]')"
[ -n "$VAL" ] || { echo "clipboard is empty"; exit 1; }
touch "$VAULT"; chmod 600 "$VAULT"
git -C "$REPO" check-ignore -q "$VAULT" || { echo "refusing: .env is not git-ignored"; exit 1; }
if grep -q "^${NAME}=" "$VAULT" 2>/dev/null; then
  sed -i '' "s|^${NAME}=.*|${NAME}=${VAL}|" "$VAULT"; echo "$NAME updated"
else
  printf '%s=%s\n' "$NAME" "$VAL" >> "$VAULT"; echo "$NAME added"
fi
echo "length ${#VAL}  (value not shown)"
