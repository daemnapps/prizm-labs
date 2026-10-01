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

import argparse, base64, json, mimetypes, re, sys, time, urllib.request
from pathlib import Path

BASE = "https://generativelanguage.googleapis.com"


def fill(template, pairs):
    """Substitute every {name} the template asks for, from name=path pairs.

    Same contract as tools/claude_text.py's fill() — stage 1 is now bound to
    doctrine slices (`components/marketing-doctrine/slices/`) for MARKET
    STATE, and this is what lets it read `{awareness_levels}` etc. the same
    way every text stage already reads `{teardown_record}`.
    """
    wants = set(re.findall(r"\{([a-z_]+)\}", template))
    given = {n for n, _ in pairs}
    unmet = sorted(wants - given)
    if unmet:
        sys.exit("prompt asks for " + ", ".join(unmet) + " — nothing supplies it")

    out, missing = template, []
    for name, path in pairs:
        f = Path(path)
        if not f.exists():
            missing.append(f"{name}={path}")
            continue
        out = out.replace("{" + name + "}", f.read_text(errors="replace"))
    if missing:
        sys.exit("missing input files: " + ", ".join(missing))
    return out


def key():
    for line in (Path.home() / ".gemini.env").read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("GEMINI_API_KEY not found in ~/.gemini.env")


def req(url, data, headers, tries=4):
    for attempt in range(1, tries + 1):
        try:
            r = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(r, timeout=900) as resp:
                return json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries:
                wait = 10 * attempt
                print(f"  HTTP {e.code}, retry {attempt}/{tries - 1} in {wait}s",
                      file=sys.stderr)
                time.sleep(wait)
                continue
            sys.exit(f"HTTP {e.code}: {e.read()[:600].decode('utf8', 'replace')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--image", action="append", required=True,
                    help="repeat for a multi-image call; order is preserved")
    ap.add_argument("--model", default="gemini-3.1-pro-preview")
    ap.add_argument("--var", action="append", default=[],
                    help="name=path, repeatable — same contract as claude_text.py")
    ap.add_argument("--out")
    a = ap.parse_args()

    pairs = []
    for v in a.var:
        if "=" not in v:
            sys.exit(f"--var wants name=path, got {v!r}")
        n, p = v.split("=", 1)
        pairs.append((n, p))

    pf = Path(a.prompt_file)
    prompt = fill(pf.read_text(), pairs) if pairs else pf.read_text()

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
