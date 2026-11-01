#!/bin/bash
cd "$(dirname "$0")"
WS="$(cd ../../.. && pwd)"   # the workspace checkout this script sits in
export DAEMN_HAND_DIR="$WS/runs/video-teardown/brand-a/_hand/sprtn-18000-men"
python3 run.py "$WS/components/swipe-organic/records/swipe-videos/sprtn-171188262/video.mp4" --brand brand-a --product flex --route ai --label sprtn-18000-men --for-avatar fed-up-king --no-frames --approve-structure 8,9 "$@"
