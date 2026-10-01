#!/usr/bin/env python3
"""Image-in / text-out Gemini run — the static-ad twin of gemini_breakdown.py.

Images go inline (base64), not through the Files API: ad creatives are small,
and the video path's ffprobe audio pre-flight would inject a false
"this file has no audio track" fact into an image prompt.

Usage:
  python3 gemini_image.py --prompt-file P.md --image a.png [--image b.png ...] \
      [--model gemini-3.1-pro-preview] --out out.md

Multiple --image flags are sent in one call, in the order given, each labeled
"IMAGE 1", "IMAGE 2", ... so the prompt can refer to them by number.
Reads GEMINI_API_KEY from ~/.gemini.env.
"""

import argparse, os, base64, json, mimetypes, sys, time, urllib.request
from pathlib import Path

BASE = "https://generativelanguage.googleapis.com"


def key():
    # the environment first (the vault is loaded into it), then the old file
    k = os.environ.get("GEMINI_API_KEY")
    if k:
        return k.strip()
    f = Path.home() / ".gemini.env"
    if f.exists():
        for line in f.read_text().splitlines():
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip()
    sys.exit("GEMINI_API_KEY not in the environment or ~/.gemini.env")


# One judge call is a prompt and one picture. It answers in seconds or it is
# stuck. 900s x 4 tries meant a stalled socket blocked the whole queue for the
# best part of an hour with nothing in the log (2026-09-10: one intake held the
# line 48 minutes). Fail fast, retry a few times, then say so.
TIMEOUT = int(os.environ.get("GEMINI_TIMEOUT", "120"))


def req(url, data, headers, tries=4):
    last = "no attempt made"
    for attempt in range(1, tries + 1):
        try:
            r = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(r, timeout=TIMEOUT) as resp:
                return json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries:
                wait = 5 * attempt
                print(f"  HTTP {e.code}, retry {attempt}/{tries - 1} in {wait}s",
                      file=sys.stderr)
                time.sleep(wait)
                continue
            sys.exit(f"HTTP {e.code}: {e.read()[:600].decode('utf8', 'replace')}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            # a dropped network is the common case and it used to escape as a
            # raw traceback, which is what nine headline audits recorded
            last = f"{type(e).__name__}: {e}"
            if attempt < tries:
                wait = 5 * attempt
                print(f"  {last[:80]}, retry {attempt}/{tries - 1} in {wait}s",
                      file=sys.stderr)
                time.sleep(wait)
                continue
    sys.exit(f"network: gave up after {tries} tries — {last}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--image", action="append", required=True,
                    help="repeat for a multi-image call; order is preserved")
    ap.add_argument("--model", default="gemini-3.1-pro-preview")
    ap.add_argument("--out")
    a = ap.parse_args()

    pf = Path(a.prompt_file)
    prompt = pf.read_text()

    parts = []
    for i, p in enumerate(a.image, 1):
        path = Path(p)
        mime = mimetypes.guess_type(str(path))[0] or "image/png"
        if not mime.startswith("image"):
            sys.exit(f"{path} is not an image ({mime})")
        blob = path.read_bytes()
        print(f"  IMAGE {i}: {path.name} ({len(blob)//1024} KB, {mime})")
        if len(a.image) > 1:
            parts.append({"text": f"IMAGE {i} — filename: {path.name}"})
        parts.append({"inline_data": {"mime_type": mime,
                                      "data": base64.b64encode(blob).decode()}})
    parts.append({"text": prompt})

    k = key()
    print(f"[1/2] sending {len(a.image)} image(s) + {len(prompt)} chars "
          f"to {a.model}")
    r = req(f"{BASE}/v1beta/models/{a.model}:generateContent?key={k}",
            data=json.dumps({"contents": [{"parts": parts}],
                             "generationConfig": {"temperature": 0.2}}).encode(),
            headers={"Content-Type": "application/json"})
    try:
        txt = "".join(p.get("text", "")
                      for p in r["candidates"][0]["content"]["parts"])
    except (KeyError, IndexError):
        sys.exit(f"unexpected response: {json.dumps(r)[:800]}")

    header = (f"<!-- images: {', '.join(Path(p).name for p in a.image)} | "
              f"prompt: {pf.name} | model: {a.model} | run: "
              f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} -->\n\n")
    out = Path(a.out) if a.out else pf.parent / f"{pf.stem}--{a.model}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(header + txt)
    print(f"[2/2] {len(txt)} chars → {out}")


if __name__ == "__main__":
    main()
