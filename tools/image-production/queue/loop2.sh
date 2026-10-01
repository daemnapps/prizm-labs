#!/bin/sh
cd "$(dirname "$0")"; set -a; . ~/.daemn/keys.env; set +a
while [ ! -f inbox/STOP ]; do python3 poll.py >> inbox/intake.log 2>&1; sleep 30; done
