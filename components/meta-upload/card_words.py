#!/usr/bin/env python3
"""The words on a card — read from where the copywriter put them, never written here.

The copywriter's stage 8 render (`runs/copywriter/<brand>/<run>/stage8--render.md`)
holds every body it wrote (`**BODY A**` … under each `**FORMAT: …**`), and below
them the numbered **HEADLINES** and **DESCRIPTIONS** lists. That file is the one
source of a Meta ad's primary text, headlines and descriptions.

Three ways to the right run, used by the lane feeders:

    run_for_body(brand, body)      the run whose render holds this exact body —
                                   how a drop's copy.csv row finds its writer
                                   (the row kept the body and lost the lists)
    runs_for_brief(brand, brief)   runs whose label carries the brief's number
                                   or one of its aliases (p130-h1-v1-apology)
    from_file(path)                a words.json, a render, or a run folder named
                                   by hand (`--words`)

Nothing is invented: no run found means empty lists, and the card's own check
fails where the owner can see why.
"""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "components/naming"))
import names as N  # noqa: E402

# three of each: the construction (the owner, 2026-10-09: "if I only need the 3")
CAP = 3
# the writer's word-count line ends a body: `*61 words.*`, `*53 words*`, `(48 words)`, `*(48 words)*`
_END = re.compile(r"^\s*[*_]*\(?\s*\d+\s+words?\.?\s*\)?[*_]*\.?\s*$", re.M)
_ITEM = re.compile(r"^\s*\d+\.\s+\*\*(.+?)\*\*", re.M)


# the writer's working notes inside a body: "*As written: 150 words — over the 50–120 range. Rewritten to range:*",
# "*131 words. Still over. Final:*" — the ad is what follows the LAST such note (2026-10-09: a render's drafts reached a card)
_NOTE = re.compile(r"^\s*[*_]\(?[^\n]*?(?:words?|rewritten|final|over|range)[^\n]*?:\)?[*_]\s*$", re.I | re.M)


def final_only(text):
    """A body with the writer's own working notes in it -> only the version after the last note."""
    notes = list(_NOTE.finditer(text or ""))
    return (text[notes[-1].end():] if notes else text or "").strip()


def render_of(run_dir):
    """The copy a card reads from a copywriter run: the copy-checked final (`final--copy.md`, 2026-10-09) when
    there is one, else the stage 8 render. A run HELD at the copy gate or the copy check gives nothing."""
    d = Path(run_dir)
    try:
        held = (json.loads((d / "check.json").read_text()) or {}).get("held") if (d / "check.json").is_file() else False
    except ValueError:
        held = False
    run = json.loads((d / "run.json").read_text()) if (d / "run.json").is_file() else {}
    if "read_check" in run:                     # the run's own latest copy check outranks a hold left by an earlier rerun
        held = not run["read_check"].get("passed")
    if held or (run.get("gate") or {}).get("copy") == "HELD":
        return ""
    for f in ("final--copy.md", "stage8--render.md"):
        if (d / f).is_file():
            return (d / f).read_text()
    return ""


def checked(run_dir):
    """True when this copywriter run's copy passed the read-back copy check (stage 8c) and its final copy exists."""
    d = Path(run_dir)
    try:
        run = json.loads((d / "run.json").read_text())
    except (OSError, ValueError):
        return False
    return bool((run.get("read_check") or {}).get("passed")) and (d / "final--copy.md").is_file() and bool(render_of(d))


def body_of(text):
    """The ad copy only: everything before the writer's word-count line."""
    text = (text or "").replace("\r\n", "\n")
    m = _END.search(text)
    return (text[:m.start()] if m else text).strip()


