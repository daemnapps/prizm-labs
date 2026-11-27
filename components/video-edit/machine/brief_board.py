#!/usr/bin/env python3
"""brief_board.py — the editing board for one video brief: a page on this machine where the editor sees the
brief's scenes in order, swaps a scene's footage in one tap, trims its in and out, previews the cut, and asks
for a regen. Nothing is generated, published or sent from here.

    python3 components/video-edit/machine/brief_board.py [--port 8916]     # http://localhost:8916/<brand>/<brief>/

What it reads:
  runs/video-writing/<brand>/<brief>/deliverable/5-brief.md   the scenes, in order (the brief's scene block)
  .../deliverable/footage.json                                 the footage ledger: owned candidates per B-roll scene
  .../deliverable/picks.json                                   the picks sent into the brief (the scene's first choice)
  runs/asset-index/<brand>/library/library.json                the footage library, through the Footage Library
                                                               board's own reader (asset-index/library/board/serve.py:
                                                               rows, frames) and library.query (the same blank, two bands)

What it writes back beside the brief: a swap or a trim is also the scene's pick in picks.json, written through
footage.write_picks (which refreshes footage.json / footage.md), so the picks, the ledger and the cut name one clip.

What it writes into the brief's edit run, runs/video-edit/<brand>/<brief>/:
  cutsheet-vN.json   every change is a NEW version of the cut sheet (CLAUDE.md "The principle"); never one rewritten
  changes.jsonl      one line per change: at, stop "board", asked, why, from, to, scene, was, now (run.py change's shape)
  run.json           made on the first change when the run is new
  regen-requests.jsonl  a regen asked for: the scene, the paid route, its price, status "waiting for owner's yes"
  work/board-vN/ + work/board-vN.mp4   a preview: compose.py (the one HyperFrames door) then a draft render

Two kinds of sheet:
  - the edit line's own sheet (the run already has cut sheets): a swap changes the B-roll entry's source and in,
    and keeps its slot on the clock (start and length), so the words it covers stay covered; a trim moves the in.
  - the board's rough cut (no sheet yet): v1 is laid from the brief — each B-roll scene its first pick (picks.json,
    else the ledger's best, else the library's same-blank best), every other scene a labelled slate until production
    lays it. A swap or a trim re-lays the rough cut with the new choice; the clock follows the in and out.

The gate (cutsheet.check) is shown, not skipped: a rough cut is red until the voice and the made scenes are laid,
and the master still comes only from the edit line (run.py render). The preview is a draft of what the sheet holds.

Regen is the paid production path (video-production: a remake order for a production run's scene, or the scene
generated). The board shows its price (video-production/machine/shot_route.py) and stops: the request waits for
owner's yes for that run. No brand is named in this file.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
REPO = TOOL.parents[1]
COMPONENTS = REPO / "components"
PORT = 8916
WRITING = REPO / "runs" / "video-writing"
EDITS = REPO / "runs" / "video-edit"
LOCK = threading.Lock()
PREVIEWS: dict = {}       # (brand, brief) -> {"state", "version", "file", "error"}

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


VP = COMPONENTS / "video-production" / "machine"
SCN = _load("vp_scenes", VP / "scenes.py")                      # the brief's scene block
FOOT = _load("vp_footage", VP / "footage.py")                   # role_of, query_for — the footage step's own words
LIBB = _load("asset_library_board", COMPONENTS / "asset-index" / "library" / "board" / "serve.py")
L = LIBB.L                                                       # library.py, as the Footage Library board loaded it
SR = _load("vp_shot_route", VP / "shot_route.py")               # the paid routes' prices


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def write(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False))


# ------------------------------------------------------------ the brief

def deliverable(brand: str, brief: str) -> Path:
    return WRITING / brand / brief / "deliverable"


def run_dir(brand: str, brief: str) -> Path:
    return EDITS / brand / brief


def briefs() -> list[dict]:
    """Every brief with a scene block, newest ledger first; a brief with a footage ledger is marked."""
    out = []
    for f in sorted(WRITING.glob("*/*/deliverable/5-brief.md")) if WRITING.is_dir() else []:
        d = f.parent
        led = d / "footage.json"
        out.append({"brand": d.parents[1].name, "brief": d.parent.name, "ledger": led.is_file(),
                    "picks": (d / "picks.json").is_file(), "at": (led if led.is_file() else f).stat().st_mtime})
    return sorted(out, key=lambda r: (not r["ledger"], -r["at"]))


SECTION_BEAT = {"unique-mechanism": "mechanism", "demonstration": "mechanism", "social-proof": "proof",
                "testimonial": "proof", "results": "transformation", "agitation": "problem", "pain": "problem",
                "story": "identification", "lifestyle": "identification", "offer": "product",
                "call-to-action": "product", "cta": "product", "routine": "routine"}


def seconds_of(s: dict) -> float:
    """A scene's length before it is cut: its own seconds, else its words at ~2.6 a second, never under 3 s
    (video-production/machine/budget.py _scene_seconds, the same rule the budget prices by)."""
    if s.get("seconds"):
        return float(s["seconds"])
    words = len(" ".join([str(s.get("voice") or s.get("say") or ""), *[str(x) for x in s.get("lyrics") or []]]).split())
    return round(max(words / 2.6, 3.0), 1)


def scenes(brand: str, brief: str) -> list[dict]:
    text = (deliverable(brand, brief) / "5-brief.md").read_text()
    doc, why = SCN.json_block(text)
    if not isinstance(doc, dict) or not doc.get("scenes"):
        raise ValueError(f"no scene block in the brief ({why or 'no scenes'})")
    out = []
    for s in doc["scenes"]:
        if not isinstance(s, dict):
            continue
        seen, said = FOOT.query_for(s)
        sec = s.get("section")
        beat = sec if sec in LIBB.BEAT_ORDER else SECTION_BEAT.get(str(sec or ""))
        out.append({"id": s.get("id"), "kind": s.get("kind"), "role": FOOT.role_of(s), "section": sec, "beat": beat,
                    "shows": seen[:400], "said": said or " / ".join(str(x) for x in s.get("lyrics") or []),
                    "seconds": seconds_of(s), "action": FOOT.core_of(s)})
    return out


def picks_of(brand: str, brief: str) -> dict:
    """picks.json beside the brief (editor-picks/v1, read by footage.read_picks — the Footage Library board writes it):
    {"scenes": {scene: its pick}, "pool": [picks for the brief, no scene]}. A scene's last pick is its pick, as
    footage.apply_picks reads it. Each pick: id ("<clip>:<library scene>", the library row), clip_id, in, out."""
    out = {"scenes": {}, "pool": []}
    for k in FOOT.read_picks(deliverable(brand, brief)).get("picks") or []:
        if not isinstance(k, dict):
            continue
        rid = k.get("id") or (f"{k['clip_id']}:{k['library_scene']}" if k.get("clip_id") and k.get("library_scene") is not None else None)
        row = {"id": rid, "clip": k.get("clip_id"), "in": k.get("in"), "out": k.get("out"), "for_scene": k.get("for_scene")}
        if k.get("for_scene") is None:
            out["pool"].append(row)
        else:
            out["scenes"][str(k["for_scene"])] = row
    return out


# ------------------------------------------------------------ the footage: the library board's rows, the same blank

def library(brand: str):
    """(page rows by id, raw rows by id, raw rows by Shared Assets path) — the Footage Library board's reader."""
    try:
        data, by = LIBB.rows(brand)
    except (OSError, ValueError):
        return {}, {}, {}
    page = {r["id"]: r for r in data}
    by_label: dict = {}
    for rid, r in by.items():
        if r.get("kind") != "picture":
            by_label.setdefault(r.get("label"), []).append(rid)
    return page, by, by_label


