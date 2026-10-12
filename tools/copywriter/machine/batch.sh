#!/bin/bash
# Run the copy chain over a list of sources, a few at a time.
# Usage: machine/batch.sh <brand> <product-file>      (edit the list below)
#   <brand>         folder name under brands/ — there is no default brand
#   <product-file>  e.g. brands/<brand>/products/<product>.md
# Run from the package root (tools/copywriter). Logs land in logs/.
BRAND="$1"
PROD="$2"
if [ -z "$BRAND" ] || [ -z "$PROD" ]; then
  echo "usage: machine/batch.sh <brand> <product-file>   — name the brand; nothing is assumed" >&2
  exit 2
fi
HERE="$(cd "$(dirname "$0")" && pwd)"
WS="$(python3 -c 'import sys; sys.path.append(sys.argv[1]); from run_kit.paths import repo; print(repo(sys.argv[2]))' "$HERE/../../../components/run-kit" "$HERE")" || exit 2   # run-kit paths.repo(): AI_WORKSPACE, else this checkout
if [ ! -d "$WS/brands/$BRAND" ]; then
  echo "no brands/$BRAND under $WS" >&2
  exit 2
fi
# The paid swipe home, through the one helper (components/swipe-paid/swipe_home.py).
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
S="$(python3 -c 'import sys; sys.path.append(sys.argv[1]); import swipe_home; print(swipe_home.root("paid"))' "$REPO/components/swipe-paid")"
run () {  # run <label> <teardown-path> <video-path> <reference>
  python3 machine/copy.py "$2" --brand "$BRAND" --brand-root "$WS" --product "$PROD" \
    --source-reference "$4" ${3:+--video "$3"} --channel "Meta (feed / Reels)" \
    --label "$1" --hooks 5 > "logs/$1.log" 2>&1
  echo "  done: $1"
}
mkdir -p logs
run "ad-luxe-foundation"  "$S/swipes/ai-swipe-luxe-foundation/teardown/1-teardown/v6.md"  "$S/swipes/ai-swipe-luxe-foundation/source.mp4"  "Luxe foundation · ex-husband run-in · paid ad" &
run "ad-competitor-b"    "$S/swipes/swipe-competitor-b-158486664/teardown/1-teardown/v6.md" "$S/swipes/swipe-competitor-b-158486664/source.mp4" "competitor-b · mother endorses balm · paid ad" &
run "ad-ugc-tallow"       "$S/swipes/ugc-swipe/teardown/1-teardown/v6.md" "$S/swipes/ugc-swipe/source.mp4" "UGC tallow balm · family eczema story · paid ad" &
wait
run "ad-competitor-e"         "$S/swipes/competitor-e-whistleblower/teardown/1-teardown/v6.md" "$S/swipes/competitor-e-whistleblower/source.mp4" "competitor-e · Korean stick as topical filler · paid ad" &
run "org-aging-comedy"    "$S/swipes/organic-aging-comedy/teardown/1-teardown/v6.md" "$S/swipes/organic-aging-comedy/source.mp4" "Aging comedy · bikini try-on with cover-up · organic" &
wait
echo "BATCH COMPLETE"
