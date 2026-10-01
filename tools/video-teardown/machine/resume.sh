#!/bin/bash
cd "$(dirname "$0")"
fail=0
for r in ai-swipe-luxe-foundation organic-aging-comedy ugc-swipe <person>-top-post; do
  echo; echo "════════ $r"
  v="runs/$r/source.mp4"
  extra=""
  [ "$r" = "<person>-top-post" ] && extra="--creator <person>"
  python3 run.py "$v" --label "$r" $extra --from 3 --video-count 3 2>&1 || fail=1
done
echo; echo "════════ done, fail=$fail"
exit $fail
