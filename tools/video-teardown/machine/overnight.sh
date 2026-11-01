#!/bin/bash
cd "$(dirname "$0")"
RUNS="$(python3 -c 'import workdir; print(workdir.root())')"
# Shared Assets on whoever's Drive is signed in on this Mac (components/brandpath/drive_index.py mount())
SHARED="$(python3 -c 'import sys; sys.path.append("../../brandpath"); import drive_index; print(drive_index.mount() or "")')"
fail=0
run(){
  echo; echo "════════ $2"
  python3 run.py "$1" --label "$2" ${3:+--creator "$3"} --video-count 3 2>&1 || fail=1
}
# Product-A first: it only needs its frames redone, and it is the fastest way to
# see whether generation is actually working again before three more videos run.
run "$RUNS/product-a-whistleblower/source.mp4" "product-a-whistleblower"
run "$HOME/Downloads/Swipe Files/AQOaxJLMYLqDvUsfqNOxF1vjheFaAqTelVCjmBl6MOmj4DqkJ8g4uX7vsH4mlmLQlBMcQfkmdXZMM1aJVJas0PXMsvNd5Od1qYu5Pp28xg.mp4" "ai-swipe-luxe-foundation"
run "$HOME/Downloads/Swipe Files/SnapInsta.to_AQMv9b2YR1dNgY3VSvDdbRHAD5Mw3bCy3N2QJCLFmv6zlVvB3Zisj3zzc-wh7hRYEsIwJPsRthtWG28WggNbb-2EnE9s87yOudlE_gk.mp4" "organic-aging-comedy"
run "$HOME/Downloads/Swipe Files/AQMHag8EFMqTkoN94LgTp1tiw5jMg_byyRQQ8qos5y8qis9-kWonRI0lmB2bJWKaL-9E9LZQ1G3nYuvGLnj6zd5hZWtuD2fvO34Exh5YVQ.mp4" "ugc-swipe"
run "$SHARED/tools/video-teardown/creators/creator-a/posts/01-DZAllXxMoho/video.mp4" "creator-a-top-post" "creator-a"
echo; echo "════════ batch finished with fail=$fail"
exit $fail
