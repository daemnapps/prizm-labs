#!/bin/bash
# Make a fresh checkout ready to run the image production board.
# What git cannot carry (pictures, cast sheets, product builds, git-ignored run folders) comes from the team Drive.
#   components/image-production/tools/setup_machine.sh <brand> [--dry-skin]
# Safe to run twice: it only adds files that are missing. It deletes nothing.
set -e
BRAND="${1:-brand_b}"
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
DRIVE="$(ls -d "$HOME"/Library/CloudStorage/GoogleDrive-*/"Shared drives"/"Shared Assets" 2>/dev/null | head -1)"
[ -n "$DRIVE" ] || { echo "No Shared Assets drive found. Open Google Drive for desktop and make sure Shared Assets is available, then run this again."; exit 1; }
echo "repo:  $REPO"; echo "drive: $DRIVE"
for d in casting products sets worlds wardrobe skin looks props; do
  if [ -d "$DRIVE/runs/ai-elements/$BRAND/$d" ]; then
    mkdir -p "$REPO/runs/ai-elements/$BRAND/$d"
    rsync -a --ignore-existing "$DRIVE/runs/ai-elements/$BRAND/$d/" "$REPO/runs/ai-elements/$BRAND/$d/" && echo "  copied $d"
  fi
done
if [ "$2" = "--dry-skin" ]; then
  PACK="$(ls -t "$DRIVE"/runs/image-teardown/$BRAND/dry-skin-batch/runs-pack-*.tar.gz 2>/dev/null | head -1)"
  [ -f "$PACK" ] || { echo "Dry Skin run pack not found on the Drive: $PACK"; exit 1; }
  mkdir -p "$REPO/runs/image-teardown/$BRAND"; (cd "$REPO/runs/image-teardown/$BRAND" && tar xzkf "$PACK" 2>/dev/null || true) && echo "  unpacked the Dry Skin runs (files she already has are kept, never overwritten)"
fi
KEYS="$HOME/.upright-keys.env"
[ -f "$KEYS" ] && echo "  keys file found (names only: $(grep -c '=' "$KEYS") entries)" || echo "  MISSING $KEYS: get the team key file, one NAME=value per line, chmod 600."
echo "Check:  python3 components/image-teardown/tools/preflight.py --brand $BRAND"
echo "Board:  python3 components/image-production/bench/serve.py   then open http://localhost:8895/prompt"
