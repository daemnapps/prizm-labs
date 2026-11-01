#!/usr/bin/env python3
"""The brief's variations as data: `out/variations.json`, one file per run, written from stage 5.

    variation_rows.py show  <run>     the five rows, as a table
    variation_rows.py check <run>     validate out/variations.json (exit 1 on a problem)
    variation_rows.py stage <run>     write out/variations.json from the stage 5 answer (05-image-variations.md)

THE BATCH (the owner, 2026-10-27): "It'd be 6 total images in that batch: 5 unique variations from the initial one that we
made." So a batch is the approved picture plus exactly five variations, and each variation is ONE change off the
approved picture. The rows are what tools/image-edit `vary_recipe` reads (`vary.py <approved.png> --brand <b>
--from-brief <run>/out/variations.json`):

    {"source": "stage5", "from": "05-image-variations.md",
     "variations": [{"id": "v1", "label": "<what changes, in a few words>",
                     "words": ["LINE ONE / LINE TWO", ...],       one string per caption zone, " / " is the line break
                     "picture": "<the one change, in plain words>",
                     "swap": [{"from": "<a swap-list row's from>", "to": "<what it becomes>", "kind": "<swaps kind>"}],
                     "stays_drop": ["<a 'what stays' line the change undoes>"],
                     "people": "cast" | "made-up",
                     "person": {"who": "...", "age": "...", "look": "...", "wardrobe": "..."}}, ... five rows]}

Every row has `id` and `label` and at least one of the change keys; nothing else is taken.
"""
import argparse
import json
import re
import sys
from pathlib import Path

FILE = "variations.json"
ANSWER = "05-image-variations.md"
COUNT = 5                                   # the approved picture + 5 = the batch of 6 (the owner, 2026-10-27)
CHANGES = ("words", "picture", "swap", "stays_drop", "people", "person")
PEOPLE = ("cast", "made-up")
PERSON = ("who", "age", "look", "wardrobe")
SWAP_KINDS = ("cast", "product", "library", "drawn", "words")    # swaps rule 1, tools/image-writing/tools/swaps.py


def _row_problems(i, v):
    at = f"row {i + 1}"
    if not isinstance(v, dict):
        return [f"{at} is not an object"]
    out = []
    if not str(v.get("id") or "").strip():
        out.append(f"{at} has no id")
    if not str(v.get("label") or "").strip():
        out.append(f"{at} has no label")
    extra = sorted(set(v) - {"id", "label"} - set(CHANGES))
    if extra:
        out.append(f"{at} carries keys vary_recipe does not take: {', '.join(extra)}")
    if not any(v.get(k) not in (None, "", []) for k in CHANGES):
        out.append(f"{at} changes nothing: it needs words, picture, swap, stays_drop, people or person")
    w = v.get("words")
    # a zone with no words of its own (a picture field) stays an empty string, in its place (2026-10-28: the approved
    # warehouse headline has one, and all five rows were refused for keeping it)
    if w is not None and not (isinstance(w, list) and w and all(isinstance(x, str) for x in w) and any(x.strip() for x in w)):
        out.append(f"{at} words must be a list of strings, one per caption zone")
    if v.get("picture") is not None and not (isinstance(v["picture"], str) and v["picture"].strip()):
        out.append(f"{at} picture must be the one change, in words")
    sw = v.get("swap")
    if sw is not None:
        if not isinstance(sw, list) or not sw:
            out.append(f"{at} swap must be a list of rows")
        else:
            for r in sw:
                if not (isinstance(r, dict) and str(r.get("from") or "").strip() and str(r.get("to") or "").strip()):
                    out.append(f"{at} swap row needs a from and a to")
                elif r.get("kind") is not None and r["kind"] not in SWAP_KINDS:
                    out.append(f"{at} swap kind {r['kind']!r} is not one of {', '.join(SWAP_KINDS)}")
    sd = v.get("stays_drop")
    if sd is not None and not (isinstance(sd, list) and all(isinstance(x, str) and x.strip() for x in sd)):
        out.append(f"{at} stays_drop must be a list of lines")
    if v.get("people") is not None and v["people"] not in PEOPLE:
        out.append(f"{at} people must be {' or '.join(PEOPLE)}")
    p = v.get("person")
    if p is not None:
        if not isinstance(p, dict) or not p:
            out.append(f"{at} person must be an object with {', '.join(PERSON)}")
        else:
            bad = sorted(set(p) - set(PERSON))
            if bad:
                out.append(f"{at} person carries {', '.join(bad)}; it takes {', '.join(PERSON)}")
            if not all(isinstance(x, str) and x.strip() for x in p.values()):
                out.append(f"{at} person values must be words")
    return out


def validate(d):
    """Every way a record breaks the contract; [] when it holds."""
    if not isinstance(d, dict):
        return ["the record is not an object"]
    vs = d.get("variations")
    if not isinstance(vs, list):
        return ["no `variations` list"]
    out = []
    if len(vs) != COUNT:
        out.append(f"{len(vs)} variations: a batch is the approved picture plus exactly {COUNT}")
    for i, v in enumerate(vs):
        out += _row_problems(i, v)
    ids = [str(v.get("id")) for v in vs if isinstance(v, dict) and v.get("id")]
    dup = sorted({x for x in ids if ids.count(x) > 1})
    if dup:
        out.append(f"ids used twice: {', '.join(dup)}")
    return out


