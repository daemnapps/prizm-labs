#!/usr/bin/env python3
"""handoff_run.py — the video editor as a tool: a video-editor hand-off folder in,
one 9:16 master in its returned/ out, stopping only at the edit line's two
review points (steps.json: STOP 1 the timeline, STOP 2 the captions).

    python3 machine/run.py handoff <hand-off folder> [--dry-run]
    python3 machine/run.py handoff <hand-off folder> --approve timeline [--note "..."]
    python3 machine/run.py handoff <hand-off folder> --approve captions [--note "..."]

It is not a second edit line. It finds the kit in the hand-off (assets/…/edit-kit.json),
finds the kit's media (in the folder, else in the same folder on the Drive mount the
manifest names), copies the kit into the run, and calls run.py's own `start` — the
same gather → cut → gate → stops → export → checks → file. Around that it adds only:

  - a STATUS file at every stop (run folder: STATUS.md + status.json): what is
    waiting, where the preview is, the copy on the Drive, what the kit is missing,
    the edit line's open decisions — and the one line that resumes it;
  - the previews and the master mirrored to the Drive at
    Shared Assets/runs/video-edit/<brand>/<label>/ (runs/README.md: media on the Drive);
  - at the end: the master named by the naming rule's short form
    (<brand>_<product>_<brief>_<batch>_asset-01.mp4) into the hand-off's returned/
    (here and on the Drive), then the hand-off tool's own take-back — and the same master
    into Shared Assets/meta/<brand>/1-check/video/<ad name>/ with its card for the owner's approval
    (components/meta-upload/feed_video.py; tests only into $META_CARDS_ROOT).

`--approve` records the approval (run.py approve) and carries on to the next stop.
`--dry-run` checks the hand-off, the media and the gate; it renders nothing, copies
nothing, writes nothing and calls no model or paid service.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _read(p: Path, default=None):
    return json.loads(p.read_text()) if p.is_file() else default


def _write(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def drive_shared() -> Path | None:
    """The local Drive mount's Shared Assets folder, or None."""
    cs = Path.home() / "Library" / "CloudStorage"
    for m in sorted(cs.glob("GoogleDrive-*")):
        p = m / "Shared drives" / "Shared Assets"
        if p.is_dir():
            return p
    return None


def drive_rel(p) -> str | None:
    """A path on the Drive mount as the Drive names it ("Shared Assets/…"), so a run record
    reads the same on every Mac (triage page 12). A path off the mount is kept as given."""
    if not p:
        return None
    shared = drive_shared()
    if shared:
        try:
            return "Shared Assets/" + Path(p).relative_to(shared).as_posix()
        except ValueError:
            pass
    return str(p)


def kit_rel(kit_dir, root) -> str:
    """run.json's kit, written from the repo root like status.json's run; a kit outside it stays absolute."""
    try:
        return Path(kit_dir).relative_to(root).as_posix()
    except ValueError:
        return str(kit_dir)


def kit_dir_of(state: dict, root) -> Path:
    """run.json's kit as a folder. Repo-relative from 2026-10-07; older records keep their
    absolute paths as history and are read as written."""
    k = Path(state["kit"])
    return k if k.is_absolute() else Path(root) / k


# ---------------------------------------------------------------- reading the hand-off
def read_handoff(folder: Path) -> dict:
    mf = _read(folder / "manifest.json")
    if not mf:
        raise SystemExit(f"no manifest.json in {folder} — not a hand-off folder")
    if mf.get("role") != "video-editor":
        raise SystemExit(f"{folder.name} is a {mf.get('role')} hand-off, not a video-editor one")
    kits = sorted((folder / "assets").rglob("edit-kit.json"), key=lambda p: len(p.parts))
    if not kits:
        raise SystemExit(f"no edit-kit.json under {folder / 'assets'} — the hand-off carries no edit kit")
    briefs = mf.get("briefs") or []
    if len(briefs) != 1:
        raise SystemExit(f"{len(briefs)} briefs in this hand-off; one kit makes one master, so one brief per hand-off")
    mount = Path((mf.get("drive") or {}).get("mount") or "")
    if not mount.is_dir() and (mf.get("drive") or {}).get("target") and drive_shared():
        mount = drive_shared().parent / (mf["drive"]["target"])  # target is 'Shared Assets/handoffs/...'
    b = briefs[0]
    product = str(b.get("product_id") or "")
    prefix = f"product_{mf['brand']}_"
    return {"folder": folder, "manifest": mf, "brand": mf["brand"], "brief": b["id"], "kit_rel": kits[0].parent.relative_to(folder),
            "product": product[len(prefix):] if product.startswith(prefix) else product or "none",
            "label": f"{b['id']}_{mf.get('date') or folder.name.rsplit('_', 1)[-1]}",
            "drive": mount if mount and str(mount) != "." and mount.is_dir() else None}


