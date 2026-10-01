#!/bin/bash
# Finished ads in → Meta ad copy out, one set per ad.
#
#   machine/ads_to_copy.sh <folder-of-mp4s> <brand> <creator> <product-path> [label-prefix]
#
# For every video: a RECORDS teardown (triage + breakdown + audience, no
# brief — run.py --to 1b finishes clean by design), then the copy machine
# writes the Meta set (primary text + headlines + descriptions) from the
# record, comprehensive with the creative. Publish lifts it to output/;
# gdoc_out.py turns published copy into Google Docs afterwards.
#
# Born from Jackie's 7-ad delivery (2026-08-31) and the three snags that
# batch hit, all now fixed in the machines themselves: records runs exit
# clean at their stop; the brand tree is found by shape (no --brand-root
# needed); product paths resolve as file or folder in either tree.
set -u
SRC="${1:?folder of mp4s}"; BRAND="${2:?brand}"; CREATOR="${3:?creator}"
PROD="${4:?product path}"; PREFIX="${5:-$CREATOR}"
VT="$HOME/Projects/ai-workspace/components/video-teardown/machine"
CP="$HOME/Projects/ai-workspace/components/copywriter"
for v in "$SRC"/*.mp4 "$SRC"/*.mov; do
  [ -f "$v" ] || continue
  base=$(basename "$v"); base="${base%.*}"
  label="$PREFIX-$(echo "$base" | tr 'A-Z ' 'a-z-' | tr -cd 'a-z0-9-')"
  echo "=== $label ==="
  (cd "$VT" && python3 run.py "$v" --brand "$BRAND" --creator "$CREATOR" \
      --label "$label" --to 1b)
  slug=$(echo "$label" | tr 'A-Z' 'a-z')
  rec="$VT/runs/$slug/stages/1-teardown.md"
  [ -f "$rec" ] || rec="$VT/runs/$slug/1-teardown.md"
  [ -f "$rec" ] || { echo "NO RECORD for $label — teardown really failed"; continue; }
  (cd "$CP" && python3 machine/copy.py "$rec" --brand "$BRAND" --product "$PROD" \
      --video "$v" --channel "Meta (feed / Reels)" --write-as caption \
      --source-reference "$CREATOR · finished ad · $base" \
      --label "$label") || { echo "COPY FAILED $label"; continue; }
  (cd "$CP" && python3 machine/publish.py "$label")
  echo "=== done $label ==="
done
echo "BATCH COMPLETE — publish docs with: /usr/bin/python3 machine/gdoc_out.py --all [--folder <id>]"
