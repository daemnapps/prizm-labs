#!/usr/bin/env python3
"""The brief queue — what is waiting for an editor, per brand, written where
the editor already looks: the brand's `briefs/` folder on Google Drive.

    python3 queue.py build --brand <brand>            # rebuild one brand's queue
    python3 queue.py build --all                      # every brand with a briefs folder
    python3 queue.py set   --brand <brand> <brief> bounty="$150" due=2026-09-30 note="face product first"
    python3 queue.py show  --brand <brand>            # print it
    python3 queue.py ship  <run-folder> --brand <brand>   # one finished run → a package on Drive
    python3 queue.py ship  --auto                     # every finished run in the private workspace → Drive

Where things live, and why: the TOOLS are in this public repo. The BRIEFS —
runs, packs, brand material — never are. They live in the private workspace
(`AI_WORKSPACE`, default `~/Projects/ai-workspace`) and on Google Drive, which
is where editors read them. `ship` is the bridge: a run whose pack passed its
gates (it has `deliverable/EDITOR-PACK.md`) is zipped and dropped into the
brand's `briefs/` folder on Drive, once, and the queue picks it up.

Nothing here is state of its own. A brief is OPEN because its package is in
the folder, CLAIMED because a file named `<brief> — <who>` sits in
`briefs/claims/`, DELIVERED because files sit in `briefs/delivered/<brief>/`.
The folder is the truth; this tool only reads it and writes the table. The
only hand-set fields — bounty, due, note, and the owner's APPROVED / PAID —
live in `queue.json` beside the table and survive every rebuild.

Brand-agnostic: the brand is an argument, the Drive account is an
environment variable (`DRIVE_ACCOUNT`), and the brief names come from the
files.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE_EXT = {".zip"}
PACKAGE_SUFFIXES = ("-premiere-handoff", "-editor-handoff", "-handoff", "-pack")
TYPE_BY_FOLDER = {"ai-video-production": "video", "video": "video",
                  "image-production": "static", "images": "static", "static": "static"}


def drive_root() -> Path:
    cs = Path.home() / "Library/CloudStorage"
    acct = os.environ.get("DRIVE_ACCOUNT")
    if acct:
        return cs / f"GoogleDrive-{acct}"
    return next(iter(sorted(cs.glob("GoogleDrive-*"))), cs / "GoogleDrive")


def brands_root() -> Path:
    return drive_root() / "Shared drives/Shared Assets/brands"


def briefs_folder(brand: str) -> Path | None:
    """`brands/<brand>/briefs`, or wherever a `briefs` folder has drifted to
    under that brand — reported, so the drift is visible, never silent."""
    base = brands_root() / brand
    direct = base / "briefs"
    if direct.is_dir():
        return direct
    for depth in ("*/briefs", "*/*/briefs"):
        for cand in sorted(base.glob(depth)):
            if cand.is_dir():
                print(f"note: {brand}'s briefs folder is at {cand.relative_to(base)} — "
                      f"not at briefs/ — move it back when convenient", file=sys.stderr)
                return cand
    return None


def brief_name(p: Path) -> str:
    n = p.stem if p.suffix.lower() in PACKAGE_EXT else p.name
    for s in PACKAGE_SUFFIXES:
        if n.endswith(s):
            n = n[: -len(s)]
    return n


def packages(folder: Path) -> list[dict]:
    """Every brief package under the briefs folder: a zip, or a folder holding
    a handoff. `claims/`, `delivered/` and dotfiles are not packages."""
    out = []
    for sub in sorted(folder.iterdir()):
        if sub.name.startswith(".") or sub.name in ("claims", "delivered") or sub.name.startswith("QUEUE"):
            continue
        if sub.is_file() and sub.suffix.lower() in PACKAGE_EXT:
            out.append({"brief": brief_name(sub), "type": "video", "package": sub.name, "mtime": sub.stat().st_mtime})
        elif sub.is_dir():
            kind = TYPE_BY_FOLDER.get(sub.name.lower())
            kids = [k for k in sorted(sub.iterdir()) if not k.name.startswith(".")]
            if kind:
                for k in kids:
                    if k.is_file() and k.suffix.lower() in PACKAGE_EXT or k.is_dir():
                        out.append({"brief": brief_name(k), "type": kind,
                                    "package": f"{sub.name}/{k.name}", "mtime": k.stat().st_mtime})
            elif any(k.name.lower().endswith(("-handoff.md", "editor-pack.md", "brief.md")) for k in kids):
                out.append({"brief": brief_name(sub), "type": "video", "package": sub.name + "/",
                            "mtime": sub.stat().st_mtime})
    return out


def claims(folder: Path) -> dict[str, str]:
    d = folder / "claims"
    out = {}
    if d.is_dir():
        for f in d.iterdir():
            m = re.match(r"^(.*?)\s+[—–-]\s+(.+?)(\.\w+)?$", f.name)
            if m:
                out[m.group(1).strip()] = m.group(2).strip()
    return out


def deliveries(folder: Path) -> dict[str, list[str]]:
    d = folder / "delivered"
    out = {}
    if d.is_dir():
        for sub in d.iterdir():
            if sub.is_dir():
                files = [f.name for f in sorted(sub.iterdir()) if not f.name.startswith(".")]
                if files:
                    out[sub.name] = files
    return out


def load_meta(folder: Path) -> dict:
    p = folder / "queue.json"
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except json.JSONDecodeError:
        print(f"queue.json unreadable at {p} — starting from empty, the old one is kept as queue.json.bad",
              file=sys.stderr)
        p.rename(p.with_suffix(".json.bad"))
        return {}


def build(brand: str, write: bool = True) -> list[dict]:
    folder = briefs_folder(brand)
    if not folder:
        print(f"{brand}: no briefs folder under {brands_root() / brand}", file=sys.stderr)
        return []
    meta = load_meta(folder)
    hand = meta.get("briefs", {})
    cl, dl = claims(folder), deliveries(folder)
    rows = []
    for pk in sorted(packages(folder), key=lambda r: -r["mtime"]):
        b = pk["brief"]
        h = hand.get(b, {})
        if h.get("paid"):
            status = "paid"
        elif h.get("approved"):
            status = "approved"
        elif b in dl:
            status = "delivered"
        elif b in cl:
            status = "claimed"
        else:
            status = "open"
        rows.append({
            "brief": b, "type": pk["type"], "status": status,
            "who": cl.get(b, h.get("who", "")), "bounty": h.get("bounty", ""),
            "due": h.get("due", ""), "package": pk["package"],
            "delivered": dl.get(b, []), "note": h.get("note", ""),
            "added": datetime.fromtimestamp(pk["mtime"]).strftime("%Y-%m-%d"),
        })
    if write:
        (folder / "QUEUE.md").write_text(render(brand, rows, folder))
        meta.setdefault("briefs", {})
        for r in rows:
            meta["briefs"].setdefault(r["brief"], {})
        meta["built"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        (folder / "queue.json").write_text(json.dumps(meta, indent=2))
        # keep the folders the prompts write into, so the first claim never fails on a missing folder
        (folder / "claims").mkdir(exist_ok=True)
        (folder / "delivered").mkdir(exist_ok=True)
    return rows


def render(brand: str, rows: list[dict], folder: Path) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    L = [f"# Briefs — {brand}", "",
         f"Built {now} from this folder. Rebuilt every hour. "
         "A brief is **open** because its package is here, **claimed** because a file named "
         "`<brief> — <your name>` is in `claims/`, **delivered** because your files are in "
         "`delivered/<brief>/`. Nobody edits this table by hand.", "",
         "| # | Brief | Type | Status | Who | Bounty | Due | Package | Delivered | Note |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        L.append(f"| {i} | {r['brief']} | {r['type']} | **{r['status']}** | {r['who'] or '—'} | "
                 f"{r['bounty'] or '—'} | {r['due'] or '—'} | `{r['package']}` | "
                 f"{len(r['delivered']) or '—'} | {r['note']} |")
    if not rows:
        L.append("| — | nothing waiting | | | | | | | | |")
    L += ["", "## How to take one", "",
          "1. In Higgsfield Supercomputer, paste the **Pull briefs** prompt "
          "(`tools/editor-onboarding/prompts/02-pull-briefs-v3-damon.md`) with this brand's name.",
          "2. It claims the brief, downloads the package, lays it out, and walks the review and the asks with you.",
          "3. Finished files go to `delivered/<brief>/` here, named `<brief>--<what>--v1`. "
          "Never into the package.", "",
          f"Folder: `Shared Assets/{folder.relative_to(drive_root() / 'Shared drives/Shared Assets')}`", ""]
    return "\n".join(L)


WORKSPACE = Path(os.environ.get("AI_WORKSPACE", Path.home() / "Projects/ai-workspace"))
PACK_FILES = ("EDITOR-PACK.md", "editor-pack.md")


def finished_runs() -> list[tuple[str, Path]]:
    """(brand, run folder) for every run in the private workspace whose pack
    passed its gates. The pack file exists only when `run.py pack` cleared
    every gate, so its presence is the whole test."""
    out = []
    for machine in sorted((WORKSPACE / "runs").glob("*")):
        if not machine.is_dir():
            continue
        for brand in sorted(machine.iterdir()):
            if not brand.is_dir() or brand.name.startswith((".", "_")):
                continue
            for run in sorted(brand.iterdir()):
                if run.is_dir() and any((run / "deliverable" / f).exists() for f in PACK_FILES):
                    out.append((brand.name, run))
    return out


def ship(run: Path, brand: str, dry: bool = False) -> Path | None:
    """Zip a finished run's deliverable and put it in the brand's briefs folder
    on Drive. Never twice: a brief already on the queue under the same name is
    left alone, so a re-run never duplicates a row or overwrites what an
    editor has claimed."""
    import shutil, tempfile
    folder = briefs_folder(brand)
    if not folder:
        print(f"{brand}: no briefs folder on Drive — make brands/{brand}/briefs first", file=sys.stderr)
        return None
    name = run.name
    have = {r["brief"] for r in packages(folder)}
    # a hand-shipped zip is often the run's short name ("resilia" for
    # "resilia-song-…"); either one being a prefix of the other is the same brief
    if any(name == e or name.startswith(e + "-") or e.startswith(name + "-") for e in have):
        return None
    dest_dir = folder / "ai-video-production"
    dest = dest_dir / f"{name}-editor-handoff.zip"
    if dry:
        print(f"would ship {brand}/{name} → {dest.relative_to(folder)}")
        return dest
    src = run / "deliverable"
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / name
        shutil.copytree(src, base / name)
        for extra in run.glob("*-handoff.md"):
            shutil.copy2(extra, base / name / extra.name)
        for extra in run.glob("*brief*.md"):
            shutil.copy2(extra, base / name / extra.name)
        z = shutil.make_archive(str(Path(td) / name), "zip", base)
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(z, dest)
    print(f"shipped {brand}/{name} → Shared Assets/brands/{brand}/{dest.relative_to(folder)}")
    return dest


def cmd_ship(a):
    if a.auto:
        n = 0
        for brand, run in finished_runs():
            if ship(run, brand, dry=a.dry_run):
                n += 1
        if n:
            for brand in {b for b, _ in finished_runs()}:
                if briefs_folder(brand):
                    build(brand)
        print(f"auto-ship: {n} new package(s)")
        return
    run = Path(a.run).expanduser().resolve()
    if not any((run / "deliverable" / f).exists() for f in PACK_FILES):
        sys.exit(f"{run} has no deliverable/EDITOR-PACK.md — the pack has not cleared its gates, nothing ships")
    if ship(run, a.brand, dry=a.dry_run) and not a.dry_run:
        build(a.brand)


def cmd_set(a):
    folder = briefs_folder(a.brand)
    if not folder:
        sys.exit(f"{a.brand}: no briefs folder")
    meta = load_meta(folder)
    row = meta.setdefault("briefs", {}).setdefault(a.brief, {})
    for kv in a.fields:
        k, _, v = kv.partition("=")
        if k in ("approved", "paid"):
            row[k] = v.lower() in ("1", "true", "yes")
        else:
            row[k] = v
    (folder / "queue.json").write_text(json.dumps(meta, indent=2))
    build(a.brand)
    print(f"{a.brand}/{a.brief}: " + ", ".join(f"{k}={v}" for k, v in row.items()))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--brand"); b.add_argument("--all", action="store_true")
    s = sub.add_parser("show"); s.add_argument("--brand", required=True)
    st = sub.add_parser("set"); st.add_argument("--brand", required=True); st.add_argument("brief"); st.add_argument("fields", nargs="+")
    sh = sub.add_parser("ship"); sh.add_argument("run", nargs="?"); sh.add_argument("--brand"); sh.add_argument("--auto", action="store_true"); sh.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.cmd == "set":
        return cmd_set(a)
    if a.cmd == "ship":
        if not a.auto and not (a.run and a.brand):
            sys.exit("ship <run-folder> --brand <brand>, or ship --auto")
        return cmd_ship(a)
    if a.cmd == "show":
        f = briefs_folder(a.brand)
        print((f / "QUEUE.md").read_text() if f and (f / "QUEUE.md").exists() else f"{a.brand}: no queue yet")
        return
    brands = [a.brand] if a.brand else [p.name for p in sorted(brands_root().iterdir())
                                        if p.is_dir() and not p.name.startswith(".") and briefs_folder(p.name)]
    if not brands:
        sys.exit("say --brand <brand> or --all")
    for br in brands:
        rows = build(br)
        counts = {}
        for r in rows:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        print(f"{br}: {len(rows)} brief(s) — " + (", ".join(f"{k} {v}" for k, v in counts.items()) or "none"))


if __name__ == "__main__":
    main()