def kit_media(kit: dict) -> list[str]:
    """Every file the kit names, relative to the kit folder."""
    out = []
    for k in ("voice", "music"):
        if (kit.get(k) or {}).get("src"):
            out.append(kit[k]["src"])
    for c in kit.get("clips") or []:
        out.append(c["src"])
        if (c.get("voice") or {}).get("src"):
            out.append(c["voice"]["src"])
    out += [x["src"] for x in kit.get("sfx") or [] if x.get("src")]
    return [m for m in dict.fromkeys(out) if not Path(m).is_absolute()]


def find_kit(h: dict) -> tuple[Path, list[str]]:
    """The kit folder whose media are all there: the hand-off itself, else its copy on the Drive.
    Returns (folder, missing) — missing is empty when one of them is whole."""
    local = h["folder"] / h["kit_rel"]
    kit = _read(local / "edit-kit.json")
    need = kit_media(kit)
    places = [local] + ([h["drive"] / h["kit_rel"]] if h["drive"] else [])
    best, best_missing = local, need
    for p in places:
        missing = [m for m in need if not (p / m).is_file() or (p / m).stat().st_size == 0]
        if not missing:
            return p, []
        if len(missing) < len(best_missing):
            best, best_missing = p, missing
    return best, best_missing


def copy_kit(src: Path, dest: Path) -> None:
    """The kit into the run (only what changed). The hand-off is never written to."""
    for f in src.rglob("*"):
        if f.is_file():
            d = dest / f.relative_to(src)
            if not d.exists() or d.stat().st_size != f.stat().st_size:
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, d)


def relocate(run: Path, brand: str, label: str) -> None:
    """A run moved between checkouts: point the cut sheet's own working files back into this run folder.
    Only paths that no longer exist and that sit inside a run of the same brand/label are touched."""
    key = f"/{brand}/{label}/"
    for sheet_p in run.glob("cutsheet-v*.json"):
        txt = sheet_p.read_text()
        sheet = json.loads(txt)
        changed = False

        def fix(o):
            nonlocal changed
            if isinstance(o, dict):
                for k, v in o.items():
                    if isinstance(v, str) and v.startswith("/") and key in v and not Path(v).exists():
                        o[k] = str(run / v.split(key, 1)[1]); changed = True
                    else:
                        fix(v)
            elif isinstance(o, list):
                for x in o:
                    fix(x)
        fix(sheet)
        if changed:
            sheet_p.write_text(json.dumps(sheet, indent=1, ensure_ascii=False) + "\n")


def restore_work(run: Path, kit_dir: Path, R) -> list[str]:
    """The levelled copies the cut sheet plays are media, so they are not in git: a run opened
    from another checkout makes them again from the kit (the same loudness pass, so the same files)."""
    made = []
    sheet_p = R.latest_sheet(run)
    if not sheet_p:
        return made
    sheet = json.loads(sheet_p.read_text())
    kit = _read(kit_dir / "edit-kit.json", {})
    clips = kit.get("clips") or []
    for c in sheet.get("picture") or []:
        src = Path(str(c.get("src", "")))
        if src.name.endswith(".level.mp4") and src.is_absolute() and not src.exists():
            stem = src.name[: -len(".level.mp4")]
            orig = next((k["src"] for k in clips if Path(k["src"]).stem == stem), None)
            if orig and (kit_dir / orig).is_file():
                src.parent.mkdir(parents=True, exist_ok=True)
                R.level_clip(kit_dir / orig, src.parent); made.append(src.name)
    for v in (sheet.get("voice_cuts") or []) + ([sheet["voice"]] if sheet.get("voice") else []):
        src = Path(str(v.get("src", "")))
        if src.name == "voice.level.wav" and src.is_absolute() and not src.exists():
            owner = next((k for k in clips if k.get("id") == src.parent.name and (k.get("voice") or {}).get("src")), None)
            orig = owner["voice"]["src"] if owner else (kit.get("voice") or {}).get("src")
            if orig and (kit_dir / orig).is_file():
                R.level_voice(kit_dir / orig, src.parent); made.append(f"{src.parent.name}/{src.name}")
    return list(dict.fromkeys(made))


