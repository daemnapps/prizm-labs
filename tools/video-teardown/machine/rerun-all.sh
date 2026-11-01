#!/bin/bash
cd "$(dirname "$0")"
RUNS="$(python3 -c 'import workdir; print(workdir.root())')"
fail=0
run(){
  echo; echo "════════════════ $1"
  extra=""
  [ "$1" = "creator-a-top-post" ] && extra="--creator creator-a"
  python3 run.py "$RUNS/$1/source.mp4" --label "$1" $extra --video-count 3 --redo 2>&1 || fail=1
}
for v in product-a-whistleblower ai-swipe-luxe-foundation ugc-swipe organic-aging-comedy creator-a-top-post; do
  run "$v"
done
echo; echo "════════════════ all five finished, fail=$fail"
exit $fail
