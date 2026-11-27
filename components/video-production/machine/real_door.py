#!/usr/bin/env python3
"""THE REAL-FOOTAGE DOOR — the Real lane's one swap in the AI chain (owner ruling, 20 Nov 2026: a Real production runs
the AI chain's stations exactly; only generation changes).

ai_lane.py runs every station as for an AI brief; at three stations it calls this door instead of a paid one:

    elements   elements(run, brief, brand, cast)  every brief person bound to a real cast-bank entry, or a footage
                                                  extra (never made); places, props and the product come from footage
    pictures   pictures(run)                      every picture the storyboard lists (media/<scene>-F1 ...) is a frame
                                                  of the section's cast member's best-matching moment
    clips      clips(run)                         every call in clips/plan.json is that cast member's moments, matched to
                                                  the call's direction, trimmed or joined to the call's seconds, written
                                                  to clips/<call id>.mp4

The cast is <run>/real-cast.json {"cast": {brief cast id: cast-bank id}} (the first is the lead). Each cast-bank entry
(runs/ai-elements/<brand>/casting/<id>/spec.json) carries real_footage {where, plays, only_scenes_with}. The matching is
the Studio's cast matcher (components/video-studio/cast_picks.py Matcher): the asset index searched inside that
person's footage only, other brands refused, placed on a clean measured moment, no stretch used twice in the ad. Each
placement is looked at through frame_look.looked (the moments index's judged look: letterbox, other brand, captions
marked, not refused) and the cast through swipe_cut.cast_check. Every picture and clip gets a provenance record
(<file>.real.json: source clip, in and out, why). Nothing is generated and no credit is spent: ffmpeg only.

    python3 real_door.py pictures <run>      python3 real_door.py clips <run>      python3 real_door.py check <run>

No brand, product or person is named here.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
STUDIO = WS / "components" / "video-studio"
W, H = 1080, 1920                  # every deliverable is 9:16 at 1080x1920
FILL = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"
MIN_PIECE = 2.0                    # a joined clip's shortest piece (seconds)
TRIES = 4                          # placements looked at before a refused look is kept with its reason


def _read(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def _write(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str) + "\n")


def _studio():
    """The Studio's cast matcher and the footage library's root on this machine."""
    if str(STUDIO) not in sys.path:
        sys.path.insert(0, str(STUDIO))
    import cast_picks as CP  # noqa: E402
    import seed_from_brief as SB  # noqa: E402
    return CP, SB


def _chain(name):
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    return __import__(name)


def _brief_doc(text):
    blocks = re.findall(r"```json\s*\n(.*?)\n```", text or "", re.S)
    try:
        return json.loads(blocks[-1]) if blocks else {}
    except ValueError:
        return {}


def _first_named(cast, text):
    """The cast id named EARLIEST in the text (a picture's subject names who it is about first), or None."""
    pos = [(m.start(), b) for b in cast for m in [re.search(r"\b%s\b" % re.escape(b), str(text or ""), re.I)] if m]
    return min(pos)[1] if pos else None


# ------------------------------------------------------------------ the cast

def cast_file(run) -> Path:
    return Path(run) / "real-cast.json"


def parse_cast(text: str) -> dict:
    """"A=bank-a,B=bank-b" -> {"A": "bank-a", "B": "bank-b"} (order kept: the first is the lead)."""
    out = {}
    for part in [p.strip() for p in str(text or "").split(",") if p.strip()]:
        if "=" not in part:
            raise SystemExit(f"--cast takes BRIEF_ID=cast-bank-id pairs, comma separated; got {part!r}")
        k, v = part.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def elements(run, brief, brand: str, cast: dict) -> dict:
    """THE ELEMENTS STATION, REAL: every person the brief names is bound to a real cast-bank entry with footage, or is a
    footage extra (never made); settings, props and the product come from the cast's own footage. Refuses a cast id the
    brief does not name, and a cast-bank entry with no footage folder. Writes <run>/real-cast.json."""
    CP, _ = _studio()
    roles = CP.roles_of(brand, cast)                       # refuses an entry with no real_footage.where
    ec = _chain("elements_check")
    text = Path(brief).read_text()
    td = ec.resolve_teardown(Path(brief).resolve().parent.parent)
    sh = ec.sheet(text, brand, root=WS, teardown=td)
    items = sh.get("items") or []
    people = [i["id"] for i in items if i.get("kind") == "person"]
    unknown = [b for b in cast if b not in people]
    if unknown:
        raise SystemExit("real cast names " + ", ".join(unknown) + " — not a person in this brief (" + ", ".join(people) + ")")
    folder = lambda w: [p for p in w.strip("/").split("/") if p][-1]  # noqa: E731
    rec = {"schema": "real-cast/v1", "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "brand": brand,
           "brief": str(brief), "cast": dict(cast), "lead": next(iter(cast)),
           "bound": {b: {"cast_bank": cast[b], "where": roles[b]["where"], "folder": folder(roles[b]["where"][0]),
                         "plays": roles[b].get("plays") or {}, "only_scenes_with": roles[b].get("only_scenes_with")}
                     for b in cast},
           "extras": [p for p in people if p not in cast],
           "from_footage": [f"{i['kind']} {i['id']}" for i in items if i.get("kind") != "person"],
           "made": [], "note": "Real lane: no person, place or prop is generated; a person with no real cast-bank entry "
                               "is a footage extra (whoever the cast's own footage shows)."}
    _write(cast_file(run), rec)
    return rec


def cast_of(run) -> dict:
    rec = _read(cast_file(run), {}) or {}
    if not rec.get("cast"):
        raise SystemExit(f"no real cast on this run ({cast_file(run)}): the elements station binds it first")
    return rec


def _brand(run, rec):
    return rec.get("brand") or (_read(Path(run) / "run.json", {}) or {}).get("brand")


def _setup(run):
    CP, SB = _studio()
    rec = cast_of(run)
    brand = _brand(run, rec)
    cast = rec["cast"]
    roles = CP.roles_of(brand, cast)
    root = SB.drive_root()
    M = CP.Matcher(brand, [str(root)] if root else [])
    for f in (Path(run) / "media").glob("*.real.json"):     # stretches this ad already plays stay taken
        p = _read(f, {}) or {}
        if p.get("file"):
            M.take(p["file"], float(p["in"]), float(p["out"]) - float(p["in"]))
    for f in (Path(run) / "clips").glob("*.real.json"):
        for piece in (_read(f, {}) or {}).get("pieces") or []:
            M.take(piece["file"], float(piece["in"]), float(piece["out"]) - float(piece["in"]))
    return CP, M, brand, cast, roles, rec["lead"]


def _look(brand, h, start, need, shows):
    """The moments index's judged look of this stretch (frame_look.looked) -> (ok, said); (True, "not judged") when no
    judged moment covers it (a live look is a paid model call, so it is never asked here)."""
    try:
        FL = _chain("frame_look")
        got = FL.looked(brand, h.get("shared_path") or "", start, need, shows, {"footage": True})
    except Exception as e:  # noqa: BLE001
        return True, f"not looked ({type(e).__name__})"
    if got is None:
        return True, "not judged by the moments index"
    return got


_DUR = {}


def duration(f) -> float:
    """A clip's length in seconds (ffprobe), 0 when it cannot be read."""
    if f not in _DUR:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                           capture_output=True, text=True)
        try:
            _DUR[f] = float(r.stdout.strip())
        except ValueError:
            _DUR[f] = 0.0
    return _DUR[f]


