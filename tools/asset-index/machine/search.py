#!/usr/bin/env python3
"""
search.py — find a shot in the footage we own, with no service and no network.

    python3 machine/search.py --brand <brand> "man runs fingers along his jaw, razor bumps"

Reads the index records directly (work/<brand>-*/<clip_id>/clip.json +
breakdown.json) and scores every SCENE inside every clip — what it shows
(visuals, subject, setting, products, shot, usable_for) and what is said in it
(spoken, on-screen text) — against a description. Deterministic: the same
records and the same words give the same answer, every time.

Only clips that resolve to the company Shared Assets drive are returned
(shared_paths.py's map), so every answer is footage a person can actually open.
Each hit carries the clip, the time range inside it, the Shared Assets path,
the nearest indexed frame and a score from 0 to 1.

Creator footage is checked against the brand's usage-rights register
(rights.py): a clip whose creator's row forbids the use asked for (`use`,
"ads" by default) or whose window has ended is never returned (the team,
2026-10-30, after NO-ADS footage sat in the index); every hit carries its
`rights` verdict, `unknown` for a creator with no row.

Library: `search(query_seen, query_said, brand=...)` -> list of hits.
Brand-agnostic: the brand (and optionally the collections) come from the caller.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
if "shared_paths" in sys.modules:
    shared_paths = sys.modules["shared_paths"]
else:
    sys.path.insert(0, str(HERE))
    import shared_paths  # noqa: E402
# the usage-rights reader, loaded by path: a caller may have loaded this file by path too, and no other
# module named `rights` on sys.path may stand in for it
if "asset_index_rights" in sys.modules:
    rights = sys.modules["asset_index_rights"]
else:
    import importlib.util
    _spec = importlib.util.spec_from_file_location("asset_index_rights", HERE / "rights.py")
    rights = importlib.util.module_from_spec(_spec)
    sys.modules["asset_index_rights"] = rights
    _spec.loader.exec_module(rights)

STOP = set("""
a an the and or but if then than so of to in on at by for with from into onto over under up down out off
is are was were be been being am do does did done have has had having it its it's this that these those there here
he him his she her hers they them their we us our you your i me my mine yours
as not no nor too very just only also even still again ever never always all any some each every both
one two three first last next same other another more most less least much many few
can could would should will shall may might must
what which who whom whose when where why how
like about around through while after before because until
frame shot scene seen shows show showing camera lens close wide medium held holds hold looking look looks
left right top bottom edge centre center middle side part half
no none nothing visible just slightly little bit
still steady lens toward towards while across along away back front
""".split())

# A description's words, reduced so "bumps"/"bumping"/"bumped" meet.
def _stem(w: str) -> str:
    for suf in ("ingly", "edly", "ing", "ers", "ies", "ied", "ed", "es", "er", "ly", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            w = w[: -len(suf)]
            if suf in ("ies", "ied"):
                w += "y"
            break
    # doubled final consonant after stripping (running -> runn -> run)
    if len(w) > 3 and w[-1] == w[-2] and w[-1] not in "aeiouls":
        w = w[:-1]
    return w


def tokens(text: str, drop: set[str] | None = None) -> list[str]:
    out = []
    for w in re.findall(r"[A-Za-z][A-Za-z'\-]*", text or ""):
        lw = w.lower().strip("'-").replace("'s", "")
        if len(lw) < 3 or lw in STOP or (drop and lw in drop):
            continue
        out.append(_stem(lw))
    return out


# ------------------------------------------------------------- the records

MAPPED_WEIGHT = 0.7    # a name-only match scores below a described match of equal overlap (LD-59 (image records))


def _mapped_doc(rec_dir: Path, clip: dict) -> list[dict]:
    """A mapping-only record (described false, LD-59 (image records)): one document from its folder and file-name
    words plus any pointer text another component wrote. No scenes, so no in/out — a caller that cuts footage
    needs LD-63 (describe on use) first."""
    ws = " ".join(clip.get("words") or []) + " " + str(clip.get("text") or "")
    meta = clip.get("meta") or {}
    fr = (clip.get("frames") or [None])[0]
    return [{
        "clip_id": clip.get("clip_id") or rec_dir.name, "collection": rec_dir.parent.name, "scene": 1,
        "t_start": None, "t_end": None, "duration_s": meta.get("duration_s"),
        "visuals": str(clip.get("text") or ""), "spoken": "", "subject": "", "setting": "", "usable_for": [],
        "talking_head": False, "kind": clip.get("kind"), "described": False,
        "frame": str(rec_dir / fr["file"]) if fr and (rec_dir / fr["file"]).is_file() else None,
        "frame_file": fr["file"] if fr else None, "record_dir": str(rec_dir), "proxy": None,
        "seen": set(tokens(ws)), "shown": set(tokens(ws)), "said": set(),
    }]


def _scene_docs(rec_dir: Path, mapped: bool = True) -> list[dict]:
    try:
        clip = json.loads((rec_dir / "clip.json").read_text())
    except Exception:
        return []
    if clip.get("described") is False and not (rec_dir / "breakdown.json").is_file():
        return _mapped_doc(rec_dir, clip) if mapped else []
    try:
        bd = json.loads((rec_dir / "breakdown.json").read_text())
    except Exception:
        return []
    meta = clip.get("meta") or {}
    if not meta.get("duration_s"):
        return []                      # a still, not footage
    whole = " ".join(str(x) for x in [
        bd.get("subject") or "", bd.get("setting") or "",
        " ".join(bd.get("products_visible") or []), " ".join(bd.get("shot") or []),
        " ".join(bd.get("usable_for") or [])])
    frames = clip.get("frames") or []
    scenes = bd.get("scenes") or [{"t_start": 0.0, "t_end": meta.get("duration_s"),
                                   "visuals": bd.get("action") or "", "spoken": "", "on_screen_text": ""}]
    out = []
    for i, sc in enumerate(scenes):
        t0 = float(sc.get("t_start") or 0.0)
        t1 = float(sc.get("t_end") or meta.get("duration_s") or t0)
        mid = (t0 + t1) / 2
        fr = min(frames, key=lambda f: abs(float(f.get("at_s") or 0) - mid)) if frames else None
        out.append({
            "clip_id": clip.get("clip_id") or rec_dir.name,
            "collection": rec_dir.parent.name,
            "scene": i + 1,
            "t_start": round(t0, 2), "t_end": round(t1, 2),
            "duration_s": meta.get("duration_s"),
            "visuals": sc.get("visuals") or "",
            "spoken": sc.get("spoken") or "",
            "subject": bd.get("subject") or "",
            "setting": bd.get("setting") or "",
            "usable_for": bd.get("usable_for") or [],
            "products": list(bd.get("products_visible") or []),
            "talking_head": bool(bd.get("talking_head")),
            "frame": str(rec_dir / fr["file"]) if fr and (rec_dir / fr["file"]).is_file() else None,
            "frame_file": fr["file"] if fr else None,
            "record_dir": str(rec_dir),
            "proxy": str(rec_dir / "proxy.mp4") if (rec_dir / "proxy.mp4").is_file() else None,
            "seen": set(tokens(f"{sc.get('visuals') or ''} {whole}")),
            "shown": set(tokens(sc.get("visuals") or "")),
            "said": set(tokens(f"{sc.get('spoken') or ''} {sc.get('on_screen_text') or ''}")),
        })
    return out


def frame_of(hit: dict) -> str | None:
    """The frame picture for ONE hit, fetched when a caller asks: rebuilt through shared_paths.record_frames
    (a ranged seek when the record knows its Drive id, the picture itself for a still). Never called by search."""
    if hit.get("frame"):
        return hit["frame"]
    return _frame_now(hit)


def _frame_now(d: dict) -> str | None:
    """A hit with no frame picture on this machine gets it rebuilt from its clip through the key
    (shared_paths.record_frames, LD-58 (record frames on demand)) — one hit, on a caller's ask."""
    if not d.get("record_dir") or not d.get("frame_file"):
        return None
    for f in shared_paths.record_frames(d["record_dir"]):
        if Path(f).name == d["frame_file"]:
            return f
    return None