_DRIVE = [None, False]


def drive_root() -> Path | None:
    """This machine's copy of Shared Assets (the video editor's own finder, handoff_run.drive_shared), once."""
    if not _DRIVE[1]:
        _DRIVE[1] = True
        try:
            import handoff_run as HR
            _DRIVE[0] = HR.drive_shared()
        except Exception:  # noqa: BLE001 — no Drive on this machine: the proxy, else nothing
            _DRIVE[0] = None
    return _DRIVE[0]


def local_file(brand: str, raw: dict | None, shared_path: str | None = None) -> tuple[Path | None, str]:
    """The clip on this machine: the full file on Shared Assets, else the library's local proxy. (path, which)."""
    sp = shared_path or (raw or {}).get("label")
    root = drive_root()
    if root and sp and sp.startswith("Shared Assets/"):
        f = Path(root) / sp[len("Shared Assets/"):]
        if f.is_file():
            return f, "full"
    if raw and raw.get("frame"):
        p = L.RUNS / brand / raw["frame"]
        if (p.parent / "proxy.mp4").is_file():
            return p.parent / "proxy.mp4", "proxy"
    return None, "not on this machine"


def option(brand: str, rid: str, page: dict, by: dict, band: str, score=None) -> dict | None:
    r, raw = page.get(rid), by.get(rid)
    if not r or not raw:
        return None
    f, which = local_file(brand, raw)
    return {"id": rid, "band": band, "score": score, "tier": r.get("tier"), "marks": r.get("marks") or ["clean"],
            "polish": r.get("pol"), "handles": r.get("hand") or [], "shows": r.get("shows"), "says": r.get("says"),
            "in": r.get("in"), "out": r.get("out"), "cut": r.get("cut"), "beat": r.get("beat"),
            "path": r.get("path"), "file": r.get("file"), "drive": r.get("drive"), "shared_path": raw.get("label"),
            "frame": f"/frame/{brand}/{rid}.jpg", "local": which, "src": str(f) if f else None,
            "clip_url": f"/clip/{brand}/{rid}.mp4" if f else None}


