#!/bin/zsh
# The general (any-creator) briefs for <brand> — every saved skincare / body-scrub
# product-promo swipe through the chain, views first, no frames (no pictures reach
# the brief any more). One after another; survives this session (nohup).
#   usage: general_run.sh <brand> [queue-file]   (queue defaults to $RUNS/_general-queue.txt)
if [ -z "$1" ]; then echo "usage: general_run.sh <brand> [queue-file]" >&2; exit 2; fi
BRAND="$1"
cd "$(dirname "$0")"
RUNS="$(python3 -c 'import workdir; print(workdir.root())')"
while IFS=$'\t' read -r label product video; do
  [ -z "$label" ] && continue
  if [ -f "$RUNS/$(echo "$label" | tr 'A-Z' 'a-z')/brief-final.md" ]; then echo "== $label already done"; continue; fi
  echo "== $label ($product) $(date '+%H:%M')"
  python3 run.py "$video" --brand "$BRAND" --product "$product" --route creator --label "$label" --no-frames 2>&1 | grep -E "^▶|done in|STOPPED|SKIPPED|Traceback|10 |10a|10b|✔"
done < "${2:-$RUNS/_general-queue.txt}"
echo "== QUEUE FINISHED $(date '+%H:%M')"
