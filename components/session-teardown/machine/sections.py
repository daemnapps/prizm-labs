"""The page under test as SECTIONS — page-teardown's structure — so a recording can say "never got past the offer
box" instead of "scrolled 64%".

Where the structure comes from, first hit wins:
  0. the page's own BUILD RECORD: the page-chain run that built the control version — asked of the page system
     (`components/naming/page_list.py page_context`, the page list's own record), else found by run.json `page` and
     `version` matching the page list's control. Its page.json is the page as written — every section's job and our own words —
     and its run.json carries the brief, the job and, for a variant, the hypothesis it was built to test;
  1. a page-chain run that already tore down this page's control: runs/page-chain/<brand>/*/structure.json whose
     run.json `source_url` is the control's address (a run that tore down a swipe is never used — its sections are
     the swipe's, not ours);
  2. otherwise this run tears the control down itself with page-teardown's own structure prompt, as its
     `structure` step (see run.py), from the page text (a sample's `pages/<page_id>.txt`, or page-teardown's
     capture of the live address).

Depth: page-teardown gives each section its word count and pictures, not pixels. A section's share of the page is
its weight (words, plus PICTURE_WORDS per picture, plus BUTTON_WORDS for a button) over the page's; the bands run
top to bottom in order. So "scrolled 64%" reads as "in §6 offer box" — an estimate, and the page says so.
"""
import json
from pathlib import Path
from urllib.parse import urlparse

PICTURE_WORDS = 40
BUTTON_WORDS = 15
MIN_WORDS = 10


def _path(url):
    return (urlparse(url or "").path or "/").rstrip("/") + "/"


def from_page_chain(control_url, brand, runs_root):
    """(structure, the run folder it came from) for the newest page-chain teardown of this control, else (None, None)."""
    root = Path(runs_root) / brand
    if not root.is_dir():
        return None, None
    hits = []
    for rj in root.glob("*/run.json"):
        try:
            st = json.loads(rj.read_text())
        except ValueError:
            continue
        sj = rj.parent / "structure.json"
        if sj.is_file() and st.get("source_url") and _path(st["source_url"]) == _path(control_url):
            hits.append((st.get("updated") or st.get("started") or "", rj.parent))
    if not hits:
        return None, None
    d = sorted(hits)[-1][1]
    return json.loads((d / "structure.json").read_text()), d


TEXT_TYPES = ("headline", "subhead", "eyebrow", "paragraph", "items", "bullets", "steps", "quote", "faq", "offer",
              "guarantee", "note", "button")
FORM_ORDER = ("offer", "guarantee", "faq", "steps", "items", "bullets", "quote", "paragraph", "headline")


def _words(v):
    if isinstance(v, str):
        return len(v.split())
    if isinstance(v, list):
        return sum(_words(x) for x in v)
    if isinstance(v, dict):
        return sum(_words(x) for k, x in v.items() if k not in ("rows", "source", "type", "src", "file"))
    return 0


def structure_of_page(page_doc):
    """page-writing's page.json (sections of typed blocks) as page-teardown's structure shape, keeping each
    section's first heading so the page map can say which section it is in our own words."""
    out = []
    for i, sec in enumerate(page_doc.get("sections") or []):
        blocks = [b for b in sec.get("blocks") or [] if isinstance(b, dict)]
        types = [b.get("type") for b in blocks]
        form = next((t for t in FORM_ORDER if t in types), types[0] if types else "section")
        head = next((b.get("text") for b in blocks if b.get("type") in ("headline", "subhead") and b.get("text")), "")
        button = next((b.get("text") for b in blocks if b.get("type") == "button" and b.get("text")), "none")
        out.append({"n": sec.get("n") or i + 1, "job": sec.get("job") or "", "form": form, "heading": head,
                    "words": sum(_words(b) for b in blocks if b.get("type") in TEXT_TYPES),
                    "pictures": [b for b in blocks if b.get("type") == "picture"], "button": button})
    return {"format": page_doc.get("format"), "sections": out}


PLAN_KEYS = ("brief", "job", "version", "page", "topic", "avatar", "format", "target_format", "hypothesis", "change",
             "hypothesis_file")


