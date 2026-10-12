#!/bin/sh
cd "$(dirname "$0")"; set -a; for f in ../../../../.env "$HOME/.daemn/keys.env"; do [ -f "$f" ] && { . "$f"; break; }; done; set +a
while [ ! -f inbox/STOP ]; do python3 poll.py >> inbox/intake.log 2>&1; sleep 30; done
