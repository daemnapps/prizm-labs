#!/bin/bash
cd "$(dirname "$0")"
RUNS="$(python3 -c 'import workdir; print(workdir.root())')"
for v in creator-top-post organic-aging-comedy ai-swipe-luxe-foundation ugc-swipe; do
  echo; echo "════════════════ $v"
  extra=""
  [ "$v" = "creator-top-post" ] && extra="--creator creator-zane"
  python3 run.py "$RUNS/$v/source.mp4" --label "$v" $extra --video-count 3 --redo 2>&1
done
echo; echo "════════════════ ALL FOUR DONE"
