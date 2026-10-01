#!/usr/bin/env python3
"""Text-in / text-out Gemini run, for the stages after the video teardown.

The replication spec takes a teardown record and returns a spec — no video
involved, so `gemini_breakdown.py` (which requires a file upload) can't run
it. Same key file, same model default, same output convention.

Usage:
  python3 gemini_text.py --prompt-file prompts/replication-v1.txt \
      --var teardown_record=results/ulta--teardown-v2--gemini-3-flash-preview.txt \
      --out results/ulta--replication-v1--gemini-3-flash-preview.txt

Every {placeholder} in the prompt must be supplied via --var name=path, or
the run stops before spending anything.
"""

import argparse, json, re, sys, time, urllib.request
from pathlib import Path

BASE = "https://generativelanguage.googleapis.com"


def key():
    for line in (Path.home() / ".gemini.env").read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("GEMINI_API_KEY not found in ~/.gemini.env")


def req(url, data=None, headers=None, tries=4):
    for attempt in range(1, tries + 1):
        try:
            r = urllib.request.Request(url, data=data, headers=headers or {})
            with urllib.request.urlopen(r, timeout=600) as resp:
                return json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries:
                wait = 10 * attempt
                print(f"  HTTP {e.code}, retry {attempt}/{tries - 1} in {wait}s",
                      file=sys.stderr)
                time.sleep(wait)
                continue
            sys.exit(f"HTTP {e.code}: {e.read()[:500].decode('utf8', 'replace')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--var", action="append", default=[],
                    metavar="NAME=PATH",
                    help="fill {NAME} in the prompt with the contents of PATH")
    ap.add_argument("--model", default="gemini-3-flash-preview")
    ap.add_argument("--out")
    a = ap.parse_args()

    pf = Path(a.prompt_file)
    prompt = pf.read_text()

    supplied = {}
    for pair in a.var:
        if "=" not in pair:
            sys.exit(f"--var needs NAME=PATH, got: {pair}")
        name, path = pair.split("=", 1)
        supplied[name] = Path(path).read_text()

    # Check the PROMPT's own placeholders, before substituting. Checking after
    # substitution false-alarms whenever a supplied file happens to mention
    # brace syntax — e.g. a brand file that documents its own variable name.
    wanted = set(re.findall(r"\{([a-z_]+)\}", prompt))
    missing = sorted(wanted - set(supplied))
    if missing:
        sys.exit(f"unfilled placeholders: {', '.join(missing)}\n"
                 f"supply each with --var NAME=PATH")

    for name, body in supplied.items():
        prompt = prompt.replace("{" + name + "}", body)

    k = key()
    print(f"[1/2] sending {len(prompt)} chars to {a.model}")
    url = f"{BASE}/v1beta/models/{a.model}:generateContent?key={k}"
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    r = req(url, data=body, headers={"Content-Type": "application/json"})
    try:
        txt = "".join(p.get("text", "")
                      for p in r["candidates"][0]["content"]["parts"])
    except (KeyError, IndexError):
        sys.exit(f"unexpected response: {json.dumps(r)[:800]}")

    header = (f"<!-- prompt: {pf.name} | model: {a.model} | "
              f"vars: {','.join(supplied) or 'none'} | run: "
              f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} -->\n\n")
    out = Path(a.out) if a.out else (
        Path(__file__).parent / "results" /
        f"{pf.stem}--{a.model}.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(header + txt)
    print(txt[:2000])
    print(f"[2/2] full output → {out}")


if __name__ == "__main__":
    main()
