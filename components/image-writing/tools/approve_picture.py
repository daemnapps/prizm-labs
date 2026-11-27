#!/usr/bin/env python3
"""Record a person's yes on a first picture, so steps 5 and 6, the hand-off and the run sheet all read the picture that
was really approved. Any brand, any product; nothing is generated and no model is called.

    approve_picture.py <run> --brand <brand> --picture <file> --said "<their words>" --product <id>
                       --words "<words>" --where "<where they sit>" [--words ... --where ...]
                       [--swap "<kind> | <from> | <to>"]... [--stays "<what stays>"]...
                       [--plate <the picture without words>] [--real-photo] [--product-in-frame "<where>"]

Writes `<run>-first` (.png, .recipe.json, .liked.json, .plate.png) into runs/image-production/<brand>/prompt-bench/, the
one home every reader of an approved picture looks in. Refuses with no words from the person. `--real-photo` says the
picture is a real person's own photo: nothing about them is ever changed and every variation is words only. With no
--swap, the run's own swap list (out/swaps.json) is used. Python 3.9.
"""
import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

REPO = next(p for p in Path(__file__).resolve().parents if (p / "brands").is_dir() and (p / "components").is_dir())
REAL = ["The approved picture is the finished file itself: a real person's own photo with the words and the product laid over it. It is built in layers, never generated and never printed from a 3D set.",
        "Nothing about the person, their skin, the light, the camera or the place is changed, redrawn, generated or added, in the approved picture or in any variation: changing a real person's photo would make false proof. The brief describes the real photo as it is.",
        "Every variation changes words only, on the same photo and layout. No variation carries a picture change. Each headline is a plain line this person would say, and it has to be true of this photo."]


def run_home(run, brand, root):
    d = Path(run)
    return d if d.is_absolute() else (root / "runs" / "image-teardown" / brand / d.name)


def old_products(brand, refs, folders, root):
    """Every old product picture behind a first picture: named in its swaps, or copied beside it. Official sheets only."""
    import importlib.util
    f = root / "components" / "casting" / "casting" / "new_only.py"
    if not f.is_file():
        return []
    sp = importlib.util.spec_from_file_location("new_only", str(f))
    no = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(no)
    bad = [no.old_picture(r, brand, ws=root) for r in refs if r]
    bad += [no.copy_of_old(q, brand, ws=root) for d in folders if d.is_dir() for q in sorted(d.glob("*.png"))]
    return [b for b in bad if b]


def record(run, brand, picture, said, product, words, wheres, swaps=(), stays=(), plate=None, real=False, in_frame="", root=REPO):
    if not str(said or "").strip():
        raise SystemExit("refused: a picture is approved only with the person's own words (--said)")
    if len(words) != len(wheres) or not words:
        raise SystemExit("refused: every --words needs its --where, and an approved picture names the words on it (say \"none\" when it carries none)")
    if not Path(picture).is_file():
        raise SystemExit("refused: no picture at %s" % picture)
    d = run_home(run, brand, root)
    own = {}
    f = d / "out" / "swaps.json"
    if f.is_file():
        own = json.loads(f.read_text())
    rows = []
    for s in swaps:
        p = [x.strip() for x in s.split("|")]
        if len(p) != 3:
            raise SystemExit("refused: a --swap reads \"kind | from | to\": " + s)
        rows.append({"kind": p[0], "from": p[1], "to": p[2], "ref": None})
    st = (REAL if real else []) + ["Where the words sit: " + "; ".join("%s: %s" % (w, t) for w, t in zip(words, wheres)) + ". Nowhere else."]
    if in_frame:
        st.append("The product stays in the picture, approved: " + in_frame + ".")
    st += list(stays) or ([] if rows else list(own.get("stays") or []))
    used = rows or own.get("swaps") or []
    bad = old_products(brand, [w.get("ref") for w in used if isinstance(w, dict)], {d / "finals", Path(picture).resolve().parent}, root)
    if bad:
        raise SystemExit("refused: " + "; ".join(sorted(set(bad))) + ". Use the official casting sheet (the product kit's model/sheet/current/cutouts) and make the picture again.")
    sl = {"swaps": rows or own.get("swaps") or [], "stays": st, "product_in_frame": bool(in_frame), "product_where": in_frame or None,
          "product_sides": [], "words": "set_on_top", "source": "approved picture"}
    br = {"brand": brand, "run": d.name, "product": product, "skip": [], "added": [], "our_copy": list(words), "swap_list": sl, "real_photo": bool(real)}
    home = root / "runs" / "image-production" / brand / "prompt-bench"
    home.mkdir(parents=True, exist_ok=True)
    b = home / (d.name + "-first")
    shutil.copy2(picture, b.with_suffix(".png"))
    if plate:
        shutil.copy2(plate, home / (d.name + "-first.plate.png"))
    (home / (d.name + "-first.recipe.json")).write_text(json.dumps({"brief": br, "picture": b.name + ".png", "made": "layers: real photo, words, product" if real else "see the run"}, indent=1, ensure_ascii=False) + "\n")
    (home / (d.name + "-first.liked.json")).write_text(json.dumps({"liked": dt.datetime.now().isoformat(timespec="seconds"), "by": "a person", "said": said, "brief": br}, indent=1, ensure_ascii=False) + "\n")
    return b.with_suffix(".png")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    for k in ("brand", "picture", "said", "product"):
        ap.add_argument("--" + k, required=True)
    for k in ("words", "where", "swap", "stays"):
        ap.add_argument("--" + k, action="append", default=[])
    ap.add_argument("--plate")
    ap.add_argument("--real-photo", action="store_true")
    ap.add_argument("--product-in-frame", default="")
    a = ap.parse_args(argv)
    print(record(a.run, a.brand, a.picture, a.said, a.product, a.words, a.where, a.swap, a.stays, a.plate, a.real_photo, a.product_in_frame))
    return 0


if __name__ == "__main__":
    sys.exit(main())