def _ledger_row(brand: str, h: dict, by_label: dict, by: dict) -> str | None:
    """A ledger candidate's library row: same file, the scene its in/out overlaps most (library.enrich's rule)."""
    ids = by_label.get(h.get("shared_path")) or []
    if not ids or h.get("in") is None:
        return ids[0] if ids else None
    a, b = float(h["in"]), float(h.get("out") or h["in"])
    return max(ids, key=lambda i: (min(b, by[i]["out"]) - max(a, by[i]["in"]), -abs(by[i]["in"] - a)))


def blank_of(brand: str, sc: dict) -> dict:
    """The library blank for a scene: its beat, the product it names (the brand vocabulary's words), its action."""
    L.use_brand(brand)
    text = f"{sc.get('shows') or ''} {sc.get('said') or ''}".lower()
    prod = next((pid for pid, words in (L.BRAND.get("products") or {}).items()
                 if any(re.search(rf"\b{re.escape(str(w).lower())}\b", text) for w in (words or [pid]))), None)
    blank = {"action_words": sc.get("action") or sc.get("shows") or "", "text": "any"}
    if sc.get("beat"):
        blank["beat"] = sc["beat"]
    if prod and prod != "set-or-box":
        blank["product"] = prod
    return blank


def options(brand: str, brief: str, sc: dict, led: dict | None, page: dict, by: dict, by_label: dict,
            picks: dict | None = None) -> dict:
    """Every choice for one B-roll scene: what was picked for it on the Footage Library board (its own pick, then the
    brief's pool), the ledger's candidates, then the library's same blank in two bands — ranked (best match) and
    different (other creators and settings). Text marks show; they never exclude."""
    seen, out = set(), {"picked": [], "ledger": [], "ranked": [], "different": [], "blank": None}
    mine = (picks or {}).get("scenes", {}).get(str(sc["id"]))
    for p in ([mine] if mine else []) + list((picks or {}).get("pool") or []):
        o = option(brand, p.get("id"), page, by, "pick" if p is mine else "pool") if p.get("id") else None
        if o and o["id"] not in seen:
            if p.get("in") is not None and p.get("out") is not None:
                o["in"], o["out"] = float(p["in"]), float(p["out"])
            seen.add(o["id"]); out["picked"].append(o)
    for h in (led or {}).get("candidates") or []:
        rid = _ledger_row(brand, h, by_label, by)
        o = option(brand, rid, page, by, "ledger", h.get("score")) if rid else None
        if o and o["id"] not in seen:
            seen.add(o["id"]); out["ledger"].append(o)
    rows = [r for r in by.values() if r.get("kind") != "picture"]
    if rows:
        blank = blank_of(brand, sc)
        res = L.query(rows, blank, n=8)
        if not res["ranked"] and blank.get("product"):
            blank.pop("product"); res = L.query(rows, blank, n=8)
        if not res["ranked"] and blank.get("beat"):
            blank.pop("beat"); res = L.query(rows, blank, n=8)
        out["blank"] = blank
        for band in ("ranked", "different"):
            for r in res[band]:
                rid = f"{r['clip']}:{r.get('scene', 0)}"
                o = option(brand, rid, page, by, band)
                if o and rid not in seen:
                    seen.add(rid); out[band].append(o)
    return out


# ------------------------------------------------------------ the cut sheet

def sheets(run: Path) -> list[Path]:
    return sorted(run.glob("cutsheet-v*.json"), key=lambda p: int(p.stem.split("-v")[1]))


def latest(run: Path) -> Path | None:
    s = sheets(run)
    return s[-1] if s else None


def board_made(sheet: dict | None) -> bool:
    return bool(sheet) and (sheet.get("meta") or {}).get("made_by") == "brief board"