# ---------------------------------------------------------------- the edit line's open decisions
def open_decisions() -> list[str]:
    d = _read(TOOL / "context" / "edit-line.json", {})
    out = []
    for p in d.get("phases") or []:
        for s in p.get("stages") or []:
            for o in s.get("open") or []:
                if not (o.get("settled") or o.get("a") or o.get("answer")):
                    out.append(f"{o.get('n')} · {o.get('q')}  (now: {o.get('now') or '—'})")
    return out


# ---------------------------------------------------------------- Drive mirror
def mirror(run: Path, brand: str, label: str, files: list[Path]) -> Path | None:
    shared = drive_shared()
    if not shared:
        return None
    dest = shared / "runs" / "video-edit" / brand / label
    for f in files:
        if f and f.is_file():
            d = dest / f.relative_to(run)
            if not d.exists() or d.stat().st_size != f.stat().st_size or d.stat().st_mtime < f.stat().st_mtime:
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, d)
    return dest


def drive_link(p: Path | None) -> str | None:
    """The Drive web link of a file on the mount (its id is on the file once Drive has synced it), else None."""
    import subprocess
    if not p or not Path(p).exists():
        return None
    r = subprocess.run(["xattr", "-p", "com.google.drivefs.item-id#S", str(p)], capture_output=True, text=True)
    v = r.stdout.strip()
    if r.returncode != 0 or len(v) < 10:
        return None
    return f"https://drive.google.com/{'drive/folders' if Path(p).is_dir() else 'file/d'}/{v}" + ("" if Path(p).is_dir() else "/view")


# ---------------------------------------------------------------- status
def write_status(run: Path, h: dict, state: dict, sheet: dict | None, drive_dir: Path | None, extra: dict | None = None, root: Path | None = None) -> dict:
    def rel(p):  # repo paths are written from the repo root, so the status reads the same from any checkout
        try:
            return str(Path(p).relative_to(root)) if root else str(p)
        except ValueError:
            return str(p)
    stops = state.get("stops") or {}
    waiting = next((s for s in ("timeline", "captions") if stops.get(s) == "waiting"), None)
    preview = {"timeline": "work/rough-cut.mp4", "captions": "work/captioned.mp4"}.get(waiting)
    done = (state.get("steps") or {}).get("returned")
    st = {"handoff": h["folder"].name, "brief": h["brief"], "brand": h["brand"], "run": rel(run), "updated": _now(),
          "state": ("done — master in returned/" if done else f"waiting on the owner — {waiting}" if waiting
                    else "held — " + (extra or {})["held"] if (extra or {}).get("held")
                    else "blocked — " + (extra or {})["blocked"] if (extra or {}).get("blocked") else "running"),
          "waiting_on": waiting,
          "page": rel(run / "timeline.html") if (run / "timeline.html").exists() else None,
          "live_page": rel(run / "live.html") if (run / "live.html").exists() else None,
          "preview": rel(run / preview) if preview and (run / preview).exists() else None,
          "drive": drive_rel(drive_dir) if drive_dir else None,
          "drive_preview": drive_rel(drive_dir / preview) if drive_dir and preview and (drive_dir / preview).exists() else None,
          "drive_link": drive_link(drive_dir / preview) if drive_dir and preview else None,
          "resume": (f"python3 tools/video-edit/machine/run.py handoff {rel(h['folder'])} --approve {waiting}" if waiting else None),
          "missing_from_kit": (sheet or {}).get("missing") or [], "notes_for_damon": (sheet or {}).get("notes_for_damon") or [],
          "open_decisions": open_decisions(), **(extra or {})}
    _write(run / "status.json", st)
    say = {"timeline": "STOP 1 — the timeline. The cut with the dead air out, no captions yet. Approve it, or say what to change.",
           "captions": "STOP 2 — the captions. Same cut, captions on. Approve it, switch the look, or fix a word."}
    md = [f"# {h['brief']} — the edit", "", f"**{st['state']}**", ""]
    if waiting:
        md += [say[waiting], "", f"- Watch: {st['drive_link'] or '`' + str(st['drive_preview'] or st['preview']) + '`'}", f"- The page: `{st['page']}`",
               f"- On approval the session runs: `{st['resume']}`", ""]
    if done:
        md += [f"- Master: `{done.get('file')}`", f"- Drive: `{done.get('drive') or '—'}`", ""]
    if st["missing_from_kit"]:
        md += ["## Not in the kit (the edit leaves these out)", ""] + [f"- {m}" for m in st["missing_from_kit"]] + [""]
    if st["notes_for_damon"]:
        md += ["## Notes", ""] + [f"- {m}" for m in st["notes_for_damon"]] + [""]
    md += ["## Open on the edit line (not decided here)", ""] + [f"- {m}" for m in st["open_decisions"]] + [""]
    (run / "STATUS.md").write_text("\n".join(md))
    return st


