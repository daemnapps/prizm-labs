#!/usr/bin/env python3
"""Describe every swiped creative in the naming convention's own words.

    swipe_fields.py apply [brand]      write `fields` into blocks.json
    swipe_fields.py report [brand]     what is classified, what is not

A competitor's ad and one of ours are the same kind of object. The naming
convention already has words for it — media, source, talent, problem, angle,
concept, format, ratio — so the swipe library uses those words rather than
inventing a parallel set. `naming/names.py` owns the vocabulary; this file
imports it and never re-declares a value.

That is the whole point: a Meta export grouped on `problem` and the swipe
corpus grouped on `problem` are answering one question. When an ad wins, its
manifest carries `swipe:<brand>:<ad_id>`, and the thing it was built from is
one lookup away.

WHAT IS DERIVED AND WHAT IS JUDGED
    media    derived — a file with video is a video ad, otherwise static
    ratio    derived — measured off the file in the Drive mirror
    source   JUDGED — is this AI, a creator, a studio shoot? Nothing in the
             ad tool's payload says, and it is the split worth the most.
    talent   JUDGED — a person, and whether the same person recurs
    problem  JUDGED — read off the copy and the creative
    angle    JUDGED — and only against the brand's signed vocabulary
    concept  JUDGED — the execution
    format   JUDGED — the template it was built in

Judged fields are written as `unclassified`, never left blank: blank reads as
an answer (`none` means "nobody is in it") and a missing key reads as a bug.
Filling them is the judging pass, and it is a person's job.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "naming"))
import names as N  # the vocabulary, imported and never re-declared
from pathlib import Path
for _r in Path(HERE).parents:          # the swipe home, one definition for both pools
    if (_r / "components" / "swipe-paid" / "swipe_home.py").is_file():
        sys.path.append(str(_r / "components" / "swipe-paid"))
        break
import swipe_home  # noqa: E402

DRIVE = str(swipe_home.root("paid"))

# Their word -> the convention's word. The ad tool says "image"; the buyer,
# and therefore the name, says "static".
MEDIA_FROM_TOOL = {"video": "video", "image": "static"}


def ratio_of(path):
    """The frame, as one of the convention's values, measured off the file.

    Ratio is the one judged-looking field that is not a judgement — it is a
    fact about the file, and reading it costs nothing once the media is on
    disk. Anything that is not a ratio we ship in is reported as measured
    (`1080x1350`) rather than forced into a bucket it does not belong in.
    """
    if not path or not os.path.exists(path):
        return "unknown"
    try:
        if path.endswith((".mp4", ".mov")):
            out = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", path],
                capture_output=True, text=True, timeout=30).stdout.strip()
        else:
            out = subprocess.run(["identify", "-format", "%wx%h", path],
                                 capture_output=True, text=True, timeout=30).stdout.strip()
        w, h = (int(x) for x in out.split("x")[:2])
    except Exception:
        return "unknown"
    if not w or not h:
        return "unknown"
    r = w / h
    for label, target in (("9x16", 9 / 16), ("4x5", 4 / 5), ("1x1", 1.0),
                          ("16x9", 16 / 9)):
        if abs(r - target) < 0.03:
            return label
    return f"{w}x{h}"


def media_path(brand, block_slug, ad_id, is_video):
    sub = f"video/{ad_id}.mp4" if is_video else f"photos/{ad_id}.jpg"
    return os.path.join(DRIVE, brand, "blocks", block_slug, sub)


def fields_for(brand, angle, ad_id, media_row, measure=True):
    """One creative, in the convention's words."""
    is_video = bool(media_row.get("video"))
    path = media_path(brand, angle["slug"], ad_id, is_video)
    f = {k: N.UNCLASSIFIED for k in N.CREATIVE_FIELDS}
    f["media"] = MEDIA_FROM_TOOL["video" if is_video else "image"]
    f["ratio"] = ratio_of(path) if measure else "unmeasured"
    return f


def apply_brand(brand, measure=True):
    p = os.path.join(HERE, brand, "blocks.json")
    if not os.path.exists(p):
        return None
    doc = json.load(open(p))
    n = measured = 0
    for a in doc["blocks"]:
        for ad_id, m in a["media"].items():
            prev = m.get("fields") or {}
            f = fields_for(brand, a, ad_id, m, measure=measure)
            # a judgement already made is never overwritten by a re-run
            for k, v in prev.items():
                if v not in (N.UNCLASSIFIED, "unknown", "unmeasured", None, ""):
                    f[k] = v
            m["fields"] = f
            m["swipe_id"] = N.swipe_id(brand, ad_id)
            n += 1
            measured += f["ratio"] not in ("unknown", "unmeasured")
    doc["vocabulary"] = {
        "source": "components/naming/names.py",
        "creative_fields": N.CREATIVE_FIELDS,
        "unclassified": N.UNCLASSIFIED,
        "swipe_id": "swipe:<brand>:<ad_id> — what a production manifest keeps",
    }
    json.dump(doc, open(p, "w"), indent=1, ensure_ascii=False)
    return n, measured


def brands():
    return sorted(d for d in os.listdir(HERE)
                  if os.path.isdir(os.path.join(HERE, d))
                  and os.path.exists(os.path.join(HERE, d, "blocks.json")))


def cmd_apply(brand=None, *rest):
    measure = "--no-measure" not in rest
    for b in ([brand] if brand else brands()):
        r = apply_brand(b, measure=measure)
        if r is None:
            print(f"  {b:<14} no blocks.json")
            continue
        n, m = r
        print(f"  {b:<14} {n:>5} creatives described · {m:>5} ratios measured")


def cmd_report(brand=None, *_):
    import collections
    for b in ([brand] if brand else brands()):
        p = os.path.join(HERE, b, "blocks.json")
        doc = json.load(open(p))
        rows = [m.get("fields") or {} for a in doc["blocks"] for m in a["media"].values()]
        if not rows:
            continue
        print(f"\n{b} — {len(rows)} creatives")
        for f in N.CREATIVE_FIELDS:
            c = collections.Counter(r.get(f, "missing") for r in rows)
            todo = c.get(N.UNCLASSIFIED, 0)
            known = ", ".join(f"{k} {v}" for k, v in c.most_common(4)
                              if k != N.UNCLASSIFIED) or "—"
            flag = f"  ← {todo} to judge" if todo else ""
            print(f"  {f:<9} {known}{flag}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    args = sys.argv[2:]
    {"apply": cmd_apply, "report": cmd_report}.get(cmd, lambda *a: sys.exit(__doc__))(*args)
