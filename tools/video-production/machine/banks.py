#!/usr/bin/env python3
"""
banks.py — music and sound effects, picked from a bank that was made once.

ELEMENTS.md §3 (2026-09-23): the teardown names the music by
`{energy, tempo_bpm, mood}` and the sound effects by cue; production PICKS
each one from its bank and records `{bank_id, file}` into plan.json; the edit
lays them and decides nothing. "A bank is made once and reused forever. A
missing row is an error, never a silent fallback."

The index lives in the repo — `tools/video-production/banks/<bank>/
index.json`, one row per file — and the audio lives on the Drive at the row's
`file` (`Shared Assets/banks/<bank>/<id>.mp3`). A row the bank still has to
make says `status: "to make"`; it is never picked, and the refusal names it,
so the gate says exactly what is missing and the maker (`make_bank.py`) says
exactly what it would cost.

    python3 machine/banks.py status                # made vs to make, per bank
    python3 machine/banks.py pick music --energy mid --tempo 104 --mood warm
    python3 machine/banks.py pick sfx --cue whoosh

Deterministic: the same tags pick the same row, every time — music by energy
and mood (exact), then the nearest tempo inside the bank's tolerance, then
the id; a sound effect by its cue name (the row's id, else a tag).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANKS_DIR = HERE.parent / "banks"
BANKS = ("music", "sfx")
DEFAULT_TOLERANCE = 20


class BankMiss(Exception):
    """No row fits. The message names what is missing and how to make it."""


def index_path(bank: str, root=None) -> Path:
    return Path(root or BANKS_DIR) / bank / "index.json"


def load(bank: str, root=None) -> dict:
    if bank not in BANKS:
        raise BankMiss(f"there is no {bank!r} bank — the banks are: {' · '.join(BANKS)}")
    p = index_path(bank, root)
    try:
        doc = json.loads(p.read_text())
    except FileNotFoundError:
        raise BankMiss(f"the {bank} bank has no index at {p}")
    except ValueError as e:
        raise BankMiss(f"the {bank} bank's index will not parse ({e})")
    if not isinstance(doc.get("rows"), list):
        raise BankMiss(f"the {bank} bank's index has no 'rows' list")
    return doc


def made(row: dict) -> bool:
    return str(row.get("status") or "").lower() == "made" and bool(str(row.get("file") or "").strip())


def cue_name(cue: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(cue or "").lower()).strip("-")


def _make_hint(bank: str, rid: str) -> str:
    return (f"python3 machine/make_bank.py --bank {bank} --only {rid} --dry-run "
            f"(then made once, for real, on an approved spend)")


def pick_music(tags: dict, root=None) -> dict:
    doc = load("music", root)
    tol = float(doc.get("tempo_tolerance_bpm") or DEFAULT_TOLERANCE)
    energy = str(tags.get("energy") or "").lower().strip()
    mood = str(tags.get("mood") or "").lower().strip()
    try:
        bpm = float(tags.get("tempo_bpm"))
    except (TypeError, ValueError):
        raise BankMiss(f"music tags {tags!r} carry no tempo_bpm number")

    def fits(r):
        rm = str(r.get("mood") or "").lower()
        rtags = [str(t).lower() for t in r.get("tags") or []]
        return str(r.get("energy") or "").lower() == energy and (rm == mood or mood in rtags)

    rows = [r for r in doc["rows"] if isinstance(r, dict) and fits(r)]
    near = sorted(rows, key=lambda r: (abs(float(r.get("tempo_bpm") or 0) - bpm), str(r.get("id"))))
    ok = [r for r in near if made(r) and abs(float(r.get("tempo_bpm") or 0) - bpm) <= tol]
    if ok:
        return ok[0]
    # Nearest instead of nothing (the owner, 2026-09-23: "improvise and infer"): a mood
    # word the bank doesn't carry (e.g. "upbeat, curious") falls back to any of its
    # words, then to the right energy alone — always the nearest MADE tempo.
    words = [w.strip() for w in re.split(r"[,/&]| and ", mood) if w.strip()]
    for loose in (lambda r: str(r.get("energy") or "").lower() == energy and any(w in (str(r.get("mood") or "").lower(), *[str(t).lower() for t in r.get("tags") or []]) for w in words),
                  lambda r: str(r.get("energy") or "").lower() == energy,
                  lambda r: True):
        cand = sorted([r for r in doc["rows"] if isinstance(r, dict) and made(r) and loose(r)],
                      key=lambda r: (abs(float(r.get("tempo_bpm") or 0) - bpm), str(r.get("id"))))
        if cand:
            return {**cand[0], "_nearest": f"asked for energy {energy} · mood {mood} · {bpm:g} bpm; nearest made row"}
    want = f"energy {energy} · mood {mood} · {bpm:g} bpm (±{tol:g})"
    waiting = [r for r in near if not made(r)]
    if waiting:
        r = waiting[0]
        raise BankMiss(f"no MADE music row fits {want} — row {r.get('id')!r} "
                       f"({r.get('tempo_bpm')} bpm) is on the list but {r.get('status') or 'not made'}: "
                       + _make_hint("music", str(r.get("id"))))
    if near:
        r = near[0]
        raise BankMiss(f"no music row fits {want} — the nearest, {r.get('id')!r}, is "
                       f"{r.get('tempo_bpm')} bpm; add a row at this tempo to "
                       f"banks/music/index.json and make it")
    raise BankMiss(f"no music row is {want} — add one to banks/music/index.json "
                   f"(status \"to make\") and make it")


def pick_sfx(cue: str, root=None) -> dict:
    doc = load("sfx", root)
    name = cue_name(cue)
    if not name:
        raise BankMiss("a sound effect with no cue name")
    rows = [r for r in doc["rows"] if isinstance(r, dict)]
    exact = sorted((r for r in rows if cue_name(r.get("id")) == name), key=lambda r: str(r.get("id")))
    tagged = sorted((r for r in rows if name in [cue_name(t) for t in r.get("tags") or []]),
                    key=lambda r: str(r.get("id")))
    for group in (exact, tagged):
        ok = [r for r in group if made(r)]
        if ok:
            return ok[0]
    waiting = [r for r in exact + tagged if not made(r)]
    if waiting:
        r = waiting[0]
        raise BankMiss(f"sfx cue {cue!r} is row {r.get('id')!r}, which is "
                       f"{r.get('status') or 'not made'}: " + _make_hint("sfx", str(r.get("id"))))
    raise BankMiss(f"sfx cue {cue!r} is not in the bank — add a row named {name!r} to "
                   f"banks/sfx/index.json (status \"to make\") and make it")


def pick(bank: str, tags, root=None) -> dict:
    """The one row these tags pick, or BankMiss naming what is missing."""
    if bank == "music":
        return pick_music(tags if isinstance(tags, dict) else {}, root)
    if bank == "sfx":
        cue = tags.get("cue") if isinstance(tags, dict) else tags
        return pick_sfx(str(cue or ""), root)
    load(bank, root)       # raises for an unknown bank
    raise BankMiss(f"no picker for the {bank} bank")


def resolve(plan: dict, root=None) -> list[str]:
    """Resolve `plan.music` and every `plan.sfx` cue to a bank row, writing
    `bank_id` and `file` onto each, in place. Everything else the brief said
    is carried untouched. Returns the findings — one per row that could not
    be picked; the caller refuses on any."""
    fails: list[str] = []
    music = plan.get("music")
    if isinstance(music, dict) and music:
        try:
            row = pick_music(music, root)
            music["bank_id"], music["file"] = row["id"], row["file"]
        except BankMiss as e:
            fails.append(f"music: {e}")
    for i, cue in enumerate(plan.get("sfx") or [], 1):
        if not isinstance(cue, dict):
            continue
        try:
            row = pick_sfx(cue.get("cue"), root)
            cue["bank_id"], cue["file"] = row["id"], row["file"]
        except BankMiss as e:
            fails.append(f"sfx[{i}]: {e}")
    return fails


def status(root=None) -> dict:
    out = {}
    for bank in BANKS:
        try:
            rows = [r for r in load(bank, root)["rows"] if isinstance(r, dict)]
        except BankMiss as e:
            out[bank] = {"error": str(e)}
            continue
        out[bank] = {"made": [r["id"] for r in rows if made(r)],
                     "to_make": [r["id"] for r in rows if not made(r)]}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", help="a banks folder other than tools/video-production/banks")
    sub = ap.add_subparsers(dest="verb", required=True)
    sub.add_parser("status")
    p = sub.add_parser("pick")
    p.add_argument("bank", choices=BANKS)
    p.add_argument("--energy")
    p.add_argument("--tempo", type=float)
    p.add_argument("--mood")
    p.add_argument("--cue")
    a = ap.parse_args(argv)
    if a.verb == "status":
        for bank, s in status(a.root).items():
            if "error" in s:
                print(f"{bank}: {s['error']}")
                continue
            print(f"{bank}: {len(s['made'])} made · {len(s['to_make'])} to make")
            for rid in s["to_make"]:
                print(f"   to make  {rid}")
        return 0
    try:
        tags = ({"energy": a.energy, "tempo_bpm": a.tempo, "mood": a.mood}
                if a.bank == "music" else {"cue": a.cue})
        row = pick(a.bank, tags, a.root)
    except BankMiss as e:
        print(f"REFUSED {e}", file=sys.stderr)
        return 2
    print(json.dumps(row, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
