#!/bin/bash
cd "$(dirname "$0")"
fail=0
run(){
  echo; echo "════════════════ $1"
  extra=""
  [ "$1" = "<person>-top-post" ] && extra="--creator <person>"
  python3 run.py "runs/$1/source.mp4" --label "$1" $extra --video-count 3 --redo 2>&1 || fail=1
}
for v in <competitor>-whistleblower ai-swipe-luxe-foundation ugc-swipe organic-aging-comedy <person>-top-post; do
  run "$v"
done
echo; echo "════════════════ all five finished, fail=$fail"
exit $fail
