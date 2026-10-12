#!/bin/sh
cd "$(dirname "$0")"; set -a; for f in ../../../../.env "$HOME/.daemn/keys.env"; do [ -f "$f" ] && { . "$f"; break; }; done; set +a
while [ ! -f inbox/POSTER_STOP ]; do python3 poster_intake.py >> inbox/poster.log 2>&1; sleep 20; done
