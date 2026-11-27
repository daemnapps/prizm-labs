#!/bin/zsh
# run-daily.sh — the daily footage-library pass for one machine, any brands.
#
#   ASSET_LIBRARY_CHECKOUT=<clean checkout of this repo> ASSET_LIBRARY_BRANDS="<brand> <brand>" \
#   ASSET_LIBRARY_DAILY_USD=2.00 [ASSET_LIBRARY_KEY_ENV=<env var holding the model key>] \
#   zsh components/asset-index/library/run-daily.sh
#
# Run it from a scheduler (launchd, cron) against a CLEAN checkout that nothing else edits, never a working
# tree people use: it pulls origin/main, runs library/index_new.py per brand inside the daily cap (map new
# Drive files, describe and check new footage, find shot changes, rebuild), then commits and pushes only
# runs/asset-index/<brand>/. The model key is read by name: the shared loader's GEMINI_API_KEY, or the
# variable named in ASSET_LIBRARY_KEY_ENV. A key out of credit pauses the paid steps; the free ones still run.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
WS="${ASSET_LIBRARY_CHECKOUT:?set ASSET_LIBRARY_CHECKOUT to a clean checkout}"
# brands: ASSET_LIBRARY_BRANDS, else every brand whose brands/<brand>/footage-library.json has daily.on (daily_brands.py)
BRANDS=(${=ASSET_LIBRARY_BRANDS:-$(cd "$WS" && /usr/bin/python3 components/asset-index/library/daily_brands.py | cut -d' ' -f1)})
CAP="${ASSET_LIBRARY_DAILY_USD:-2.00}"
PY="${ASSET_LIBRARY_PYTHON:-/usr/bin/python3}"
say() { echo "$(date '+%Y-%m-%d %H:%M:%S')  $*"; }

for i in 1 2 3; do
  git -C "$WS" pull -q --rebase origin main && break
  say "pull failed (try $i); waiting a minute"; sleep 60
done

KEYARGS=()
[[ -n "$ASSET_LIBRARY_KEY_ENV" && -n "${(P)ASSET_LIBRARY_KEY_ENV}" ]] && KEYARGS=(--key-env "$ASSET_LIBRARY_KEY_ENV")

for b in $BRANDS; do
  say "pass: $b, cap \$$CAP, key ${ASSET_LIBRARY_KEY_ENV:-GEMINI_API_KEY}"
  (cd "$WS" && "$PY" -B components/asset-index/library/index_new.py --brand "$b" --budget "$CAP" $KEYARGS) \
    || say "index_new failed for $b"
  git -C "$WS" add "runs/asset-index/$b"
  if ! git -C "$WS" diff --cached --quiet; then
    git -C "$WS" commit -q -m "asset-index: daily footage-library pass, $b, $(date '+%Y-%m-%d')" || say "commit refused for $b"
  fi
done

for i in 1 2 3; do
  git -C "$WS" pull -q --rebase origin main && git -C "$WS" push -q origin HEAD:main && { say "pushed"; break; }
  say "push failed (try $i); waiting a minute"; sleep 60
done