def slate(run: Path) -> Path:
    """A plain dark frame the rough cut lays under a scene that production makes (free, ffmpeg, once)."""
    f = run / "board" / "slate.png"
    if not f.is_file():
        f.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x1b1f1b:s=1080x1920",
                        "-frames:v", "1", str(f)], capture_output=True)
    return f


def first_choice(sc: dict, opts: dict, picks: dict) -> dict | None:
    """The scene's first choice: its pick from picks.json (at the picked times), else the ledger's best, else the
    same blank's best. A pool pick is offered, never laid by itself."""
    mine = next((o for o in opts.get("picked") or [] if o["band"] == "pick"), None)
    return mine or (opts["ledger"] or opts["ranked"] or [None])[0]


def owned_of(o: dict) -> dict:
    return {k: o.get(k) for k in ("id", "band", "tier", "marks", "polish", "handles", "shared_path", "drive", "path",
                                  "local", "in", "out")}


def lay(brand: str, brief: str, run: Path, scs: list[dict], choice: dict) -> dict:
    """The board's rough cut from the brief and one choice per B-roll scene ({scene: option with in/out})."""
    picture, overlays, t = [], [], 0.0
    blank_png = str(slate(run))
    for sc in scs:
        o = choice.get(sc["id"])
        if sc["role"] == "broll" and o and o.get("src"):
            dur = round(max(0.5, float(o["out"]) - float(o["in"])), 3)
            picture.append({"id": sc["id"], "roll": "b", "kind": "broll", "src": o["src"], "start": round(t, 3),
                            "duration": dur, "source_start": float(o["in"]), "scene": sc["id"], "still": False,
                            "volume_db": None, "section": sc.get("section"),
                            "why": f"{sc['id']}: our footage ({o.get('band')}), tier {o.get('tier')}", "owned": owned_of(o)})
        else:
            dur = sc["seconds"]
            what = ("pick not on this machine — " + (o.get("file") or "")) if o else \
                {"presenter": "presenter — from production", "broll": "no footage picked yet"}.get(sc["role"], f"{sc.get('kind') or 'scene'} — made by production")
            row = {"id": sc["id"], "roll": "b" if sc["role"] == "broll" else "a", "kind": None, "src": blank_png,
                   "start": round(t, 3), "duration": dur, "source_start": 0, "scene": sc["id"], "still": True,
                   "volume_db": None, "section": sc.get("section"), "why": f"{sc['id']}: placeholder — {what}"}
            if o:
                row["owned"] = owned_of(o)
            picture.append(row)
            overlays.append({"id": f"{sc['id']}-slate", "kind": "label", "text": f"{sc['id']} · {what}"[:80],
                             "start": round(t, 3), "duration": dur, "zone": "center"})
        t += dur
    return {"meta": {"brand": brand, "label": brief, "format": "board-rough", "style_id": None, "width": 1080,
                     "height": 1920, "fps": 30, "made_by": "brief board",
                     "brief": f"runs/video-writing/{brand}/{brief}/deliverable/5-brief.md"},
            "controls": {"transition": {"value": "cut"}, "captions": {"value": "off"}},
            "voice": None, "voice_cuts": [], "music": None, "sfx": [], "picture": picture,
            "captions": {"look": None, "words": []}, "overlays": overlays,
            "notes_for_owner": ["A rough cut laid on the brief board from the brief's footage picks: the voice, captions "
                                "and the scenes production makes are not laid yet, so it does not pass the gate."]}


def choices_in(sheet: dict) -> dict:
    """The board's choices back out of one of its sheets: scene -> option (with its in/out)."""
    out = {}
    for c in sheet.get("picture") or []:
        o = c.get("owned")
        if o:
            out[c["scene"]] = {**o, "src": c["src"] if not c.get("still") else None,
                               "in": c["source_start"] if not c.get("still") else o.get("in"),
                               "out": c["source_start"] + c["duration"] if not c.get("still") else o.get("out")}
    return out


def save(run: Path, brand: str, brief: str, sheet: dict, asked: str, why: str, scene=None, was=None, now_=None) -> str:
    """A new version of the sheet and its line in changes.jsonl — never a sheet rewritten."""
    with LOCK:
        last = latest(run)
        n = int(last.stem.split("-v")[1]) + 1 if last else 1
        name = f"cutsheet-v{n}.json"
        write(run / name, sheet)
        with (run / "changes.jsonl").open("a") as f:
            f.write(json.dumps({"at": now(), "stop": "board", "asked": asked, "why": why, "from": last.name if last else None,
                                "to": name, "scene": scene, "was": was, "now": now_, "by": "brief board"},
                               ensure_ascii=False) + "\n")
        if not (run / "run.json").is_file():
            write(run / "run.json", {"machine": "video-edit", "brand": brand, "label": brief, "made_by": "brief board",
                                     "brief": sheet["meta"].get("brief"), "started": now(), "stops": {}})
        return name


