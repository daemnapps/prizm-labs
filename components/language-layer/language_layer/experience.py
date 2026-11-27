"""The experience index: real lived moments, one fresh set per run.

Positioning and benefits stay constant; the lived experience changes every run (2026-11-02).
Two halves:

  pick()   rows from the index for one run: different scenes, the ones earlier runs were
           handed rest, the ones that fit the swipe first.
  fixed()  a fixed brand file with its lived moments taken out, so the only moments a
           writer sees are the rotating ones. Reads the strip list; the brand file is
           never written (brands/ is read-only to machines).

Machine output lives under runs/language-layer/<brand>/experience/: `<avatar>.json` the
index, `strip.json` the lines to lift out of the fixed files, `shown.jsonl` what each run
was handed. A brand's own `language/experiences.json` wins over the index when a person
has filed one.
"""
import json
import os
import re
import time
from pathlib import Path

from . import engine as E

REST_RUNS = 5             # a row handed to a run sits out this many runs
PICK = 8                  # enough for the control and five hooks, all different moments
STOP = set("the a an and or of to in on at my i me is was it that this with for her she you".split())


def _home(brand, root=None):
    base = Path(root) if root else E.WORKSPACE
    return Path(base) / "runs" / "language-layer" / brand / "experience"


def load(brand, avatar, root=None):
    """The index for one avatar, a filed brand copy first. [] when there is none."""
    base = Path(root) if root else E.WORKSPACE
    for f in (base / "brands" / brand / "core-avatars" / avatar / "language" / "experiences.json",
              _home(brand, root) / f"{avatar}.json"):
        if f.is_file():
            try:
                return json.loads(f.read_text()).get("rows") or []
            except ValueError:
                return []
    return []


def _words(text):
    return {w for w in re.findall(r"[a-z]{3,}", (text or "").lower()) if w not in STOP}


def shown_scenes(brand, run=None, root=None, last=REST_RUNS):
    """Rows handed to the last `last` runs, this run left out so a re-run keeps its set."""
    f = _home(brand, root) / "shown.jsonl"
    if not f.is_file():
        return set()
    rows = []
    for line in f.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    rows = [r for r in rows if r.get("run") != run]
    out = set()
    for r in rows[-last:]:
        out |= set(r.get("ids") or [])
    return out


def pick(brand, avatar, hint="", run=None, n=PICK, root=None, record=True):
    """`n` rows across themes, the rested ones first. A run asking again gets the set it was given."""
    home = _home(brand, root)
    rows = load(brand, avatar, root)
    if not rows:
        return []
    f = home / "shown.jsonl"
    if run and f.is_file():
        for line in f.read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("run") == run and r.get("avatar") == avatar:
                keep = dict.fromkeys(r.get("ids") or [])
                indexed = {x.get("id"): x for x in rows}
                got = [indexed[key] for key in keep if key in indexed]
                if got:
                    return got
    resting = shown_scenes(brand, run, root)
    want = _words(hint)

    def score(r):
        fit = len(want & _words(" ".join([r.get("scene", ""), r.get("does", ""), r.get("quote", "")])))
        return (r.get("id") in resting, -fit, r.get("id") or "")

    out, themes = [], {}
    for r in sorted(rows, key=score):                 # no theme crowds the set
        t = r.get("theme") or "other"
        if themes.get(t, 0) >= 2:
            continue
        themes[t] = themes.get(t, 0) + 1
        out.append(r)
        if len(out) == n:
            break
    if record and run:
        home.mkdir(parents=True, exist_ok=True)
        with f.open("a") as w:
            w.write(json.dumps({"run": run, "avatar": avatar, "at": int(time.time()),
                                "ids": [r.get("id") for r in out],
                                "themes": [r.get("theme") for r in out]}) + "\n")
    return out


