#!/usr/bin/env python3
"""system-research result writer — step 4 (the page) and step 5 (save it).

    python3 .claude/skills/system-research/write_result.py <result.json>
        [--out-root DIR] [--date YYYY-MM-DD]

Reads one result JSON (schema in SKILL.md), refuses it on a bad answer, chip,
shelf, trust tier or sketch (exit 2), and writes
    runs/system-research/<YYYY-MM-DD>-<job-slug>/result.json + page.html
A folder that already exists is never overwritten: the next free -2, -3 ... is used.

Stdlib only, Python 3.9.6-clean. Finds the workspace by walking up to the first
folder holding components/ and .claude/ (AI_WORKSPACE wins when it holds both) —
run-kit's paths.repo() is the same walk, but importing it from a skill folder
needs the root first, so the walk is repeated here rather than imported.
Re-derived from the 2026-10-08 prototype, not imported (SI-95 (system research)).
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

ANSWERS = {
    "use": "Use it",
    "extend": "Extend it",
    "being-built": "Someone is building it",
    "nothing": "Nothing exists",
}
CHIPS = [  # the spec's six, in its order
    ("exists", "exists, used as is"),
    ("adapt", "exists, needs adapting"),
    ("build", "to build"),
    ("outside", "outside, adopt or trial"),
    ("person", "a person does it"),
    ("open", "open question"),
]
CHIP_LABEL = dict(CHIPS)
SHELVES = [("apps", "Apps and paid software"), ("ai-tools", "AI tools"),
           ("open-source", "Open-source libraries")]
TRUST_TIERS = ("official vendor", "well-known open source", "unvetted community")
SKETCH_KINDS = ("animation", "simulator", "working-rule", "mockup", "chart")
SKETCH_DATA = {"real": "real data", "example": "example data — not real"}
# A sketch never calls out. (1) a src/href/srcset/action/url()/@import/fetch()/import()
# pointing at an http(s) or protocol-relative URL; (2) a network API (fetch,
# XMLHttpRequest, WebSocket, EventSource, sendBeacon) anywhere beside any outside URL
# (catches a URL held in a variable). SVG/XHTML namespace URIs are not calls.
SKETCH_OUTBOUND = re.compile(
    r"""(?:\b(?:src|href|srcset|action|formaction|data)\s*=\s*["']?\s*"""
    r"""|\b(?:fetch|import)\s*\(\s*["'`]?\s*|\burl\(\s*["']?\s*|@import\s+["']?\s*)"""
    r"""(?:(?:https?|wss?):)?//""", re.I)
SKETCH_NET_API = re.compile(r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon)\b")
SKETCH_ANY_URL = re.compile(r"(?:https?|wss?)://(?!www\.w3\.org/)", re.I)
SECTIONS = [  # the spec's fixed order (step 4)
    ("recommendation", "Recommendation"),
    ("steps", "The five steps"),
    ("flow", "How the recommendation would work"),
    ("sketch", "Sketch"),  # only when there is one (skipped on "use it")
    ("our-system", "What our system has"),
    ("parts", "Parts we already have"),
    ("outside", "What exists outside"),
    ("options", "The options"),
    ("also-helps", "Could also help other work"),
    ("trial", "The cheap trial"),
    ("sources", "Sources"),
]


class Refused(ValueError):
    """The result breaks the schema; the message lists every reason."""


def repo_root(start=None) -> Path:
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env) / "components").is_dir() and (Path(env) / ".claude").is_dir():
        return Path(env)
    here = Path(start or __file__).resolve()
    for d in [here, *here.parents]:
        if (d / "components").is_dir() and (d / ".claude").is_dir():
            return d
    raise FileNotFoundError("no workspace found upward of " + str(here))


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s[:60].rstrip("-")) or "job"


