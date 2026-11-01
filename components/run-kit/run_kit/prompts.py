"""Prompt files: highest -vN- wins (NUMERIC — an alphabetical sort lets v2
beat v10), and a prompt asking for a variable nobody supplied is refused by
reading the TEMPLATE, not the filled text (a brand file may itself contain a
{token}). Lifted from email.py:155 and pages/run.py:105."""
import hashlib
import re
from pathlib import Path

VERSION = re.compile(r"-v(\d+)[-.]")
FIELD = re.compile(r"\{([a-z][a-z0-9_]*)\}")


class PromptError(Exception):
    pass


def latest(folder, stage):
    best, best_v = None, -1
    for f in Path(folder).rglob(f"{stage}-*.md"):
        if "superseded" in f.parts:
            continue
        m = VERSION.search(f.name)
        v = int(m.group(1)) if m else 0
        if v > best_v:
            best, best_v = f, v
    if best is None:
        raise PromptError(f"no prompt file for {stage} in {folder}")
    return best


def wanted(template):
    return sorted(set(FIELD.findall(template)))


def fill(template, fields):
    missing = [w for w in wanted(template) if w not in fields]
    if missing:
        raise PromptError("the prompt asks for fields nobody supplied: " + ", ".join(missing))
    out = template
    for name, value in fields.items():
        out = out.replace("{" + name + "}", str(value) if value not in (None, "") else "(none supplied)")
    return out


def sha(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.is_file() else None
