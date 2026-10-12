#!/usr/bin/env bash
# Run one prompt against one video. Video may live anywhere on the machine;
# the output always lands in results/ inside the repo.
#
#   ./run-prompt.sh <video> <prompt-file> [label] [model]
#
# label is a short readable name for the video (scraper filenames are
# unreadable hashes); defaults to the filename stem, truncated.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
video="${1:?usage: run-prompt.sh <video> <prompt-file> [label] [model]}"
prompt="${2:?usage: run-prompt.sh <video> <prompt-file> [label] [model]}"
label="${3:-}"
model="${4:-gemini-3-flash-preview}"

vstem="${label:-$(basename "${video%.*}" | cut -c1-24)}"
pstem="$(basename "${prompt%.*}")"
mkdir -p "$here/results"
out="$here/results/${vstem}--${pstem}--${model}.txt"

python3 "$here/gemini_breakdown.py" "$video" \
  --prompt-file "$prompt" --model "$model" --out "$out"
