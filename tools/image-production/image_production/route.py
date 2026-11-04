"""The ONE model route. Read from `models.json`, never decided in code.

Two implementations disagreed and both were doing it privately:
`tools/email-production/simple_email.py` sent every email picture to
OpenAI's GPT Image and overrode the frame per call;
`tools/image-production/static/tools/plates.py` split on whether a PERSON is in
frame and routed the rest to a model reached through a session on an MCP.
The split is kept (it is the measured one); the private choosing is not.

Nothing here knows what a caller is. A route row is a `when` and a model, and
the first row whose every `when` key matches the facts wins — so adding an
arm is a row in a JSON file, not a branch in somebody's chain.
"""
import importlib.util
import json
import os

from . import paths as P


class NoRoute(SystemExit):
    pass


# Which model does each picture job, and the judge, is the Generative Model House's answer, never this table's
# (the owner, 2026-10-20: "any of these generative tools that we build should just reference model house";
# LD-78 (house picture models)). The table keeps the doors: endpoints, params, sizes, key.
HOUSE_RULE = "components/generative-model-house/MODEL-HOUSE.md"
HOUSE_JOBS = (
    (("models", "gpt-image-person"), "pictures.generate"),
    (("models", "gpt-image-edit"), "pictures.edit"),
    (("models", "seedream-higgsfield"), "pictures.backup"),
    (("models", "nano-banana-higgsfield"), "pictures.object"),
    (("models", "gpt-image-openai-net"), "pictures.safety_net"),
    (("judge",), "behind.judge"),
)
_MH = []