def validate(r) -> None:
    errs = []
    if not isinstance(r, dict):
        raise Refused("result must be a JSON object")
    if not str(r.get("job") or "").strip():
        errs.append("job: missing")
    answer = (r.get("our_system") or {}).get("answer")
    if answer not in ANSWERS:
        errs.append("our_system.answer: %r is not one of %s" % (answer, ", ".join(ANSWERS)))
    rec = r.get("recommendation")
    if not isinstance(rec, dict) or not str(rec.get("text") or "").strip():
        errs.append("recommendation.text: missing")
    for i, st in enumerate(r.get("flow") or []):
        if st.get("chip") not in CHIP_LABEL:
            errs.append("flow[%d].chip: %r is not one of %s"
                        % (i, st.get("chip"), ", ".join(CHIP_LABEL)))
    shelves = dict(SHELVES)
    for i, o in enumerate(r.get("outside") or []):
        if o.get("shelf") not in shelves:
            errs.append("outside[%d].shelf: %r is not one of %s"
                        % (i, o.get("shelf"), ", ".join(shelves)))
        if o.get("trust_tier") not in TRUST_TIERS:
            errs.append("outside[%d].trust_tier: %r is not one of %s"
                        % (i, o.get("trust_tier"), ", ".join(TRUST_TIERS)))
    if sum(1 for o in (r.get("options") or []) if o.get("recommended")) > 1:
        errs.append("options: more than one row is marked recommended")
    errs.extend(sketch_errors(r.get("sketch")))
    if r.get("date") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(r["date"])):
        errs.append("date: %r is not YYYY-MM-DD" % r["date"])
    if errs:
        raise Refused("; ".join(errs))


def sketch_errors(sk) -> list:
    """Old form: a plain string (rendered as text). New form: an object (an iframe)."""
    if sk is None or isinstance(sk, str):
        return []
    if not isinstance(sk, dict):
        return ["sketch: must be an object (or the old plain string)"]
    errs = []
    if not str(sk.get("title") or "").strip():
        errs.append("sketch.title: missing")
    if sk.get("kind") not in SKETCH_KINDS:
        errs.append("sketch.kind: %r is not one of %s" % (sk.get("kind"), ", ".join(SKETCH_KINDS)))
    if sk.get("data") not in SKETCH_DATA:
        errs.append("sketch.data: %r is not one of %s" % (sk.get("data"), ", ".join(SKETCH_DATA)))
    body = sk.get("html")
    if not isinstance(body, str) or not body.strip():
        errs.append("sketch.html: missing")
    elif SKETCH_OUTBOUND.search(body) or (SKETCH_NET_API.search(body)
                                          and SKETCH_ANY_URL.search(body)):
        errs.append("sketch.html: loads or calls an outside URL — a sketch is "
                    "self-contained (inline CSS/JS only) and never calls a live system")
    return errs


def sketch_shown(r) -> bool:
    """An object sketch renders as its own section, except on "use it"."""
    return isinstance(r.get("sketch"), dict) and (r.get("our_system") or {}).get("answer") != "use"


# ---------- page ----------

def e(x) -> str:
    return html.escape("" if x is None else str(x))


def link(ref) -> str:
    ref = "" if ref is None else str(ref)
    if re.match(r"https?://", ref):
        return '<a href="%s">%s</a>' % (e(ref), e(ref))
    return "<code>%s</code>" % e(ref) if ref else ""


def chip(key) -> str:
    return '<span class="chip c-%s">%s</span>' % (e(key), e(CHIP_LABEL.get(key, key)))


def table(headers, rows, marked=None) -> str:
    if not rows:
        return '<p class="none">None.</p>'
    h = "".join("<th>%s</th>" % e(x) for x in headers)
    body = []
    for i, row in enumerate(rows):
        cls = ' class="rec"' if marked is not None and marked(i) else ""
        body.append("<tr%s>%s</tr>" % (cls, "".join("<td>%s</td>" % c for c in row)))
    return '<div class="tw"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (
        h, "".join(body))


