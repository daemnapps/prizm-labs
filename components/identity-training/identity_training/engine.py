#!/usr/bin/env python3
"""Train a brand asset into a LoRA identity on fal — character or product.

    python3 components/identity-training/train_identity.py \
        --brand brand-a --character june
    python3 components/identity-training/train_identity.py \
        --brand brand-a --product glow-body-scrub

Proven 2026-08-31/09-01 on June (25 board slices -> same woman in every
scene, zero reference images) and the Glow Body Scrub (25 images
incl. label-band close-ups, 2000 steps -> color/shape/logo locked; micro
text still wobbles at hero size, so label-forward frames composite the
real packshot instead — that rule lives with the frames stage).

What it does, per the owner's standard:
- CHARACTER: slices the character's certified board set (the boards ARE
  the training curriculum) + master into individual training images.
- PRODUCT: every image in the product's images/ folder EXCEPT any shot
  showing more than this product, plus rotations and label-band close-up
  crops (the close-ups are what teach the typography).
- Uploads to fal (the company account), trains flux-lora-fast-training,
  and writes `lora.json` beside the source (or under `--out`): url,
  trigger word, date, training-set description. The lora.json IS the
  record — words in git, weights on fal.

Machine-agnostic (components rule 8): the credential comes from the
environment (`FAL_KEY`), the workspace root from `AI_WORKSPACE` when set,
and every write lands where `--out` says — or, with no `--out`, exactly
where it has always landed: beside the brand source.

Two seams let a host machine keep its own habits without this engine
learning them (`configure()`):

    key_lookup(name)   consulted only when the environment has no key
    drive_lookup(rel)  a Drive mirror of a repo-relative path, or None

`tools/video-teardown/machine/train_identity.py` is a shim that sets
both — its vault (`keys.py`) and its Drive mount (`chain.drive_root()`) —
so the owner's invocation behaves as it did before the move.

Brand-agnostic (workspace rule 7): everything resolves from the brand
folder given at run time; nothing here names a brand.
"""

import argparse
import io
import json
import os
import re
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

WS = Path(os.environ.get("AI_WORKSPACE")
          or Path(os.environ.get("AI_WORKSPACE") or ".").resolve())
TRAINER = "https://queue.fal.run/fal-ai/flux-lora-fast-training"
STORAGE = ("https://rest.alpha.fal.ai/storage/upload/initiate"
           "?storage_type=fal-cdn-v3")

CHARACTER_STEPS = 1000
PRODUCT_STEPS = 2000
NOTE = ("characters hold identity outright; products hold "
        "color/shape/logo — label-forward hero frames composite "
        "the real packshot instead of generating the label")

_KEY_LOOKUP = None
_DRIVE_LOOKUP = None


def configure(key_lookup=None, drive_lookup=None):
    """Install a host machine's credential vault and/or Drive mount.

    Both are fallbacks, never overrides: the environment wins on keys, and
    the repo wins on images. A host that sets neither loses nothing the
    environment already carries.
    """
    global _KEY_LOOKUP, _DRIVE_LOOKUP
    if key_lookup is not None:
        _KEY_LOOKUP = key_lookup
    if drive_lookup is not None:
        _DRIVE_LOOKUP = drive_lookup


def fal_key(name="FAL_KEY"):
    """Env first (components rule 8); the host's vault only after."""
    v = os.environ.get(name)
    if v:
        return v
    if _KEY_LOOKUP is not None:
        return _KEY_LOOKUP(name)
    return None


def fal(url, data=None, key=None):
    r = urllib.request.Request(
        url, data=json.dumps(data).encode() if data is not None else None,
        headers={"Authorization": "Key %s" % key,
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=600) as resp:
        return json.loads(resp.read() or b"{}")


def brand_dir(brand):
    # ONE brand home (the owner, 2026-09-02) — brands is gone
    for root in (WS / "brands" / brand,):
        if root.is_dir():
            return root
    sys.exit("no brand folder for '%s'" % brand)


def drive_dir(rel):
    """The Drive mirror of a repo-relative brand path, if the host has one."""
    if _DRIVE_LOOKUP is None:
        return None
    try:
        return _DRIVE_LOOKUP(rel)
    except Exception:
        return None


def images_from(folder):
    if not folder or not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir()
                  if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))


def _brandpath():
    """components/brandpath — the brand's folders by their plan name."""
    sys.path.insert(0, str(WS / "components" / "brandpath"))
    import brandpath
    return brandpath