def _brief_state(brand: str, brief: str):
    scs = scenes(brand, brief)
    led = {r.get("scene"): r for r in (read(deliverable(brand, brief) / "footage.json", {}) or {}).get("scenes") or []}
    page, by, by_label = library(brand)
    picks = picks_of(brand, brief)
    opts = {sc["id"]: options(brand, brief, sc, led.get(sc["id"]), page, by, by_label, picks) for sc in scs if sc["role"] == "broll"}
    return scs, opts, picks, page, by


def _desc(o: dict | None) -> str:
    if not o:
        return "nothing"
    return f"{o.get('id')} {float(o.get('in') or 0):.2f}–{float(o.get('out') or 0):.2f}s"


def current_sheet(brand: str, brief: str) -> tuple[Path, dict | None]:
    run = run_dir(brand, brief)
    p = latest(run)
    return run, (read(p) if p else None)


def ensure_sheet(brand: str, brief: str, scs, opts, picks) -> tuple[Path, dict]:
    """The sheet to change: the run's latest; with none, v1 is the rough cut laid from the brief."""
    run, sheet = current_sheet(brand, brief)
    if sheet is None:
        choice = {sc["id"]: first_choice(sc, opts[sc["id"]], picks) for sc in scs if sc["role"] == "broll"}
        sheet = lay(brand, brief, run, scs, {k: v for k, v in choice.items() if v})
        save(run, brand, brief, sheet, "lay the rough cut", "the brief's scenes in order, each B-roll scene its first pick")
    return run, sheet


def write_pick(brand: str, brief: str, scene: str, rid: str | None, t_in, t_out) -> None:
    """The scene's choice back into the brief's picks.json through footage.write_picks (the Footage Library board's
    own door), so the picks, the footage ledger and the cut sheet name the same clip at the same times."""
    if not rid:
        return
    page, by, _ = library(brand)
    r, v = by.get(rid), page.get(rid)
    if not r or not v:
        return
    FOOT.write_picks(deliverable(brand, brief), brand, brief, [{
        "id": rid, "clip_id": r["clip"], "library_scene": r.get("scene"), "for_scene": scene,
        "in": round(float(t_in), 3), "out": round(float(t_out), 3), "cut_source": v.get("cut"),
        "shared_path": r.get("label") or r.get("rel"), "drive": v.get("drive"), "beat": v.get("beat"),
        "products": v.get("prod"), "tier": v.get("tier"), "text_marks": v.get("marks"), "shows": v.get("shows"),
        "by": "brief board"}])


def swap(brand: str, brief: str, scene: str, rid: str, why: str) -> dict:
    scs, opts, picks, page, by = _brief_state(brand, brief)
    if scene not in opts:
        raise ValueError(f"{scene} is not a B-roll scene of this brief")
    o = next((x for b in ("picked", "ledger", "ranked", "different") for x in opts[scene][b] if x["id"] == rid), None) \
        or option(brand, rid, page, by, "library")
    if not o:
        raise ValueError(f"{rid} is not in the library")
    run, sheet = ensure_sheet(brand, brief, scs, opts, picks)
    if board_made(sheet):
        ch = choices_in(sheet)
        was = ch.get(scene)
        ch[scene] = o
        new = lay(brand, brief, run, scs, ch)
    else:
        new = json.loads(json.dumps(sheet))
        c = next((x for x in new["picture"] if x.get("scene") == scene and (x.get("roll") == "b" or x.get("kind") == "broll")), None)
        if not c:
            raise ValueError(f"{scene} has no B-roll slot in the edit line's sheet")
        if not o.get("src"):
            raise ValueError(f"{rid} is not on this machine (Shared Assets or the library's proxy)")
        was = c.get("owned") or {"id": c.get("src"), "in": c.get("source_start"), "out": c.get("source_start", 0) + c["duration"]}
        span = float(o["out"]) - float(o["in"])
        c.update(src=o["src"], source_start=float(o["in"]), still=False, owned=owned_of(o),
                 why=f"{scene}: our footage ({o.get('band')}), tier {o.get('tier')} — swapped on the brief board")
        if span < c["duration"] - 0.04:
            c["note"] = f"the pick runs {span:.2f}s and the slot is {c['duration']:.2f}s: it plays on past its out"
    name = save(run, brand, brief, new, f"swap {scene} to {rid}", why or "swapped on the board", scene, _desc(was), _desc(o))
    c = next(x for x in new["picture"] if x.get("scene") == scene)
    write_pick(brand, brief, scene, rid, c["source_start"] if not c.get("still") else o["in"],
               c["source_start"] + c["duration"] if not c.get("still") else o["out"])
    return {"saved": name}