def block(text):
    """The last fenced json block in the answer that carries a `variations` list, parsed; None when there is none."""
    for raw in reversed(re.findall(r"```(?:json)?\s*\n(.*?)\n```", text, flags=re.S)):
        try:
            d = json.loads(raw)
        except ValueError:
            continue
        if isinstance(d, dict) and isinstance(d.get("variations"), list):
            return d
        if isinstance(d, list) and d and isinstance(d[0], dict) and "id" in d[0]:
            return {"variations": d}
    return None


def from_stage5(run):
    """(record, problems) from the stage 5 answer. The record is None when there is no block to read."""
    f = Path(run) / "out" / ANSWER
    if not f.is_file():
        return None, [f"no {ANSWER}"]
    d = block(f.read_text(errors="replace"))
    if d is None:
        return None, ["no fenced json block with a `variations` list in the answer"]
    rec = {"source": "stage5", "from": ANSWER, "variations": d["variations"]}
    return rec, validate(rec)


def load(run):
    f = Path(run) / "out" / FILE
    try:
        return json.loads(f.read_text()) if f.is_file() else None
    except ValueError:
        return None


def write(run, rec):
    """Writes out/variations.json. A file written by hand before stage 5 wrote one is kept beside it, never lost."""
    f = Path(run) / "out" / FILE
    old = load(run)
    if old is not None and old.get("source") != "stage5":
        keep = f.with_name("variations.by-hand.json")
        if not keep.exists():
            keep.write_text(f.read_text())
    f.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    return f


def show(run):
    rec = load(run)
    if not rec:
        print(f"no {FILE} in {Path(run).name}")
        return 1
    for v in rec.get("variations") or []:
        moved = [k for k in CHANGES if v.get(k) not in (None, "", [])]
        print(f"{v.get('id', '?'):<4} {str(v.get('label', ''))[:60]:<60}  {', '.join(moved)}")
    return 0


def _run_dir(name):
    p = Path(name)
    if p.is_dir():
        return p
    for r in Path(__file__).resolve().parents:
        f = r / "tools" / "image-teardown" / "tools" / "paths.py"
        if f.is_file():                     # the teardown's run_dir: runs/image-teardown/<brand>/<label>/ (2026-10-28)
            import importlib.util
            TP = sys.modules.get("image_teardown_paths")
            if TP is None:                  # loaded under its own name: a caller's own `paths` is never shadowed
                spec = importlib.util.spec_from_file_location("image_teardown_paths", f)
                TP = importlib.util.module_from_spec(spec)
                sys.modules["image_teardown_paths"] = TP
                spec.loader.exec_module(TP)
            q = TP.run_dir(name)
            if q.is_dir():
                return q
            break
    sys.exit(f"no run at {name}")


# THE HEADLINE IS A FORMAT (2026-10-27): the video hook step's discipline, on the picture's headline. the owner: "look at
# the headline process for video because that's pretty dialed in, we need to leverage the same process." Stage 5 v6
# prints the approved headline as a FORMAT with named [BLANKS]; every variation keeps every fixed word, in order. The
# check is video-teardown's own (machine/hook_format.py fixed_parts, fits), loaded by path, no model.

def _hook_format():
    import importlib.util
    f = Path(__file__).resolve().parents[2] / "video-teardown" / "machine" / "hook_format.py"
    spec = importlib.util.spec_from_file_location("iw_hook_format", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def format_line(run):
    """The FORMAT HEADLINE stage 5 wrote: the approved headline with its [BLANKS], or None."""
    f = Path(run) / "out" / "05-image-variations.md"
    if not f.is_file():
        return None
    return _hook_format().labelled(f.read_text(), "FORMAT HEADLINE")


def approved_headline(run):
    f = Path(run) / "out" / "approved-words.md"
    if not f.is_file():
        return None
    got = [l.split("`")[1] for l in f.read_text().splitlines() if l.count("`") >= 2]
    return got[0] if got else None


def format_problems(run, rec):
    """[] when the format is the approved headline's own words and every row's headline keeps every fixed word of it."""
    HF = _hook_format()
    fmt, appr = format_line(run), approved_headline(run)
    if not fmt:
        return ["no FORMAT HEADLINE line: print the approved headline as a format with its [BLANKS]"]
    out = []
    if appr and not HF.fits(fmt, appr):
        out.append(f"the FORMAT HEADLINE's fixed words are not the approved headline's own, in order ({fmt!r} vs {appr!r})")
    if not HF.fixed_parts(fmt):
        out.append("the FORMAT HEADLINE has no fixed words: everything is a blank")
    for v in rec.get("variations") or []:
        head = (v.get("words") or [""])[0]
        if head and not HF.fits(fmt, head):
            out.append(f"{v.get('id')} breaks the format: {head!r} does not keep every fixed word of {fmt!r}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("what", choices=("show", "check", "stage"))
    ap.add_argument("run")
    a = ap.parse_args()
    run = _run_dir(a.run)
    if a.what == "show":
        sys.exit(show(run))
    if a.what == "check":
        rec = load(run)
        bad = validate(rec) if rec is not None else [f"no {FILE}"]
        for b in bad:
            print("  ✗ " + b)
        print("ok" if not bad else f"{len(bad)} problem(s)")
        sys.exit(1 if bad else 0)
    rec, bad = from_stage5(run)
    if rec is None or bad:
        sys.exit("not written: " + "; ".join(bad))
    print(f"wrote {write(run, rec)}")


if __name__ == "__main__":
    main()
