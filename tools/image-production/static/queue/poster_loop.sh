#!/bin/sh
cd "$(dirname "$0")"; set -a; . ~/.daemn/keys.env; set +a
while [ ! -f inbox/POSTER_STOP ]; do python3 poster_intake.py >> inbox/poster.log 2>&1; sleep 20; done
