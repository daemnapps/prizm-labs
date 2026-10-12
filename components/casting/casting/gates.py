"""The gates this component runs, through the shared `marketing_chain_checks.hold()`.

Three of the five (`components/quality-checks`):

    inputs     before any model runs   the brand is real, the role is named,
                                       the registry is readable — and the role
                                       is one the bank does NOT already cover
    elements   before any model runs   every style and format named is a real,
                                       DEFINED row in the element library
    media      after the judge         a generated sheet the judge failed is
                                       HELD: it is not filed into the brand's
                                       cast folder and no later step
                                       references it

`hold()` writes a gate-keyed `check.json` into the run folder. A held run SAYS
WHY: printed when it happens, in `check.json`, and in the record.

Lifted in shape from
`tools/image-production/image_production/gates.py`.
"""
import json
import sys
import time
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
        print("  ✗ %s" % e)
        if mode == "hold":
            raise
        print("  (gates are on warn — carrying on; check.json still says HELD)")
        return False


# ------------------------------------------------------------------ inputs

def input_problems(req, answer, build=False, start=None):
    """Everything that has to be true before a model is worth starting."""
    problems = []

    try:
        P.need_brand(req.get("brand"), "the cast bank", start)
    except P.BrandRequired as e:
        problems.append(str(e))

    if not str(req.get("role") or "").strip():
        problems.append("no role — `who plays this role?` is the question this "
                        "component answers, and the role cannot be read from "
                        "anywhere else")

    for p in (answer or {}).get("problems") or []:
        problems.append("the cast registry: %s" % p)

    if not build:
        return problems

    # ---- a role the bank covers NEVER gets a new face. This is the whole
    # point of the bank: a second face for a role that already has one breaks
    # that face across everything already shipped.
    if (answer or {}).get("covered"):
        p = answer["person"]
        problems.append(
            "this role is already cast: %s (`%s`), banked in %s — %s. A role the "
            "bank covers never gets a new face, because a second face breaks the "
            "first one across everything already shipped. Cast them, or name the "
            "role the bank does NOT cover."
            % (p.get("name") or p["id"], p["id"], p["where"], p["source"]))

    if not str(req.get("id") or "").strip():
        problems.append("no `id` — the character's folder name under the brand's "
                        "cast folder; it is a name a person chooses, never one "
                        "this component coins")
    elif (answer or {}).get("bank"):
        for row in (answer.get("candidates") or []):
            if row["id"] == req.get("id"):
                problems.append("`%s` is already banked (%s) — a rebuild gets a new "
                                "id and supersedes; it never writes over a banked "
                                "character" % (req["id"], row["source"]))

    kind = req.get("kind")
    if kind not in ("authority", "roster"):
        problems.append("`kind` is not declared — `authority` (the credentialed "
                        "voice that fronts a script) or `roster` (the person with "
                        "the problem). It decides which record the proposed row "
                        "belongs in, and it is never read out of the role: that "
                        "is a guess")

    for field, what in (("who", "the character — what makes this person this person"),
                        ("wardrobe", "the wardrobe, completely; never left to inference"),
                        ("world", "the room, the framing and the light the baseline carries")):
        if not str(req.get(field) or "").strip():
            problems.append("no `%s` — %s" % (field, what))

    if not str(req.get("noun") or "").strip():
        problems.append(
            "no `noun` — the word the model is given for the subject. It is "
            "REQUIRED and never defaulted: a vague noun is a vague face, and a "
            "default is this component deciding something about a brand's person "
            "that nobody asked it to decide")

    base = req.get("_baseline") or {}
    if not base.get("baseline"):
        problems.append(
            "no baseline — identity comes from an IMAGE, never from a paragraph. "
            "A character written as prose is a different person every roll, which "
            "is the exact failure the cast bank exists to prevent. Nothing in the "
            "owned footage matched, so a person picks the frame")
    elif not base.get("on_this_machine"):
        problems.append("the baseline is not a file on this machine: %s — a remote "
                        "url is a declaration the model never sees; nothing here "
                        "downloads" % base.get("baseline"))

    # `out` is NOT required: this component has its own run home,
    # `runs/casting/<brand>/<label>/` (runs/README.md, ruled 2026-09-17), and a
    # caller that names one is overriding a declared default rather than
    # supplying a missing fact. The dry run prints whichever it resolved to.
    return problems


def inputs_gate(req, answer, out_dir, build=False, mode="hold", start=None):
    return _gate("inputs", input_problems(req, answer, build, start), out_dir, mode)


# ---------------------------------------------------------------- elements

def resolve_elements(req, lib=None):
    """Every element id the request names, asked of the library. An unknown id
    is REFUSED naming the real ids — never quietly dropped."""
    lib = lib if lib is not None else library()
    picked, rows, problems = {}, {}, []
    for field, asset in (("style", "image"), ("format", "image")):
        value = req.get(field)
        if not value:
            continue
        picked[field] = value
        try:
            row = lib.get(field, asset, value)
        except Exception as e:                   # noqa: BLE001 — Unknown is the library's own
            problems.append("%s: %s" % (field, e))
            continue
        if str(row.get("what") or "").strip().upper().startswith("[TO DEFINE"):
            problems.append("%s `%s` is named in the library but not defined yet — "
                            "a row nobody has written is not a row a prompt can "
                            "carry" % (field, value))
            continue
        rows[field] = row
    return {"picked": picked, "rows": rows, "problems": problems}


def elements_gate(req, out_dir, mode="hold"):
    el = req.get("_elements") or {"picked": {}, "problems": []}
    _record(out_dir, el.get("picked") or {}, el.get("problems") or [])
    return _gate("elements", list(el.get("problems") or []), out_dir, mode)


def _record(out_dir, picked, problems):
    if not out_dir:
        return
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / "elements.json").write_text(json.dumps(
        {"asked": "components/elements", "picked": picked, "problems": problems,
         "checked": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
        indent=1, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------- media

def media_gate(out_dir, killed):
    """`killed` is the judge's own list: `[(step, [reason, ...])]`.

    Writes the media gate into `check.json` — HELD naming each sheet and why.
    It never raises: a held sheet was never filed into the brand's cast folder
    in the first place, and the run's record still has to be written."""
    problems = ["%s — held from the bank: %s"
                % (step, "; ".join(map(str, fails)) or "failed the judge")
                for step, fails in killed]
    try:
        return _gate("media", problems, out_dir, mode="warn") if problems \
            else _gate("media", [], out_dir)
    except Exception as e:                       # noqa: BLE001 — a gate that cannot write must say so
        print("  ! media gate could not be recorded: %s" % e)
        return not problems


# -------------------------------------------------------------------- read

def state(out_dir):
    f = Path(out_dir) / "check.json"
    try:
        return json.loads(f.read_text()) if f.is_file() else {}
    except ValueError:
        return {}


def held(out_dir, gates=None):
    return dict((g, v.get("problems", [])) for g, v in state(out_dir).items()
                if v.get("result") == "HELD" and (gates is None or g in gates))