def trim(brand: str, brief: str, scene: str, t_in: float, t_out: float | None, why: str) -> dict:
    scs, opts, picks, _, _ = _brief_state(brand, brief)
    run, sheet = ensure_sheet(brand, brief, scs, opts, picks)
    new = json.loads(json.dumps(sheet))
    if board_made(sheet):
        ch = choices_in(sheet)
        o = ch.get(scene)
        if not o:
            raise ValueError(f"{scene} has no footage to trim")
        was = dict(o)
        if t_out is None or t_out <= t_in + 0.2:
            raise ValueError("the out must be after the in")
        o["in"], o["out"] = round(t_in, 3), round(t_out, 3)
        new = lay(brand, brief, run, scs, ch)
        now_ = o
    else:
        c = next((x for x in new["picture"] if x.get("scene") == scene and (x.get("roll") == "b" or x.get("kind") == "broll")), None)
        if not c:
            raise ValueError(f"{scene} has no B-roll slot in the edit line's sheet")
        was = {"id": (c.get("owned") or {}).get("id") or c.get("src"), "in": c["source_start"], "out": c["source_start"] + c["duration"]}
        c["source_start"] = round(t_in, 3)     # the slot keeps its length on the clock: the in moves, the out follows
        now_ = {**was, "in": c["source_start"], "out": c["source_start"] + c["duration"]}
    name = save(run, brand, brief, new, f"trim {scene}", why or "trimmed on the board", scene, _desc(was), _desc(now_))
    write_pick(brand, brief, scene, (now_ or {}).get("id"), now_["in"], now_["out"])
    return {"saved": name}


# ------------------------------------------------------------ regen: the paid path, priced, held at the gate

def production_runs(brand: str, brief: str) -> list[str]:
    """Production runs made from this brief (their plan or run record names the brief folder)."""
    out = []
    for f in (REPO / "runs" / "video-production" / brand).glob("*/run.json") if (REPO / "runs" / "video-production" / brand).is_dir() else []:
        try:
            if f"/{brief}/" in f.read_text():
                out.append(str(f.parent.relative_to(REPO)))
        except OSError:
            pass
    return out


def regen_price(sc: dict) -> dict:
    secs = sc["seconds"]
    return {"seconds": secs, "ai_usd": SR.ai_cost(secs), "swap_usd": SR.swap_cost(secs),
            "how": f"AI scene: {SR.PICTURES_PER_AI_SHOT} pictures × {SR.PICTURE_TRIES} tries + a Seedance 2.5 clip of "
                   f"{max(secs, 4.0):.0f}s × {SR.RETRY} tries (shot_route.py)"}


def regen(brand: str, brief: str, scene: str, why: str) -> dict:
    sc = next((s for s in scenes(brand, brief) if s["id"] == scene), None)
    if not sc:
        raise ValueError(f"{scene} is not in the brief")
    price = regen_price(sc)
    prod = production_runs(brand, brief)
    row = {"at": now(), "scene": scene, "why": why or "asked on the board", "route": "AI", "usd": price["ai_usd"],
           "price": price, "path": ("remake order on " + prod[-1]) if prod else "video-production: generate this scene",
           "status": "waiting for owner's yes", "spent": 0}
    run = run_dir(brand, brief)
    run.mkdir(parents=True, exist_ok=True)
    with LOCK, (run / "regen-requests.jsonl").open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def regen_requests(brand: str, brief: str) -> list[dict]:
    f = run_dir(brand, brief) / "regen-requests.jsonl"
    try:
        return [json.loads(x) for x in f.read_text().splitlines() if x.strip()]
    except OSError:
        return []


# ------------------------------------------------------------ preview: compose.py, then a draft render