CSS = """
:root{--bg:#f6f7f9;--panel:#fff;--fg:#15171c;--muted:#5c6170;--line:#dde0e6;--accent:#2450d8;
--exists:#0f7b4f;--adapt:#8a6a00;--build:#b4480f;--outside:#2450d8;--person:#7a3fb8;--open:#a12f3a;--rec:#e7f3ec}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#111318;--panel:#1a1d24;--fg:#e8eaef;
--muted:#9aa0ad;--line:#2c303a;--accent:#7f9dff;--exists:#4ccb8f;--adapt:#e0b94a;--build:#f08a52;--outside:#7f9dff;
--person:#c39af0;--open:#f07a85;--rec:#14301f;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#111318;--panel:#1a1d24;--fg:#e8eaef;--muted:#9aa0ad;--line:#2c303a;--accent:#7f9dff;
--exists:#4ccb8f;--adapt:#e0b94a;--build:#f08a52;--outside:#7f9dff;--person:#c39af0;--open:#f07a85;--rec:#14301f;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:920px;margin:0 auto;padding:32px 16px 64px}
header h1{font-size:1.6rem;margin:0 0 4px}header p{margin:0;color:var(--muted)}
section{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin-top:18px}
h2{font-size:1.1rem;margin:0 0 10px}h3{font-size:.95rem;margin:14px 0 6px;color:var(--muted)}
.big{font-size:1.1rem;font-weight:600}.muted,.none{color:var(--muted)}code{font-size:.88em}
a{color:var(--accent)}.tw{overflow-x:auto}table{border-collapse:collapse;width:100%}
th,td{text-align:left;vertical-align:top;padding:6px 8px;border-bottom:1px solid var(--line)}
th{font-size:.8rem;color:var(--muted);font-weight:600}tr.rec td{background:var(--rec)}
.chip{display:inline-block;font-size:.75rem;font-weight:600;padding:1px 8px;border-radius:999px;
border:1px solid currentColor;white-space:nowrap}
.c-exists{color:var(--exists)}.c-adapt{color:var(--adapt)}.c-build{color:var(--build)}
.c-outside{color:var(--outside)}.c-person{color:var(--person)}.c-open{color:var(--open)}
.tally{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px}
ol.flow{padding-left:22px}ol.flow li{margin:6px 0}
.ans{display:inline-block;font-weight:700;padding:2px 10px;border-radius:6px;border:1px solid var(--line)}
pre{white-space:pre-wrap;background:var(--bg);padding:10px;border-radius:6px}
.badge{display:inline-block;font-size:.75rem;font-weight:700;padding:1px 8px;border-radius:6px;
border:1px solid currentColor;margin-left:6px;vertical-align:middle}
.b-real{color:var(--exists)}.b-example{color:var(--build);background:var(--bg)}
iframe.sketch{display:block;width:100%;height:480px;border:1px solid var(--line);border-radius:8px;
background:#fff;margin-top:8px}
"""


def render(r: dict, saved_at: str) -> str:
    os_ = r.get("our_system") or {}
    answer = os_.get("answer")
    rec = r.get("recommendation") or {}
    outside = r.get("outside") or []
    options = r.get("options") or []
    flow = r.get("flow") or []
    parts = r.get("parts") or []
    have = r.get("parts_we_have") or []
    matches = os_.get("matches") or []
    s = {}

    s["recommendation"] = (
        '<p class="big">%s</p><p>Confidence: <b>%s</b> · Our system: <span class="ans">%s</span></p>'
        '<p><b>What would change it:</b> %s</p>' % (
            e(rec.get("text")), e(rec.get("confidence") or "not stated"),
            e(ANSWERS[answer]), e(rec.get("would_change_it") or "not stated")))
    if isinstance(r.get("sketch"), str) and r["sketch"]:  # the old plain-text form
        s["recommendation"] += "<h3>Sketch</h3><pre>%s</pre>" % e(r["sketch"])

    by_shelf = {k: sum(1 for o in outside if o.get("shelf") == k) for k, _ in SHELVES}
    picked = [o.get("name") for o in options if o.get("recommended")]
    step2 = ("Skipped: our system answered “use it”." if answer == "use" else
             " · ".join("%s: %d" % (lbl, by_shelf[k]) for k, lbl in SHELVES))
    s["steps"] = "<ol>%s</ol>" % "".join("<li><b>%s</b> %s</li>" % (a, b) for a, b in [
        ("Our system.", "Job split into %d part(s); whole job: %s; %d match(es); %d part(s) we have."
         % (len(parts), e(ANSWERS[answer]), len(matches), len(have))),
        ("Outside.", e(step2)),
        ("Weigh the options.", "%d option(s); recommended: %s." % (
            len(options), e(picked[0]) if picked else "none marked")),
        ("Make it visual.", "This page."),
        ("Save it.", "<code>%s</code>" % e(saved_at)),
    ])

    tally = "".join('<span>%s %d</span>' % (chip(k), sum(1 for f in flow if f.get("chip") == k))
                    for k, _ in CHIPS)
    steps = "".join('<li>%s <b>%s</b> — %s%s</li>' % (
        chip(f.get("chip")), e(f.get("step")), e(f.get("who_or_what")),
        (' · part: %s' % e(f["part"])) if f.get("part") else "") for f in flow)
    s["flow"] = ('<div class="tally">%s</div><ol class="flow">%s</ol>' % (tally, steps)
                 if flow else '<p class="none">No flow given.</p>')

    if sketch_shown(r):
        sk = r["sketch"]
        s["sketch"] = (
            '<h3>%s<span class="badge b-%s">%s</span> <span class="muted">· %s</span></h3>%s'
            '<iframe class="sketch" sandbox="allow-scripts" title="%s" srcdoc="%s"></iframe>' % (
                e(sk["title"]), e(sk["data"]), e(SKETCH_DATA[sk["data"]]), e(sk["kind"]),
                ('<p class="muted">%s</p>' % e(sk["note"])) if sk.get("note") else "",
                e(sk["title"]), e(sk["html"])))

    s["our-system"] = ('<p>Whole job: <span class="ans">%s</span></p>' % e(ANSWERS[answer])
                       + table(["Name", "Path", "What it does", "Note"],
                               [[e(m.get("name")), link(m.get("path")), e(m.get("what")),
                                 e(m.get("note"))] for m in matches]))
    s["parts"] = (("<p class=\"muted\">Parts: %s</p>" % e(" · ".join(parts)) if parts else "")
                  + table(["Part", "We have", "Path", "Note"],
                          [[e(p.get("part")), e(p.get("name")), link(p.get("path")),
                            e(p.get("note"))] for p in have]))

    if answer == "use" and not outside:
        s["outside"] = '<p class="none">Not searched: our system answered “use it”.</p>'
    else:
        s["outside"] = "".join(
            "<h3>%s</h3>%s" % (e(lbl), table(["Name", "Trust tier", "Link", "Notes"], [
                [e(o.get("name")), e(o.get("trust_tier")), link(o.get("url")), e(o.get("notes"))]
                for o in outside if o.get("shelf") == k])) for k, lbl in SHELVES)

    s["options"] = table(
        ["", "Option", "Fit", "Cost", "Time to first result", "Needs from us", "Maintainer"],
        [["★ recommended" if o.get("recommended") else "", e(o.get("name")), e(o.get("fit")),
          e(o.get("cost")), e(o.get("time")), e(o.get("needs")), e(o.get("maintainer"))]
         for o in options],
        marked=lambda i: bool(options[i].get("recommended")))

    helps = r.get("could_also_help") or []
    s["also-helps"] = table(["Option", "Other work it would help"], [
        [e(h.get("option")), e(h.get("work"))] if isinstance(h, dict) else ["", e(h)]
        for h in helps])
    s["trial"] = "<p>%s</p>" % e(rec.get("trial") or "not stated")
    srcs = r.get("sources") or []
    s["sources"] = ("<ul>%s</ul>" % "".join(
        "<li>%s %s</li>" % (e(x.get("label")), link(x.get("ref"))) if isinstance(x, dict)
        else "<li>%s</li>" % link(x) for x in srcs)) if srcs else '<p class="none">None.</p>'

    body = "".join('<section id="%s"><h2>%s</h2>%s</section>' % (sid, e(h), s[sid])
                   for sid, h in SECTIONS if sid in s)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            "<title>System research</title><style>%s</style></head><body><main>"
            "<header><h1>%s</h1><p>System research · %s</p></header>%s</main></body></html>\n"
            % (CSS, e(r.get("job")), e(r.get("date")), body))