def character_source(brand, name):
    """(home, repo-relative path, source folder or None) — opens nothing."""
    brand_dir(brand)   # the loud "no brand folder" exit, as before
    # ai-elements/characters/<name> — the same key on the Drive mirror since
    # the 2026-09-29 folder move (was ai-cast/<name> on both sides)
    base = _brandpath().brand_path(brand, "ai-elements/characters", name)
    rel = str(base.relative_to(WS))
    src = base if images_from(base) or images_from(base / "boards") \
        else drive_dir(rel)
    return base, rel, src


def product_source(brand, slug):
    """(home, repo-relative path, source folder or None) — opens nothing."""
    base = brand_dir(brand) / "products" / slug
    rel = str((base / "images").relative_to(WS))
    src = (base / "images") if images_from(base / "images") else drive_dir(rel)
    return base, rel, src


def character_set(brand, name):
    """Master + sliced board panels — the certified boards are the curriculum."""
    from PIL import Image
    base, rel, src = character_source(brand, name)
    if not src:
        sys.exit("no images for %s in the repo or on the Drive (%s)"
                 % (name, rel))
    out = []
    for f in images_from(src):
        if "master" in f.name.lower():
            out.append(Image.open(f).convert("RGB"))
    grids = {"expressions": (2, 3), "wardrobe": (2, 2), "wardrobe2": (2, 2),
             "hair": (2, 2), "details": (2, 2)}
    for f in images_from(src / "boards"):
        key = f.stem.lower()
        im = Image.open(f).convert("RGB")
        if key in grids:
            cols, rows = grids[key]
            w, h = im.size
            for r in range(rows):
                for c in range(cols):
                    out.append(im.crop((c * w // cols, r * h // rows,
                                        (c + 1) * w // cols,
                                        (r + 1) * h // rows)))
        else:
            out.append(im)      # context singles
    return out, base


def product_set(brand, slug):
    """Originals + rotations + label-band close-ups; multi-product shots out."""
    from PIL import Image
    base, rel, src = product_source(brand, slug)
    if not src:
        sys.exit("no images for %s in the repo or on the Drive (%s)"
                 % (slug, rel))
    out = []
    for f in images_from(src):
        if "and-" in f.name.lower():
            continue        # a shot showing another product beside this one
        im = Image.open(f).convert("RGB")
        w, h = im.size
        out.append(im)
        out.append(im.rotate(7, expand=True, fillcolor="white"))
        out.append(im.rotate(-7, expand=True, fillcolor="white"))
        out.append(im.crop((int(w * .15), int(h * .05),
                            int(w * .85), int(h * .60))))   # wordmark band
        out.append(im.crop((int(w * .15), int(h * .40),
                            int(w * .85), int(h * .95))))   # name band
    return out, base


def trigger_word(brand, who):
    return re.sub(r"[^a-z0-9]", "", "%s%s" % (brand, who))[:24]


def plan(brand, character=None, product=None, steps=None, out=None):
    """Everything the run decides before it opens an image or a socket."""
    if bool(character) == bool(product):
        sys.exit("name exactly one of --character or --product")
    if character:
        home, rel, src = character_source(brand, character)
        who, kind = character, "character"
        default_steps = CHARACTER_STEPS
        masks = True            # the person is the subject
    else:
        home, rel, src = product_source(brand, product)
        who, kind = product, "product"
        default_steps = PRODUCT_STEPS
        masks = False           # the label is the point — never mask it out
    dest = Path(out).resolve() if out else home
    return {"kind": kind, "who": who, "home": home, "rel": rel, "source": src,
            "steps": steps or default_steps, "masks": masks,
            "trigger": trigger_word(brand, who),
            "record_path": dest / "lora.json"}


def record(p, url, images):
    return {"kind": p["kind"], "trigger": p["trigger"], "lora_url": url,
            "trained": time.strftime("%Y-%m-%d"), "steps": p["steps"],
            "training_images": images, "account": "company fal",
            "note": NOTE}


def existing_records(p):
    """The subject's lora.json records that exist — its home first, then --out.

    A fresh --out never hides an identity the subject already has at home.
    """
    out, seen = [], set()
    for path in (p["home"] / "lora.json", p["record_path"]):
        if path.resolve() not in seen and path.exists():
            seen.add(path.resolve())
            out.append(path)
    return out


def record_complete(path):
    """True only for a JSON object carrying a non-empty trigger and lora_url."""
    try:
        rec = json.loads(Path(path).read_text())
    except Exception:
        return False
    return (isinstance(rec, dict) and bool(rec.get("trigger"))
            and bool(rec.get("lora_url")))


def write_record(p, rec, out=None):
    """The one write a run makes. Under --out when given, or beside the source."""
    path = p["record_path"]
    if out is not None:
        root = Path(out).resolve()
        try:
            path.resolve().relative_to(root)
        except ValueError:
            sys.exit("refusing to write outside --out: %s" % path)
        root.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=2) + "\n")
    return path


def parser():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--character")
    ap.add_argument("--product")
    ap.add_argument("--steps", type=int, default=None)
    ap.add_argument("--out", default=None,
                    help="where lora.json lands; default is beside the "
                         "brand source, exactly as before")
    ap.add_argument("--retrain", action="store_true",
                    help="train again even though this subject already has a "
                         "trained identity. Without it an existing lora.json "
                         "is reported and nothing is spent — an identity is "
                         "trained ONCE and reused forever (the owner, 2026-09-02).")
    ap.add_argument("--dry-run", action="store_true",
                    help="resolve inputs and destination, print the plan, "
                         "call nothing and write nothing")
    return ap


def main(argv=None):
    a = parser().parse_args(argv)
    p = plan(a.brand, a.character, a.product, a.steps, a.out)

    if a.dry_run:
        candidates = images_from(p["source"]) + images_from(
            p["source"] / "boards" if p["source"] else None)
        print("dry run — nothing called, nothing written")
        print("%s '%s' · trigger %s · steps %d · masks %s"
              % (p["kind"], p["who"], p["trigger"], p["steps"], p["masks"]))
        print("source: %s" % (p["source"] or "MISSING (%s)" % p["rel"]))
        print("candidate source files: %d" % len(candidates))
        print("would write: %s" % p["record_path"])
        found = existing_records(p)
        if found and not record_complete(found[0]):
            print("NOTE: record at %s is incomplete — a real run would stop "
                  "here non-zero (fix it or pass --retrain)" % found[0])
        elif found:
            print("NOTE: already trained (%s) — a real run would stop here "
                  "and spend nothing (pass --retrain to override)" % found[0])
        return 0

    # AN IDENTITY IS TRAINED ONCE AND REUSED FOREVER (the owner, 2026-09-02).
    # The record beside the asset is the check: if it is there, this subject
    # already has an identity and training it again spends money to produce a
    # second, slightly different version of a person who is supposed to be the
    # same person in every ad we ever make. The home record counts even when
    # --out points somewhere fresh, and a record that does not parse into a
    # usable identity is an error, never a pass.
    found = existing_records(p)
    if found and not a.retrain:
        existing = found[0]
        if not record_complete(existing):
            sys.exit("record at %s is unreadable or incomplete; fix it or "
                     "pass --retrain" % existing)
        rec = json.loads(existing.read_text())
        print("ALREADY TRAINED — nothing to do, nothing spent.")
        print("  subject: %s '%s'" % (p["kind"], p["who"]))
        print("  trigger: %s" % rec.get("trigger", "?"))
        print("  trained: %s (%s images, %s steps)"
              % (rec.get("trained", "?"), rec.get("training_images", "?"),
                 rec.get("steps", "?")))
        print("  record:  %s" % existing)
        print("Use --retrain only when the subject itself changed — new "
              "packaging, a recast face — never to 'refresh' an identity.")
        return 0

    key = fal_key("FAL_KEY")
    if not key:
        sys.exit("no FAL_KEY — put the company key in the environment "
                 "(the mini's job env, or your own shell)")

    if p["kind"] == "character":
        imgs, home = character_set(a.brand, a.character)
    else:
        imgs, home = product_set(a.brand, a.product)
    who = p["who"]
    print("%d training images for %s '%s' · trigger %s"
          % (len(imgs), p["kind"], who, p["trigger"]))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for i, im in enumerate(imgs, 1):
            b = io.BytesIO()
            im.save(b, "JPEG", quality=95)
            z.writestr("%s-%02d.jpg" % (who, i), b.getvalue())

    init = fal(STORAGE, {"file_name": "%s-lora.zip" % who,
                         "content_type": "application/zip"}, key)
    up = urllib.request.Request(init["upload_url"], data=buf.getvalue(),
                                method="PUT",
                                headers={"Content-Type": "application/zip"})
    with urllib.request.urlopen(up, timeout=600):
        pass
    print("uploaded")

    job = fal(TRAINER, {"images_data_url": init["file_url"],
                        "trigger_word": p["trigger"], "steps": p["steps"],
                        "create_masks": p["masks"]}, key)
    print("training…", job.get("request_id"))
    while True:
        st = fal(job["status_url"] + "?logs=0", key=key)
        if st.get("status") in ("COMPLETED", "FAILED", "ERROR"):
            print(st["status"])
            break
        time.sleep(20)
    res = fal(job["response_url"], key=key)
    url = res["diffusers_lora_file"]["url"]

    path = write_record(p, record(p, url, len(imgs)), a.out)
    print("lora.json written -> %s" % path)
    print("lora:", url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
