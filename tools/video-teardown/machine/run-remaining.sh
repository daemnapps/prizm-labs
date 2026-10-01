#!/bin/bash
cd "$(dirname "$0")"
for v in <person>-top-post organic-aging-comedy ai-swipe-luxe-foundation ugc-swipe; do
  echo; echo "════════════════ $v"
  extra=""
  [ "$v" = "<person>-top-post" ] && extra="--creator <person>"
  python3 run.py "runs/$v/source.mp4" --label "$v" $extra --video-count 3 --redo 2>&1
done
echo; echo "════════════════ ALL FOUR DONE"
