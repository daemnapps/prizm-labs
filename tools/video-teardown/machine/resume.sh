#!/bin/bash
cd "$(dirname "$0")"
RUNS="$(python3 -c 'import workdir; print(workdir.root())')"
fail=0
for r in ai-swipe-luxe-foundation organic-aging-comedy ugc-swipe creator-a-top-post; do
  echo; echo "════════ $r"
  v="$RUNS/$r/source.mp4"
  extra=""
  [ "$r" = "creator-a-top-post" ] && extra="--creator creator-a"
  python3 run.py "$v" --label "$r" $extra --from 3 --video-count 3 2>&1 || fail=1
done
echo; echo "════════ done, fail=$fail"
exit $fail
