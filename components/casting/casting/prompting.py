"""The three generating steps' prompts. Slots, never prose.

Each prompt is a FILE (`prompts/<step>-vN-damon.md`), so a change to how a
character is asked for is a change the owner can read — it is never a string
edited inside code. Highest `-vN-` wins, NUMERICALLY (an alphabetical sort
lets v2 beat v10), which is `components/run-kit/run_kit/prompts.py`'s rule and
is asked of it rather than re-implemented.

A prompt file is documentation above the `---` rule and the prompt below it,
so the reasoning travels with the prompt without being sent
(`tools/image-production/image_production/prompting.py`, same split).

The ORDER of the slots is the contract. A slot with nothing in it is dropped
entirely — never sent empty, never filled with a guess.
"""
import re
import sys

from . import paths as P

SLOT = re.compile(r"\{([a-z_]+)\}")

# What each step's prompt may ask for. A skeleton asking for anything else is
# an error, not a silently empty line.
ORDER = {
    "master": ("world", "noun", "who", "wardrobe", "style", "standing_rules"),
    "anchor": (),
    "detail": ("detail", "standing_rules"),
}


def kit():
    """run-kit's prompt rules. APPENDED to sys.path, never inserted at 0."""
    d = str(P.sibling("run-kit"))
    if d not in sys.path:
        sys.path.append(d)
    from run_kit import prompts as K
    return K


def latest(step, folder=None):
    return kit().latest(folder or P.prompts_dir(), step)


def sha(path):
    return kit().sha(path)


def body(path):
    from pathlib import Path
    text = Path(path).read_text()
    parts = re.split(r"^---\s*$", text, maxsplit=1, flags=re.M)
    return (parts[1] if len(parts) > 1 else parts[0]).strip()


def standing_rules(folder=None):
    """The rules on every character generation. Read from the file."""
    return body(latest("standing-rules", folder))


def slots(step, req, folder=None):
    """Every slot's value for one step. Nothing is invented: each value is
    either the caller's words or a row the element library returned."""
    out = dict((k, "") for k in ORDER[step])
    if step == "master":
        out["world"] = str(req.get("world") or "").strip()
        out["noun"] = str(req.get("noun") or "").strip()
        out["who"] = str(req.get("who") or "").strip()
        out["wardrobe"] = str(req.get("wardrobe") or "").strip()
        rows = (req.get("_elements") or {}).get("rows") or {}
        bits = []
        for field, label in (("style", "HOW IT IS RENDERED"),
                             ("format", "THE SHAPE IT TAKES")):
            r = rows.get(field)
            if r:
                bits.append("%s (%s): %s" % (label, r.get("name") or r["id"],
                                             r.get("what") or ""))
        out["style"] = "\n\n".join(bits)
    elif step == "detail":
        out["detail"] = str(req.get("detail") or "").strip()
    if "standing_rules" in out:
        rules = standing_rules(folder)
        for extra in req.get("rules") or []:
            rules += "\n\n" + str(extra)
        out["standing_rules"] = rules
    return out


def render(step, req, folder=None):
    """The prompt exactly as it will be sent. `(text, path)`."""
    if step not in ORDER:
        raise ValueError("`%s` is not a generating step — have: %s"
                         % (step, ", ".join(sorted(ORDER))))
    path = latest(step, folder)
    skeleton = body(path)
    asked = set(SLOT.findall(skeleton))
    unknown = sorted(asked - set(ORDER[step]))
    if unknown:
        raise ValueError("%s asks for slots nothing fills: %s"
                         % (path.name, ", ".join(unknown)))
    values = slots(step, req, folder)
    out = skeleton
    for name in ORDER[step]:
        out = out.replace("{" + name + "}", values.get(name) or "")
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out, path
