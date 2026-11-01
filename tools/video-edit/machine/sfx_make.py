#!/usr/bin/env python3
"""sfx_make.py — the sound effects the swipe or the brief CALLS FOR and no bank has yet, made for this edit
(video system sync 2026-10-21, E39). Never an effect nobody called for (V14).

    python3 sfx_make.py <video-production-run> --out <edit run dir> [--dry-run]

Reads <out>/edit-map.json: every cue the map laid out (`sfx`, from the brief's plan.json sfx and the storyboard's
sound layer) that is not `made`. Each becomes a row of a bank that lives IN THIS EDIT RUN (<out>/banks/sfx/index.json,
status "to make", its prompt the cue's own words), and production's bank maker makes it through its command:

    tools/video-production/machine/make_bank.py --bank sfx --root <out>/banks --out <out>/sfx --spend

so production's own bank is never written by the edit, and the next plan (edit_map.py) finds the made row
(edit_map._sfx_row looks in the run's bank first). Exit 0 = every called cue now has a made row (or there were none).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MAKE_BANK = REPO / "tools" / "video-production" / "machine" / "make_bank.py"
SECONDS = 1.5      # an effect is short: it lands on its moment and gets out of the way


def cue_id(cue: str) -> str:
    """The row id a cue is found by — production's banks.cue_name, the same rule, so edit_map finds the made row."""
    return re.sub(r"[^a-z0-9]+", "-", str(cue or "").lower()).strip("-") or "cue"


def wanted(out: Path) -> list[dict]:
    """The cues the map laid out and could not lay: called for (they are in the brief or the storyboard), not made."""
    m = json.loads((out / "edit-map.json").read_text())
    seen, rows = set(), []
    for c in m.get("sfx") or []:
        what = str(c.get("cue") or c.get("what") or "").strip()
        if c.get("made") or not what or what.lower() in ("none", "no", "-"):
            continue
        i = cue_id(what)
        if i in seen:
            continue
        seen.add(i)
        rows.append({"id": i, "tags": [i], "prompt": f"{what} — a single short sound effect, clean, no music, no voice",
                     "seconds": SECONDS, "loop": False, "status": "to make",
                     "source": "elevenlabs sound-generation (made by the edit for a called cue, E39)"})
    return rows


def bank_of(out: Path, rows: list[dict]) -> Path:
    """The run's own bank: its index with these rows added (a row already made there stays)."""
    root = out / "banks"
    p = root / "sfx" / "index.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    doc = json.loads(p.read_text()) if p.exists() else {"bank": "sfx", "drive_root": str((out / "sfx").resolve()), "rows": []}
    have = {r.get("id") for r in doc["rows"]}
    doc["rows"] += [r for r in rows if r["id"] not in have]
    p.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    return root


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("run"); ap.add_argument("--out", required=True); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out)
    rows = wanted(out)
    if not rows:
        print("sfx: every called cue is made (or none was called) — nothing to make")
        return 0
    root = bank_of(out, rows)
    cmd = [sys.executable, str(MAKE_BANK), "--bank", "sfx", "--root", str(root), "--out", str(out / "sfx")] + \
          (["--dry-run"] if a.dry_run else ["--spend"])
    for r in rows:
        cmd += ["--only", r["id"]]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print((res.stdout + res.stderr).strip()[-2000:])
    if res.returncode != 0:
        print(f"sfx: the bank maker stopped (exit {res.returncode}) — the audit will hold NO SOUND FX", file=sys.stderr)
        return 1
    print(f"sfx: {len(rows)} called cue(s) {'priced' if a.dry_run else 'made'}: {', '.join(r['id'] for r in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
