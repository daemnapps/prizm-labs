#!/usr/bin/env python3
"""Tag every asset in a saved pull on the creative-diversity dimensions.

Reads only the saved pull (runs/creative-diversity/<brand>/<date>/) — it never
calls Meta. Each asset's video or image goes to Gemini with the prompt
prompts/tag-ad-v1-damon.md, filled with the brand's real lists. Tags are
checked against those lists; anything off-list is kept as `new:` or flagged.

    python3 components/creative-diversity/tag.py brand-a [date]

Writes tags.json beside the pull. Re-running only tags what is missing.
"""
import base64
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import daemn_keys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PROMPT = HERE / "prompts" / "tag-ad-v1-damon.md"
MODEL = "gemini-3.8-flash"
API = "https://generativelanguage.googleapis.com"
LIB = ROOT / "components" / "elements" / "library"


def rows(name):
    return json.loads((LIB / f"{name}.json").read_text())["rows"]


def ids(name):
    return [r["id"] for r in rows(name)]


def first_line(path, label):
    for line in path.read_text().splitlines():
        if label.lower() in line.lower():
            return re.sub(r"^[-*\s]*\**[^:]*:\**\s*", "", line).strip()
    return ""


def lists(brand):
    b = ROOT / "brands" / brand
    av = json.loads((b / "core-avatars" / "avatars.json").read_text())["avatars"]
    who = []
    for a in av:
        for sub in a.get("sub_avatars") or []:
            card = next((b / a["folder"] / "sub-avatars").glob(f"sub-*-{sub}.md"), None)
            desire = first_line(card, "core desire") if card else ""
            who.append(f"- `{sub}` ({a['id']}): {desire[:200]}")
        if not a.get("sub_avatars"):
            who.append(f"- `{a['id']}` (core, no sub-avatars yet): {a.get('label')}")
    ang = json.loads((b / "strategy" / "angles.json").read_text())
    ang_rows = ang.get("angles") or [v for v in ang.values() if isinstance(v, list)][0]
    angles = [f"- `{r['id']}`: {(r.get('what') or r.get('name') or '')[:160]}"
              for r in ang_rows if r.get("status") == "active"]
    settings = json.loads((b / "strategy" / "settings.json").read_text())["settings"]
    core = json.loads((b / "brand-identity" / "core-message" / "core-message.json").read_text())["core"]
    dims = json.loads((HERE / "dimensions.json").read_text())
    offer = json.loads((ROOT / "brands" / brand / "strategy" / "offer-page.json").read_text())
    pos = (b / "brand-identity" / "position.md").read_text()
    stage = next((l for l in pos.splitlines() if "MARKET STAGE" in l), "unknown")
    aw = "\n".join(f"- `{r['id']}`: {r.get('what', '')[:140]}" for r in rows("doctrine.awareness"))
    return {
        "BRAND": offer.get("brand_name") or brand.title(),
        "OFFER": f"{offer['product']} → {offer['page']}",
        "CORE": core,
        "STAGE": stage.strip("*# ").strip(),
        "AVATARS": "\n".join(who),
        "AWARENESS": aw,
        "ANGLES": "\n".join(angles),
        "VIDEO_FORMATS": " · ".join(f"`{i}`" for i in ids("format.video")),
        "VIDEO_STRUCTURES": " · ".join(f"`{i}`" for i in ids("structure.video")),
        "IMAGE_FORMATS": " · ".join(f"`{i}`" for i in ids("format.image")),
        "CAROUSEL_FORMATS": " · ".join(f"`{i}`" for i in ids("format.carousel")),
        "VIDEO_STYLES": " · ".join(f"`{i}`" for i in ids("style.video")),
        "IMAGE_STYLES": " · ".join(f"`{i}`" for i in ids("style.image")),
        "SETTINGS": "\n".join(f"- `{s['id']}`: {s['what']}" for s in settings),
    }


def fill(brand):
    text = PROMPT.read_text()
    for k, v in lists(brand).items():
        text = text.replace("{" + k + "}", v)
    return text


def call(url, body=None, headers=None, raw=False, method=None, tries=5):
    for n in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
            with urllib.request.urlopen(req, timeout=600) as r:
                b = r.read()
                return (b, dict(r.headers)) if raw else json.loads(b or b"{}")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and n < tries:
                time.sleep(8 * n)
                continue
            raise RuntimeError(f"Gemini {e.code}: {e.read()[:300]!r}")
        except urllib.error.URLError:
            if n < tries:
                time.sleep(8 * n)
                continue
            raise


