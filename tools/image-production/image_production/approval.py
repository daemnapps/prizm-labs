"""Approved bases: a picture we made may only be used as a reference, or edited from, once it has an approved record.

the owner, 2026-10-26: "once one image has slop the next has slop, and a different end frame makes the video bad ... we are
isolating to get the highest quality images, which then go into video." So slop must not be passed forward as a base.

A picture we made has a `<picture>.recipe.json` beside it (plain.make and the engine write one). Its approval is
`<picture>.approval.json`: {"approved": bool, "gate_passed": bool, "judge": "pass"|..., "by", "at"}. It is approved only when
the picture passed its sheet gate (it carried a complete recipe) AND its judge. The engine writes the record when the judge
passes a picture; a picture the plain path made has no judge, so a person's approval (`approve`) writes it.

Material that is not ours to approve (a swipe, a product photograph, a banked cast picture) has no recipe record and is
allowed as it is. `gate.approved_bases_required` in models.json turns the refusal on; it is off until the callers approve.
"""
import json
import time
from pathlib import Path

from . import route as R


class ApprovalRefused(ValueError):
    """A picture that has no approved record was offered as a base: nothing was sent and nothing was spent."""


def recipe_path(pic):
    return Path(pic).with_suffix(".recipe.json")


def record_path(pic):
    """`<picture>.approved.json` (the name the prompt-generator's `approved_record` reads); written only for an APPROVED
    picture, so the file's existence is never a false approval. A picture that did not pass has `<picture>.scored.json`."""
    return Path(pic).with_suffix(".approved.json")


def scored_path(pic):
    return Path(pic).with_suffix(".scored.json")


def is_ours(pic):
    """A picture we made: it has our recipe record beside it."""
    return recipe_path(pic).is_file()


def read(pic):
    """The picture's record: approved, scored (below criteria), liked, or CHOSEN: a picture made on a path with no output
    judge (the plain path, the Prompt Bench) is its own only attempt, so its recipe record says `chosen`. None = never
    chosen or judged."""
    for f in (record_path(pic), scored_path(pic)):
        try:
            if f.is_file():
                return json.loads(f.read_text())
        except ValueError:
            return None
    try:
        if Path(pic).with_suffix(".liked.json").is_file():
            return {"approved": True, "chosen": True, "below_criteria": False, "by": "a person"}
        r = recipe_path(pic)
        got = json.loads(r.read_text()) if r.is_file() else {}
        if got.get("chosen"):
            bc = got.get("below_criteria")
            return {"approved": False, "chosen": True, "below_criteria": bool(bc) or bool(got.get("carries_below_criteria")),
                    "failed_checks": list(bc) if isinstance(bc, list) else []}
    except ValueError:
        pass
    return None


def write(pic, gate_passed, judge, by="engine", note=None, below_criteria=False, failed_checks=None):
    """Write the picture's record. `approved` is true only when the sheet gate AND the judge passed, and then it is
    `<picture>.approved.json`. Anything else is `<picture>.scored.json`: the judge's verdict, `below_criteria` and the plain
    failed checks. A below-criteria picture may still be used as a base: the flag is carried forward (`flag_of`)."""
    ok = bool(gate_passed) and str(judge).lower() == "pass"
    rec = {"approved": ok, "gate_passed": bool(gate_passed), "judge": judge, "below_criteria": bool(below_criteria) or not ok,
           "failed_checks": list(failed_checks or []), "by": by, "note": note, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    if ok:
        record_path(pic).write_text(json.dumps(rec, indent=1))
        if scored_path(pic).is_file():
            scored_path(pic).unlink()
    else:
        scored_path(pic).write_text(json.dumps(rec, indent=1))
        if record_path(pic).is_file():
            record_path(pic).unlink()                  # a re-judged picture that no longer passes is no longer approved
    return rec


def flag_of(pic):
    """The below_criteria flag of a picture of ours, when it carries one (a record that says so)."""
    got = read(pic) or {}
    return bool(got.get("below_criteria"))


def approve(pic, by, note=None):
    """A person's approval of a picture the plain path made (it had no judge). Refused unless the picture carries a recipe
    record whose sheet was complete: a picture made without its sheet cannot be approved as a base."""
    r = recipe_path(pic)
    if not r.is_file():
        raise ApprovalRefused(f"{Path(pic).name} has no recipe record, so it is not a picture we made and cannot be approved as a base.")
    got = json.loads(r.read_text())
    if not got.get("recipe"):
        raise ApprovalRefused(f"{Path(pic).name} was made without a recipe (its sheet), so it cannot be approved as a base.")
    return write(pic, True, "pass", by=by, note=note)


def required(t=None):
    return bool(((t or R.table()).get("gate") or {}).get("approved_bases_required"))


def check_bases(paths, t=None):
    """Refuse, by name, any picture of ours without an approved record. A no-op while the gate is off."""
    if not required(t):
        return
    bad = []
    for p in paths or []:
        if not p:
            continue
        p = Path(str(p))
        if is_ours(p) and read(p) is None:             # never judged: an input the chain does not have
            bad.append(p.name)
    if bad:
        raise ApprovalRefused("tools/image-production refuses to use " + ", ".join(bad) + " as a base: it was made here "
                              "but has no record of being judged (an approved record, or a scored one that says "
                              "below_criteria). Nothing was sent and nothing was spent.")