def render(rows):
    """Rows as a writing stage reads them."""
    if not rows:
        return ("(no lived experiences indexed for this avatar: build the piece on the swipe's own "
                "moment, and never invent one)")
    out = []
    for r in rows:
        src = r.get("source") or {}
        where = " · ".join(str(x) for x in (src.get("type"), src.get("url") or src.get("name")) if x)
        out.append(f'- [{r.get("id")}] "{(r.get("quote") or "").strip()}"\n'
                   f'  _scene: {r.get("scene")} · {r.get("zone")} · {where or "source not recorded"}_')
    return "\n".join(out)


def block(brand, avatar, run=None, root=None, hint=""):
    """The moments as a block for a language query. Empty when the avatar has no index."""
    rows = pick(brand, avatar, hint, run or f"auto-{os.getpid()}", root=root)
    if not rows:
        return ""
    return ("\n\n## Lived moments for this run\n\nReal moments in their own words. A lived moment in "
            "this piece comes from this list or from the swipe, never from memory or another ad.\n\n"
            + render(rows))


def is_fixed(path):
    """A file whose lived moments rotate instead of riding along."""
    p = str(path)
    name = p.rsplit("/", 1)[-1]
    if "/brands/" not in "/" + p:
        return False
    if name in ("language-bank.md", "avatar.md", "position.md", "story.md"):
        return True
    return "/core-avatars/" in p and name in ("profile.md", "rules.md", "culture-map.md")


def clean_file(path, brand=None):
    """A file's text, its lived moments lifted out when it is a fixed brand file."""
    path = Path(path)
    text = path.read_text()
    m = re.search(r"/brands/([^/]+)/", "/" + str(path.resolve()))
    if not is_fixed(path.resolve()) or not (brand or m):
        return text
    return fixed(text, brand or m.group(1))


def repeats(text, brand, root=None):
    """Stock moments a finished piece used anyway, with counts."""
    out = {}
    for t in strip_list(brand, root).get("terms") or []:
        n = len(re.findall(re.escape(t), text, re.I))
        if n:
            out[t] = n
    return out


def strip_list(brand, root=None):
    f = _home(brand, root) / "strip.json"
    if not f.is_file():
        return {}
    try:
        return json.loads(f.read_text())
    except ValueError:
        return {}


def _drop_terms(text, terms):
    """Any sentence or list segment naming a term goes, a whole section under a heading that
    names one goes, and a table row keeps its shape with the term swapped for a neutral word."""
    hit = re.compile("|".join(re.escape(t) for t in terms), re.I)
    out, skip = [], None
    for ln in text.splitlines():
        h = re.match(r"(#+)\s", ln)
        if h and skip is not None and len(h.group(1)) <= skip:
            skip = None
        if skip is not None:
            continue
        if not hit.search(ln):
            out.append(ln)
            continue
        if h:
            skip = len(h.group(1))
            continue
        if ln.lstrip().startswith("|"):
            out.append(hit.sub("cover-ups", ln))
            continue
        sep = " · " if " · " in ln else None
        bits = ln.split(sep) if sep else re.split(r"(?<=[.!?…])\s+", ln)
        kept = [b for b in bits if not hit.search(b)]
        left = (sep or " ").join(kept).rstrip()
        if len(re.sub(r"[\W_]", "", left)) >= 12:
            out.append(left)
    return "\n".join(out)


def fixed(text, brand, root=None):
    """`text` with its lived moments lifted out: the listed lines, then every sentence naming a
    listed term. Unchanged when the brand has no strip list."""
    spec = strip_list(brand, root)
    if not spec:
        return text
    cut = sorted({" ".join(x.split()) for x in spec.get("lines") or [] if x.strip()},
                 key=lambda value: (-len(value), value))
    kept = []
    for ln in text.splitlines():
        flat = " ".join(ln.split())
        if any(c in flat for c in cut):
            bare = flat
            for c in cut:
                bare = bare.replace(c, "")
            if len(re.sub(r"[\W_]", "", bare)) < 25:     # nothing left worth keeping
                continue
            for c in cut:                                # keep the rest of a mixed line
                ln = ln.replace(c, "")
        kept.append(ln)
    out = "\n".join(kept)
    return _drop_terms(out, spec["terms"]) if spec.get("terms") else out
