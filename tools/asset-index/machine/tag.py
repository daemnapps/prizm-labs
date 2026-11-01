"""tag.py: what is actually IN every picture of a brand's proof index and of its product photos, so a layout can
pick real content and say truly what it shows.

the owner, 2026-10-17: "Let's create real indexes, use real people, use real content, and we make adjustments
from there in order to scale this process." The proof index (proof.py) knows where each picture is and
what folder it came from; this records what a person would see in it: who is in it, which product and
whether the product looks right, which botanical, texture, baked-in words, the setting and light, its
quality, and what an email could use it for.

    python3 machine/tag.py --brand <brand> [--label proof] [--kinds ugc,review,social-post] [--limit N] [--workers 6]
    python3 machine/tag.py --brand <brand> --label products|stills|… [--limit N] [--ids <drive id>,<drive id>]

--label proof (or any label with a proof.json) reads proof.json and its thumbs. --label products reads the
mapping records map_all wrote (runs/asset-index/<brand>/products/<drive id>/clip.json, pictures only) and
fetches each picture by its Drive id through gdrive-creator (GDRIVE_SA_KEY, nothing kept on disk): the
email layout picked product photos by file name alone and wrote what it guessed they showed (the team,
2026-10-28: a "Black man's jaw, CRUSH in frame" that was a white man's face with no product). Each tag of a
product photo carries "ref", the drive: reference the email layout uses.

Writes tags.json beside the records (one entry per id, merged on re-run, so it only ever looks at a picture
once). Pictures go to the vision model in numbered sheets of 12 through the image engine's judge entry
(tools/image-production/models.json, GEMINI_API_KEY from the environment). Brand-agnostic: the brand's
product names come from its own products folder and products/images.json, their looks from its product files.
"""
import argparse
import base64
import io
import json
import os
import re
import sys
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent.parent / "brandpath"))
import brandpath  # noqa: E402

REPO = Path(brandpath.repo(HERE))
CELL, PER = 300, 12
try:
    FONT = ImageFont.load_default(size=28)
except TypeError:
    FONT = ImageFont.load_default()

ASK = """You are indexing a brand's own pictures so an email designer can pick real content and describe it truly.
The sheet shows {n} pictures, each with a big number in its top-left corner. The brand's products:
{products}
What they really look like (when on file):
{looks}

For EACH number, answer with one JSON object. Return ONLY a JSON array of {n} objects, in number order:
{{"n": <number>,
 "shot": "selfie-with-product | person-using-product | skin-closeup | face-closeup | product-hero | product-in-texture | texture-only | ingredient | product-with-ingredients | lifestyle | graphic-card | before-after | review-screenshot | other",
 "people": "none | woman 20-39 | woman 40-54 | woman 55-70 | woman 70+ | man 18-29 | man 30-49 | man 50+ | several",
 "skin_tone": "none | light | medium | deep",   // of the person shown, when one is
 "holding": "<product name held, or none>",
 "products": ["<product names visible>"],
 "product_ok": true | false | null,   // the products look like their real packaging above, not redrawn; null when none is shown
 "botanicals": ["<any botanical or ingredient visible>"],
 "texture": "none | scrub | cream | foam | gel | other",
 "baked_text": "none | small | large",   // words rendered INTO the picture (captions, headlines, labels beyond the product's own)
 "setting": "<2-4 words: bathroom, kitchen, plain studio, outdoors…>",
 "light": "<2-4 words>",
 "quality": 1-5,   // 5 = campaign-grade, sharp, well lit; 1 = blurry or broken
 "use_for": ["proof" | "hero" | "product" | "texture" | "ingredient" | "story" | "grid"],
 "one_line": "<what a person sees, plainly: who, doing what, which product if any; 14 words max>"}}
Judge only what is visible. No guessing names. Name a product only when you can see it."""