@lru_cache(maxsize=8)
def _corpus(brand: str, work: str, maps: str, collections: tuple | None, mapped: bool = True) -> tuple:
    work_p, maps_p = Path(work), Path(maps)
    if collections:
        cols = [work_p / c for c in collections]
    elif work_p == shared_paths.WORK:
        cols = shared_paths.collections(brand)    # runs/asset-index/ first (in git, keyed by Drive id), then work/
    else:
        cols = shared_paths.collections_of(brand, work_p)
    docs = []
    for col in cols:
        m = shared_paths.load_map(col, maps_p)
        for rec in sorted(p for p in col.iterdir() if (p / "clip.json").is_file()):
            e = m.get(rec.name) or {}
            label = e.get("label") or shared_paths.label_of(e.get("path"))
            if not label:
                continue               # never a personal-drive path, never an unresolved clip
            # KEYS ONLY (LD-56 (footage index in git)): a record is accepted on its "Shared Assets/…" label
            # (and Drive id when it has one) — never by testing this machine's mount
            for d in _scene_docs(rec, mapped):
                d["shared_path"] = label
                d["drive_id"] = e.get("drive_id") or (rec.name if (col / "map.json").is_file() else None)
                docs.append(d)
    n = len(docs) or 1
    df: dict[str, int] = {}
    for d in docs:
        for t in d["seen"] | d["said"]:
            df[t] = df.get(t, 0) + 1
    idf = {t: math.log(1 + n / c) for t, c in df.items()}
    return docs, idf, n


def _cover(q: list[str], have: set[str], idf: dict, unknown: float) -> float:
    q = list(dict.fromkeys(q))
    if not q:
        return 0.0
    tot = sum(idf.get(t, unknown) for t in q)
    hit = sum(idf.get(t, unknown) for t in q if t in have)
    return hit / tot if tot else 0.0


