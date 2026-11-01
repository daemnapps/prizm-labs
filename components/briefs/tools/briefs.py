#!/usr/bin/env python3
"""Ask for a brief by what it IS — not by which chain happens to print it.

    python3 tools/briefs.py list                       every style, by status and state
    python3 tools/briefs.py find --asset video         every brief that makes a video
    python3 tools/briefs.py find --asset video --actor creator
    python3 tools/briefs.py path video--creator        where that prompt lives today
    python3 tools/briefs.py path static--designer --newest   the highest -vN- beside it
    python3 tools/briefs.py records                    what each style reads FROM
    python3 tools/briefs.py check                      every declared path still exists?
    python3 tools/briefs.py retire                     the kill list, with its evidence

the owner, 2026-09-30: *"All of our tools can just round through whatever brief
needs to be built based off whatever records we have."* This is that door. It
resolves; it never prints — the caller runs the prompt into its own run folder,
exactly as today.

No model, no credential, no network. Reads `briefs.json` and nothing else.
"""
import argparse, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
WS = HERE.parent.parent
REG = HERE / "briefs.json"
# components rule 6: `status` is the approval word, `state` activity only (triage page 15, Option A)
STATUSES = ("draft", "approved", "deprecated")
STATES = ("live", "parked")
VERSION = re.compile(r"-v(\d+)[-.]")


def newest(prompt, root=None):
    """The highest -vN- beside a pinned prompt, N as a NUMBER — the rule
    image-teardown's run.py `prompt_for()` runs by: top level of the pin's own
    folder only, so `archive/` and `superseded/` never compete. A pin with no
    -vN- is returned as it is."""
    root = Path(root or WS)
    p = Path(prompt)
    m = VERSION.search(p.name)
    if not m:
        return prompt
    pattern = p.name[:m.start()] + "-v*" + p.name[m.end() - 1:]
    hits = [f for f in (root / p.parent).glob(pattern) if VERSION.search(f.name)]
    if not hits:
        return prompt
    top = max(hits, key=lambda f: (int(VERSION.search(f.name).group(1)), f.name))
    return str(p.parent / top.name)


def load():
    return json.loads(REG.read_text())


def say(m):
    print(m, flush=True)


def style_for(teardown_type, reg=None):
    """The style id(s) an image-teardown brief TYPE is, off `teardown_types`.
    An unmapped type returns [] — its reason sits in the register; a word that
    is not a teardown type at all raises KeyError."""
    m = (reg or load())["teardown_types"]
    if teardown_type.startswith("_") or teardown_type not in m:
        raise KeyError(f"not an image-teardown brief type: {teardown_type!r}")
    v = m[teardown_type]
    return list(v) if isinstance(v, list) else []


def _row(b):
    ev = b.get("evidence") or {}
    seen = f"{ev.get('runs',0)}×{(' ' + ev['last']) if ev.get('last','—') != '—' else ''}".strip()
    return f"  {b['id']:<24}{b['asset']:<10}{b['actor']:<11}{b['status']:<11}{b['state']:<8}{seen}"


def standing(b):
    """The list group a style sits in: deprecated (status) before its activity (state)."""
    return "deprecated" if b["status"] == "deprecated" else b["state"]


def cmd_list(a, reg):
    for group in ("live", "parked", "deprecated"):
        rows = [b for b in reg["briefs"] if standing(b) == group]
        if not rows:
            continue
        say(f"\n{group.upper()} — {len(rows)}")
        say(f"  {'id':<24}{'asset':<10}{'actor':<11}{'status':<11}{'state':<8}runs")
        for b in sorted(rows, key=lambda x: -(x.get("evidence", {}).get("runs") or 0)):
            say(_row(b))
    say(f"\n  {len(reg['briefs'])} styles · naming: {reg['_naming']}")


def cmd_find(a, reg):
    rows = [b for b in reg["briefs"] if b["status"] != "deprecated"]
    if a.asset:
        rows = [b for b in rows if b["asset"] in (a.asset, "any")]
    if a.actor:
        rows = [b for b in rows if b["actor"] in (a.actor, "either")]
    if a.record:
        rows = [b for b in rows if a.record.lower() in (b.get("record") or "").lower()]
    if not rows:
        say("  nothing declared for that — `list` shows every style")
        return 1
    for b in rows:
        say(f"\n  {b['id']}   [{b['status']} · {b['state']}]")
        say(f"    reads    {b['record']}")
        say(f"    prompt   {b['prompt']}")
        if b.get("note"):
            say(f"    note     {b['note']}")
    return 0


def cmd_path(a, reg):
    for b in reg["briefs"]:
        if b["id"] == a.id:
            say(newest(b["prompt"]) if getattr(a, "newest", False) else b["prompt"])
            return 0
    say(f"  no style called {a.id}", file=sys.stderr) if False else say(f"  no style called {a.id}")
    return 1


def cmd_records(a, reg):
    """What each style projects FROM. The point of the component: a record is
    not owned by the chain that made it."""
    by = {}
    for b in reg["briefs"]:
        if b["status"] == "deprecated":
            continue
        by.setdefault(b.get("record") or "—", []).append(b)
    for rec, rows in sorted(by.items()):
        say(f"\n  {rec}")
        for b in rows:
            say(f"      → {b['id']}  ({b['asset']} for a {b['actor']})")


def cmd_check(a, reg):
    """Every declared prompt path still on disk. A register that rots is worse
    than no register."""
    bad = 0
    for b in reg["briefs"]:
        if b.get("status") not in STATUSES or b.get("state") not in STATES:
            say(f"  BAD WORD {b['id']:<24}status={b.get('status')!r} state={b.get('state')!r}")
            bad += 1
        p = WS / b["prompt"]
        if not p.exists():
            say(f"  MISSING  {b['id']:<24}{b['prompt']}")
            bad += 1
    for r in reg.get("retire_candidates", []):
        if not (WS / r["prompt"]).exists():
            say(f"  gone     (retire candidate) {r['prompt']}")
    say(f"  {len(reg['briefs'])} declared · {bad} missing")
    return 1 if bad else 0


def cmd_retire(a, reg):
    say("  Superseded prompts still sitting in live folders.")
    say("  the owner rules this list; archive into the folder's own archive/, never delete.\n")
    say(f"  {'last used':<12}{'runs':>5}  prompt")
    for r in sorted(reg.get("retire_candidates", []), key=lambda x: x.get("last") or ""):
        say(f"  {r.get('last','—'):<12}{r.get('runs',0):>5}  {r['prompt']}")
        if r.get("careful"):
            say(f"                      ⚠ {r['careful']}")


def main():
    ap = argparse.ArgumentParser(description="Resolve a brief style by what it is.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list")
    f = sub.add_parser("find")
    f.add_argument("--asset"); f.add_argument("--actor"); f.add_argument("--record")
    p = sub.add_parser("path"); p.add_argument("id")
    p.add_argument("--newest", action="store_true", help="the highest -vN- beside the pin")
    sub.add_parser("records"); sub.add_parser("check"); sub.add_parser("retire")
    a = ap.parse_args()
    if not a.cmd:
        ap.print_help()
        return 0
    reg = load()
    return {"list": cmd_list, "find": cmd_find, "path": cmd_path,
            "records": cmd_records, "check": cmd_check, "retire": cmd_retire}[a.cmd](a, reg) or 0


if __name__ == "__main__":
    sys.exit(main())
