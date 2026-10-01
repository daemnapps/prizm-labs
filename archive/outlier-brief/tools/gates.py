#!/usr/bin/env python3
"""The gates this chain runs, and the one stop no run can skip.

Three of the five shared gates (`components/quality-checks`) apply:

    inputs     before any model runs     the idea is not empty; the brand is a
                                         real folder; a pinned avatar,
                                         sub-avatar, angle or offer is one the
                                         brand has ON FILE; a pinned awareness
                                         level is one the doctrine has; every
                                         step has a prompt; every doctrine
                                         slice and element list is there.
                                         Again after the round-out: the avatar
                                         it proposed is a real one.
    elements   after the awareness read, the awareness level, sophistication
               after the brief, and      stage and frameworks named are real
               after the format pick     library rows; every format and style
                                         picked is a real row. A row still
                                         saying `[TO DEFINE` is flagged "named,
                                         not defined yet" and not handed off —
                                         it never holds the run.
    copy       after the concept brief,  the brief arrived in its labelled
               and again at approval     parts; no UNFILLED note; every price
               (he may have edited it)   is one the offer bank sells today; the
                                         angle and offer it names are on file;
                                         and the check step found no claim the
                                         brand's files do not carry, no chopped
                                         thought, no typo.

THE REVIEW STOP is not a check — it is a person. `run.json` carries
`review.state`: `awaiting` | `approved` | `sent back`. The format pick and the
hand-offs refuse to run unless the state is `approved` AND the brief on file is
the brief that was approved (same sha).

`hold()` writes the gate-keyed `check.json` into the run and raises `Held`.

    gates.py <run folder>          print a run's check.json and review state
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
import paths as P                                             # noqa: E402
import slots as S                                             # noqa: E402
import brand_context as B                                     # noqa: E402
import elements_pick as L                                     # noqa: E402
import doctrine_slices as D                                   # noqa: E402

BRIEF_HEADS = ("THE BIG IDEA", "THE ARGUMENT", "THE AWARENESS ENTRY", "THE PROOF WE HAVE", "WHAT IS MISSING",
               "HOOK DIRECTIONS", "THE WORLD", "THE FRAMEWORKS IT FITS", "WHAT IT MUST NEVER CLAIM")
AWAITING, APPROVED, SENT_BACK = "awaiting", "approved", "sent back"


class NotApproved(Exception):
    """The later steps were asked for without an approval on file."""


def quality():
    if str(P.QUALITY) not in sys.path:
        sys.path.append(str(P.QUALITY))
    import quality_checks as Q
    return Q


def sha12(text):
    return hashlib.sha256((text or "").encode("utf-8", "replace")).hexdigest()[:12]


# ------------------------------------------------------------------ inputs

def input_problems(idea, brand, steps, avatar=None, sub=None, angle=None, offer=None,
                   awareness=None, sophistication=None, prompts_dir=None):
    """Everything the run needs, checked without spending anything."""
    out = []
    if not (idea or "").strip():
        out.append("the idea is empty — give it a few sentences, as a file or piped in with `-`")
    if not (P.BRANDS / brand).is_dir():
        out.append(f"`{brand}` is not a brand folder under brands/ — known: {', '.join(P.known_brands())}")
    else:
        lookups = [(B.check_avatar, (brand, avatar)) if avatar else None,
                   (B.check_sub, (brand, avatar, sub)) if (sub and avatar) else None,
                   (B.check_angle, (brand, angle)) if angle else None,
                   (B.check_offer, (brand, offer)) if offer else None]
        for fn, args in [x for x in lookups if x]:
            try:
                fn(*args)
            except B.NotOnFile as e:
                out.append(str(e))
        if sub and not avatar:
            out.append("a sub-avatar was named without its avatar — name both")
    for pair, rid in ((L.AWARENESS, awareness), (L.SOPHISTICATION, sophistication)):
        if rid:
            _, bad = L.lookup(pair, rid)
            if bad:
                out.append(bad)
    if str(P.RUN_KIT) not in sys.path:
        sys.path.append(str(P.RUN_KIT))
    from run_kit import prompts as KP
    for s in steps:
        try:
            KP.latest(prompts_dir or P.PROMPTS, s["key"])
        except KP.PromptError as e:
            out.append(str(e))
    out += D.missing()
    out += L.missing_lists()
    return out


# ------------------------------------------------------------------ the answers, read

def read_roundout(text, brand, pinned_avatar=None, pinned_sub=None):
    """→ ({avatar, sub, questions}, problems). A pinned avatar wins; a proposed
    one must be a real one."""
    problems = []
    try:
        got = S.block(text, "ROUNDOUT", aliases=("ROUND-OUT", "ROUND OUT"), keys=("avatar", "questions"))
    except ValueError as e:
        got = {}
        if not pinned_avatar:
            problems.append(str(e))
    avatar = pinned_avatar or (str(got.get("avatar") or "").strip().strip("`") or None)
    sub = pinned_sub or (str(got.get("sub") or "").strip().strip("`") or None)
    if sub in ("none", "null"):
        sub = None
    if not avatar and not problems:
        problems.append("the round-out named no avatar, and none was pinned on the run")
    if avatar and avatar != pinned_avatar:
        try:
            B.check_avatar(brand, avatar)
        except B.NotOnFile as e:
            problems.append(f"the round-out proposed an avatar that is not on file — {e}")
            avatar = None
    if avatar and sub and sub != pinned_sub:
        try:
            sub = B.check_sub(brand, avatar, sub)
        except B.NotOnFile:
            sub = None                                         # a guessed sub is dropped, never carried
    questions = [str(q).strip() for q in (got.get("questions") or []) if str(q).strip()]
    return {"avatar": avatar, "sub": sub, "questions": questions}, problems


def read_awareness(text):
    """→ ({awareness, sophistication}, problems) — both must be real doctrine rows."""
    try:
        got = S.block(text, "AWARENESS", aliases=("AWARENESS READ",), keys=("awareness", "sophistication"))
    except ValueError as e:
        return {"awareness": None, "sophistication": None}, [str(e)]
    out, problems = {}, []
    for field, pair in (("awareness", L.AWARENESS), ("sophistication", L.SOPHISTICATION)):
        rid = str(got.get(field) or "").strip().strip("`")
        if not rid:
            problems.append(f"the awareness read named no {field}")
            out[field] = None
            continue
        _, bad = L.lookup(pair, rid)
        if bad:
            problems.append(bad)
        out[field] = None if bad else rid
    return out, problems


def read_concept(text):
    try:
        got = S.block(text, "CONCEPT", aliases=("CONCEPT DATA",), keys=("frameworks", "angle", "offer"))
    except ValueError as e:
        return {"frameworks": [], "angle": None, "offer": None}, [str(e)]
    fw = got.get("frameworks") or []
    fw = [fw] if isinstance(fw, str) else fw

    def one(v):
        v = str(v or "").strip().strip("`")
        return None if v.lower() in ("", "none", "null") else v
    return {"frameworks": [one(f) for f in fw if one(f)], "angle": one(got.get("angle")), "offer": one(got.get("offer"))}, []


def brief_element_problems(concept):
    out = []
    if not concept["frameworks"]:
        out.append("the brief names no framework from the library")
    for f in concept["frameworks"]:
        _, bad = L.lookup(L.FRAMEWORK, f)
        if bad:
            out.append(bad)
    return out


def brief_copy_problems(brief, concept, brand):
    """What the code can see in the brief without a model."""
    Q = quality()
    out = [f"the brief is missing its labelled part: {h}" for h in S.missing_heads(brief, BRIEF_HEADS)]
    out += Q.unfilled_check(brief)
    bank = B.offer_bank(brand)
    allowed = bank
    if concept.get("offer"):
        try:
            B.check_offer(brand, concept["offer"])
            allowed = Q.offer_block(bank, concept["offer"]) or bank
        except B.NotOnFile as e:
            out.append(f"the brief names an offer that is not on file — {e}")
    out += Q.price_check(S.without_block(brief, "CONCEPT"), allowed, concept.get("offer"))
    if concept.get("angle"):
        try:
            B.check_angle(brand, concept["angle"])
        except B.NotOnFile as e:
            out.append(f"the brief names an angle that is not on file — {e}")
    return out


def check_step_problems(check_text):
    """The check step's answer (the shared ```CHECK block): a claim the brand's
    files do not carry, a chopped thought, a typo."""
    return quality().read_check_block(check_text)


# ------------------------------------------------------------------ holds

def hold(gate, run, problems):
    return quality().hold(gate, problems, run)


# ------------------------------------------------------------------ the review stop

def review_of(state):
    return (state or {}).get("review") or {"state": AWAITING, "history": []}


def require_approval(state, brief_text):
    """The format pick and the hand-offs call this first. No approval on file,
    or a brief that changed after it was approved → they refuse."""
    r = review_of(state)
    if r.get("state") != APPROVED:
        raise NotApproved(f"the concept brief is `{r.get('state', AWAITING)}`, not approved — "
                          f"nothing is picked or handed off until it is")
    if r.get("brief_sha256_12") != sha12(brief_text):
        raise NotApproved("the concept brief on file is not the one that was approved (it changed since) — "
                          "approve it again")
    return r


def state(run):
    f = Path(run) / "check.json"
    try:
        return json.loads(f.read_text()) if f.is_file() else {}
    except ValueError:
        return {}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    st = state(sys.argv[1])
    if not st:
        print(f"{sys.argv[1]}: no gate has run yet")
    for g, v in st.items():
        print(f"{g}: {v.get('result')}")
        for p in v.get("problems", []):
            print(f"   - {p}")
    try:
        rj = json.loads((Path(sys.argv[1]) / "run.json").read_text())
        print("review:", review_of(rj).get("state"))
    except (OSError, ValueError):
        pass
