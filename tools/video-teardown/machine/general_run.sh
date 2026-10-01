#!/bin/zsh
# The general (any-creator) briefs for <brand> — every saved skincare / body-scrub
# product-promo swipe through the chain, views first, no frames (no pictures reach
# the brief any more). One after another; survives this session (nohup).
cd "$(dirname "$0")"
while IFS=$'\t' read -r label product video; do
  [ -z "$label" ] && continue
  if [ -f "runs/$(echo "$label" | tr 'A-Z' 'a-z')/brief-final.md" ]; then echo "== $label already done"; continue; fi
  echo "== $label ($product) $(date '+%H:%M')"
  python3 run.py "$video" --brand <brand> --product "$product" --route creator --label "$label" --no-frames 2>&1 | grep -E "^▶|done in|STOPPED|SKIPPED|Traceback|10 |10a|10b|✔"
done < "${1:-runs/_general-queue.txt}"
echo "== QUEUE FINISHED $(date '+%H:%M')"
