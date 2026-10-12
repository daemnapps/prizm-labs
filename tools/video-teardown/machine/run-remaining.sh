#!/bin/bash
cd "$(dirname "$0")"
RUNS="$(python3 -c 'import workdir; print(workdir.root())')"
for v in mara-top-post organic-aging-comedy ai-swipe-luxe-foundation ugc-swipe; do
  echo; echo "════════════════ $v"
  extra=""
  [ "$v" = "mara-top-post" ] && extra="--creator mara-creator"
  python3 run.py "$RUNS/$v/source.mp4" --label "$v" $extra --video-count 3 --redo 2>&1
done
echo; echo "════════════════ ALL FOUR DONE"