def upload_video(k, path):
    blob = path.read_bytes()
    _, h = call(f"{API}/upload/v1beta/files?key={k}",
                json.dumps({"file": {"display_name": path.name}}).encode(),
                {"X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                 "X-Goog-Upload-Header-Content-Length": str(len(blob)),
                 "X-Goog-Upload-Header-Content-Type": "video/mp4",
                 "Content-Type": "application/json"}, raw=True)
    up = h.get("X-Goog-Upload-URL") or h.get("x-goog-upload-url")
    f = call(up, blob, {"X-Goog-Upload-Command": "upload, finalize",
                        "X-Goog-Upload-Offset": "0"})["file"]
    for _ in range(60):
        if f.get("state") == "ACTIVE":
            return f["uri"]
        time.sleep(3)
        f = call(f"{API}/v1beta/{f['name']}?key={k}")
    raise RuntimeError("video never became ready")


def tag_one(k, prompt, asset):
    path = ROOT / asset["file"]
    copy = ("\n\n## The copy that runs with it\n"
            + "\n".join(f"Primary text: {t}" for t in asset["bodies"][:3])
            + "\n" + "\n".join(f"Headline: {t}" for t in asset["titles"][:3])
            + "\n" + "\n".join(f"Link: {t}" for t in asset["links"][:2]))
    if asset.get("thumb_only"):
        copy += "\n\n(Only a still frame of this ad was available. Tag what you can see; mark unsure fields `unclear`.)"
    if path.suffix == ".mp4":
        media = {"file_data": {"mime_type": "video/mp4", "file_uri": upload_video(k, path)}}
    else:
        media = {"inline_data": {"mime_type": "image/jpeg",
                                 "data": base64.b64encode(path.read_bytes()).decode()}}
    body = {"contents": [{"role": "user", "parts": [media, {"text": prompt + copy}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}
    r = call(f"{API}/v1beta/models/{MODEL}:generateContent?key={k}",
             json.dumps(body).encode(), {"Content-Type": "application/json"})
    text = r["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def check(brand, t):
    """Mark every value that is not on its list."""
    b = ROOT / "brands" / brand
    av = json.loads((b / "core-avatars" / "avatars.json").read_text())["avatars"]
    subs = {s for a in av for s in (a.get("sub_avatars") or [])} | {a["id"] for a in av}
    ang = json.loads((b / "strategy" / "angles.json").read_text())
    ang_rows = ang.get("angles") or [v for v in ang.values() if isinstance(v, list)][0]
    allowed = {
        "sub_avatar": subs,
        "awareness": set(ids("doctrine.awareness")),
        "angle": {r["id"] for r in ang_rows},
        "setting": {s["id"] for s in json.loads((b / "strategy" / "settings.json").read_text())["settings"]},
        "style": set(ids("style.video")) | set(ids("style.image")),
        "format": set(ids("format.video")) | set(ids("structure.video")) | set(ids("format.image")) | set(ids("format.carousel")),
    }
    off = []
    for field, ok in allowed.items():
        v = str(t.get(field, "")).strip("`")
        t[field] = v
        if v and v not in ok and not v.startswith("new:") and v != "unclear":
            off.append(f"{field}={v}")
    t["off_list"] = off
    return t


def main(brand, day=None):
    base = ROOT / "runs" / "creative-diversity" / brand
    day = day or sorted(p.name for p in base.iterdir() if (p / "assets.json").exists())[-1]
    run = base / day
    assets = json.loads((run / "assets.json").read_text())["assets"]
    out = run / "tags.json"
    done = json.loads(out.read_text())["tags"] if out.exists() else {}
    k = daemn_keys.key("GEMINI_API_KEY")
    prompt = fill(brand)
    (run / "prompt-filled.md").write_text(prompt)
    todo = [a for a in assets if a.get("file") and a["asset"] not in done]
    print(f"{brand} {day}: {len(todo)} to tag, {len(done)} already tagged")

    def work(a):
        try:
            return a["asset"], check(brand, tag_one(k, prompt, a))
        except Exception as e:  # noqa: BLE001
            print(f"  {a['asset']}: {e}", file=sys.stderr)
            return a["asset"], None

    with ThreadPoolExecutor(6) as ex:
        for i, (key, t) in enumerate(ex.map(work, todo), 1):
            if t:
                done[key] = t
            if i % 10 == 0:
                out.write_text(json.dumps({"brand": brand, "model": MODEL,
                                           "prompt": PROMPT.name, "tags": done}, indent=1))
                print(f"  {i}/{len(todo)}")
    out.write_text(json.dumps({"brand": brand, "model": MODEL, "prompt": PROMPT.name,
                               "tags": done}, indent=1))
    print(f"{brand}: {len(done)} tagged -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