def _house():
    """components/generative-model-house/model_house.py, loaded by path once (the folder has a hyphen). Found
    beside this component, never through AI_WORKSPACE: that points at the brands being read, not the house."""
    if not _MH:
        spec = importlib.util.spec_from_file_location(
            "ip_model_house", P.sibling("generative-model-house", "model_house.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MH.append(mod)
    return _MH[0]


def _overlay(t):
    """Each picture row's `vendor_model` from the house's job, with the job named in `house_job`. A job the house
    does not answer, or a door that is not the row's provider, is refused by name — never the table's own id."""
    mh = _house()
    for where, job in HOUSE_JOBS:
        row = t
        for k in where:
            row = row.get(k) if isinstance(row, dict) else None
        if not isinstance(row, dict):
            continue
        try:
            got = mh.model(job)
        except KeyError as e:
            raise NoRoute(f"the Generative Model House does not answer '{job}' for image-production's "
                          f"'{where[-1]}' row ({e}) — see {HOUSE_RULE}")
        mid = got if isinstance(got, str) else (got.get("model") if isinstance(got, dict) else None)
        if not mid:
            raise NoRoute(f"the Generative Model House names no model for '{job}' — see {HOUSE_RULE}")
        door = got.get("door") if isinstance(got, dict) else None
        if door is not None and door != row.get("provider"):
            raise NoRoute(f"the Generative Model House sends '{job}' through door '{door}', but image-production's "
                          f"'{where[-1]}' row is the '{row.get('provider')}' door — see {HOUSE_RULE}")
        row["vendor_model"] = mid
        row["house_job"] = job
    return t


def table(path=None, house=True):
    t = json.loads((path or (P.home() / "models.json")).read_text())
    return _overlay(t) if house else t


def aspects(t=None):
    t = t or table()
    return {k: v for k, v in (t.get("aspects") or {}).items() if not k.startswith("_")}


def undeclared_people(req, ctx):
    """True when nothing has SAID whether a person is in frame.

    A purpose whose `people` is `"maybe"` is an undecided, not a no. The
    static-ad tool never had this problem because its signal (`cast`) was
    always declared on the ad — "nothing is inferred from the prompt text"
    (plates.py). Here the direction is free words, and reading a person out of
    them is a guess. So the caller declares, or the inputs gate refuses:
    letting `"maybe"` quietly mean `False` sent a photoreal man to the object
    model on the first real dry run of this component (2026-09-21)."""
    return req.get("people") is None and ctx["purpose"].get("people") == "maybe"


def facts(req, ctx):
    """What the route decides on. Derived once, from the request and the
    purpose — never sniffed out of the prompt text."""
    purpose = ctx["purpose"]
    people = req.get("people")
    if people is None:
        people = purpose.get("people")
    return {
        "forced": bool(req.get("model")),
        "edit": bool(req.get("from_image")),
        "people": True if people is True else (False if people in (False, "maybe", None) else people),
        "purpose": purpose["id"],
    }


def _matches(when, f):
    for k, want in (when or {}).items():
        have = f.get(k)
        if isinstance(want, list):
            if have not in want:
                return False
        elif have != want:
            return False
    return True


def pick(req, ctx, t=None):
    """(model_id, entry, why). A forced model is honoured and still has to be
    a row in the table — a model nobody declared is refused, naming the real
    ones, the same way the element library refuses an unknown id."""
    t = t or table()
    f = facts(req, ctx)
    for row in t["route"]:
        if not _matches(row.get("when"), f):
            continue
        name = row["model"]
        if name == "@forced":
            name = req["model"]
        entry = (t.get("models") or {}).get(name)
        if not entry:
            raise NoRoute(f"`{name}` is not a model in this component's route table — "
                          f"have: {', '.join(sorted(t.get('models') or {}))}")
        why = row.get("why", "")
        if undeclared_people(req, ctx) and not f["forced"] and not f["edit"]:
            why += (" — nobody said whether a person is in frame (`people`), which no longer "
                    "changes the model; it only decides whether the brand's cast rides along")
        return name, entry, why
    raise NoRoute("no route row matched — the table's last row must have an empty `when`")


def recipe_required(t=None):
    """Whether a picture call must carry a filled recipe (the variable sheet). Off until every caller supplies one; once
    on, a call without a recipe is refused by name before it reaches any door (the owner, 2026-10-26: every variable filled or
    not applicable, so there are no unexpected pictures)."""
    return bool(((t or table()).get("gate") or {}).get("recipe_required"))


def approved_bases_required(t=None):
    return bool(((t or table()).get("gate") or {}).get("approved_bases_required"))


def max_attempts(kind="pictures", t=None):
    """The configured most attempts one picture gets in total across the ladder (a failed or refused call counts, and so
    does a picture that failed its judge). Outputs are scored and never hold a flow: when attempts run out, or one passes,
    the best-scoring attempt goes forward, flagged below_criteria if it did not pass."""
    return int((((t or table()).get("gate") or {}).get("max_attempts") or {}).get(kind, 3))


def slots(name, entry, t=None):
    """The ladder as attempt slots in order: a rung with `retry` gets a second slot right after its first. A table with
    no ladder is one slot, exactly one attempt, as before."""
    out = []
    for r in rungs(name, entry, t):
        out.append({**r, "slot": r["name"], "again": False})
        if r.get("retry"):
            out.append({**r, "slot": r["name"] + " (again)", "again": True})
    return out


def rungs(name, entry, t=None):
    """The ladder a picture goes down (the owner, 2026-10-26: GPT Image 2.5, one more try on GPT when it is busy, then
    Seedream 5 Pro if GPT refuses, then Nano Banana Pro, then the transitional OpenAI net). Read from the table's
    `ladder`; a table with none (or a forced model) is a single rung, exactly as before. `entry` is the picked row,
    possibly with the caller's per-call overrides, and stays the first rung."""
    t = t or table()
    kind = {"gpt-image-person": "generate", "gpt-image-edit": "edit"}.get(name)
    spec = (t.get("ladder") or {}).get(kind) if kind else None
    if not spec:
        return [{"name": "only", "entry": entry, "retry": False, "max_images": entry.get("max_images")}]
    out = []
    for i, r in enumerate(spec):
        e = entry if i == 0 else (t.get("models") or {}).get(r["model"])
        if e is None:
            raise NoRoute(f"the ladder names `{r['model']}`, which is not a model in this route table")
        out.append({"name": r["name"], "entry": e, "retry": bool(r.get("retry")), "max_images": e.get("max_images")})
    return out


def size_for(entry, aspect):
    """The vendor's own way of asking for a frame. OpenAI takes a pixel size,
    Google takes an aspect ratio; the request shape says `aspect` either way."""
    sizes = entry.get("sizes") or {}
    return sizes.get(aspect)


# Literals for the worker's key scan (WM-121 (component keys from code)); must match every `key` in models.json.
KEY_NAMES = ("OPENAI_API_KEY", "GEMINI_API_KEY")


def key_name(entry):
    return entry.get("key")


def key_value(name):
    """The key by NAME, through the one loader (`ip_keys`, components/keys —
    SI-194 (readers use loader)). The process environment first (that is how
    the vault is loaded into a process), then the one key file
    this repo's .env (add NAME=value there). On the mini the environment is
    the only place.

    Asked by name only: never read out of a file in the repo, and this module
    opens no file itself — the loader owns where keys live. Never printed, never logged, never written into a run record.
    Returns None rather than raising, so a dry run and a fresh clone both work
    — the caller that is about to spend is the one that refuses."""
    try:
        from . import ip_keys
    except Exception:
        return None
    return ip_keys.key(name)


def key_present(entry):
    return bool(key_value(key_name(entry)))


def judge_entry(t=None):
    return (t or table())["judge"]