def listed(text, heading):
    """The numbered bold items under **HEADING** (also `**HEADLINES — two.**`)."""
    text = (text or "").replace("\r\n", "\n")
    m = re.search(r"\*\*" + heading + r"\b[^*\n]*\*\*\s*\n(.*?)(?=\n\s*\*\*[A-Z][A-Z ]+\b[^*\n]*\*\*|\n---|\Z)",
                  text, re.S)
    return [s.strip() for s in _ITEM.findall(m.group(1))] if m else []


def parse_render(text):
    """A stage 8 render -> {"bodies": {format: [body, …]}, "headlines", "descriptions"}."""
    text = (text or "").replace("\r\n", "\n")
    bodies, fmt = {}, "copy"
    # `**FORMAT: caption**` or `**`FORMAT: caption`**`; `**BODY A**`, a rewrite `**BODY A** *(final)*`
    parts = re.split(r"^(\*\*`?FORMAT:[^*]*\*\*|\*\*BODY [A-Z]\*\*.*)$", text, flags=re.M)
    for i in range(1, len(parts), 2):
        head, rest = parts[i], parts[i + 1] if i + 1 < len(parts) else ""
        if "FORMAT:" in head:
            fmt = head.strip("*`").split(":", 1)[1].strip(" `*")
            continue
        letter = head[7]
        m = _END.search(rest)
        if m:
            b = rest[:m.start()].strip()
        else:   # no word count: the body ends at the writer's next bold label or rule
            stop = re.search(r"^(\*\*|---)", rest, re.M)
            b = (rest[:stop.start()] if stop else rest).strip()
        if not b:
            continue
        got = bodies.setdefault(fmt, {})
        got[letter] = final_only(b)         # a "(final)" rewrite replaces its draft; working notes never reach a card
    return {"bodies": {f: list(v.values()) for f, v in bodies.items()},
            "headlines": listed(text, "HEADLINES"),
            "descriptions": listed(text, "DESCRIPTIONS")}


def _norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def copy_runs(brand, repo=REPO):
    """Every copywriter run of the brand that has a render, newest render last."""
    base = Path(repo) / "runs/copywriter" / N.slug(brand)
    return sorted((p.parent for p in base.glob("*/stage8--render.md")),
                  key=lambda d: (d / "stage8--render.md").stat().st_mtime)


def run_for_body(brand, body, repo=REPO):
    """The copywriter run whose render holds this body (first 200 characters, spacing ignored)."""
    want = _norm(body_of(body))[:200]
    if len(want) < 20:
        return None
    for d in reversed(copy_runs(brand, repo)):
        if want in _norm(render_of(d)):
            return d
    return None


def runs_for_brief(brand, brief, repo=REPO, product=None):
    """Runs whose label carries the brief: its number in either spelling as a
    whole token, or an alias as the label or its start. A brief numbered per
    brand+product has no `pNNN` spelling — that would be an old brief."""
    forms = {f for f in N.brief_forms(brief) if f}
    try:
        head = N.brief_header(brand, N.brief_id(brief), product) or {}
    except N.AmbiguousBrief:
        head = {}
    if head.get("count") == N.PER_PRODUCT:
        forms = {N.brief_id(brief)}
    aliases = {N.slug(a) for a in (head.get("aliases") or []) if a and len(N.slug(a)) > 4}
    homes = brief_run_names(brand, brief, product)
    out = []
    for d in copy_runs(brand, repo):
        label = d.name.lower()
        toks = set(re.split(r"[-_]", label)) | {m.group(0) for m in re.finditer(r"brief-\d{4}", label)}
        if forms & toks or any(label == a or label.startswith(a + "-") for a in aliases):
            out.append(d)
        elif homes and homes & set(Path(_source_of(d)).parts):
            out.append(d)          # the copy run was written from the brief's own run (chain.py copy)
    return out


def _source_of(d):
    try:
        return json.loads((Path(d) / "run.json").read_text()).get("source_path") or ""
    except (OSError, ValueError):
        return ""