def _free(M, f, start, need) -> bool:
    return not any(ff == f and not (start + need <= a or start >= b) for ff, a, b in M.used)


def _fit(M, f, start, need):
    """The start that plays `need` seconds inside the clip's real length (moved back from its end when it runs over),
    or None when the clip is shorter or that stretch is already used."""
    d = duration(f)
    if d < need + 0.1:
        return None
    start = min(start, round(d - need - 0.05, 2))
    return start if _free(M, f, start, need) else None


def _find(CP, M, brand, role, roles, lead, need, texts, shows):
    """The role's moment, inside its clip's real length and looked at; a refused look or a clip too short for `need` is
    passed over for this shot only (TRIES placements), never used blind."""
    refused, held = [], []
    try:
        for _ in range(TRIES * 3):
            got = M.find(role, roles, lead, need, texts)
            if not got:
                return None
            h, f, start, who = got
            at = _fit(M, f, start, need)
            if at is None:                                   # too short or overlapping: not for this shot
                held.append((f, 0.0, max(duration(f), start + need) + 1))
                M.used.append(held[-1])
                continue
            ok, said = _look(brand, h, at, need, shows)
            if ok:
                return h, f, at, who, said, refused
            refused.append({"file": f, "in": at, "why": said})
            held.append((f, at, at + need))                 # this stretch is out; the next placement is asked
            M.used.append(held[-1])
            if len(refused) >= TRIES:
                return None
        return None
    finally:
        for x in held:
            M.used.remove(x)


