"""The gates this component runs, through the shared `marketing_chain_checks.hold()`.

Three of the five (`components/quality-checks`):

    inputs     before any model runs   the brand is real, a direction was
                                       given, the purpose and the frame are on
                                       their lists, and the product is on file
                                       when one is named
    elements   before any model runs   every style, format and template named
                                       is a real, defined row in the element
                                       library (`components/elements`)
    media      after the judge         a picture the judge failed is HELD from
                                       delivery, named with the judge's reason

`hold()` writes a gate-keyed `check.json` into the caller's `out`. A held run
SAYS WHY: printed when it happens, in `check.json`, and in the record.

**The media gate does not judge.** The verdicts are `judge.py`'s, unchanged;
this only writes them down as a gate and names what was kept back. Survivors
still ship — holding one picture never holds its siblings.

Lifted from `tools/image-production/static/tools/gates.py`.
"""
import json
import sys
from pathlib import Path

from . import paths as P

MODES = ("hold", "warn")


def quality():
    """The shared checks — components/quality-checks. APPENDED to sys.path,
    never inserted at 0: a folder at position 0 shadows the stdlib."""
    d = str(P.sibling("quality-checks"))
    if d not in sys.path:
        sys.path.append(d)
    import marketing_chain_checks as Q
    return Q


def library():
    """The element library — components/elements/machine/elements.py."""
    d = str(P.sibling("elements", "machine"))
    if d not in sys.path:
        sys.path.append(d)
    import elements as E
    return E


def _gate(name, problems, out_dir, mode="hold"):
    Q = quality()
    try:
        Q.hold(name, problems, Path(out_dir) if out_dir else None)
        return True
    except Q.Held as e:
        print(f"  ✗ {e}")
        if mode == "hold":
            raise
        print("  (gates are on warn — carrying on; check.json still says HELD)")
        return False


# ------------------------------------------------------------------ inputs

def input_problems(req, ctx, purposes, aspects, notes=None):
    """Everything that has to be true before a model is worth starting.

    `notes` collects what is worth SAYING and not worth stopping for; a caller
    that passes a list gets them back in it."""
    problems = []
    notes = notes if notes is not None else []

    if not str(req.get("direction") or "").strip():
        problems.append("no direction — the words describing the picture are the one thing "
                        "this component cannot read from anywhere else")

    pid = req.get("purpose")
    if pid not in purposes:
        problems.append(f"`{pid}` is not a purpose — have: {', '.join(sorted(purposes))}")

    aspect = req.get("_aspect") or req.get("aspect")
    if aspect and aspect not in aspects:
        problems.append(f"`{aspect}` is not a frame this component makes — "
                        f"have: {', '.join(sorted(aspects))}")

    try:
        count = int(req.get("count") or 1)
        if count < 1 or count > 12:
            problems.append(f"count {count} — one to twelve pictures a request")
    except (TypeError, ValueError):
        problems.append(f"count `{req.get('count')}` is not a number")

    if not req.get("out"):
        problems.append("no `out` — the caller says where its pictures land; this component "
                        "never picks a folder on a caller's behalf")

    # The model route splits on whether a photoreal person is in frame, and a
    # purpose whose `people` is "maybe" has not said. Refused, never guessed —
    # the same rule the element library runs on.
    # `people` used to be REFUSED when undeclared, because the model route
    # split on it. It does not any more — every picture goes to one door
    # (the owner, 2026-09-22) — so the refusal was friction with nothing behind
    # it. It still decides whether the brand's CAST may ride along as a
    # reference, so an undeclared request is noted rather than held.
    from . import route as R
    if ctx and not req.get("model") and not req.get("from_image") \
            and R.undeclared_people(req, ctx):
        notes.append(
            f"nobody said whether a person is in frame (`people`), so the brand's cast "
            f"is not attached as a reference — the picture is made from the direction "
            f"alone. It no longer changes the model: every picture goes to one door")

    for m in (ctx or {}).get("_missing_objects", []):
        if m.fatal:
            problems.append(f"{m.what}: {m.detail}")

    return problems


def inputs_gate(req, ctx, out_dir, purposes, aspects, mode="hold"):
    notes = []
    problems = input_problems(req, ctx, purposes, aspects, notes)
    for n in notes:
        print(f"  note: {n}")
    return _gate("inputs", problems, out_dir, mode)


# ---------------------------------------------------------------- elements

def elements_gate(req, ctx, out_dir, mode="hold"):
    """Every element id the request names, asked of the library. An unknown id
    is REFUSED naming the real ids — never quietly dropped."""
    problems = list((ctx.get("elements") or {}).get("problems") or [])
    _record(out_dir, (ctx.get("elements") or {}).get("picked") or {}, problems)
    return _gate("elements", problems, out_dir, mode)


def _record(out_dir, picked, problems):
    if not out_dir:
        return
    import time
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / "elements.json").write_text(json.dumps(
        {"asked": "components/elements", "picked": picked, "problems": problems,
         "checked": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
        indent=1, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------- media

def media_gate(out_dir, killed):
    """`killed` is the judge's own list: [(name, [reason, ...])]. Writes the
    media gate into check.json — HELD naming each picture and why — and
    returns whether it is clean.

    It never raises: the survivors of a request still ship, and a held picture
    was never copied into the delivery folder in the first place."""
    problems = [f"{name} — held from delivery: {'; '.join(map(str, fails)) or 'failed the judge'}"
                for name, fails in killed]
    try:
        return _gate("media", problems, out_dir, mode="warn") if problems \
            else _gate("media", [], out_dir)
    except Exception as e:                       # noqa: BLE001 — a gate that cannot write must say so, not stop a delivery
        print(f"  ! media gate could not be recorded: {e}")
        return not problems


# -------------------------------------------------------------------- read

def state(out_dir):
    f = Path(out_dir) / "check.json"
    try:
        return json.loads(f.read_text()) if f.is_file() else {}
    except ValueError:
        return {}


def held(out_dir, gates=None):
    """{gate: [problems]} for every gate this request is held at."""
    return {g: v.get("problems", []) for g, v in state(out_dir).items()
            if v.get("result") == "HELD" and (gates is None or g in gates)}
