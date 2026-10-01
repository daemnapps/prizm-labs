#!/usr/bin/env python3
"""Generate a character master from a WRITTEN identity — the description
route. This is the only route for creator-inspired characters (the
variation rule: a real creator's face is never an identity reference).

  python3 master.py <prompt-file.md> <out.png>

Uses the machine's still slot (text-to-image). ~$0.04 per master.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sequence import MODEL_STILL_T2I, fetch, key, media_urls, submit, wait  # noqa: E402


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    prompt = Path(sys.argv[1]).read_text()
    out = Path(sys.argv[2])
    k = key()
    print("master (t2i, description route)...", flush=True)
    res = wait(*submit(MODEL_STILL_T2I, {
        "prompt": prompt, "num_images": 1,
        "image_size": "portrait_16_9"}, k), k, "master")
    out.parent.mkdir(parents=True, exist_ok=True)
    fetch(media_urls(res)[0], out)
    subprocess.run(["sips", "-Z", "2048", str(out)], capture_output=True)
    print(f"saved {out}", flush=True)


if __name__ == "__main__":
    main()