# ---------------------------------------------------------------- the finish
def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def give_back(run: Path, h: dict, final: Path, root: Path) -> dict:
    """The master into returned/ under its short-form name, here and on the Drive, then take-back."""
    sys.path.insert(0, str(root / "components" / "naming"))
    import names as N
    batch = N.norm_batch(h["manifest"].get("batch")) or N.next_batch(h["brand"])
    unit = N.short_unit(h["brand"], h["product"], h["brief"], batch)
    name = N.short_file(unit, 1) + ".mp4"
    ret = h["folder"] / "returned"
    ret.mkdir(parents=True, exist_ok=True)
    shutil.copy2(final, ret / name)
    drive_copy = None
    if h["drive"]:
        (h["drive"] / "returned").mkdir(parents=True, exist_ok=True)
        shutil.copy2(final, h["drive"] / "returned" / name)
        drive_copy = str(h["drive"] / "returned" / name)
    HS = _load("ad_handoff_take_back", root / "components" / "ad-handoff" / "take_back.py")
    staging = h["folder"].parents[2]  # <staging>/<role>/<brand>/<name>
    idx = HS.take_back("video-editor", h["brand"], h["folder"].name, staging, staging / "ledger.jsonl")
    for row in idx["files"]:  # the version column the hand-off asks for (master · hook-N · cutdown · cover)
        row.setdefault("version", "master" if row["file"] == name else "version")
    (ret / "index.json").write_text(json.dumps(idx, indent=1, ensure_ascii=False) + "\n")
    if h["drive"]:
        shutil.copy2(ret / "index.json", h["drive"] / "returned" / "index.json")
    return {"file": str(ret / name), "drive": drive_copy, "name": name, "batch": batch, "taken_back": idx["taken_back"], "files": len(idx["files"])}


def to_check(run: Path, h: dict, master: Path, batch: str, root: Path) -> dict:
    """The master ALSO into Shared Assets/meta/<brand>/1-check/video/<ad name>/ with its card
    (components/meta-upload/CARD.md) — the folder the owner approves from. A refusal is recorded, never raised:
    the master is already safe in returned/."""
    FV = _load("feed_video", root / "components" / "meta-upload" / "feed_video.py")
    try:
        p, src = FV.file_master(h["brand"], h["brief"], h["product"], batch, master,
                                handoff=h["folder"], run=run, repo=root)
    except Exception as e:  # noqa: BLE001 — the hand-off is done; the card's absence is shown, not fatal
        return {"state": "refused", "why": str(e)}
    return {"state": p["state"], "folder": str(p["target"]), "words_from": src, "missing": p["missing_words"]}


