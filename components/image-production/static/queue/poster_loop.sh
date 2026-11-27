#!/bin/sh
cd "$(dirname "$0")"; while [ ! -f inbox/POSTER_STOP ]; do python3 poster_intake.py >> inbox/poster.log 2>&1; sleep 20; done
