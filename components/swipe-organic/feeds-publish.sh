#!/bin/bash
# My Feeds, public — export the feeds and publish them to daemn.co/feeds/.
#
#   components/swipe-organic/feeds-publish.sh
#
# Never scheduled: releasing to the public is a person's act (the developer, 2026-10-07;
# O5b (export replace is deploy) in components/system-integration/conventions.md).
# It never pulls anything and never spends: feedsexport.py only reads what the
# last Pull already filed. It publishes ONLY docs/feeds/data, and only when the
# site checkout is on main with nothing else in progress.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
SITE="${PRIZM_SITE:-$HOME/Projects/prizm-labs}"
cd "$SITE"
git fetch -q origin
branch=$(git rev-parse --abbrev-ref HEAD)
[ "$branch" = main ] || { echo "the site checkout is on '$branch', not main — not publishing"; exit 1; }
if [ -n "$(git status --porcelain -- . ':!docs/feeds/data')" ]; then
  echo "the site checkout has other work in progress — not publishing"; exit 1
fi
git merge -q --ff-only origin/main
python3 "$HERE/feedsexport.py" --site "$SITE/docs/feeds/data"
git add -A docs/feeds/data
if git diff --cached --quiet; then echo "nothing new to publish"; exit 0; fi
git commit -q -m "My Feeds: data $(date +%F)"
git push -q origin main
echo "published — daemn.co/feeds/ updates in a minute or two"
