#!/bin/bash
cd "$(dirname "$0")"
RUNS="$(python3 -c 'import workdir; print(workdir.root())')"
fail=0
run(){
  echo; echo "════════════════ $1"
  extra=""
  [ "$1" = "mara-top-post" ] && extra="--creator mara-creator"
  python3 run.py "$RUNS/$1/source.mp4" --label "$1" $extra --video-count 3 --redo 2>&1 || fail=1
}
for v in <competitor>-whistleblower ai-swipe-luxe-foundation ugc-swipe organic-aging-comedy mara-top-post; do
  run "$v"
done
echo; echo "════════════════ all five finished, fail=$fail"
exit $fail
