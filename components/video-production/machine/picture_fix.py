#!/usr/bin/env python3
"""THE MASKED FIX — a start picture's flagged fault fixed in its own region, never a redraw ("small miss, small fix").

    python3 picture_fix.py <run> <picture id> --fix "what to change" [--ref <picture> ...] [--dry-run]

The picture door has no mask, so the mask is made here: the region the fault is in is found on the picture (one vision
question, its box), widened to the picture's own 9:16 shape, cut out, edited on its own with the fix and the identity
pictures it needs, and laid back in its place with a soft edge. Everything outside the region is the picture as it was,
pixel for pixel. GATE-4: the edit names the kept 3D print the picture was made from (`<picture>.print.json`, run.py
note_print), so the picture door takes it; a picture with no recorded print is refused before anything is spent.

Every version is kept (`media/versions/<id>-fix-v<n>.png`), the fix is written on the picture's record (`fixed` in
direct.json) and in the ledger. Nothing here names a brand, product or person.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASPECT = 9 / 16              # width / height of every start picture
MIN_W = 0.34                 # the smallest region, as a share of the picture's width (an edit needs context)
PAD = 0.06                   # added round the fault's box on every side, as a share of the picture's width
FEATHER = 0.06               # the soft edge the edited region is laid back with, as a share of the region's width


def _load(name):
    sp = importlib.util.spec_from_file_location(f"vm_pf_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def _read(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


LOCATE = ("Image 1 is a picture with one fault to fix: {fault}\n"
          "Return JSON only: {{\"box\": [x0, y0, x1, y1]}} — the smallest box, as fractions of the picture's width and "
          "height (0 to 1, top-left origin), round everything that must change to fix it (the whole person or object "
          "involved, not only a detail of it).")


def locate(run, picture, fault, ask=None):
    """The fault's box (x0, y0, x1, y1), fractions of the picture, from one vision question; the whole picture when the
    answer cannot be read."""
    V = None
    if ask is None:
        V = _load("v2_checks")
        ask = lambda job, prompt, images: V.ask(run, job, prompt, images,  # noqa: E731
                                                model=V.model_of(V.CFG["checks"]["review_model"]))
    text, _info = ask(f"{Path(picture).stem}-fix-locate", LOCATE.format(fault=fault), [picture])
    try:
        got = json.loads(text) if isinstance(text, str) else text
    except ValueError:
        got = (V or _load("v2_checks")).json_of(text)
    if isinstance(got, list):                     # an answer given as the box itself, or as a list of answers
        got = {"box": got} if len(got) == 4 and all(isinstance(v, (int, float)) for v in got) else (got[0] if got else {})
    try:
        x0, y0, x1, y1 = [float(v) for v in (got or {}).get("box")]
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            raise ValueError
        return x0, y0, x1, y1
    except (TypeError, ValueError):
        return 0.0, 0.0, 1.0, 1.0


def region(box, w, h):
    """The box padded and widened to the picture's own shape (so the door's 9:16 edit fits it back unstretched), in
    pixels, inside the picture."""
    x0, y0, x1, y1 = box
    x0, x1 = (x0 - PAD) * w, (x1 + PAD) * w
    y0, y1 = y0 * h - PAD * w, y1 * h + PAD * w
    bw = max(x1 - x0, MIN_W * w, (y1 - y0) * ASPECT)
    bh = bw / ASPECT
    if bh > h:
        bh, bw = h, h * ASPECT
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    left = min(max(cx - bw / 2, 0), w - bw)
    top = min(max(cy - bh / 2, 0), h - bh)
    return int(round(left)), int(round(top)), int(round(left + bw)), int(round(top + bh))


def lay_back(picture, edited, box, out):
    """The edited region laid back into the picture at `box` with a soft edge; outside it, the picture unchanged."""
    from PIL import Image, ImageDraw, ImageFilter
    base = Image.open(picture).convert("RGB")
    l, t, r, b = box
    patch = Image.open(edited).convert("RGB").resize((r - l, b - t), Image.LANCZOS)
    f = max(2, int((r - l) * FEATHER))
    m = Image.new("L", patch.size, 0)
    ImageDraw.Draw(m).rectangle([f, f, patch.size[0] - f - 1, patch.size[1] - f - 1], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(f / 2))
    base.paste(patch, (l, t), m)
    base.save(out)
    return out


EDIT = ("Image 1 is one part of a picture, cut out. Change ONLY this, inside image 1: {fix} Keep everything else in image "
        "1 exactly as it is — the framing, every edge, the light, the colours, the style and every other person and "
        "thing — so it fits back into its picture without a seam. No words, letters or labels added anywhere.")


def fix(run, iid, fix_words, refs=(), brand=None, dry=False, generate=None, ask=None, ledger=None):
    """Fix one flagged fault of a start picture in its region. Returns the fix record."""
    run = Path(run)
    rec_all = _read(run / "direct.json", {}) or {}
    row = rec_all.get(iid) or {}
    pic = Path(row.get("file") or run / "media" / f"{iid}.png")
    if not pic.is_file():
        raise SystemExit(f"{iid}: no picture on record")
    side = _read(Path(str(pic) + ".print.json"), {}) or {}
    kp = side.get("print")
    if not kp or not Path(kp).is_file():
        raise SystemExit(f"{iid}: no kept 3D print recorded for this picture — it is remade from its print, not fixed "
                         f"(GATE-4)")
    from PIL import Image
    w, h = Image.open(pic).size
    box = region(locate(run, pic, fix_words, ask=ask), w, h)
    versions = run / "media" / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    n = len(list(versions.glob(f"{iid}-fix-v*.png"))) + 1
    before = versions / f"{iid}-fix-v{n}-before.png"
    crop = versions / f"{iid}-fix-v{n}-region.png"
    Image.open(pic).convert("RGB").crop(box).save(crop)
    R = _load("run")
    sent = [crop] + [Path(r) for r in refs if Path(r).is_file()]
    it = {"for": iid.split("-")[0], "params": {"prompt": ((row.get("asked") or {}).get("prompt") or "")}}
    words = (EDIT.format(fix=fix_words.rstrip(".") + ".") + " " + R.who_is_who(it, iid, sent, run)).strip()
    out = {"picture": iid, "box": list(box), "fix": fix_words, "refs": [str(r) for r in sent[1:]], "words": words,
           "from_print": kp}
    if dry:
        return {**out, "dry_run": True}
    edited = versions / f"{iid}-fix-v{n}-region-edited.png"
    gen = generate or _load("direct_openai").generate
    res = gen(words, sent, edited, people=bool(R.shot_roster(it, iid, run)), from_print=kp)
    shutil.copy2(pic, before)
    lay_back(pic, res.get("file") or edited, box, pic)
    shutil.copy2(pic, versions / f"{iid}-fix-v{n}.png")
    out.update({"model": res.get("model"), "before": str(before), "version": n})
    row.setdefault("fixed", []).append({k: out[k] for k in ("fix", "box", "model", "version", "from_print")})
    rec_all[iid] = row
    (run / "direct.json").write_text(json.dumps(rec_all, indent=1, ensure_ascii=False) + "\n")
    try:
        (ledger or R.preflight.ledger)(run, res.get("model"), f"{iid}-fix-{n}", 0.0, "done", brand=brand, shot=iid,
                                       note=f"masked fix: {fix_words[:200]}", usage=res.get("usage"))
    except (Exception, SystemExit) as e:  # noqa: BLE001 — the picture is fixed; a ledger it cannot write is said
        print(f"  {iid}: fix not on the ledger ({type(e).__name__}: {str(e)[:120]})", file=sys.stderr)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run"); ap.add_argument("picture")
    ap.add_argument("--fix", required=True, help="what to change, in words")
    ap.add_argument("--ref", action="append", default=[], help="an identity picture the fix needs (a master, a kit picture)")
    ap.add_argument("--brand")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    run = Path(a.run).resolve()
    brand = a.brand or (_read(run / "run.json", {}) or {}).get("brand")
    print(json.dumps(fix(run, a.picture, a.fix, a.ref, brand, a.dry_run), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