def brief_run_names(brand, brief, product=None):
    """The folder name of the brief's own writing run(s) — a copy run whose source
    file sits in one of them belongs to the brief, whatever its label says."""
    try:
        hit = N.find_brief(brand, brief, product)
    except N.AmbiguousBrief:
        return set()
    out = set()
    for rec in ((hit or {}).get("register") or {}, (hit or {}).get("header") or {}):
        run = rec.get("run")
        if run and len(Path(str(run)).name) > 4:
            out.add(Path(str(run)).name)
    return out


def _cap(xs):
    return list(dict.fromkeys(x.strip() for x in xs if x and x.strip()))[:CAP]


def empty():
    return {"primary": [], "headlines": [], "descriptions": []}


def from_runs(runs):
    """Words from one or more copywriter runs: every body (format order kept), the lists."""
    w = empty()
    for d in runs:
        r = parse_render(render_of(d))
        for fmt_bodies in r["bodies"].values():
            w["primary"] += fmt_bodies
        w["headlines"] += r["headlines"]
        w["descriptions"] += r["descriptions"]
    return {k: _cap(v) for k, v in w.items()}


def from_file(path):
    """--words: a words.json ({primary, headlines, descriptions}), a render, or a run folder."""
    p = Path(path)
    if p.is_dir():
        return from_runs([p])
    if p.suffix == ".json":
        d = json.loads(p.read_text())
        d = d.get("words", d)
        return {k: _cap(d.get(k) or []) for k in ("primary", "headlines", "descriptions")}
    r = parse_render(p.read_text())
    return {"primary": _cap([b for v in r["bodies"].values() for b in v]),
            "headlines": _cap(r["headlines"]), "descriptions": _cap(r["descriptions"])}


def brief_page(brand, brief, product=None):
    """The brief's landing page as naming reads it — the register, then an open
    proposal under runs/ (SI-97 (brand research proposals)), then the brand header. {} when none or on any error."""
    try:
        import page_pick as PP
        return PP.landing_page(brand, N.brief_id(brief), product) or {}
    except Exception:
        return {}


def from_copy_set(brand, brief, repo=REPO, product=None):
    """(words, where) from the APPROVED copy set for the brief's product + angle, or (None, None).

    One set per brand + product + angle (tools/copywriter/machine/copy_set.py,
    the owner 2 Oct 2026: "we don't actually need to change the copy for each ad unless it's
    a completely different angle"). Its {offer} and {click} are filled for the brief's
    own landing page type, so the words match the page the ad sends people to."""
    if not brief or brief == "none":
        return None, None
    try:
        head = N.brief_header(brand, N.brief_id(brief), product) or {}
    except Exception:
        return None, None
    prod, angle = head.get("product") or product, head.get("angle")
    if not (prod and angle):
        return None, None
    sys.path.insert(0, str(Path(repo) / "tools/copywriter/machine"))
    import copy_set as CS
    s = CS.approved(brand, prod, angle, ws=repo)
    if not s:
        return None, None
    page = brief_page(brand, brief, prod) or head.get("landing_page") or {}
    w = CS.fill(s, page_type=page.get("page_type"), link_id=(page.get("link_ids") or [None])[0])
    return {k: _cap(v) for k, v in w.items()}, f"{s['id']} v{s['version']} (copy set)"


def for_brief(brand, brief, repo=REPO, product=None):
    """(words, where) for a brief with no copy row of its own: the approved copy set for its
    angle, else its copywriter runs, else empty."""
    w, where = from_copy_set(brand, brief, repo, product)
    if w:
        return w, where
    runs = runs_for_brief(brand, brief, repo, product) if brief and brief != "none" else []
    if not runs:
        return empty(), None
    return from_runs(runs), ", ".join(str(Path(d).relative_to(repo)) for d in runs)


def missing(words):
    """What a card's words still lack, in plain words ([] when it has the minimum)."""
    out = []
    if not words.get("primary"):
        out.append("no primary text")
    if not words.get("headlines"):
        out.append("no headline")
    return out
