#!/bin/bash
# Run the copy chain over a list of sources, a few at a time.
# Usage: machine/batch.sh <brand> <product-file>      (edit the list below)
#   <brand>         folder name under brands/ — there is no default brand
#   <product-file>  e.g. brands/<brand>/products/<product>.md
# Run from the package root (components/copywriter). Logs land in logs/.
BRAND="$1"
PROD="$2"
if [ -z "$BRAND" ] || [ -z "$PROD" ]; then
  echo "usage: machine/batch.sh <brand> <product-file>   — name the brand; nothing is assumed" >&2
  exit 2
fi
WS="${AI_WORKSPACE:-$HOME/Projects/ai-workspace}"          # the tree holding brands/
if [ ! -d "$WS/brands/$BRAND" ]; then
  echo "no brands/$BRAND under $WS" >&2
  exit 2
fi
S="$HOME/Library/CloudStorage/GoogleDrive-${DRIVE_ACCOUNT}/Shared drives/Shared Assets/swipe-paid"
run () {  # run <label> <teardown-path> <video-path> <reference>
  python3 machine/copy.py "$2" --brand "$BRAND" --brand-root "$WS" --product "$PROD" \
    --source-reference "$4" ${3:+--video "$3"} --channel "Meta (feed / Reels)" \
    --label "$1" --hooks 5 > "logs/$1.log" 2>&1
  echo "  done: $1"
}
mkdir -p logs
run "ad-luxe-foundation"  "$S/swipes/ai-swipe-luxe-foundation/teardown/1-teardown/v6.md"  "$S/swipes/ai-swipe-luxe-foundation/source.mp4"  "Luxe foundation · ex-husband run-in · paid ad" &
run "ad-<competitor>"    "$S/swipes/swipe-<competitor>-158486664/teardown/1-teardown/v6.md" "$S/swipes/swipe-<competitor>-158486664/source.mp4" "<competitor> · mother endorses balm · paid ad" &
run "ad-ugc-tallow"       "$S/swipes/ugc-swipe/teardown/1-teardown/v6.md" "$S/swipes/ugc-swipe/source.mp4" "UGC tallow balm · family eczema story · paid ad" &
wait
run "ad-<competitor>"         "$S/swipes/<competitor>-whistleblower/teardown/1-teardown/v6.md" "$S/swipes/<competitor>-whistleblower/source.mp4" "<competitor> · Korean stick as topical filler · paid ad" &
run "org-aging-comedy"    "$S/swipes/organic-aging-comedy/teardown/1-teardown/v6.md" "$S/swipes/organic-aging-comedy/source.mp4" "Aging comedy · bikini try-on with cover-up · organic" &
wait
echo "BATCH COMPLETE"
