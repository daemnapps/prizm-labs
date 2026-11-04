#!/usr/bin/env python3
"""The hand-off front door: one list of every hand-off, out and back, at runs/handoffs/INDEX.md (+ index.json), and the
START-HERE.md page for whoever fills a role, both copied to the same path on the Drive (Shared Assets/runs/handoffs/).

    python3 tools/image-edit/handoff_index.py [--no-drive]

the owner, 2026-10-28: "do what is fucking necessary to get this thing fucking smooth so it all works ... we're about to
start handing out cue work." One place out, one place back: runs/handoffs/<role>/<brand>/<brief key>/, finished work
only into its returned/. One row per hand-off: brand, brief key, role, made, files out, returned (yes/no, how many),
card state when filed. A folder is matched to its brief by brief NUMBER plus brand (the product word may be the
catalog name or the old handle), so both spellings resolve. Reads only the repo; the hand-off writers and the delivery
check call `refresh()` after they write. Spends nothing; never deletes anything, here or on the Drive.
"""
import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))
from image_edit import paths as P  # noqa: E402

DRIVE_PARTS = ["runs", "handoffs"]            # Shared Assets/runs/handoffs/ — the repo path, word for word
SKIP = {"returned", "delivery.json"}          # what came back, never counted as what went out
NOT_RETURNS = {"README.md", "index.json", "delivery.json"}
NUM = re.compile(r"brief[-_ ]?0*(\d{1,4})", re.I)


def root(repo=None):
    return Path(repo or P.repo()) / "runs" / "handoffs"


def _read(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def _register():
    """tools/image-teardown's brief register (tools/briefs.py, its one reader); {} when it cannot be read."""
    try:
        f = P.sibling("image-teardown", "tools", "briefs.py")
        spec = importlib.util.spec_from_file_location("it_briefs_register_index", f)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return dict(m.load()["briefs"])
    except Exception:  # noqa: BLE001 — the index still lists every folder, only without the register's key
        return {}


def _forms(name):
    """Every spelling of a per-product brief key, catalog form first ([] for anything else or no naming beside us)."""
    try:
        folder = str(P.sibling("naming"))
        if folder not in sys.path:
            sys.path.append(folder)
        import names as N  # noqa: E402
        return N.brief_key_forms(name)
    except Exception:  # noqa: BLE001
        return []


def brief_for(reg, brand, name):
    """(register key, record) for a hand-off folder: the exact key, else the brief NUMBER plus the brand, the product
    word breaking a tie in either spelling (brand_a_nova-face-brush_brief-0076 and brand_a_nova_brief-0076 are one brief).
    (None, {}) when nothing fits."""
    for f in [name] + _forms(name):              # every spelling of the key (names.brief_key_forms)
        if isinstance(reg.get(f), dict):
            return f, reg[f]
    m = NUM.search(name)
    if not m:
        return None, {}
    bid = f"brief-{int(m.group(1)):04d}"
    cands = [(k, r) for k, r in reg.items() if isinstance(r, dict) and r.get("brief") == bid and r.get("brand") == brand]
    if len(cands) > 1:
        word = name[len(brand) + 1:m.start()].strip("_-").lower() if name.lower().startswith(brand.lower()) else name.lower()
        same = [(k, r) for k, r in cands if str(r.get("product") or "").lower() and
                (word.startswith(str(r["product"]).lower()) or str(r["product"]).lower().startswith(word))]
        cands = same or cands
    return cands[0] if len(cands) == 1 else (None, {})


def _files(folder):
    return [f for f in folder.rglob("*") if f.is_file() and not f.name.startswith(".")]


def row(folder, role, brand, reg, repo):
    """One hand-off folder as one row."""
    rec = _read(folder / "handoff.json") or _read(folder / "manifest.json") or {}
    key, r = brief_for(reg, brand, folder.name)
    briefs = rec.get("briefs") or []
    bid = rec.get("brief") or (briefs[0].get("id") if briefs and isinstance(briefs[0], dict) else None) or r.get("brief")
    out = [f for f in _files(folder) if not (set(f.relative_to(folder).parts[:1]) & SKIP)]
    n_out = len(out) or len(rec.get("files") or []) or len(rec.get("variations") or [])
    back = folder / "returned"
    here = {f.name for f in _files(back) if f.name not in NOT_RETURNS and not f.stem.endswith("_thumb")} if back.is_dir() else set()
    dl = _read(folder / "delivery.json") or {}
    here |= {Path(x.get("file") or x.get("name") or "").name for x in dl.get("files") or []}
    here.discard("")
    card = dl.get("card") or {}
    made = str(rec.get("made") or rec.get("date") or rec.get("created") or "")[:10]
    if not made:
        made = datetime.fromtimestamp(folder.stat().st_mtime).strftime("%Y-%m-%d")
    rel = folder.relative_to(repo).as_posix()
    return {"brand": brand, "brief_key": folder.name, "register_key": key, "brief": bid, "role": role, "made": made,
            "files_out": n_out, "returned": bool(here), "returned_count": len(here),
            "card": (f"{card.get('state')} · {card.get('name')}" if card else (dl.get("state") or "")),
            "folder": rel, "drive": "Shared Assets/" + rel, "returned_to": "Shared Assets/" + rel + "/returned",
            "link": (rec.get("drive") or {}).get("link")}


def rows(repo=None):
    repo = Path(repo or P.repo())
    base, reg, out = root(repo), _register(), []
    if not base.is_dir():
        return out
    for role in sorted(d for d in base.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))):
        for brand in sorted(d for d in role.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))):
            for folder in sorted(d for d in brand.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))):
                out.append(row(folder, role.name, brand.name, reg, repo))
    return sorted(out, key=lambda x: (x["returned"], x["role"], x["brand"], x["made"], x["brief_key"]))