def preview(brand: str, brief: str) -> dict:
    run, sheet = current_sheet(brand, brief)
    if sheet is None:
        scs, opts, picks, _, _ = _brief_state(brand, brief)
        run, sheet = ensure_sheet(brand, brief, scs, opts, picks)
    v = latest(run).stem.split("-v")[1]
    key = (brand, brief)
    with LOCK:
        cur = PREVIEWS.get(key) or {}
        if cur.get("state") == "rendering":
            return cur
        PREVIEWS[key] = {"state": "rendering", "version": v, "started": now()}

    def work():
        try:
            import compose as C
            project = run / "work" / f"board-v{v}"
            out = run / "work" / f"board-v{v}.mp4"
            if board_made(sheet):
                root = run
            else:
                import handoff_run as HR
                root = HR.kit_dir_of(read(run / "run.json", {}) or {}, REPO)
            C.compose(sheet, root, project, captions=bool(((sheet.get("controls") or {}).get("captions") or {}).get("value", "on") == "on"
                                                         and (sheet.get("captions") or {}).get("words")))
            r = subprocess.run(["hyperframes", "render", str(project), "--output", str(out), "--quality", "draft", "--sdr", "--quiet"],
                               capture_output=True, text=True)
            (run / "work" / f"board-v{v}.render.log").write_text(r.stdout + r.stderr)
            if r.returncode != 0 or not out.is_file():
                raise RuntimeError((r.stderr or r.stdout or "render failed").strip().splitlines()[-1][:300])
            PREVIEWS[key] = {"state": "ready", "version": v, "file": f"/media/{brand}/{brief}/board-v{v}.mp4", "at": now()}
        except Exception as e:  # noqa: BLE001 — the page shows why; nothing else depends on a preview
            PREVIEWS[key] = {"state": "failed", "version": v, "error": str(e)[:400]}

    threading.Thread(target=work, daemon=True).start()
    return PREVIEWS[key]


# ------------------------------------------------------------ the page's data

def state(brand: str, brief: str) -> dict:
    scs, opts, picks, page, by = _brief_state(brand, brief)
    run, sheet = current_sheet(brand, brief)
    current, slot = {}, {}
    if sheet:
        root = run if board_made(sheet) else None
        for c in sheet.get("picture") or []:
            sc = c.get("scene")
            if sc in opts and (c.get("roll") == "b" or c.get("kind") == "broll"):
                o = c.get("owned")
                base = (option(brand, o["id"], page, by, o.get("band") or "sheet") if o and o.get("id") else None) or \
                       {"id": None, "band": "sheet", "file": Path(str(c.get("src"))).name, "local": "full" if Path(str(c.get("src"))).is_file() else "not on this machine"}
                if not c.get("still"):
                    base = {**base, "in": c["source_start"], "out": round(c["source_start"] + c["duration"], 3)}
                elif o:
                    base = {**base, "in": o.get("in"), "out": o.get("out")}
                current.setdefault(sc, base)
                slot.setdefault(sc, {"start": c["start"], "duration": c["duration"], "fixed": not board_made(sheet)})
        try:
            red = __import__("cutsheet").check(sheet, root or run)
        except Exception as e:  # noqa: BLE001
            red = [f"the gate could not read this sheet: {e}"]
    else:
        red = ["no cut sheet yet — the first swap or trim lays the rough cut as v1"]
        for sc in scs:
            if sc["role"] == "broll":
                o = first_choice(sc, opts[sc["id"]], picks)
                if o:
                    current[sc["id"]] = o
    changes = []
    try:
        changes = [json.loads(x) for x in (run / "changes.jsonl").read_text().splitlines() if x.strip()][-12:]
    except OSError:
        pass
    return {"brand": brand, "brief": brief, "scenes": scs, "options": opts, "current": current, "slot": slot,
            "picks": picks, "sheet": latest(run).name if sheet else None, "kind": "rough cut" if board_made(sheet) or not sheet else "edit line",
            "versions": len(sheets(run)), "gate": red, "changes": changes[::-1], "preview": PREVIEWS.get((brand, brief)),
            "regen": regen_requests(brand, brief), "prices": {sc["id"]: regen_price(sc) for sc in scs},
            "run": str(run.relative_to(REPO))}


# ------------------------------------------------------------ the server

def _home() -> str:
    rows = "".join(f'<li><a href="/{b["brand"]}/{b["brief"]}/">{b["brand"]} · {b["brief"]}</a>'
                   f'{" · footage ledger" if b["ledger"] else ""}{" · picks" if b["picks"] else ""}</li>' for b in briefs())
    return ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            "<title>Brief Editing Board</title><style>body{font:16px system-ui;margin:24px 16px;background:#f4f5f1;color:#141713}"
            "@media (prefers-color-scheme:dark){body{background:#0f120f;color:#eef0ea}a{color:#7fc79a}}li{margin:8px 0}</style>"
            f"<h1>Brief Editing Board</h1><p>Open a brief to edit its scenes.</p><ul>{rows or '<li>No brief on this machine.</li>'}</ul>")


