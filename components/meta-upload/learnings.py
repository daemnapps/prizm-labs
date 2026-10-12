#!/usr/bin/env python3
"""Learnings — every Disapprove on the approval page, sent back up to the step that caused it.

    python3 learnings.py                 # rebuild the digests from learnings.jsonl, print a count per step
    python3 learnings.py --show 4 brand-a [--tool copywriter]   # what that step would be told

Each Disapprove writes one line to `Shared Assets/meta/learnings.jsonl` (the
cards root, or $META_CARDS_ROOT in trials) — who, which ad, the reasons picked
(each reason names its upstream step and tool, reasons.json), the note, and a
snapshot of the card's words and media names. This file turns those lines into
one plain digest per step and brand:

    Shared Assets/meta/learnings/<step>-<name>/<brand>.md    e.g. learnings/4-brief/brand-a.md

newest first, one line per rejection: when, which tool, the reason, the note,
the unit. Upstream tools read their digest with `recent()`; the prompt hooks
use `prompt_block()`, which gives back nothing unless that tool's switch in
learnings-hooks.json is on (all OFF until the owner has seen the exact text).

Upstream tools load this file by path (this folder's module names — build,
brand, meta, naming — would shadow theirs on sys.path):

    _s = importlib.util.spec_from_file_location("meta_learnings", <components>/meta-upload/learnings.py)
    _L = importlib.util.module_from_spec(_s); _s.loader.exec_module(_L)

Hooks (each marked "APPROVAL-PAGE LEARNINGS HOOK" in its tool) — see learnings-hooks.json
for which prompt each one feeds. Never writes into the repo. Never raises into
an upstream tool: a read that fails returns nothing.
"""
import importlib.util, json, os, sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REASONS = HERE / "reasons.json"
HOOKS = HERE / "learnings-hooks.json"
# shared_drive.py by path, like this file — this folder stays off an upstream tool's sys.path
_s = importlib.util.spec_from_file_location("meta_shared_drive", HERE / "shared_drive.py")
SD = importlib.util.module_from_spec(_s)
_s.loader.exec_module(SD)
# same place as drop.DRIVE / cards.root() — kept here so an upstream tool can read
# its digest without importing the card machinery
DRIVE = SD.shared_assets()
KEEP = 40                       # lines per digest file
PROMPT_LINES = 8                # lines a prompt hook would add
HEAD = "Recent rejections from the approval page — don't repeat these:"


def root():
    return Path(os.environ.get("META_CARDS_ROOT") or DRIVE / "meta")


def log_path():
    return root() / "learnings.jsonl"


def _no_root():
    """No META_CARDS_ROOT and no mount: nowhere real to write, so no fake local Drive tree."""
    return not os.environ.get("META_CARDS_ROOT") and not SD.mounted(DRIVE)


def config():
    return json.loads(REASONS.read_text())


def step_name(step):
    return config()["steps"].get(str(step), "unsorted")


def step_dir(step):
    return f"{step}-{step_name(step).lower()}" if step else "0-unsorted"


def resolve(ids, lane):
    """Reason ids picked on the page -> [{id, label, step, step_name, tool}], one per
    upstream (step, tool) the reason points at. Unknown id -> ValueError."""
    cfg = config()
    by_id = {r["id"]: r for r in cfg["reasons"]}
    out = []
    for i in dict.fromkeys(ids or []):
        r = by_id.get(i)
        if not r:
            raise ValueError(f"no reason {i!r}")
        for u in r["upstream"]:
            t = u["tool"]
            tool = (t.get(lane) or t.get("*")) if isinstance(t, dict) else t
            out.append({"id": i, "label": r["label"], "step": u["step"],
                        "step_name": cfg["steps"].get(str(u["step"]), "unsorted"), "tool": tool})
    return out


def snapshot(card):
    w = card.get("words") or {}
    return {"ad_name": card.get("ad_name"), "product": card.get("product"), "avatar": card.get("avatar"),
            "angle": card.get("angle"), "format": card.get("format"),
            "words": {k: list(w.get(k) or []) for k in ("primary", "headlines", "descriptions")},
            "media": list(card.get("media") or []),
            "pages": [p.get("link_id") for p in card.get("pages") or []],
            "made_by": card.get("made_by")}


def brief_key(card):
    """brand_product_brief-NNNN, the queue's key for a brief."""
    name = card.get("ad_name") or ""
    parts = name.split("_")
    brief = card.get("brief_id") or (parts[2] if len(parts) >= 4 else None)
    if not brief or brief == "none":
        return None
    return f"{card.get('brand')}_{card.get('product')}_{brief}"


def record(card, where, by, reasons, note, at=None):
    """One disapproval -> one line in learnings.jsonl, then the digests rebuilt."""
    rec = {"at": at or datetime.now().isoformat(timespec="seconds"), "by": by,
           "brand": where["brand"], "lane": where["lane"], "unit": card.get("ad_name") or where["name"],
           "brief_key": brief_key(card),
           "reasons": [{"id": r["id"], "label": r["label"], "step": r["step"], "tool": r["tool"]} for r in reasons],
           "note": note, "card": snapshot(card)}
    if _no_root():
        print(f"learnings: {SD.NOTE} — this disapproval was NOT logged", file=sys.stderr, flush=True)
        return rec
    p = log_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    digest()
    return rec