def roles_said():
    """Who fills each role today, from image-edit's delivery.json (the one place a person is named)."""
    d = _read(HERE / "delivery.json") or {}
    return {k: (v or {}).get("filled_by") for k, v in (d.get("roles") or {}).items()}


def index_md(rs, built):
    waiting = [r for r in rs if not r["returned"]]
    L = ["# Hand-offs — out and back", "",
         f"Built {built} by `tools/image-edit/handoff_index.py`. Every hand-off lives at "
         "`runs/handoffs/<role>/<brand>/<brief key>/` (the same path on the Drive under `Shared Assets/`); the "
         "finished work comes back ONLY into its `returned/`. How to work one: `START-HERE.md`.", "",
         f"**{len(rs)} hand-offs · {len(waiting)} waiting · {len(rs) - len(waiting)} back.**", "",
         "| Brand | Brief key | Role | Made | Files out | Returned | Card |", "|---|---|---|---|---|---|---|"]
    for r in rs:
        back = f"yes ({r['returned_count']})" if r["returned"] else "no"
        L.append(f"| {r['brand']} | `{r['brief_key']}` | {r['role']} | {r['made']} | {r['files_out']} | {back} | "
                 f"{r['card'] or ''} |")
    return "\n".join(L) + "\n"


PAGE = "(private page)"   # the one reusable hand-off page (the owner, 2026-10-28)