def _send_file(h, f: Path, ctype: str):
    size = f.stat().st_size
    rng = h.headers.get("Range")
    a, b = 0, size - 1
    if rng and rng.startswith("bytes="):
        s, _, e = rng[6:].partition("-")
        a = int(s) if s else max(0, size - int(e))
        b = int(e) if s and e else size - 1
        h.send_response(206)
        h.send_header("Content-Range", f"bytes {a}-{b}/{size}")
    else:
        h.send_response(200)
    h.send_header("Content-Type", ctype)
    h.send_header("Accept-Ranges", "bytes")
    h.send_header("Content-Length", str(b - a + 1))
    h.end_headers()
    with f.open("rb") as fh:
        fh.seek(a)
        left = b - a + 1
        while left > 0:
            chunk = fh.read(min(1 << 16, left))
            if not chunk:
                break
            h.wfile.write(chunk)
            left -= len(chunk)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def json(self, obj, code=200):
        self.send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json")

    def do_GET(self):
        parts = [unquote(p) for p in urlparse(self.path).path.split("/") if p]
        try:
            if not parts:
                return self.send(200, _home().encode(), "text/html; charset=utf-8")
            if parts[0] == "frame" and len(parts) == 3:
                f = LIBB.frame(parts[1], parts[2].removesuffix(".jpg"))
                return _send_file(self, f, "image/jpeg") if f else self.send(404, b"", "image/jpeg")
            if parts[0] == "clip" and len(parts) == 3:
                _, by, _ = library(parts[1])
                f, _ = local_file(parts[1], by.get(parts[2].removesuffix(".mp4")))
                return _send_file(self, f, "video/mp4") if f else self.send(404, b"", "video/mp4")
            if parts[0] == "media" and len(parts) == 4:
                f = run_dir(parts[1], parts[2]) / "work" / Path(parts[3]).name
                return _send_file(self, f, "video/mp4") if f.is_file() and f.suffix == ".mp4" else self.send(404, b"", "video/mp4")
            if len(parts) >= 2 and (deliverable(parts[0], parts[1]) / "5-brief.md").is_file():
                if len(parts) == 2:
                    if not self.path.split("?")[0].endswith("/"):
                        self.send_response(301); self.send_header("Location", f"/{parts[0]}/{parts[1]}/"); self.end_headers(); return
                    w = LIBB.board_words(parts[0])      # the brand's page colours, as the Footage Library board uses them
                    html = ((HERE / "brief_board.html").read_text().replace("/*LIGHT*/", w["light"]).replace("/*DARK*/", w["dark"])
                            .replace("<title>Brief Editing Board</title>", f"<title>{parts[1]} · Editing Board</title>"))
                    return self.send(200, html.encode(), "text/html; charset=utf-8")
                if parts[2] == "state.json":
                    return self.json(state(parts[0], parts[1]))
            return self.send(404, b"not found", "text/plain")
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as e:  # noqa: BLE001
            return self.json({"error": str(e)}, 500)

    def do_POST(self):
        parts = [unquote(p) for p in urlparse(self.path).path.split("/") if p]
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            if len(parts) != 3 or not (deliverable(parts[0], parts[1]) / "5-brief.md").is_file():
                return self.json({"error": "no such brief"}, 404)
            brand, brief, act = parts
            if act == "swap":
                return self.json(swap(brand, brief, body["scene"], body["id"], body.get("why", "")))
            if act == "trim":
                return self.json(trim(brand, brief, body["scene"], float(body["in"]),
                                      None if body.get("out") is None else float(body["out"]), body.get("why", "")))
            if act == "preview":
                return self.json(preview(brand, brief))
            if act == "regen":
                return self.json(regen(brand, brief, body["scene"], body.get("why", "")))
            return self.json({"error": f"no action {act}"}, 404)
        except (ValueError, KeyError) as e:
            return self.json({"error": str(e)}, 400)
        except (BrokenPipeError, ConnectionResetError):
            return


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the editing board for a video brief, on this machine")
    ap.add_argument("--port", type=int, default=PORT)
    a = ap.parse_args(argv)
    print(f"Brief Editing Board on http://localhost:{a.port}/  ({len(briefs())} briefs)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
