#!/bin/bash
cd "$(dirname "$0")"
fail=0
run(){
  echo; echo "════════ $2"
  python3 run.py "$1" --label "$2" ${3:+--creator "$3"} --video-count 3 2>&1 || fail=1
}
# <competitor> first: it only needs its frames redone, and it is the fastest way to
# see whether generation is actually working again before three more videos run.
run "runs/<competitor>-whistleblower/source.mp4" "<competitor>-whistleblower"
run "~/Downloads/Swipe Files/AQOaxJLMYLqDvUsfqNOxF1vjheFaAqTelVCjmBl6MOmj4DqkJ8g4uX7vsH4mlmLQlBMcQfkmdXZMM1aJVJas0PXMsvNd5Od1qYu5Pp28xg.mp4" "ai-swipe-luxe-foundation"
run "~/Downloads/Swipe Files/SnapInsta.to_AQMv9b2YR1dNgY3VSvDdbRHAD5Mw3bCy3N2QJCLFmv6zlVvB3Zisj3zzc-wh7hRYEsIwJPsRthtWG28WggNbb-2EnE9s87yOudlE_gk.mp4" "organic-aging-comedy"
run "~/Downloads/Swipe Files/AQMHag8EFMqTkoN94LgTp1tiw5jMg_byyRQQ8qos5y8qis9-kWonRI0lmB2bJWKaL-9E9LZQ1G3nYuvGLnj6zd5hZWtuD2fvO34Exh5YVQ.mp4" "ugc-swipe"
run "~/Library/CloudStorage/GoogleDrive-${DRIVE_ACCOUNT}/Shared drives/Shared Assets/creators/<person>/posts/01-DZAllXxMoho/video.mp4" "<person>-top-post" "<person>"
echo; echo "════════ batch finished with fail=$fail"
exit $fail