def sheet(items, base):
    """A numbered contact sheet. `base` is the folder thumbs sit under, or a function item -> PIL image."""
    load = base if callable(base) else (lambda e: Image.open(base / e["thumb"]))
    cols = 4
    rows = (len(items) + cols - 1) // cols
    s = Image.new("RGB", (cols * CELL, rows * CELL), (255, 255, 255))
    d = ImageDraw.Draw(s)
    for i, e in enumerate(items):
        try:
            im = load(e).convert("RGB")
            im.thumbnail((CELL - 6, CELL - 6))
        except Exception:
            continue
        x, y = (i % cols) * CELL, (i // cols) * CELL
        s.paste(im, (x + 3, y + 3))
        d.rectangle((x + 3, y + 3, x + 46, y + 40), fill=(255, 230, 0))
        d.text((x + 10, y + 8), str(i + 1), fill=(0, 0, 0), font=FONT)
    b = io.BytesIO()
    s.save(b, "JPEG", quality=82)
    return b.getvalue()


def judge_entry():
    lane = str(REPO / "tools" / "image-production")
    if lane not in sys.path:
        sys.path.append(lane)
    from image_production import route as R
    return R.judge_entry()


def call(entry, jpg, prompt):
    k = os.environ.get(entry["key"])
    if not k:
        raise SystemExit("no %s in the environment" % entry["key"])
    payload = {"contents": [{"parts": [{"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(jpg).decode()}},
                                       {"text": prompt}]}],
               "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}}
    url = entry["endpoint"].replace("{model}", entry["vendor_model"]) + "?key=" + k
    req = urllib.request.Request(url, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read().decode())
    text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
    i, j = text.find("["), text.rfind("]")
    return json.loads(text[i:j + 1])


def products_of(brand):
    """The brand's product names: its product folders and the products its images.json declares (with titles)."""
    root = REPO / "brands" / brand / "products"
    names = {p.name: p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith(("_", ".")) and p.name not in ("reference",)}
    try:
        declared = json.loads((root / "images.json").read_text()).get("products", {})
    except (OSError, ValueError):
        declared = {}
    for k, v in declared.items():
        if not k.startswith("_"):
            title = v.get("title") if isinstance(v, dict) else None
            names[k] = "%s (%s)" % (k, title) if title else k
    return ", ".join(names[k] for k in sorted(names))


def looks_of(brand):
    """Each product's container line from its product file ('What it physically looks like'), when written."""
    root = REPO / "brands" / brand / "products"
    out = []
    for f in sorted(list(root.glob("*/product.md")) + list(root.glob("*.md"))):
        m = re.search(r"\*\*Container\*\*\s*\|\s*([^|\n]+)", f.read_text())
        if m:
            out.append("%s: %s" % (f.parent.name if f.name == "product.md" else f.stem, m.group(1).strip()))
    return "\n".join(out) or "(none on file: judge product_ok only on an obviously redrawn or fake product)"


PICTURE_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def drive_items(d):
    """The picture records under a collection folder (map_all's, kind image; or older ones with no kind, like the
    stills collection, read by their file name), as tag items: id = Drive id, ref = drive:<path>."""
    out = []
    for f in sorted(d.glob("*/clip.json")):
        try:
            r = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        label = r.get("label") or ""
        picture = r.get("kind") == "image" or (r.get("kind") is None and Path(label).suffix.lower() in PICTURE_EXTS)
        if not picture or not r.get("drive_id") or not label.startswith("Shared Assets/"):
            continue
        out.append({"id": r["drive_id"], "kind": "image", "media": "image",
                    "ref": "drive:" + label[len("Shared Assets/"):]})
    return out


def drive_loader():
    """item -> PIL image, the picture fetched by its Drive id through gdrive-creator (keys only, builder card rule 4)."""
    gdc = REPO / "components" / "gdrive-creator"
    if str(gdc) not in sys.path:
        sys.path.append(str(gdc))
    from gdrive_creator import engine as G
    local = threading.local()

    def load(e):
        # one Drive connection per thread: the client is not thread-safe, and the sheets run on --workers threads
        # (one shared connection crashed Python inside its SSL reads, 2026-10-28)
        if not hasattr(local, "svc"):
            local.svc = G.service()
        return Image.open(io.BytesIO(local.svc.files().get_media(fileId=e["id"], supportsAllDrives=True).execute()))
    return load


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--label", default="proof")
    ap.add_argument("--kinds", default="ugc,review,social-post,before-after")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids", default="", help="only these ids (comma-separated): a trial before a whole collection")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    d = REPO / "runs" / "asset-index" / a.brand / a.label
    tf = d / "tags.json"
    tags = json.loads(tf.read_text()) if tf.exists() else {}
    if (d / "proof.json").exists():
        proof = json.loads((d / "proof.json").read_text())
        kinds = set(a.kinds.split(","))
        todo = [e for e in proof["items"] if e["kind"] in kinds and (e.get("thumb") or e.get("drive_id")) and e.get("media") == "image" and e["id"] not in tags]
        fetch = drive_loader() if any(not (d / e["thumb"]).is_file() for e in todo if e.get("thumb")) else None

        def base(e):
            # the thumb on disk when this clone has it (thumbs/ is not in git), else the picture by its Drive id
            if e.get("thumb") and (d / e["thumb"]).is_file():
                return Image.open(d / e["thumb"])
            return fetch({"id": e["drive_id"]})
    else:
        todo = [e for e in drive_items(d) if e["id"] not in tags]
        base = drive_loader() if todo else None
    if a.ids:
        todo = [e for e in todo if e["id"] in a.ids.split(",")]
    if a.limit:
        todo = todo[:a.limit]
    entry = judge_entry()
    prods = products_of(a.brand)
    looks = looks_of(a.brand)
    batches = [todo[i:i + PER] for i in range(0, len(todo), PER)]
    print("%s: %d pictures to tag in %d sheets (%d already tagged)" % (a.brand, len(todo), len(batches), len(tags)))

    def run(batch):
        # a picture that will not load is left out of its sheet: a blank cell would still be described
        pics = {}
        for e in batch:
            try:
                pics[e["id"]] = base(e).convert("RGB")
            except Exception as err:  # noqa: BLE001 — one unreadable picture never sinks the sheet
                print("  not loaded, not tagged: %s (%s)" % (e["id"], type(err).__name__))
        batch = [e for e in batch if e["id"] in pics]
        if not batch:
            return batch, [], None
        try:
            res = call(entry, sheet(batch, lambda e: pics[e["id"]]), ASK.format(n=len(batch), products=prods, looks=looks))
        except Exception as e:
            return batch, None, str(e)[:200]
        return batch, res, None

    done = 0
    with ThreadPoolExecutor(a.workers) as ex:
        for batch, res, err in ex.map(run, batches):
            if err:
                print("  sheet failed: %s" % err)
                continue
            for r in res:
                try:
                    e = batch[int(r["n"]) - 1]
                except (KeyError, ValueError, IndexError):
                    continue
                r.pop("n", None)
                r["kind"] = e["kind"]
                if e.get("ref"):
                    r["ref"] = e["ref"]
                tags[e["id"]] = r
            done += 1
            if done % 10 == 0:
                tf.write_text(json.dumps(tags, indent=1, ensure_ascii=False))
                print("  %d/%d sheets" % (done, len(batches)))
    tf.write_text(json.dumps(tags, indent=1, ensure_ascii=False))
    print("wrote %s (%d pictures tagged)" % (tf.relative_to(REPO), len(tags)))


if __name__ == "__main__":
    main()
