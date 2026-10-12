"""The ONE model route. Read from `models.json`, never decided in code.

Two implementations disagreed and both were doing it privately:
`components/email-production/simple_email.py` sent every email picture to
OpenAI's GPT Image and overrode the frame per call;
`tools/image-production/static/tools/plates.py` split on whether a PERSON is in
frame and routed the rest to a model reached through a session on an MCP.
The split is kept (it is the measured one); the private choosing is not.

Nothing here knows what a caller is. A route row is a `when` and a model, and
the first row whose every `when` key matches the facts wins — so adding an
arm is a row in a JSON file, not a branch in somebody's chain.
"""
import json
import os

from . import paths as P


class NoRoute(SystemExit):
    pass


def table(path=None):
    return json.loads((path or (P.home() / "models.json")).read_text())


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


def size_for(entry, aspect):
    """The vendor's own way of asking for a frame. OpenAI takes a pixel size,
    Google takes an aspect ratio; the request shape says `aspect` either way."""
    sizes = entry.get("sizes") or {}
    return sizes.get(aspect)


def key_name(entry):
    return entry.get("key")


def key_value(name):
    """The key by NAME, through the one loader (`ip_keys`, components/keys —
    SI-194 (readers use loader)). The process environment first (that is how
    the vault is loaded into a process), then the repo's .env, then — off the
    mini only — the old
    places, in the loader's order: the macOS Keychain via `daemn_keys`, then
    ~/.daemn/keys.env, ~/.apify.env, ~/.gemini.env. On the mini (the marker
    ~/.workflow-worker.env exists) the environment is the only place.

    Asked by name only: never read out of a file in the repo, and this module
    opens no file itself — the old places are the loader's, temporary until
    Track B. Never printed, never logged, never written into a run record.
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
