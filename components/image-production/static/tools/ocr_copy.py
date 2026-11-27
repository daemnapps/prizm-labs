#!/usr/bin/env python3
"""Read the words off finished ads — headline, subhead, offer bar — so the
record can carry what an asset SAID when nobody declared it (R5, backfill).

    ocr_copy.py <runs-root> --out _ocr.json

Uses the same vision judge as the gate (gemini_image.py). Every lift is
marked `provenance: ocr` downstream; a transcription is evidence, never a
declaration. Skips files already in --out, so it resumes."""
import argparse, json, subprocess, sys, tempfile
from pathlib import Path

GEMINI = Path(__file__).resolve().parent / "gemini_image.py"
PROMPT = """Transcribe the text on this advertisement, exactly as printed —
no corrections, no completions. Reply as JSON and nothing else:
{"headline": "...", "subhead": "...", "offer_bar": "...", "other": ["..."]}
Use "" for a slot that is not there. The offer bar is the strip near the
bottom carrying the guarantee, price or call to action."""


def lift(img):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(PROMPT); pf = f.name
    out = tempfile.NamedTemporaryFile("r", suffix=".md", delete=False).name
    r = subprocess.run([sys.executable, str(GEMINI), "--prompt-file", pf, "--image", str(img), "--out", out],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return {"_error": r.stderr.strip()[:200]}
    raw = Path(out).read_text()
    try:
        return json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
    except Exception:
        return {"_error": "unreadable", "_raw": raw[:300]}


def main():
    a = argparse.ArgumentParser(); a.add_argument("root"); a.add_argument("--out", required=True); o = a.parse_args()
    outp = Path(o.out); done = json.loads(outp.read_text()) if outp.is_file() else {}
    todo = [p for mf in Path(o.root).rglob("manifest.json") for row in json.loads(mf.read_text()).get("ads", []) if "file" in row
            for p in [mf.parent / row["file"]] if p.is_file() and row["file"] not in done]
    print(f"{len(done)} done, {len(todo)} to lift", flush=True)
    for i, p in enumerate(todo, 1):
        done[p.name] = lift(p)
        outp.write_text(json.dumps(done, indent=1, ensure_ascii=False) + "\n")
        print(f"{i}/{len(todo)} {p.name[:70]} → {str(done[p.name].get('headline', done[p.name].get('_error')))[:50]}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
