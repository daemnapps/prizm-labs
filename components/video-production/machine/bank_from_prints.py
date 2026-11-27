#!/usr/bin/env python3
"""Bank a run's missing props and places from its finished 3D set prints (owner, 2026-11-20: "the print counts as the
element's picture").

The elements station refuses a run whose props and places are not banked (elements-standard.json: a picture, a real
reference, a file, a provenance record). A prop or place built into a scene's 3D set print is already drawn, at true
size, in the print: this door banks it with that print as its picture, so nothing new is generated or spent.

    python3 bank_from_prints.py <run dir> --handoff <hand-off folder> [--brand B] [--cover <artwork>] [--dry-run]

For every element the run's sheet (`<run>/elements.json` `to_make`) lists as a prop or setting:
  picture      the first finished print (`returned/`, recorded as a 3d-print) whose step in the hand-off's RUN.md
               names the element; a place gets `plates/wide.png` and two `plates/angle-N.png` from its prints
  reference    the real frame already in the element's `reference/` (the swipe's frame), else the swipe shot's
               first frame from the writing run's frame map: the real reference the standard asks for
  files        prop.md / set.md from the brief's own definition; provenance.json naming the print, its record, the
               3D project and the real reference
A prop whose look the brief says is real approved artwork laid on at the edit takes `--cover` (the artwork itself) as
both picture and reference. An element with no print naming it is left, said by name. Nothing is overwritten.
Writes only under runs/ai-elements/<brand>/. No brand, product or person is named here.
"""
import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
STEP = re.compile(r"^###\s*Step\s+\d+\s*·\s*`([^`]+)`\s*·\s*start picture for[^\n]*\n(.*?)(?=^###\s*Step|\Z)", re.M | re.S)