# ---------------------------------------------------------------- the command
def run(a, R) -> int:
    """R is run.py itself (its start / approve / latest_sheet / repo_root)."""
    folder = Path(a.folder).resolve()
    h = read_handoff(folder)
    root = R.repo_root()
    runs_root = Path(a.runs_root).resolve() if a.runs_root else root / "runs" / "video-edit"
    run_dir = runs_root / h["brand"] / h["label"]
    src_kit, missing = find_kit(h)
    print(f"hand-off  {folder.name} · {h['brief']} · kit {h['kit_rel']}")
    print(f"media     {'all there — ' + str(src_kit) if not missing else str(len(missing)) + ' missing'}")
    if missing:
        for m in missing:
            print(f"RED   kit media missing here and on the Drive: {m}")
        return 1
    if a.dry_run:
        a.kit, a.brand, a.label, a.from_step = str(src_kit), h["brand"], h["label"], None
        a.straight = False
        rc = R.start(a)
        print("open on the edit line (surfaced, not decided):")
        for d in open_decisions():
            print("  · " + d)
        return rc

    kit_dir = run_dir / "kit"
    copy_kit(src_kit, kit_dir)
    relocate(run_dir, h["brand"], h["label"])
    remade = restore_work(run_dir, kit_dir, R)
    if remade:
        print(f"remade    {len(remade)} levelled cop{'y' if len(remade) == 1 else 'ies'} the cut sheet plays (media are not in git)")
    state = _read(run_dir / "run.json")
    if state:  # the kit moves with the run, wherever the run is opened from
        state["kit"] = kit_rel(kit_dir, root); _write(run_dir / "run.json", state)
    if a.approve:
        if not state or (state.get("stops") or {}).get(a.approve) != "waiting":
            print(f"nothing is waiting at {a.approve} — status: {(state or {}).get('stops')}"); return 1
        R.approve(type("A", (), {"run": str(run_dir), "stop": a.approve, "note": a.note or "approved by the owner"})())
    a.kit, a.brand, a.label, a.straight = str(kit_dir), h["brand"], h["label"], False
    a.from_step = None
    if state and R.latest_sheet(run_dir):
        a.from_step = "gate"  # resume on the sheet already cut — a change is a new sheet version, never a re-cut
    rc = R.start(a)
    state = _read(run_dir / "run.json") or {}
    sheet = _read(R.latest_sheet(run_dir)) if R.latest_sheet(run_dir) else None
    work = run_dir / "work"
    live = not a.runs_root  # tests pass their own runs root and never touch the Drive
    drive_dir = None if not live else mirror(run_dir, h["brand"], h["label"], [run_dir / "timeline.html", run_dir / "live.html", run_dir / "STATUS.md",
                                                        work / "rough-cut.mp4", work / "captioned.mp4", work / "final.mp4"])
    extra = {}
    steps = state.get("steps") or {}
    exported = steps.get("export")
    if exported and not (steps.get("checks") or {}).get("passed"):
        extra["held"] = "the master rendered but a final check HELD it (deliverable/checks.json) — nothing went to returned/"
    elif exported and not steps.get("returned"):
        final = Path(exported["file"])
        back = give_back(run_dir, h, final, root)
        state["steps"]["returned"] = {"state": "done", "at": _now(), **back}
        if live or os.environ.get("META_CARDS_ROOT"):  # tests file cards only into their own fake root
            state["steps"]["returned"]["to_check"] = to_check(run_dir, h, Path(back["file"]), back["batch"], root)
        _write(run_dir / "run.json", state)
        print(f"RETURNED  {back['file']}")
        print(f"TAKEN BACK  {h['folder'].name}: {back['files']} file(s)")
        if (state["steps"]["returned"].get("to_check") or {}).get("folder"):
            print(f"TO CHECK  {state['steps']['returned']['to_check']['folder']}")
    if rc != 0 and not exported and not any(v == "waiting" for v in (state.get("stops") or {}).values()):
        extra["blocked"] = "the gate or a step refused — see the run's output above"
    st = write_status(run_dir, h, state, sheet, drive_dir, extra, root)
    if drive_dir:
        mirror(run_dir, h["brand"], h["label"], [run_dir / "STATUS.md", run_dir / "status.json"])
    print(f"STATUS    {st['state']} — {run_dir / 'STATUS.md'}")
    if st.get("drive_preview"):
        print(f"PREVIEW   {st['drive_preview']}")
    return rc