# ---------- files ----------

def write(result: dict, out_root: Optional[Path] = None, date: Optional[str] = None):
    """Validate, then write <out_root>/<date>-<slug>/result.json + page.html.
    Returns (folder, json_path, page_path)."""
    validate(result)
    r = dict(result)
    r["date"] = date or r.get("date") or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    validate(r)
    if isinstance(r.get("sketch"), dict) and not sketch_shown(r):
        print("note: sketch not rendered — our system answered “use it”, and a sketch "
              "is skipped then (kept in result.json)", file=sys.stderr)
    r["slug"] = slugify(r.get("slug") or r["job"])
    root = Path(out_root) if out_root else repo_root() / "runs" / "system-research"
    base = "%s-%s" % (r["date"], r["slug"])
    folder, n = root / base, 1
    while folder.exists():
        n += 1
        folder = root / ("%s-%d" % (base, n))
    folder.mkdir(parents=True)
    jp, pp = folder / "result.json", folder / "page.html"
    jp.write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        shown = str(folder.relative_to(repo_root()))
    except (ValueError, FileNotFoundError):
        shown = str(folder)
    pp.write_text(render(r, shown), encoding="utf-8")
    return folder, jp, pp


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Write a system-research result folder.")
    ap.add_argument("result", help="the result JSON (schema: SKILL.md)")
    ap.add_argument("--out-root", help="folder receiving <date>-<slug>/ "
                    "(default: <workspace>/runs/system-research)")
    ap.add_argument("--date", help="YYYY-MM-DD (default: the result's date, else today UTC)")
    a = ap.parse_args(argv)
    try:
        result = json.loads(Path(a.result).read_text(encoding="utf-8"))
        _, jp, pp = write(result, a.out_root, a.date)
    except Refused as x:
        print("refused: %s" % x, file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError) as x:
        print("error: %s" % x, file=sys.stderr)
        return 1
    print(jp)
    print(pp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