def start_md(said):
    """What every role's Claude reads first. The same process as the hand-off page (PAGE), never one brief's details
    (the owner, 2026-10-28: "consistently in the same place"; "we're just going to assume Claude Code for everyone's setup
    now. Don't assume working through Higgsfield")."""
    who = lambda r: f" ({said[r]} today)" if said.get(r) else ""  # noqa: E731
    return f"""# Start here — your hand-offs

Every brief that needs your hands is in ONE place, and your finished work goes back to ONE place. The same process,
with pictures: {PAGE}

## When a brief is handed to you

1. the team posts which briefs are yours and their numbers.
2. Pull the repo.
3. Paste this into your Claude Code (the brief number in place of NNNN):
   > Open the hand-off for brief NNNN in runs/handoffs/. Read BRIEF.md and RUN.md and follow section B. Put the finished work in its returned/ folder.
4. OK each step: Claude shows you each picture, clip or cut before it spends anything or moves on.
5. It files itself in the brief's `returned/` folder, checked against the brief. Then the owner reviews.

Everything is made from Claude Code: no other app.

## What's in every hand-off folder

`runs/handoffs/<role>/<brand>/<brief key>/` in the repo, the same path under Shared Assets on the Drive.

- `BRIEF.md`: what to make. `RUN.md`: how (A for a person, B for your Claude). `run.json`: the same for the machine.
- `refs/`: every picture, sound and reference the brief names. `returned/`: your finished work goes here.
- Pictures, the graphic designer{who('graphic-designer')}: `runs/handoffs/graphic-designer/<brand>/`
- Video, the video editor{who('video-editor')}: `runs/handoffs/video-editor/<brand>/`. Video briefs arrive with every
  scene's picture approved; the clips, the edit, B-roll and effects are yours.
- `INDEX.md` (in this folder) lists every hand-off and whether it has come back yet.

## Who to ask

- **the owner: the content** — what's being made: the scenes, the words, the look, the people, the product, whether it works.
- **the team: everything else** — files and folders, the queue, which brief is next, time, usage and credits, access.

## How to name files

Every file starts with the folder's name (the brief key), then which version it is:

- Pictures: `<brief key>-v1.png`, `<brief key>-v2.png`, …
- Video: `<brief key>-control.mp4`, `<brief key>-v1.mp4`, …
- `RUN.md` lists every name. A file without the brief key is flagged for a person to look at, never lost.

## Please don't

- Save finished work anywhere but the brief's `returned/`.
- Delete, move or rename anything on the shared drive. A moved folder breaks every link to it.
- Rewrite a prompt: say what's wrong; the fix goes into the system.
- Post anything. Nothing goes live from here; the owner approves first.
"""


def to_drive(files, put=None):
    """INDEX.md, index.json and START-HERE.md onto the Drive at Shared Assets/runs/handoffs/, same names, through
    gdrive-creator (key first, else the mount). Returns put's note; a missing Drive is said, never raised."""
    try:
        if put is None:
            folder = str(P.sibling("gdrive-creator"))
            if folder not in sys.path:
                sys.path.append(folder)
            from gdrive_creator import reach
            put = reach.put
        how, placed, note = put([str(f) for f in files], DRIVE_PARTS)
        return {"how": how, "placed": len(placed), "note": note}
    except (Exception, SystemExit) as e:  # noqa: BLE001 — the index is written here either way
        return {"how": "none", "placed": 0, "note": f"{type(e).__name__}: {e}"}


def refresh(repo=None, drive=True, put=None):
    """Rewrite INDEX.md, index.json and START-HERE.md; copy them to the Drive unless drive=False. Returns a summary."""
    repo = Path(repo or P.repo())
    base = root(repo)
    base.mkdir(parents=True, exist_ok=True)
    rs = rows(repo)
    built = datetime.now().strftime("%Y-%m-%d %H:%M")
    (base / "index.json").write_text(json.dumps(
        {"what": "every hand-off, out and back: runs/handoffs/<role>/<brand>/<brief key>/, returns only in returned/",
         "built": built, "via": "tools/image-edit/handoff_index.py", "rows": rs}, indent=1, ensure_ascii=False) + "\n")
    (base / "INDEX.md").write_text(index_md(rs, built))
    (base / "START-HERE.md").write_text(start_md(roles_said()))
    out = {"rows": len(rs), "waiting": sum(1 for r in rs if not r["returned"]), "index": "runs/handoffs/INDEX.md"}
    if drive:
        out["drive"] = to_drive([base / "INDEX.md", base / "index.json", base / "START-HERE.md"], put)
    return out


def quiet_refresh(**kw):
    """refresh() for the writers and the delivery check: never stops what called it."""
    try:
        return refresh(**kw)
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--no-drive", action="store_true", help="write the index here only")
    a = ap.parse_args(argv)
    s = refresh(drive=not a.no_drive)
    print(f"{s['rows']} hand-offs, {s['waiting']} waiting · {s['index']}")
    if s.get("drive"):
        print(f"drive: {s['drive']['how']} · {s['drive']['placed']} files" + (f" · {s['drive']['note']}" if s['drive']['note'] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
