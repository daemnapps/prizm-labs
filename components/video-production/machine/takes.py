"""takes — how many takes a clip gets and which take is kept: one source (the logic layer, 2026-11-18).

Until this file three places gave three counts: providers.json `clip_route` said 1 and 1 (a press on the board),
v2.json `clips` said 1 and 3 (the automatic run, VIDEO-RULINGS V34), and budget.py priced 1 / 1.5 / 2.5 as "a guess".
The keep rule lived in two functions of clips_run.py with nothing saying they were one rule.

Now the numbers are one block, providers.json `direct.clip_route.attempts`, and this is its only reader:

    counts("press")       {"takes": 1, "max_tries": 1}    a press on the board: one take, judged and shown
    counts("automatic")   {"takes": 1, "max_tries": 3}    the automatic run: another take only when one fails (V34)
    expected(run=None)    {"low", "likely", "high"}       what the budget prices a kept clip at; `likely` is the run's
                                                          own measured average once its clip ledger carries takes
    pick(takes)           the take kept when at least one passed
    best_attempt(takes)   the take kept, flagged, when none passed
    keep(takes)           (the kept take, below_criteria) by the two rules above, in that order
    said()                the rule in one plain sentence, for a plan page or the trail

clips_run.py (`route_cfg`, `pick`, `best_attempt`), run_v2.py, budget.py, shot_route.py and the Brief Editing Board's
price all come here. A format's own row under `clip_route.by_format` may still lay its own `max_tries` over the
count; a format playbook's `stages.clips.takes` is a record of what a run of that format used, read by nothing.

Brand-agnostic: nothing here names a brand, a product or a person.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODES = ("press", "automatic")
LEVELS = ("low", "likely", "high")
MEASURE_FROM = 3            # a run's own average replaces `likely` once this many kept clips carry their takes


def rule(reg: dict | None = None) -> dict:
    """The attempts block. A registry written before the block existed (its route still carries `takes` /
    `max_tries`) is read as it was written, so an older registry keeps meaning what it said; a route with neither is
    refused by name: a take count is never assumed."""
    if reg is None:
        reg = json.loads((HERE / "providers.json").read_text())
    route = (reg.get("direct") or {}).get("clip_route") or {}
    a = route.get("attempts")
    if isinstance(a, dict) and isinstance(a.get("max"), dict):
        return a
    if route.get("takes") or route.get("max_tries"):
        first = int(route.get("takes") or 1)
        cap = max(first, int(route.get("max_tries") or first))
        return {"first": first, "max": {"press": cap, "automatic": max(cap, 3)}, "legacy": True}
    raise SystemExit("providers.json has no direct.clip_route.attempts — the take count and the keep rule are "
                     "read from there (machine/takes.py)")


# ONE PAID TAKE (owner ruling, 2026-11-20: "we need to only have one shot. We cannot be wasting our credits ... the
# whole purpose of setting all this stuff up really well from the start is so we don't have to do this").
# Every clip gets ONE paid call, on a press and in the automatic run alike. Nothing re-sends a paid call on its own:
# no second take, no extra round, no backup model, no remake for a changed face, no resend after a refusal. A failed
# or flawed clip is reported; the fix goes into the inputs and the rules, and a remake happens only on the owner's
# word (a press on the board, or V2_EXTRA_TAKES naming the clip). This outranks the registry's `attempts.max`.
ONE_PAID_TAKE = True


def counts(mode: str = "press", reg: dict | None = None) -> dict:
    """{"takes", "max_tries"} for a press on the board or for the automatic run: one and one (ONE_PAID_TAKE)."""
    if mode not in MODES:
        raise ValueError(f"mode is one of {MODES}, not {mode!r}")
    a = rule(reg)
    first = int(a.get("first") or 1)
    if ONE_PAID_TAKE:
        return {"takes": 1, "max_tries": 1}
    return {"takes": first, "max_tries": max(first, int(a["max"][mode]))}


def measured(run) -> float | None:
    """The average number of takes a kept clip took in this run, from its clip ledger; None until enough are there."""
    if not run:
        return None
    clips = Path(run) / "clips"
    for name in ("ledger.json", "omni-ledger.json"):
        try:
            led = json.loads((clips / name).read_text())
        except (OSError, ValueError):
            continue
        n = [len(r["takes"]) for r in led.values() if isinstance(r, dict) and r.get("status") == "done"
             and isinstance(r.get("takes"), list) and r["takes"]]
        if len(n) >= MEASURE_FROM:
            return round(sum(n) / len(n), 2)
    return None


def expected(run=None, reg: dict | None = None) -> dict:
    """What a kept clip is priced at, in takes: low (right first time), likely, high (the cap on every clip)."""
    a = rule(reg)
    p = a.get("priced_at") or {}
    first, cap = float(a.get("first") or 1), float(counts("automatic", reg)["max_tries"])
    if ONE_PAID_TAKE:
        return {"low": 1.0, "likely": 1.0, "high": 1.0}
    out = {"low": float(p.get("low") or first), "likely": float(p.get("likely") or (first + cap) / 2),
           "high": float(p.get("high") or cap)}
    got = measured(run)
    if got is not None:
        out["likely"], out["measured"] = max(out["low"], min(got, out["high"])), True
    return out


# ------------------------------------------------------------ the keep rule (VIDEO-RULINGS V34)

def pick(takes: list) -> dict | None:
    """The best take that passed: the highest score; equal scores go to the take that stops a thumb harder
    (stop power, V24), then to the earlier take. None when nothing passed."""
    ok = [t for t in takes if t.get("pass")]
    return max(ok, key=lambda t: (t["score"], float(t.get("stop_power") or 0), -t["take"])) if ok else None


def best_attempt(takes: list) -> dict | None:
    """The attempt to keep when none passed: of those that made a clip, the highest score; a tie goes to the later one."""
    made = [(i, t) for i, t in enumerate(takes) if t.get("file") and Path(str(t["file"])).is_file()]
    return max(made, key=lambda it: (it[1]["score"], it[0]))[1] if made else None


def keep(takes: list) -> tuple:
    """(the take kept, below_criteria): a passing take by `pick`, else the best attempt, flagged. (None, True) when no
    attempt made a file at all — the one case with nothing to keep."""
    got = pick(takes)
    if got is not None:
        return got, False
    return best_attempt(takes), True


def said(mode: str = "automatic", reg: dict | None = None) -> str:
    if ONE_PAID_TAKE:
        return ("one paid take of every clip, never sent again on its own; a take that did not pass is kept flagged "
                "below criteria and reported, and a remake happens only on the owner's word")
    c = counts(mode, reg)
    more = (f"another only when one fails, {c['max_tries']} at most" if c["max_tries"] > c["takes"]
            else "one per press, judged and shown")
    return (f"{c['takes']} take of every clip, {more}; the best-scoring take is kept, and one that did not pass is kept "
            "flagged below criteria so the chain moves on")
