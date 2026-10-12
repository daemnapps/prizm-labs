#!/bin/sh
# keep filing whatever results.json holds, one pass at a time, until told to stop
cd "$(dirname "$0")"
set -a; for f in ../../../../.env "$HOME/.daemn/keys.env"; do [ -f "$f" ] && { . "$f"; break; }; done; set +a
while kill -0 "$1" 2>/dev/null; do sleep 10; done
while [ ! -f inbox/STOP ]; do python3 intake_jobs.py >> inbox/intake.log 2>&1; sleep 45; done
