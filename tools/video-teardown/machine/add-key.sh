#!/bin/bash
# Take a key off the clipboard into the vault, without it ever being displayed.
# Pasting a secret into a chat puts it in a transcript forever (workspace rule 6);
# the clipboard keeps it out of everything but the file it belongs in.
set -euo pipefail
NAME="${1:?usage: add-key.sh KEY_NAME}"
VAULT="$HOME/.daemn/keys.env"
VAL="$(pbpaste | tr -d '\r\n[:space:]')"
[ -n "$VAL" ] || { echo "clipboard is empty"; exit 1; }
mkdir -p "$(dirname "$VAULT")"; touch "$VAULT"; chmod 600 "$VAULT"
if grep -q "^${NAME}=" "$VAULT" 2>/dev/null; then
  sed -i '' "s|^${NAME}=.*|${NAME}=${VAL}|" "$VAULT"; echo "$NAME updated"
else
  printf '%s=%s\n' "$NAME" "$VAL" >> "$VAULT"; echo "$NAME added"
fi
echo "length ${#VAL}, first 4 chars ${VAL:0:4}…  (value not shown)"
