#!/usr/bin/env python3
"""Read any ad — a picture, a video or a piece of copy — on the creative controls.

Each asset goes to Gemini with prompts/read-controls-v1-damon.md, which binds
slices/controls.md, and comes back with a level and a one-line reason per dial
its medium uses, the emotion, the techniques, and the one thing the eye hits.
Levels are checked against each dial's scale; anything off-scale is flagged.

    python3 components/creative-controls/read.py <brand> <label> <manifest.json>
    python3 components/creative-controls/read.py one <picture> <out.json>

The manifest is a list of {"id", "kind": image|video|text, "path" or "text",
"group", "note"}. The first form writes runs/creative-controls/<brand>/<label>/scores.json
and re-reads only what is missing or failed; the second reads one picture into
the caller's own file (the image chain's stage 3 uses it). GEMINI_API_KEY is
read by name through components/keys/loader.py.
"""
import base64
import importlib.util
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import creative_controls as CC

HERE = Path(__file__).resolve().parent
PROMPT = HERE / "prompts" / "read-controls-v1-damon.md"
MODEL = "gemini-3.1-pro-preview"   # components/models/models.json
API = "https://generativelanguage.googleapis.com"
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
MEDIUM = {"image": "image", "video": "video", "text": "copy"}


def key(name):
    spec = importlib.util.spec_from_file_location("upright_keys_loader", str(CC.REPO / "components/keys/loader.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    v = mod.key(name, required=False)
    if not v:
        sys.exit("missing key %s — add the line %s=... to the one key file" % (name, name))
    return v.strip()


def call(url, body=None, headers=None, raw=False, tries=5):
    for n in range(1, tries + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers or {}), timeout=600) as r:
                b = r.read()
                return (b, dict(r.headers)) if raw else json.loads(b or b"{}")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and n < tries:
                time.sleep(8 * n)
                continue
            raise RuntimeError("Gemini %s: %r" % (e.code, e.read()[:300]))
        except urllib.error.URLError:
            if n < tries:
                time.sleep(8 * n)
                continue
            raise


def upload_video(k, path):
    blob = path.read_bytes()
    _, h = call("%s/upload/v1beta/files?key=%s" % (API, k), json.dumps({"file": {"display_name": path.name}}).encode(),
                {"X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                 "X-Goog-Upload-Header-Content-Length": str(len(blob)),
                 "X-Goog-Upload-Header-Content-Type": "video/mp4", "Content-Type": "application/json"}, raw=True)
    up = {k.lower(): v for k, v in h.items()}["x-goog-upload-url"]
    f = json.loads(call(up, blob, {"X-Goog-Upload-Command": "upload, finalize", "X-Goog-Upload-Offset": "0"}, raw=True)[0])["file"]
    while f.get("state") == "PROCESSING":
        time.sleep(5)
        f = call("%s/v1beta/%s?key=%s" % (API, f["name"], k))
    return f["uri"]


def prompt_for(asset):
    return (PROMPT.read_text()
            .replace("{creative_controls}", CC.SLICE.read_text())
            .replace("{asset_kind}", MEDIUM[asset["kind"]])
            .replace("{asset_note}", asset.get("note") or "none"))


def read_one(k, asset):
    parts = [{"text": prompt_for(asset)}]
    if asset["kind"] == "text":
        parts.append({"text": "THE COPY:\n" + asset["text"]})
    elif asset["kind"] == "video":
        parts.append({"file_data": {"mime_type": "video/mp4", "file_uri": upload_video(k, Path(asset["path"]))}})
    else:
        p = Path(asset["path"])
        parts.append({"inline_data": {"mime_type": MIME.get(p.suffix.lower(), "image/jpeg"),
                                      "data": base64.b64encode(p.read_bytes()).decode()}})
    body = {"contents": [{"parts": parts}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}
    r = call("%s/v1beta/models/%s:generateContent?key=%s" % (API, MODEL, k),
             json.dumps(body).encode(), {"Content-Type": "application/json"})
    got = json.loads(r["candidates"][0]["content"]["parts"][0]["text"])
    return got[0] if isinstance(got, list) and got else got   # the model sometimes wraps it in a list


def check(got, kind):
    """Every dial the medium uses present and on its scale; every emotion and technique a real one."""
    c = CC.load()
    problems = []
    for d in CC.dials(MEDIUM[kind]):
        v = (got.get("dials") or {}).get(d["id"])
        if not isinstance(v, dict) or v.get("level") not in [s["level"] for s in d["scale"]]:
            problems.append("%s: off-scale or missing (%r)" % (d["id"], v))
    known = {t["id"] for t in c["techniques"]}
    problems += ["technique not in the bank: %s" % t for t in got.get("techniques") or [] if t not in known]
    emotions = {e["id"] for e in c["emotions"]}
    for slot in ("primary", "secondary"):
        e = (got.get("emotion") or {}).get(slot)
        if e and e not in emotions:
            problems.append("emotion not in the bank: %s" % e)
    return problems


def main(brand, label, manifest):
    k = key("GEMINI_API_KEY")
    out = CC.REPO / "runs" / "creative-controls" / brand / label
    out.mkdir(parents=True, exist_ok=True)
    f = out / "scores.json"
    done = json.loads(f.read_text()) if f.exists() else {}
    todo = [a for a in json.loads(Path(manifest).read_text()) if a["id"] not in done or done[a["id"]]["problems"]]
    print("%d to read · %d already read · %s" % (len(todo), len(done), MODEL))

    def work(a):
        try:
            got = read_one(k, a)
            return a, got, check(got, a["kind"])
        except Exception as e:  # one bad asset never stops the batch
            return a, None, ["read failed: %s" % e]

    with ThreadPoolExecutor(4) as pool:
        for a, got, problems in pool.map(work, todo):
            done[a["id"]] = {"asset": a, "read": got, "problems": problems}
            f.write_text(json.dumps(done, indent=1, ensure_ascii=False))
            print("  %s: %s" % (a["id"], "ok" if not problems else "; ".join(problems)[:160]))
    print("→ %s" % f)


def one(path, out):
    k = key("GEMINI_API_KEY")
    asset = {"id": Path(path).stem, "kind": "image", "path": path, "note": "a swipe"}
    for _ in range(3):  # the reader names a technique off the bank now and then; a fresh read usually lands
        got = read_one(k, asset)
        problems = check(got, "image")
        if not problems:
            break
    # a technique off the bank is one label, never worth stopping a brief: it is dropped and kept beside the read
    known = {t["id"] for t in CC.load()["techniques"]}
    off = [t for t in got.get("techniques") or [] if t not in known]
    if off:
        got["techniques"] = [t for t in got["techniques"] if t in known]
        got["techniques_off_bank"] = off
    problems = check(got, "image")
    if problems:
        sys.exit("controls reading off-scale: " + "; ".join(problems))
    Path(out).write_text(json.dumps(got, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "one":
        one(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 4:
        main(*sys.argv[1:])
    else:
        sys.exit(__doc__)