def from_context(ctx, ws):
    """(structure, plan, run folder) from the page system's page_context() answer — the page list's own record of
    which page-chain run built the control — else (None, None, None)."""
    if not ctx or not ctx.get("run"):
        return None, None, None
    d = Path(ws) / ctx["run"]
    if not (d / "page.json").is_file():
        return None, None, None
    st = {}
    try:
        st = json.loads((d / "run.json").read_text())
    except (OSError, ValueError):
        pass
    plan = {k: st[k] for k in PLAN_KEYS if st.get(k)}
    brief = ctx.get("brief") or {}
    if isinstance(brief, dict):
        for k in ("job", "hypothesis", "change"):
            if brief.get(k) and k not in plan:
                plan[k] = brief[k] if not isinstance(brief[k], dict) else brief[k].get("text") or ""
    if (ctx.get("control") or {}).get("brief"):
        plan["brief"] = ctx["control"]["brief"]
    return structure_of_page(json.loads((d / "page.json").read_text())), plan, d


def from_build(page_id, control_version, brand, runs_root):
    """(structure, plan, run folder) from the page-chain run that BUILT this page's control, else (None, None, None)."""
    root = Path(runs_root) / brand
    if not root.is_dir():
        return None, None, None
    hits = []
    for rj in root.glob("*/run.json"):
        try:
            st = json.loads(rj.read_text())
        except ValueError:
            continue
        if st.get("page") == page_id and st.get("version") == control_version and (rj.parent / "page.json").is_file():
            hits.append((st.get("updated") or "", rj.parent, st))
    if not hits:
        return None, None, None
    _, d, st = sorted(hits, key=lambda h: h[0])[-1]
    plan = {k: st[k] for k in PLAN_KEYS if st.get(k)}
    return structure_of_page(json.loads((d / "page.json").read_text())), plan, d


def page_map(structure):
    """[{n, form, job, label, start, end}] with start/end as % of the page's depth. None when there is no structure."""
    secs = [s for s in (structure or {}).get("sections") or [] if isinstance(s, dict)]
    if not secs:
        return None
    w = []
    for s in secs:
        words = max(int(s.get("words") or 0), MIN_WORDS)
        pics = len(s.get("pictures") or [])
        button = BUTTON_WORDS if str(s.get("button") or "none").strip().lower() != "none" else 0
        w.append(words + PICTURE_WORDS * pics + button)
    total = float(sum(w))
    out, at = [], 0.0
    for i, (s, wi) in enumerate(zip(secs, w)):
        start, end = at, (100.0 if i == len(secs) - 1 else at + 100.0 * wi / total)
        n = s.get("n") or i + 1
        form = str(s.get("form") or "section")
        out.append({"n": n, "form": form, "job": str(s.get("job") or ""), "label": "§%s %s" % (n, form),
                    "heading": str(s.get("heading") or ""), "start": round(start, 1), "end": round(end, 1)})
        at = end
    return out


def at(pmap, depth):
    """The section a visitor's deepest scroll ended in."""
    if not pmap or depth is None:
        return None
    d = float(depth)
    for s in pmap:
        if d <= s["end"]:
            return s
    return pmap[-1]


def as_text(pmap):
    if not pmap:
        return "(no page map: no teardown of this page's control is on file, so depth is given as scroll % only)"
    return "\n".join("%s · %d–%d%% of the page · job: %s%s" % (
        s["label"], s["start"], s["end"], s["job"], (' · heading: "%s"' % s["heading"]) if s.get("heading") else "")
        for s in pmap)


def plan_text(plan):
    """What the page was built to do, from its build record — or a plain note that there is none."""
    if not plan:
        return "(no build record for this page: it was not built by the page chain, so only its sections are known)"
    names = {"brief": "page brief", "job": "built as", "version": "version", "topic": "topic", "avatar": "avatar",
             "format": "source format", "target_format": "format", "hypothesis": "hypothesis it was built to test",
             "change": "the change it carries"}
    return "\n".join("- %s: %s" % (names.get(k, k), v) for k, v in plan.items() if k in names)


def reach_counts(pmap, furthest_by_group):
    """How many in each group got NO further than each section: {"left": {label: n}, "converted": {...}}."""
    out = {}
    for g, labels in furthest_by_group.items():
        counts = {s["label"]: 0 for s in pmap or []}
        for lab in labels:
            if lab in counts:
                counts[lab] += 1
        out[g] = counts
    return out


def reach_text(pmap, counts, n):
    if not pmap:
        return "(no page map)"
    rows = ["section | left: furthest here (of %d) | converted: furthest here (of %d)" % (n["left"], n["converted"])]
    for s in pmap:
        rows.append("%s | %d | %d" % (s["label"], counts["left"].get(s["label"], 0),
                                      counts["converted"].get(s["label"], 0)))
    return "\n".join(rows)