def _read(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def brief_doc(text):
    blocks = re.findall(r"```json\s*\n(.*?)\n```", text or "", re.S)
    try:
        return json.loads(blocks[-1]) if blocks else {}
    except ValueError:
        return {}


ANY_STEP = re.compile(r"^###\s*Step\s+\d+\s*·\s*`([^`]+)`\s*·\s*(start picture|clip) for\s+(S[\w.]+?(?:-shot-\d+)?)\b[^\n]*\n(.*?)(?=^###\s*Step|\Z)",
                      re.M | re.S)


def prints_naming(handoff: Path, name: str) -> list:
    """The finished 3D prints of the shots whose RUN.md steps (the start picture's or the clip's) name the element,
    in step order: a clip step's shot takes that shot's start-picture print."""
    got = Path(handoff) / "returned"
    words = re.compile(r"\b" + re.escape(name.lower()) + r"\b")
    steps = ANY_STEP.findall((Path(handoff) / "RUN.md").read_text())
    pic_of = {shot: f for f, what, shot, _ in steps if what == "start picture"}
    out = []
    for f, what, shot, body in steps:
        if not words.search(body.lower()):
            continue
        p = got / pic_of.get(shot, f if what == "start picture" else "")
        rec = _read(Path(str(p) + ".made.json"), {}) or {}
        if p.is_file() and rec.get("job") == "3d-print" and p not in out:
            out.append(p)
    return out


def _made(p: Path) -> dict:
    rec = _read(Path(str(p) + ".record.json"), {}) or {}
    gen = rec.get("generation") or {}
    return {"print": str(p), "record": str(p) + ".made.json", "project": gen.get("projectId"),
            "generation": gen.get("id"), "job": gen.get("jobSetType")}


def real_ref(folder: Path, td: Path, k: str = "K01"):
    """(file in the folder, where it came from): the element's own real frame, else the swipe shot's first frame."""
    ref = folder / "reference"
    have = sorted(x for x in ref.glob("*") if x.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")) if ref.is_dir() else []
    if have:
        m = re.search(r"(K\d+)", have[0].name)
        return have[0], f"the swipe's own frame{(' (' + m.group(1) + ')') if m else ''}, from {td.name}'s frame map"
    src = td / "framemap" / "shots" / f"{k}-first.jpg"
    return (src, f"the swipe's own frame ({k}), from {td.name}'s frame map") if src.is_file() else (None, "")


def _write(f: Path, text: str, dry: bool):
    if f.exists() or dry:
        return
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)


def _copy(src: Path, dst: Path, dry: bool):
    if dst.exists() or dry:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def provenance(element, kind, ref_file, ref_kind, ref_from, made_with, brand, sub, label):
    return json.dumps({"_what": "banked from the run's finished 3D set prints (owner, 2026-11-20: the print counts as the "
                                "element's picture)", "element": element, "kind": kind,
                       "made": time.strftime("%Y-%m-%d"),
                       "real_references": [{"file": ref_file, "kind": ref_kind, "from": ref_from}],
                       "rights": "our own 3D set print; the reference is " + ("our own artwork" if ref_kind == "real packshot"
                                                                              else "the swipe's frame, used as reference only"),
                       "made_with": made_with,
                       "drive": f"Shared Assets/runs/ai-elements/{brand}/{sub}/{element}/",
                       "runs": [label]}, indent=1, ensure_ascii=False) + "\n"


def bank(run: Path, handoff: Path, brand: str, cover: Path = None, dry: bool = False) -> dict:
    run, handoff = Path(run), Path(handoff)
    rj = _read(run / "run.json", {}) or {}
    bf = Path(rj.get("brief_from") or run / "brief.md")
    bf = bf if bf.is_absolute() else WS / bf          # run.json keeps a workspace-relative path
    doc = brief_doc(bf.read_text())
    td = bf.resolve().parent.parent
    props = {str(p.get("name")).lower(): p for p in doc.get("props") or [] if p.get("name")}
    world = {str(w.get("id")).lower(): w for w in doc.get("world") or [] if w.get("id")}
    sheet = _read(run / "elements.json", {}) or {}
    res = {"banked": {}, "left": {}}
    for it in sheet.get("to_make") or []:
        kind, eid = it.get("kind"), str(it.get("id"))
        folder = WS / str(it.get("folder") or "")
        if kind not in ("prop", "setting") or not it.get("folder"):
            continue
        if kind == "prop":
            d = props.get(eid.lower(), {})
            if cover and re.search(r"artwork|cover", str(d.get("look") or "") + " " + eid, re.I):
                _copy(cover, folder / "picture.png", dry)
                _copy(cover, folder / "reference" / ("artwork" + cover.suffix), dry)
                ref_file, ref_kind, ref_from = "reference/artwork" + cover.suffix, "real packshot", \
                    "our own approved artwork, as used before in " + cover.parent.parent.name
                made = {"pictures": "none generated — picture.png IS our approved artwork", "artwork": str(cover)}
            else:
                pr = prints_naming(handoff, eid)
                if not pr:
                    res["left"][eid] = "no finished 3D print names it"
                    continue
                ref, ref_from = real_ref(folder, td)
                if not ref:
                    res["left"][eid] = "no real reference to bank it from"
                    continue
                if ref.parent != folder / "reference":
                    _copy(ref, folder / "reference" / ref.name, dry)
                _copy(pr[0], folder / "picture.png", dry)
                ref_file, ref_kind = "reference/" + ref.name, "real video frame"
                made = {"pictures": "none generated — picture.png IS the 3D set print it stands in", **_made(pr[0])}
            _write(folder / "prop.md", f"# {eid}\n\n- What it is: {d.get('look') or eid}\n- Size: {d.get('size') or '—'}\n"
                                       f"- Where it came from: banked from {run.name}'s finished 3D set prints "
                                       f"(the print counts as its picture, owner 2026-11-20)\n- Ads: {run.name}\n", dry)
            _write(folder / "provenance.json", provenance(folder.name, "prop", ref_file, ref_kind, ref_from, made, brand,
                                                          "props", run.name), dry)
        else:
            w = world.get(eid.lower(), {})
            pr = prints_naming(handoff, eid)
            if len(pr) < 3:
                res["left"][eid] = f"{len(pr)} finished print(s) name it; a place needs a wide plate and two angles"
                continue
            ref, ref_from = real_ref(folder, td)
            if not ref:
                res["left"][eid] = "no real reference to bank it from"
                continue
            _copy(ref, folder / "reference" / ref.name, dry)
            _copy(pr[0], folder / "plates" / "wide.png", dry)
            _copy(pr[1], folder / "plates" / "angle-1.png", dry)
            _copy(pr[2], folder / "plates" / "angle-2.png", dry)
            _write(folder / "set.md", f"# {eid}\n\n{w.get('description') or ''}\n\n- Time of day: {w.get('time_of_day') or '—'}\n"
                                      f"- Light: {w.get('light') or '—'}\n- Dressing: {', '.join(w.get('dressing') or [])}\n"
                                      f"- Plates: the run's finished 3D set prints (owner 2026-11-20: the print counts as "
                                      f"the place's picture)\n- Ads: {run.name}\n", dry)
            _write(folder / "provenance.json", provenance(folder.name, "setting", "reference/" + ref.name,
                                                          "real video frame", ref_from,
                                                          {"pictures": "none generated — the plates ARE 3D set prints",
                                                           "plates": [_made(p) for p in pr[:3]]},
                                                          brand, "sets", run.name), dry)
        res["banked"][eid] = str(folder)
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run")
    ap.add_argument("--handoff", required=True)
    ap.add_argument("--brand")
    ap.add_argument("--cover", help="our approved artwork for a prop the brief says is laid on at the edit")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    brand = a.brand or (_read(Path(a.run) / "run.json", {}) or {}).get("brand")
    res = bank(Path(a.run), Path(a.handoff), brand, Path(a.cover) if a.cover else None, a.dry_run)
    for k, v in res["banked"].items():
        print(f"{'would bank' if a.dry_run else 'banked'} {k} → {v}")
    for k, v in res["left"].items():
        print(f"LEFT {k}: {v}")
    return 0 if not res["left"] else 1


if __name__ == "__main__":
    sys.exit(main())
