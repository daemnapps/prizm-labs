#!/usr/bin/env python3
"""CONSISTENCY — one look per ad, the same person in every picture, the same place in every shot, measured.

    python3 consistency.py --production <idea> [--out <dir>]

Reads the production's elements through style_chain.py (its style, its pinned look, each person's and location's one
variant) and checks, with a PASS / FAIL / NOT YET line each:

  look      every element of the ad was made with the ad's ONE pinned look reference and its style
  one       every person and location resolves to exactly one folder in the ad's style
  person    the same face in every picture of that person: SFace likeness of each picture's best face to the person's
            kept 3D print in the ad's style (else their master; the reader take_layers.py and lips.py use), at or over
            SAME (OpenCV's own SFace match line); and each picture nearer to them than to anyone else in the cast
  cast      one style across the whole cast: each person's master sits as close to the rest of the cast as the others
            do (SFace reads a shared drawn style as closeness), within STYLE_GAP of the cast's median
  place     the same place in every shot of that location: colour match of each shot to the set's picture (Lab
            colour histogram correlation at or over PLACE_CORR, mean colour within PLACE_DE)

Pictures read: a person's sheets and master in the ad's style, their kept 3D print, and every production still whose
record names them (`picture_from`). A location's set picture and every production still that names it (a take's record, or a start picture's
motion/first-frame.json, which names its set and the variant sheets it was made from).
Writes <out>/consistency.json, CONSISTENCY.md and consistency.jpg (each person and location, all their pictures side by
side, each marked with its score). Agnostic: nothing here names a brand, person or style. No model is called.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAME = 0.363          # SFace cosine at which two faces are the same person (OpenCV's own match threshold)
PLACE_CORR = 0.50     # Lab a/b histogram correlation at which a shot is the same place's colour
PLACE_DE = 18.0       # mean Lab distance (ΔE76) within which a shot keeps the set's colour
NO_FACE = ("colour-key", "details", "hands")       # sheets that show no face: not read for likeness
CACHE = Path.home() / ".cache" / "take-layers"     # the face models take_layers.py and lips.py fetch


def _load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


SC = _load("cons_style_chain", HERE / "style_chain.py")


# ── verdicts (pure: tested without any model) ────────────────────────────────────────────────────────────────────────

def person_verdict(name: str, scores: dict, others: dict) -> dict:
    """scores: {picture: likeness to own reference or None (no face read)}; others: {picture: (nearest other person,
    their likeness)}. PASS when every read picture is at or over SAME and, picture by picture, nearer to this person
    than to anyone else in the cast."""
    read = {k: v for k, v in scores.items() if v is not None}
    if not read:
        return {"name": name, "verdict": "NOT YET", "why": "no face could be read in any picture"}
    low = sorted(k for k, v in read.items() if v < SAME)
    swapped = sorted(k for k, v in read.items() if k in others and others[k][1] >= v)
    own = min(read.values())
    if low or swapped:
        why = []
        if low:
            why.append(f"{len(low)} of {len(read)} pictures under {SAME}: " + ", ".join(Path(k).stem for k in low))
        if swapped:
            why.append("nearer someone else: " + ", ".join(f"{Path(k).stem} ({others[k][0]} {others[k][1]:.2f} vs "
                                                          f"{read[k]:.2f})" for k in swapped))
        return {"name": name, "verdict": "FAIL", "why": "; ".join(why), "lowest": round(own, 3)}
    near = max((v[1] for v in others.values()), default=None)
    return {"name": name, "verdict": "PASS", "lowest": round(own, 3),
            "why": f"{len(read)} pictures, lowest likeness {own:.2f} (line {SAME})"
                   + (f"; nearest anyone else gets {near:.2f}" if near is not None else "")}


STYLE_GAP = 0.20      # how far below the cast's median closeness one person may sit and still share the cast's style


def cast_style_verdict(closeness: dict) -> dict:
    """closeness: {person: mean SFace likeness of their master to every other cast member's master}. In a cast drawn
    in one style the faces sit close together (the style dominates the read); a half-stylised person sits far below the
    rest. PASS when everyone is within STYLE_GAP of the cast's median; needs three people or more."""
    if len(closeness) < 3:
        return {"verdict": "NOT YET", "why": "needs three people or more to measure one style across the cast"}
    vals = sorted(closeness.values())
    med = vals[len(vals) // 2] if len(vals) % 2 else (vals[len(vals) // 2 - 1] + vals[len(vals) // 2]) / 2
    off = sorted(k for k, v in closeness.items() if v < med - STYLE_GAP)
    band = ", ".join(f"{k} {v:.2f}" for k, v in sorted(closeness.items(), key=lambda x: -x[1]))
    if off:
        return {"verdict": "FAIL", "why": f"not in the cast's style: {', '.join(off)} (median {med:.2f}, band "
                                          f"{med - STYLE_GAP:.2f}+; {band})"}
    return {"verdict": "PASS", "why": f"one style across {len(vals)} people (median {med:.2f}; {band})"}


def place_verdict(name: str, scores: dict) -> dict:
    """scores: {shot: (histogram correlation, mean ΔE)}. PASS when every shot keeps the set's colour."""
    if not scores:
        return {"name": name, "verdict": "NOT YET", "why": "no shot of this location made yet"}
    bad = sorted(k for k, (c, de) in scores.items() if c < PLACE_CORR or de > PLACE_DE)
    if bad:
        return {"name": name, "verdict": "FAIL", "why": f"{len(bad)} of {len(scores)} shots off the set's colour: " + ", ".join(bad)}
    return {"name": name, "verdict": "PASS",
            "why": f"{len(scores)} shots, lowest correlation {min(c for c, _ in scores.values()):.2f}, "
                   f"largest ΔE {max(de for _, de in scores.values()):.1f}"}


def look_verdict(style_id, pinned: dict | None, records: dict) -> dict:
    """records: {element: {"style": id, "look": file or None}}. PASS when every element is in the ad's style and was
    made with the pinned look (an element born before the pin, with no look recorded, is listed, not failed)."""
    if not records:
        return {"verdict": "NOT YET", "why": "no element made yet"}
    off = sorted(k for k, r in records.items() if r.get("style") != style_id)
    other = sorted(k for k, r in records.items() if pinned and r.get("look") and
                   Path(r["look"]).name != Path(pinned.get("file", "")).name)
    if off or other:
        return {"verdict": "FAIL", "why": "; ".join(x for x in (
            ("not in the ad's style: " + ", ".join(off)) if off else "",
            ("made with another look picture: " + ", ".join(other)) if other else "") if x)}
    return {"verdict": "PASS", "why": f"{len(records)} elements, all {style_id}, one look picture "
                                      f"({Path((pinned or {}).get('file', 'none')).name})"}


def one_verdict(elements: list) -> dict:
    """Every person and location resolves to exactly one folder in the ad's style."""
    seen, dup, none = {}, [], []
    for e in elements:
        if e.get("kind") not in ("person", "set"):
            continue
        key = (e["kind"], e.get("name") or e["id"])
        if not e.get("dir") or e.get("state") not in ("have", "master"):
            none.append(key[1])
        elif key in seen and seen[key] != e["dir"]:
            dup.append(key[1])
        seen[key] = e.get("dir")
    if dup or none:
        return {"verdict": "FAIL" if dup else "NOT YET",
                "why": "; ".join(x for x in (("two folders: " + ", ".join(dup)) if dup else "",
                                             ("not made yet: " + ", ".join(none)) if none else "") if x)}
    return {"verdict": "PASS", "why": f"{len(seen)} people and locations, one folder each"}


# ── pictures ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def person_pictures(e: dict, production_dir: Path | None, brand: str) -> list:
    d = Path(e["dir"])
    pics = [p for p in [d / "master.jpg"] if p.is_file()]
    pics += [p for p in sorted((d / "sheets").glob("*.jpg")) if not any(n in p.stem for n in NO_FACE)]
    sets = SC.workspace() / "runs" / "image-production" / brand / "sets" / f"cast-{e['id']}-{e['style']}"
    rec = SC._read(sets / "set.json")
    pics += [sets / p["file"] for p in rec.get("prints") or [] if str(p.get("note", "")).startswith("kept")
             and (sets / p["file"]).is_file()]
    return pics + production_stills(production_dir, e, "person")


def anchor(e: dict, brand: str) -> Path:
    """The picture a person is measured against: their kept 3D print in the ad's style (the one every sheet was made
    from), else their master."""
    sets = SC.workspace() / "runs" / "image-production" / brand / "sets" / f"cast-{e['id']}-{e['style']}"
    kept = [p for p in SC._read(sets / "set.json").get("prints") or [] if str(p.get("note", "")).startswith("kept")]
    if kept and (sets / kept[-1]["file"]).is_file():
        return sets / kept[-1]["file"]
    return Path(e["dir"]) / "master.jpg"


def production_stills(production_dir: Path | None, e: dict, kind: str) -> list:
    """The production's stills whose record names this element (`picture_from` [{element, file}] or `set`)."""
    out = []
    if not production_dir or not production_dir.is_dir():
        return out
    for rec in list(production_dir.glob("scenes/*/*.json")) + list(production_dir.glob("scenes/*/motion/first-frame.json")):
        r = SC._read(rec)
        names = {str(x.get("element", "")).split("/styles/")[0] for x in r.get("picture_from") or [] if isinstance(x, dict)}
        if kind == "set":
            names |= {str(r.get("set") or "").split("/styles/")[0]}
        if e["id"] in names:
            for key in ("picture", "start", "still"):
                f = r.get(key)
                if f and (rec.parent / f).is_file():
                    out.append(rec.parent / f)
    return out


def vision_python():
    for p in (os.environ.get("VISION_PYTHON"), str(CACHE / "venv" / "bin" / "python")):
        if p and Path(p).exists():
            return p
    return None


class Faces:
    """YuNet finds faces, SFace tells them apart: the same two readers take_layers.py uses."""

    def __init__(self):
        import cv2
        self.cv2 = cv2
        self.det = cv2.FaceDetectorYN.create(str(CACHE / "yunet.onnx"), "", (320, 320), 0.6, 0.3, 50)
        self.rec = cv2.FaceRecognizerSF.create(str(CACHE / "sface.onnx"), "")

    def vectors(self, path):
        import numpy as np
        img = self.cv2.imread(str(path))
        if img is None:
            return []
        s = 1600 / max(img.shape[:2])
        img = self.cv2.resize(img, None, fx=s, fy=s)
        self.det.setInputSize((img.shape[1], img.shape[0]))
        _, rows = self.det.detect(img)
        out = []
        for r in rows if rows is not None else []:
            if r[2] < img.shape[1] * 0.03:
                continue
            v = self.rec.feature(self.rec.alignCrop(img, r)).ravel()
            out.append(v / (np.linalg.norm(v) + 1e-9))
        return out


def likeness(vecs, ref_vecs) -> float | None:
    if not vecs or not ref_vecs:
        return None
    return float(max(float(a @ b) for a in vecs for b in ref_vecs))


def place_score(ref, shot) -> tuple:
    import cv2
    import numpy as np
    a, b = (cv2.cvtColor(cv2.resize(cv2.imread(str(p)), (256, 256)), cv2.COLOR_BGR2LAB) for p in (ref, shot))
    h = [cv2.normalize(cv2.calcHist([x], [1, 2], None, [32, 32], [0, 256, 0, 256]), None).flatten() for x in (a, b)]
    corr = float(cv2.compareHist(h[0], h[1], cv2.HISTCMP_CORREL))
    de = float(np.linalg.norm(a.reshape(-1, 3).mean(0) - b.reshape(-1, 3).mean(0)) * 100 / 255)
    return round(corr, 3), round(de, 1)


def picture(rows: list, out: Path) -> None:
    """One row per person or location: every picture side by side, each captioned with its score and a mark."""
    from PIL import Image, ImageDraw
    H, pad, cap = 260, 8, 34
    lines = []
    for r in rows:
        ims = []
        for p, label, ok in r["pics"]:
            im = Image.open(p).convert("RGB")
            im.thumbnail((int(H * 1.6), H))
            ims.append((im, label, ok))
        lines.append((r["title"], r["verdict"], ims))
    width = max([sum(i.width + pad for i, _, _ in ims) for _, _, ims in lines] + [600]) + pad
    height = sum(H + cap + 40 for _ in lines) + pad
    sheet = Image.new("RGB", (width, height), (246, 244, 240))
    d = ImageDraw.Draw(sheet)
    y = pad
    for title, verdict, ims in lines:
        col = {"PASS": (47, 122, 79), "FAIL": (180, 50, 40)}.get(verdict, (110, 102, 94))
        d.text((pad, y + 8), f"{title}   {verdict}", fill=col)
        y += 30
        x = pad
        for im, label, ok in ims:
            sheet.paste(im, (x, y))
            d.rectangle([x, y + H + 2, x + im.width, y + H + cap - 4], fill=(255, 255, 255))
            mark = "" if ok is None else ("OK " if ok else "OFF ")
            d.text((x + 4, y + H + 8), (mark + label)[:40], fill=(47, 122, 79) if ok else (180, 50, 40) if ok is False else (60, 60, 60))
            x += im.width + pad
        y += H + cap + 10
    sheet.save(out, quality=85)


def check(production: str, out: Path, briefs: Path | None = None) -> dict:
    n = SC.needs(production, briefs)
    sid = n["style"]["id"]
    pinned = SC.ad_look(production, briefs, pin=False)
    bdir = SC.brief_path(production, briefs).parent
    people = [e for e in n["elements"] if e["kind"] == "person" and e.get("dir")]
    places = [e for e in n["elements"] if e["kind"] == "set"]
    records = {}
    for e in n["elements"]:
        if not e.get("dir"):
            continue
        d = Path(e["dir"])
        rec = SC._read(d / "spec.json") or SC._read(d / "element.json")
        prov = SC._read(d / "provenance.json")
        look = (prov.get("look_from") or {}).get("file") if isinstance(prov.get("look_from"), dict) else None
        look = look or next((Path(d, x["file"]).name for x in rec.get("production_references") or []
                             if "look only" in str(x.get("use", ""))), None) or (rec.get("look") or {}).get("file")
        records[e.get("name") or e["id"]] = {"style": SC.canonical(rec.get("style_id")) or SC.master_style(d) or sid
                                             if e["state"] in ("have", "master") else None, "look": look}
    result = {"production": production, "style": sid, "look": pinned,
              "look_check": look_verdict(sid, pinned, records), "one_check": one_verdict(n["elements"]),
              "people": [], "places": []}
    rows = []
    if people:
        F = Faces()
        masters = {e["name"]: F.vectors(anchor(e, n["brand"])) for e in people}
        mvec = {}
        for e in people:
            pics = person_pictures(e, bdir, n["brand"])
            scores, vec_of = {}, {}
            for p in pics:
                vec_of[p] = F.vectors(p)
                scores[str(p.relative_to(SC.workspace())) if SC.workspace() in p.parents else p.name] = likeness(vec_of[p], masters[e["name"]])
            others = {}
            for (key, p) in zip(scores, pics):
                best = [(o, likeness(vec_of[p], masters[o])) for o in masters if o != e["name"] and masters[o]]
                best = [b for b in best if b[1] is not None]
                if best and scores[key] is not None:
                    others[key] = max(best, key=lambda b: b[1])
            v = person_verdict(e["name"], scores, others)
            mvec[e["name"]] = F.vectors(Path(e["dir"]) / "master.jpg")
            v["scores"] = {k: (round(x, 3) if x is not None else None) for k, x in scores.items()}
            result["people"].append(v)
            rows.append({"title": f"{e['name']} · {e['id']} · {sid}", "verdict": v["verdict"],
                         "pics": [(p, (f"{s:.2f} " if s is not None else "no face ") + p.stem[:22],
                                   None if s is None else s >= SAME) for p, s in zip(pics, scores.values())]})
    if people:
        close = {}
        for a in mvec:
            sims = [likeness(mvec[a], mvec[b]) for b in mvec if b != a]
            sims = [x for x in sims if x is not None]
            if sims:
                close[a] = round(sum(sims) / len(sims), 3)
        result["cast_style"] = dict(cast_style_verdict(close), closeness=close)
    else:
        result["cast_style"] = cast_style_verdict({})
    for e in places:
        ref = Path(e["picture"]) if e.get("picture") else None
        shots = production_stills(bdir, e, "set") if ref else []
        scores = {s.name: place_score(ref, s) for s in shots}
        v = place_verdict(e.get("name") or e["id"], scores)
        v["scores"] = scores
        result["places"].append(v)
        if ref:
            rows.append({"title": f"{e.get('name') or e['id']} · set · {sid}", "verdict": v["verdict"],
                         "pics": [(ref, "set picture", None)] + [(s, f"{c:.2f}/{de:.0f} {s.stem[:16]}",
                                                                   c >= PLACE_CORR and de <= PLACE_DE)
                                                                  for s, (c, de) in zip(shots, scores.values())]})
    out.mkdir(parents=True, exist_ok=True)
    (out / "consistency.json").write_text(json.dumps(result, indent=1, ensure_ascii=False, default=str) + "\n")
    (out / "CONSISTENCY.md").write_text(markdown(result))
    if rows:
        picture(rows, out / "consistency.jpg")
    return result


def markdown(r: dict) -> str:
    L = [f"# Consistency · {r['production']} · {r['style']}", "",
         f"Look picture (one for the whole ad): `{Path((r.get('look') or {}).get('file', 'none')).name}`", "",
         "| Check | Verdict | Why |", "|---|---|---|",
         f"| One look | {r['look_check']['verdict']} | {r['look_check']['why']} |",
         f"| One variant each | {r['one_check']['verdict']} | {r['one_check']['why']} |",
         f"| One style across the cast | {r['cast_style']['verdict']} | {r['cast_style']['why']} |"]
    for p in r["people"]:
        L.append(f"| Same person · {p['name']} | {p['verdict']} | {p['why']} |")
    for p in r["places"]:
        L.append(f"| Same place · {p['name']} | {p['verdict']} | {p['why']} |")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--production", required=True)
    ap.add_argument("--out", help="folder for the report (default: the production's own folder)")
    a = ap.parse_args(argv)
    try:
        import cv2  # noqa: F401
    except ImportError:
        py = vision_python()
        if not py or os.environ.get("CONSISTENCY_REEXEC"):
            raise SystemExit("the face reader needs opencv: run components/video-studio/lips.py setup once on this machine")
        return subprocess.call([py, __file__] + (argv or sys.argv[1:]), env=dict(os.environ, CONSISTENCY_REEXEC="1"))
    out = Path(a.out) if a.out else SC.brief_path(a.production).parent
    r = check(a.production, out)
    print(markdown(r))
    print(f"report: {out / 'CONSISTENCY.md'} · picture: {out / 'consistency.jpg'}")
    return 1 if any(x["verdict"] == "FAIL" for x in [r["look_check"], r["one_check"], r["cast_style"]]
                    + r["people"] + r["places"]) else 0


if __name__ == "__main__":
    sys.exit(main())