def search(seen: str, said: str = "", brand: str = "", *, core: str = "", require: list[str] | None = None,
           per: int = 3, drop: set[str] | None = None,
           work: Path | None = None, maps: Path | None = None, collections: list[str] | None = None,
           exclude_talking: bool = False, mapped: bool = True, use: str | None = "ads",
           rights_file: Path | None = None, today=None) -> list[dict]:
    """Best owned scenes for a description. `seen` = what the shot shows; `said` =
    the words over it. `core` = the action itself (what HAPPENS), when the
    caller can tell it apart from the detail of the frame — a long frame
    description (the tee, the chain, the window) otherwise outweighs the one
    thing the shot must show. `require` = named things (a product) the clip
    must show to stand in for the shot; each hit lists the ones it lacks in
    `missing`. `drop` = words to ignore (invented names).
    `mapped` = let name-only records (described false, LD-59 (image records)) join; they score at
    MAPPED_WEIGHT and every hit says `described`.
    `use` = what the footage is for, "ads", "website" or "email" (rights.py; for email only `allowed` comes back): creator footage whose usage-rights
    row refuses that use, or whose `until` has passed, is left out; None = no filter (every hit still
    carries its `rights`). `rights_file` = a register other than the brand's own (tests).
    -> hits, best first, at most one per clip."""
    docs, idf, n = _corpus(brand, str(work or shared_paths.WORK), str(maps or shared_paths.MAPS),
                           tuple(collections) if collections else None, mapped)
    if not docs:
        return []
    unknown = math.log(1 + n)          # a word no record has weighs the most: nothing like it exists
    qc = tokens(core, drop)
    qs = tokens(f"{seen} {core}", drop)
    qw = tokens(said, drop)
    need = sorted({t for r in require or [] for t in tokens(r)})
    register = rights.load(brand, rights_file)
    seen_rights: dict[str, dict] = {}
    best: dict[str, dict] = {}
    for d in docs:
        if exclude_talking and d["talking_head"]:
            continue
        ok = seen_rights.get(d["shared_path"])
        if ok is None:
            ok = seen_rights[d["shared_path"]] = rights.verdict(d["shared_path"], register, use or "ads", today)
        if use and ok["state"] in ("refused", "expired"):
            continue
        if use == "email" and ok["state"] != "allowed":
            continue                   # a person in an email is a cleared creator, never footage of no one's (LD-101)
        # recall: how much of what the scene must show this clip's scene shows
        rec = _cover(qs, d["seen"], idf, unknown)
        crec = _cover(qc, d["seen"], idf, unknown) if qc else None
        if qc:
            # the action counts most: a clip that does the thing beats one that
            # only shares the frame's furniture
            rec = 0.6 * _cover(qc, d["seen"], idf, unknown) + 0.4 * rec
        # precision: how much of what this clip's scene shows the scene asks for —
        # a long montage matches many words by chance and is not the shot
        prec = _cover(sorted(d["shown"]), set(qs) | set(qw), idf, unknown) if d["shown"] else 0.0
        # a three-word note ("Man looks at camera.") is not evidence of the shot
        prec *= min(1.0, len(d["shown"]) / 6)
        vis = 0.6 * rec + 0.4 * prec
        # the words over it only break ties between pictures; they never make one
        spk = _cover(qw, d["said"] | d["seen"], idf, unknown) if qw else 0.0
        score = vis * (0.85 + 0.15 * spk) if qw else vis * 0.85
        if d["talking_head"]:
            score *= 0.85              # B-roll wants the thing shown, not a face talking
        if d.get("described") is False:
            score *= MAPPED_WEIGHT
        if score <= 0:
            continue
        cur = best.get(d["clip_id"])
        if cur is None or score > cur["score"]:
            best[d["clip_id"]] = {
                "clip_id": d["clip_id"], "collection": d["collection"], "score": round(score, 3),
                "seen_match": round(vis, 3), "said_match": round(spk, 3),
                "missing": [t for t in need if t not in d["seen"] and t not in d["said"]],
                "action_match": None if crec is None else round(crec, 3), "action_words": len(set(qc)),
                "in": d["t_start"], "out": d["t_end"],
                "shared_path": d["shared_path"], "drive_id": d.get("drive_id"), "frame": d["frame"], "proxy": d["proxy"],
                # a hit with no frame on disk comes back WITHOUT one; frame_of(hit) fetches it when a caller
                # asks (the full-download guard, 2026-10-21) — a search never reads a clip
                "record_dir": d["record_dir"], "frame_file": d.get("frame_file"),
                "shows": d["visuals"], "says": d["spoken"], "talking_head": d["talking_head"],
                "products": d.get("products") or [],
                "described": d.get("described", True), "kind": d.get("kind") or "video",
                "rights": ok,
            }
    hits = sorted(best.values(), key=lambda h: (-h["score"], h["clip_id"]))
    return hits[:per]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query")
    ap.add_argument("--said", default="")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--per", type=int, default=5)
    a = ap.parse_args(argv)
    for h in search(a.query, a.said, a.brand, per=a.per):
        span = f"{h['in']:.1f}-{h['out']:.1f}s" if h["in"] is not None else f"({h['kind']}, not described)"
        print(f"{h['score']:.2f}  {h['clip_id']}  {span}  {h['shows'][:90]}")
        print(f"      {h['shared_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
