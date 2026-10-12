#!/usr/bin/env python3
"""Does the picture show what the headline says?

The gate never asked this. It read the type, the bar and the product, and let
through ads whose words and picture argue different things. This asks the
vision judge one question per delivered picture and writes the answer beside
the queue, so the failures are a list Damon can act on.
"""
import json, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "tools"))
import queue as Q
GEM = HERE.parent / "tools/gemini_image.py"
OUT = HERE / "headline-audit.json"

Q_TMPL = """Look at this advertisement. Its printed headline reads:

    "{h}"

Answer three things, briefly and only from what you can see:
1. VERDICT: MATCH or MISMATCH — does the photograph show what that headline is
   about? The problem it names, the person it describes, the moment it claims.
   MISMATCH if the words and the picture are arguing different things, or if
   what the headline names is nowhere in the picture.
2. SEEN: one sentence on what is actually in the picture.
3. WHY: one sentence on why that is a match or is not.

Reply as JSON only: {{"verdict":"MATCH"|"MISMATCH","seen":"...","why":"..."}}"""


def ask(img, headline):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(Q_TMPL.format(h=headline)); pf = f.name
    o = tempfile.NamedTemporaryFile("r", suffix=".md", delete=False).name
    r = subprocess.run([sys.executable, str(GEM), "--prompt-file", pf, "--image", str(img), "--out", o],
                       capture_output=True, text=True)
    if r.returncode: return {"verdict": "UNKNOWN", "why": r.stderr.strip()[:150]}
    raw = Path(o).read_text()
    try: return json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
    except Exception: return {"verdict": "UNKNOWN", "why": raw[:150]}


def main():
    done = json.loads(OUT.read_text()) if OUT.is_file() else {}
    ocr = json.loads((Q.RUNS_ROOT / "_ocr.json").read_text())
    todo = []
    for run in Q.RUNS:
        for mf in sorted((Q.RUNS_ROOT / run / "ads").glob("*/manifest.json")):
            man = json.loads(mf.read_text())
            spec = json.loads((Q.RUNS_ROOT / run / "batch.json").read_text())
            ad = next((a for a in spec["ads"] if a["slug"] == mf.parent.name), {})
            for row in man.get("ads", []):
                f = mf.parent / row["file"]
                # an UNKNOWN is a crash, not an answer — resume retries it,
                # or a network blip would silently become a permanent verdict
                if not f.is_file(): continue
                if done.get(row["name"], {}).get("verdict") in ("MATCH", "MISMATCH"): continue
                h = ((ad.get("copy") or {}).get("headline") or ocr.get(row["file"], {}).get("headline") or "").replace("\n", " ").strip()
                if not h: continue
                todo.append((row["name"], f, h, man["talent"], man["format"], mf.parent.name))
    print(f"{len(done)} judged, {len(todo)} to go", flush=True)
    for i, (name, f, h, man, fmt, slug) in enumerate(todo, 1):
        a = ask(f, h)
        done[name] = {"headline": h, "man": man, "format": fmt, "unit": slug, **a}
        OUT.write_text(json.dumps(done, indent=1, ensure_ascii=False) + "\n")
        print(f"{i}/{len(todo)} {a.get('verdict','?'):9} {man:7} {fmt:16} {h[:44]}", flush=True)
    bad = [k for k, v in done.items() if v.get("verdict") == "MISMATCH"]
    print(f"\nDONE — {len(done)} judged, {len(bad)} mismatched", flush=True)


if __name__ == "__main__":
    main()