def read(brand=None, lane=None):
    p = log_path()
    if not p.is_file():
        return []
    out = []
    for line in p.read_text().splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (not brand or r.get("brand") == brand) and (not lane or r.get("lane") == lane):
            out.append(r)
    # newest first; same second -> the later line wins
    return [r for _, r in sorted(enumerate(out), key=lambda ir: (ir[1].get("at") or "", ir[0]), reverse=True)]


def summary(brand=None, lane=None, notes=5):
    """The Learnings tab: by upstream step, then tool — counts per reason, newest notes."""
    recs = read(brand, lane)
    steps = defaultdict(lambda: defaultdict(lambda: {"count": 0, "reasons": Counter(), "labels": {}, "notes": []}))
    for r in recs:
        for x in r.get("reasons") or []:
            t = steps[x["step"]][x["tool"]]
            t["count"] += 1
            t["reasons"][x["id"]] += 1
            t["labels"][x["id"]] = x["label"]
            if len(t["notes"]) < notes and not any(n["at"] == r["at"] and n["unit"] == r["unit"] for n in t["notes"]):
                t["notes"].append({k: r.get(k) for k in ("at", "by", "brand", "lane", "unit", "note")}
                                  | {"reasons": [y["label"] for y in r["reasons"] if y["tool"] == x["tool"]]})
    cfg = config()
    out = []
    for s in sorted(steps, key=lambda s: s or 99):
        tools = [{"tool": tool, "count": t["count"],
                  "reasons": [{"id": i, "label": t["labels"][i], "count": n} for i, n in t["reasons"].most_common()],
                  "notes": t["notes"]} for tool, t in sorted(steps[s].items(), key=lambda kv: -kv[1]["count"])]
        out.append({"step": s, "name": cfg["steps"].get(str(s), "Not sorted"), "count": sum(t["count"] for t in tools),
                    "tools": tools})
    return {"total": len(recs), "steps": out}


def line(r, x):
    note = " ".join((r.get("note") or "").split())
    return (f"- {(r.get('at') or '')[:10]} [{x['tool']}] {x['label']} — \"{note}\" "
            f"(unit {r.get('unit')}, {r.get('lane')}, by {r.get('by')})")


def digest():
    """learnings/<step>-<name>/<brand>.md for every step and brand that has a rejection."""
    if _no_root():
        print(f"learnings: {SD.NOTE} — digests NOT written", file=sys.stderr, flush=True)
        return []
    files = defaultdict(list)
    for r in read():
        for x in r.get("reasons") or []:
            files[(x["step"], r["brand"])].append(line(r, x))
    out = []
    for (step, brand), lines in files.items():
        d = root() / "learnings" / step_dir(step)
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"{brand}.md"
        body = (f"# Rejections — step {step} {step_name(step)} — {brand}\n\n"
                f"Written by components/meta-upload/learnings.py from the approval page's Disapprove. "
                f"Newest first, last {KEEP}.\n\n" + "\n".join(lines[:KEEP]) + "\n")
        tmp = f.with_name("." + f.name + ".tmp")
        tmp.write_text(body)
        os.replace(tmp, f)
        out.append(f)
    return out


def recent(step, brand, tool=None, n=PROMPT_LINES):
    """The newest digest lines for a step + brand (only `tool`'s, when given). [] on any trouble."""
    try:
        f = root() / "learnings" / step_dir(step) / f"{brand}.md"
        lines = [l for l in f.read_text().splitlines() if l.startswith("- ")]
        if tool:
            lines = [l for l in lines if f"[{tool}]" in l]
        return lines[:n]
    except Exception:
        return []


def hook_on(tool):
    """learnings-hooks.json switch for this tool (default OFF). $META_LEARNINGS_HOOKS
    ('all' or a comma list) overrides it for trials."""
    env = os.environ.get("META_LEARNINGS_HOOKS")
    if env is not None:
        return env == "all" or tool in [x.strip() for x in env.split(",")]
    try:
        return bool(json.loads(HOOKS.read_text()).get(tool, {}).get("on"))
    except Exception:
        return False


def prompt_block(tool, step, brand):
    """The text a prompt hook adds to what the model is sent — "" while the switch is off
    or there is nothing to say. Exactly: HEAD, then up to PROMPT_LINES digest lines."""
    if not brand or not hook_on(tool):
        return ""
    lines = recent(step, brand, tool)
    return ("\n\n" + HEAD + "\n" + "\n".join(lines) + "\n") if lines else ""


def show(tool, step, brand, out=None):
    """For a step with no model prompt (catalog, landing pages, generation runs): print the
    recent rejections to the person's run log. Changes nothing any model is sent. Always on."""
    lines = recent(step, brand, tool) if brand else []
    if lines:
        print(f"{HEAD} (step {step} · {tool} · {brand})\n" + "\n".join("  " + l for l in lines),
              file=out or sys.stderr, flush=True)
    return lines


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--show", nargs=2, metavar=("STEP", "BRAND"))
    ap.add_argument("--tool")
    a = ap.parse_args()
    if a.show:
        print("\n".join(recent(int(a.show[0]), a.show[1], a.tool, n=KEEP)) or "nothing")
    else:
        files = digest()
        s = summary()
        print(f"{s['total']} disapprovals -> {len(files)} digest file(s) under {root() / 'learnings'}")
        for st in s["steps"]:
            print(f"  {st['step']} {st['name']}: " + ", ".join(f"{t['tool']} {t['count']}" for t in st["tools"]))
