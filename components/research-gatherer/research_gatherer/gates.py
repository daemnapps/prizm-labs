"""The gatherer's gates — where a pull is checked, and how a hold is recorded.

Rollout, 2026-09-20. The gatherer already refused bad work (a row with no
permalink is never written; a row from a room that plainly belongs to someone
else is never filed; no rooms means nothing is pulled). What it did not do is
SAY SO in the one place every tool says it. This module routes those holds
through the shared `components/quality-checks` (marketing-chain-checks) `hold(gate, problems, out_dir)`,
so a pull that files nothing leaves a gate-keyed `check.json` in its run folder
and reads HELD — and it asks the one element library (`components/elements`)
whether the doctrine terms a research question names are real ones.

    inputs     before anything is pulled   the sub-avatar file exists; there are rooms to pull from
    elements   before anything is pulled   every technique / delivery dial a research question names is in the library
    delivery   before rows enter the bank  every row carries a permalink; no row from a mismatched room; something to file

WHAT PASSES AND FAILS IS UNCHANGED. `build_bank_rows` still does the dropping;
these functions only look at what it produced and write the verdict down.

Never raises (the engine's own rule): a missing quality-checks or elements
component is written down as "not checked", never a crash, and never a pass
that was not earned.
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

GATE_NAMES = ("inputs", "elements", "delivery")


def _repo():
    """The workspace that carries the shared components — AI_WORKSPACE first,
    then by walking up from this file. Independent of the engine's WORKSPACE on
    purpose: a test points THAT at a temp tree, and the shared code is not in it."""
    found = []
    env = os.environ.get("AI_WORKSPACE")
    if env:
        found.append(Path(env))
    found += list(HERE.parents)
    for d in found:
        if any((d / "components" / n).is_dir() for n in CHECKS_DIRS):
            return d
    return None


def _import_from(folder, name):
    """Import `name` from `folder`, APPENDING to sys.path — never position 0
    (a folder that carries a copy.py or email.py would shadow the stdlib)."""
    if name in sys.modules:
        return sys.modules[name]
    if folder is None or not Path(folder).is_dir():
        return None
    if str(folder) not in sys.path:
        sys.path.append(str(folder))
    try:
        return __import__(name)
    except Exception:
        return None


# Renamed marketing-chain-checks on 2026-10-02; the folder may carry either name.
CHECKS_DIRS = ("marketing-chain-checks", "quality-checks")


def marketing_chain_checks():
    repo = _repo()
    folder = next((repo / "components" / n for n in CHECKS_DIRS
                   if repo and (repo / "components" / n / "marketing_chain_checks").is_dir()), None)
    return _import_from(folder, "marketing_chain_checks")


quality_checks = marketing_chain_checks     # the old name, for callers that learned it


def element_library():
    repo = _repo()
    return _import_from(repo / "components" / "elements" / "machine" if repo else None, "elements")


# ---------------------------------------------------------------- the checks

def inputs_problems(sub_file_found, rooms):
    out = []
    if not sub_file_found:
        out.append("no sub-avatar file on file for this brand / avatar / sub — "
                   "nothing to read desire words or rooms from")
    elif not rooms:
        out.append("no rooms on file and discovery came back empty — nothing pulled, no room invented")
    return out


def question_labels(questions):
    """What a research question's `framework` names that the element library
    holds a list for. `techniques.<id>` (or a bare technique id, the built-in
    fallback's shape) is a doctrine technique; `delivery.<dial>` names a
    delivery dial, which the library keeps as a list of its own. Anything else
    (desire, awareness, sophistication, mood, verification, spoken.levels)
    names a whole doctrine block, not a row on a list — there is nothing to
    look up, so nothing is claimed about it."""
    techniques, dials = [], []
    for q in questions or []:
        fw = str(q.get("framework") or "")
        if fw.startswith("techniques."):
            techniques.append((q.get("id"), fw.split(".", 1)[1]))
        elif fw.startswith("delivery."):
            dials.append((q.get("id"), fw.split(".", 1)[1]))
        elif fw and "." not in fw and str(q.get("id") or "").startswith("fallback-"):
            techniques.append((q.get("id"), fw))
    return techniques, dials


def question_problems(questions):
    """-> (problems, checked). [] when every doctrine term the questions name
    is a real one; the library's own refusal is passed through, so the real ids
    are named. `checked` is False when the library could not be asked at all —
    written down as not checked, never as a pass."""
    E = element_library()
    if E is None:
        return [], False
    techniques, dials = question_labels(questions)
    problems = []
    for qid, tid in techniques:
        for p in E.check({("doctrine", "technique"): tid}):
            problems.append(f"research question {qid}: {p}")
    for qid, dial in dials:
        try:
            E.rows("delivery", dial)
        except Exception as e:      # elements.Unknown — names the lists the library has
            problems.append(f"research question {qid}: {e.args[0] if e.args else e}")
    return problems, True


def delivery_problems(entries, pulled=0, no_receipt=0, dropped=0):
    """Looked at AFTER build_bank_rows has done its dropping, BEFORE a row is
    written into the avatar's bank."""
    out = []
    for e in entries or []:
        if not ((e.get("source") or {}).get("ref")):
            out.append(f"row {e.get('id')} carries no permalink — a row with no receipt is never filed")
        if ((e.get("fit") or {}).get("verdict")) == "no":
            out.append(f"row {e.get('id')} came from {(e.get('fit') or {}).get('room')}, "
                       "a room that does not match this avatar's demographics")
    if not entries:
        out.append(f"nothing to file: {pulled} item(s) came back, {no_receipt} with no permalink, "
                   f"{dropped} from a room that does not match this avatar's demographics")
    return out


# ---------------------------------------------------------------- the one hold

def record(gate, problems, out_dir=None):
    """Write the gate's verdict into <out_dir>/check.json through the shared
    hold(). Returns the problems that HELD the work ([] on a pass). Never raises."""
    problems = [p for p in (problems or []) if p]
    Q = marketing_chain_checks()
    if Q is not None:
        try:
            Q.hold(gate, problems, out_dir)
            return []
        except Q.Held as h:
            return list(h.problems)
        except Exception:
            pass
    # quality-checks could not be reached: the same file, the same shape, so
    # the hold is still visible — and it says who wrote it.
    try:
        if out_dir:
            f = Path(out_dir) / "check.json"
            state = json.loads(f.read_text()) if f.is_file() else {}
            state[gate] = {"result": "pass" if not problems else "HELD", "problems": problems,
                           "written_by": "research-gatherer (components/quality-checks not found)"}
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return problems