def _marks(h):
    tm = list(h.get("text_marks") or [])
    return ["captioned: marked"] if tm and tm != ["clean"] else []


# ------------------------------------------------------------------ pictures

def _section_texts(g):
    sf = g.get("start_frame") or {}
    return [sf.get(k) for k in ("subject", "action", "composition", "location") if sf.get(k)]


def pictures(run) -> dict:
    """Every picture the storyboard lists, as a frame of the section's cast member's best-matching moment, written where
    the AI picture would go (media/<id>.png) with media/<id>.real.json. A picture already there is kept."""
    run = Path(run)
    cp = _chain("clips_plan")
    CP, M, brand, cast, roles, lead = _setup(run)
    sb = _read(run / "storyboard.json", {}) or {}
    plan = _read(run / "plan.json", {}) or {}
    swapped = {str(s.get("id")) for s in plan.get("scenes") or [] if s.get("source_plan") == "swap"}
    (run / "media").mkdir(exist_ok=True)
    placed, kept, open_ = [], [], []
    for g in sb.get("sections") or []:
        if g.get("scenes") and all(str(s) in swapped for s in g["scenes"]):
            continue
        ids = cp.picture_ids(g)
        want = [ids["start"], ids["end"]] + [o["id"] for o in ids["own"]] + [x["id"] for x in ids.get("setups") or []]
        texts = _section_texts(g)
        people = cp.section_people(g)
        for iid in [x for x in dict.fromkeys(want) if x]:
            if cp.picture_file(run, iid) is not None:
                kept.append(iid)
                continue
            role = _first_named(cast, " ".join(texts)) or next((p for p in people if p in cast), None) or lead
            shows = " ".join(texts[:2]) or g.get("lyric") or ""
            got = _find(CP, M, brand, role, roles, lead, 1.0, texts + [g.get("lyric") or ""], shows)
            if not got:
                open_.append(iid)
                continue
            h, f, start, who, said, refused = got
            M.take(f, start, 1.0)
            at = round(start + 0.5, 2)
            out = run / "media" / f"{iid}.png"
            r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.2f}", "-i", f, "-frames:v", "1",
                                "-vf", FILL, str(out)], capture_output=True, text=True)
            if r.returncode or not out.is_file():
                open_.append(iid)
                continue
            rec = {"schema": "real-picture/v1", "picture": iid, "section": g.get("id"), "scenes": g.get("scenes"),
                   "role": who.split(" ")[0], "role_note": who, "cast_bank": cast.get(who.split(" ")[0]),
                   "file": f, "shared_path": h.get("shared_path"), "in": start, "out": round(start + 1.0, 2),
                   "frame_at": at, "matched_on": shows[:240], "index_says": (h.get("shows") or "")[:200],
                   "score": h.get("score"), "look": said, "marks": _marks(h), "passed_over": refused,
                   "why": f"{who}: the cast member's moment that best matches the picture's subject and action"}
            _write(run / "media" / f"{iid}.real.json", rec)
            placed.append(rec)
    res = {"placed": len(placed), "kept": len(kept), "open": open_,
           "by_role": _count(p["role_note"] for p in placed)}
    _write(run / "real-pictures.json", {**res, "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "pictures": placed})
    return res


def _count(xs):
    out = {}
    for x in xs:
        out[x] = out.get(x, 0) + 1
    return out


# ------------------------------------------------------------------ clips

def _direction(run, call, sections):
    """The words a call's footage is matched on: its prompt, its camera and motion plan, its beats, its sung line."""
    cm = (_read(run / "clips" / "camera-motion.json", {}) or {}).get("scenes") or {}
    g = sections.get(call.get("section_id")) or {}
    words = [str((call.get("params") or {}).get("prompt") or call.get("prompt") or "")]
    for sid in call.get("scenes") or []:
        words.append(str((cm.get(sid) or {}).get("words") or ""))
    for b in call.get("beats") or []:
        words.append(" ".join(str(v) for v in (b.values() if isinstance(b, dict) else [b])))
    words.append(str(g.get("lyric") or ""))
    return [w for w in words if w.strip()], g


def clips(run) -> dict:
    """Every call in clips/plan.json as the section's cast member's own moments, matched to the call's direction, trimmed
    or joined to the call's seconds: clips/<id>.mp4 (1080x1920, silent) with clips/<id>.real.json. A clip already there
    is kept."""
    run = Path(run)
    CP, M, brand, cast, roles, lead = _setup(run)
    plan = _read(run / "clips" / "plan.json", {}) or {}
    sections = {g.get("id"): g for g in (_read(run / "storyboard.json", {}) or {}).get("sections") or []}
    made, kept, open_, started = [], [], [], set()
    for call in plan.get("calls") or []:
        cid = call.get("id")
        out = run / "clips" / f"{cid}.mp4"
        if out.is_file():
            kept.append(cid)
            continue
        need = round(float(call.get("seconds") or call.get("duration") or 4.0), 2)
        texts, g = _direction(run, call, sections)
        sf = " ".join(_section_texts(g))
        named = " ".join(texts[:1]) + " " + sf
        role = (_first_named(cast, named) or next((p for p in call.get("characters") or [] if p in cast), None)
                or next((p for p in _chain("clips_plan").section_people(g) if p in cast), None) or lead)
        shows = (texts[0] if texts else sf)[:300]
        pieces, left, size = [], need, need
        # THE CLIP STARTS FROM ITS START PICTURE, as in the AI chain: the picture's own moment plays on when its clip
        # holds the call (the first call of that picture only)
        pic = _read(run / "media" / f"{call.get('start_frame')}.real.json", {}) or {}
        if pic.get("file") and pic["picture"] not in started:
            stretch = (pic["file"], float(pic["in"]), float(pic["out"]))
            M.used.remove(stretch) if stretch in M.used else None
            at = float(pic["in"])
            if duration(pic["file"]) >= at + need + 0.05 and _free(M, pic["file"], at, need):
                started.add(pic["picture"])
                M.take(pic["file"], at, need)
                pieces.append({"file": pic["file"], "shared_path": pic.get("shared_path"), "in": round(at, 2),
                               "out": round(at + need, 2), "seconds": need, "role": pic["role"],
                               "role_note": pic["role_note"], "index_says": pic.get("index_says"),
                               "score": pic.get("score"), "look": pic.get("look"), "marks": pic.get("marks") or [],
                               "passed_over": [], "from_picture": pic["picture"]})
                left = 0.0
            else:
                M.used.append(stretch)
        while left > 0.05:
            piece = round(min(size, left), 2)
            if 0.05 < left - piece < MIN_PIECE:                # never leave a stub shorter than a piece
                piece = round(left - MIN_PIECE, 2) if left - MIN_PIECE >= MIN_PIECE else round(left, 2)
            got = _find(CP, M, brand, role, roles, lead, piece, texts + [sf], shows)
            if got:
                h, f, start, who, said, refused = got
                M.take(f, start, piece)
                pieces.append({"file": f, "shared_path": h.get("shared_path"), "in": round(start, 2),
                               "out": round(start + piece, 2), "seconds": piece, "role": who.split(" ")[0],
                               "role_note": who, "index_says": (h.get("shows") or "")[:200], "score": h.get("score"),
                               "look": said, "marks": _marks(h), "passed_over": refused})
                left = round(left - piece, 2)
                continue
            if size > MIN_PIECE:
                size = max(MIN_PIECE, round(size / 2, 2))   # no one moment holds it: join shorter ones
                continue
            break
        if left > 0.05 or not pieces:
            open_.append(cid)
            continue
        if not _assemble(pieces, out):
            open_.append(cid)
            continue
        role = pieces[0]["role"]
        rec = {"schema": "real-clip/v1", "call": cid, "section": call.get("section_id"), "scenes": call.get("scenes"),
               "seconds": need, "role": role, "cast_bank": cast.get(role), "pieces": pieces,
               "start_picture": call.get("start_frame"),
               "matched_on": shows, "why": f"{role}: the cast member's moments that best match the call's direction "
                                           f"(prompt, camera and motion plan, beats, line), "
                                           + ("one moment trimmed" if len(pieces) == 1 else f"{len(pieces)} moments joined")}
        _write(run / "clips" / f"{cid}.real.json", rec)
        made.append(rec)
    res = {"made": len(made), "kept": len(kept), "open": open_, "calls": len(plan.get("calls") or []),
           "pieces": sum(len(m["pieces"]) for m in made),
           "by_role": _count(p["role_note"] for m in made for p in m["pieces"])}
    _write(run / "real-clips.json", {**res, "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "clips": made})
    return res


def _assemble(pieces, out: Path) -> bool:
    """The pieces, each filled to 9:16, joined in order, silent (the edit lays the song or the voice)."""
    args, chains = [], []
    for i, p in enumerate(pieces):
        args += ["-ss", f"{p['in']:.3f}", "-t", f"{p['seconds']:.3f}", "-i", p["file"]]
        chains.append(f"[{i}:v]{FILL},fps=30,format=yuv420p[v{i}]")
    graph = ";".join(chains) + ";" + "".join(f"[v{i}]" for i in range(len(pieces))) + \
        f"concat=n={len(pieces)}:v=1:a=0[v]"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y"] + args + ["-filter_complex", graph, "-map", "[v]", "-an",
                                                                 "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
                                                                 str(out)], capture_output=True, text=True)
    return r.returncode == 0 and out.is_file()


# ------------------------------------------------------------------ checks

def check(run) -> dict:
    """The cast check over every real picture and clip (swipe_cut.cast_check: every placement plays its role's own
    footage, every cast member on screen) and the looks the moments index refused."""
    run = Path(run)
    rec = cast_of(run)
    if str(STUDIO) not in sys.path:
        sys.path.insert(0, str(STUDIO))
    import swipe_cut as SC  # noqa: E402
    picks = {"people": {"cast": {b: v["folder"] for b, v in rec["bound"].items()}}, "shots": {}, "sources": {}}
    rows = []
    for f in sorted((run / "media").glob("*.real.json")):
        p = _read(f, {}) or {}
        rows.append((p["picture"], p["role"], p["file"]))
    for f in sorted((run / "clips").glob("*.real.json")):
        c = _read(f, {}) or {}
        for i, p in enumerate(c.get("pieces") or []):
            rows.append((f"{c['call']}.{i + 1}", p["role"], p["file"]))
    scenes = {"all": []}
    for rid, role, file in rows:
        key = "L-" + hashlib.md5(file.encode()).hexdigest()[:8]
        picks["sources"][key] = file
        picks["shots"][rid] = {"source": key, "role": role}
        scenes["all"].append({"id": rid})
    try:
        SC.cast_check(picks, scenes, {"cast": list(rec["cast"])}, sung=True)
        cast_ok, said = True, "every placement plays its role's own footage; every cast member is on screen"
    except SystemExit as e:
        cast_ok, said = False, str(e)
    out = {"cast_ok": cast_ok, "cast": said, "placements": len(rows),
           "on_screen": _count(r[1] for r in rows)}
    _write(run / "real-check.json", {**out, "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
    return out


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) != 2 or a[0] not in ("pictures", "clips", "check"):
        print(__doc__)
        return 2
    res = {"pictures": pictures, "clips": clips, "check": check}[a[0]](Path(a[1]).resolve())
    print(json.dumps(res, indent=1, ensure_ascii=False))
    return 0 if not res.get("open") and res.get("cast_ok", True) else 2


if __name__ == "__main__":
    sys.exit(main())
