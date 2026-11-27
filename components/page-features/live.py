#!/usr/bin/env python3
"""PF-7 (working versions): a person's page is live or a draft, and the folder
says which (developer's page rulings, 2026-10-21, relayed by the lead).

    platform/views/viewers/<p>/drafts/<family>--<name>.html   a draft, with its
        <family>--<name>.changes.jsonl beside it (the overlay, the badges and
        the personal-view strip are on it)
    platform/views/viewers/<p>/<family>.html                   THE live page,
        one per person per family: no sidebar, no badges, no overlay code, no
        personal-view strip, no demo banner; data-feature attributes stay

There is no mode file: "at most one live version" holds by path. Live is never
edited directly (features.change() refuses a live page); a change makes a
draft first. Going live = check_live(), then transform() of the draft, then:
the old live (if any) moves to drafts/<family>--<UTC date>.html, the live
form is written, the draft's change lines are appended to the live log
<p>/<family>.changes.jsonl, and one line goes to <p>/<family>.live.jsonl
(went-live time and base, read by PF-8 (show my pages); since PF-19 (behind
notice) also "actions", the blob of the family's actions.json then, read by
stale_actions() on every click: changed since → the page's direct buttons copy
a request for Claude until it is caught up or made live again). A failing check
moves and writes nothing and lists the failures by number, each starting
with the feature tag (D16: …) or "page:".

A PREPARED page is a live-path page whose <head> carries PREPARED_META
(PF-9 (share check)'s /page-share writes it); first_open() reruns the live-form
checks on this machine and removes the mark.

First target run-detail, DATA ONLY: no router and no act() door is built or
called here (PF-4 (page starter kit)); a wired action on the page with no run
entry fails the check. PF-15 (direct by default): every wired action of the
family needs a run entry in _templates/<family>.actions.json — `direct` with a
kind (quick, job, confirm-job, external) or `via_claude` with a written why —
else a failure by number; a page's act.js block (kit/act.js, between ACT_START
and ACT_END) must equal its family template's. Stdlib only, Python 3.9. Git only through the runner (features.run_git
by default), and only git add / commit / push of exactly the paths written.
"""
import datetime
import hashlib
import json
import os
import re
import sys
import tempfile
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import features  # noqa: E402  PF-1 (page-features skeleton), same component
import check  # noqa: E402  PF-3 (feature check), same component

OVERLAY_START = "<!-- page-features overlay: component-owned, do not edit -->"
OVERLAY_END = "<!-- end page-features overlay -->"
# PF-15 (direct by default): kit/act.js, carried whole by a page between these markers, the way the overlay is.
ACT_START = "<!-- page-features act.js: component-owned, do not edit -->"
ACT_END = "<!-- end page-features act.js -->"
RUN_KINDS = ["quick", "job", "confirm-job", "external"]
RUN_TABLES = ["direct", "via_claude"]
NO_RUN_ENTRY = ("wired button with no run entry — add it to %s.actions.json direct, "
                "or via: claude with why")
DEMO_START = "<!-- demo stand-in -->"
DEMO_END = "<!-- end demo stand-in -->"
PREPARED_META = '<meta name="page-state" content="prepared">'

OUTCOMES = ["done", "failed", "held", "refused", "running"]
RUN_PLACEHOLDER = "<run>"
FEATURE_ATTR = 'data-feature="'
# ov-prefs' ACCENT table (run-detail--demo.html, the ov-prefs script).
ACCENT = {"blue": "#3b6fd8", "green": "#2f8a57", "plum": "#8a4fb8", "rust": "#b5532a"}
LIVE_RE = re.compile(r"^%s/([^/]+)/(%s)\.html$" % (features.VIEWERS, features.SLUG))
FO_ANY_RE = re.compile(
    r'<script\b[^>]*\bid="fo-(?:features|prefs)"[^>]*>.*?</script>', re.S)
FO_PREFS_RE = re.compile(r'<script\b[^>]*\bid="fo-prefs"[^>]*>(.*?)</script>', re.S)
PV_OPEN_RE = re.compile(r"<([a-zA-Z][\w-]*)\b[^>]*\sdata-personal-view\b[^>]*>")
PAGE_PREFS_RE = re.compile(r'<style id="page-prefs">.*?</style>\n?', re.S)
SHA_RE = re.compile(r'data-template-sha="([0-9a-f]{40})"')
DEMO_TEXT_RE = re.compile(r"Demo:|DEMO:|\bid\s*=\s*[\"']demo-")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
LIVE_KINDS = ["live", "first-open"]
# PF-19 (behind notice): "actions", the blob of _templates/<family>.actions.json at going live (null when the
# family keeps none); optional, so a line written before it stays valid.
LIVE_KEYS = ["kind", "at", "by", "from", "base", "old", "changes", "actions"]
LIVE_OPTIONAL = ["actions"]
STALE_ACTIONS = ("this page's buttons changed in the team version after it went live (%s), so it copies a "
                 "request for Claude instead — say 'catch up my %s page', or make it live again")
NOTE_COVERAGE = "coverage not checked: PF-3b (coverage and anchors)"
NOTE_DATA = ("the data stays embedded (const DATA): PF-4 (page starter kit)'s "
             "live reader is not on main")


# --- paths ------------------------------------------------------------------

def live_path(draft_rel):
    """platform/views/viewers/<p>/drafts/<family>--<name>.html →
    platform/views/viewers/<p>/<family>.html; ValueError for any other path."""
    match = features.DRAFT_RE.match(draft_rel or "")
    if not match:
        raise ValueError("%r is not a draft page (%s/<person>/drafts/<family>--<name>.html)"
                         % (draft_rel, features.VIEWERS))
    return "%s/%s/%s.html" % (features.VIEWERS, match.group(1), match.group(2))


def _log_rel(page_rel):
    return page_rel[:-len(".html")] + ".changes.jsonl"


def _live_log_rel(person, family):
    return "%s/%s/%s.live.jsonl" % (features.VIEWERS, person, family)


# --- PF-19 (behind notice): the run table a live page went live with -------------

def blob_id(path):
    """The git blob id of a file's bytes (what `git hash-object` names it with no filters), None when it cannot
    be read. No git: the page server asks it on every click."""
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError:
        return None
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def actions_blob(family, root):
    """blob_id of _templates/<family>.actions.json; None when the family keeps none."""
    return blob_id(os.path.join(root, features.TEMPLATES, "%s.actions.json" % family))


def last_live(person, family, root):
    """The last valid line of <p>/<family>.live.jsonl as an object, or None."""
    path = os.path.join(root, _live_log_rel(person, family))
    if not os.path.isfile(path):
        return None
    try:
        lines = features.read_changes(path)
    except features.LoadError:
        return None
    for line in reversed(lines):
        if not validate_live_log([line]):
            return json.loads(line)
    return None


def stale_actions(page_rel, root):
    """Why a live page's direct buttons fall back to copying a request, or None: its family's actions.json has
    changed since the page went live (the "actions" its last live.jsonl line recorded). `page_rel` is under
    platform/views/viewers/ (<p>/<family>.html, the page server's own form) or the repo-relative path. A draft, a
    template, or a line from before PF-19 (behind notice) recorded nothing: None, the buttons stay direct."""
    rel = (page_rel or "").replace("\\", "/")
    if not rel.startswith(features.VIEWERS + "/"):
        rel = "%s/%s" % (features.VIEWERS, rel)
    match = LIVE_RE.match(rel)
    if not match or match.group(1).startswith("_"):
        return None
    person, family = match.group(1), match.group(2)
    last = last_live(person, family, root)
    if not last or "actions" not in last:
        return None
    if last["actions"] == actions_blob(family, root):
        return None
    return STALE_ACTIONS % (last["at"][:10], family)


def _archive_rel(root, person, family, date):
    """drafts/<family>--<date>.html, or -2, -3 … when taken."""
    base = "%s/%s/drafts/%s--%s" % (features.VIEWERS, person, family, date)
    rel, i = base + ".html", 1
    while os.path.exists(os.path.join(root, rel)):
        i += 1
        rel = "%s-%d.html" % (base, i)
    return rel


# --- spans and the transform --------------------------------------------------

def _overlay_span(html):
    """(start, end) of OVERLAY_START … OVERLAY_END inclusive; None when the
    page carries neither marker; ValueError when they are not one pair."""
    return _marked_span(html, OVERLAY_START, OVERLAY_END, "overlay")


def _act_span(html):
    """PF-15 (direct by default): the act.js block, as _overlay_span."""
    return _marked_span(html, ACT_START, ACT_END, "act.js")


def _marked_span(html, start_marker, end_marker, what):
    starts, ends = html.count(start_marker), html.count(end_marker)
    if starts == 0 and ends == 0:
        return None
    start, end = html.find(start_marker), html.find(end_marker)
    if starts != 1 or ends != 1 or end < start:
        raise ValueError("the %s markers are not one pair (%d start, %d end)"
                         % (what, starts, ends))
    return start, end + len(end_marker)


def _demo_spans(html):
    spans, pos = [], 0
    while True:
        start = html.find(DEMO_START, pos)
        if start < 0:
            return spans
        end = html.find(DEMO_END, start + len(DEMO_START))
        if end < 0:
            raise ValueError("a demo stand-in starts with no end (%s)" % DEMO_END)
        spans.append((start, end + len(DEMO_END)))
        pos = end + len(DEMO_END)


def _inside(pos, spans):
    return any(s <= pos < e for s, e in spans)


def _element_end(html, name, after):
    """The end of the element whose start tag ends at `after`: its matching
    close tag, nested same-name tags counted; `after` when there is none."""
    depth = 1
    for match in re.finditer(r"<(/?)%s\b[^>]*>" % re.escape(name), html[after:], re.I):
        depth += -1 if match.group(1) else 1
        if depth == 0:
            return after + match.end()
    return after


def _removal_spans(html):
    """Every span the live form drops: the overlay block, the fo-features and
    fo-prefs blocks, each element carrying data-personal-view, each marked
    demo stand-in. Merged, in order. ValueError as _overlay_span/_demo_spans."""
    spans = []
    overlay = _overlay_span(html)
    if overlay:
        spans.append(overlay)
    for match in FO_ANY_RE.finditer(html):
        if not _inside(match.start(), spans):
            spans.append((match.start(), match.end()))
    for match in PV_OPEN_RE.finditer(html):
        if not _inside(match.start(), spans):
            spans.append((match.start(), _element_end(html, match.group(1), match.end())))
    spans.extend(_demo_spans(html))
    # A span that fills its own line takes the line's newline with it.
    grown = []
    for start, end in spans:
        if (start == 0 or html[start - 1] == "\n") and end < len(html) and html[end] == "\n":
            end += 1
        grown.append((start, end))
    merged = []
    for start, end in sorted(grown):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def _json_block(html, regex):
    match = regex.search(html)
    if not match:
        return {}
    try:
        value = json.loads(match.group(1))
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def page_prefs(html):
    """The page's own fo-prefs object ({} when absent or not JSON)."""
    return _json_block(html, FO_PREFS_RE)


def _catalog(html):
    match = features.FO_BLOCK_RE.search(html)
    if not match:
        return {}
    try:
        value = json.loads(match.group(2))
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def bake_css(catalog, prefs):
    """The CSS ov-prefs applies at load, as one string: hidden (unless the
    number's `locked` holds "hidden"), order first/last, text_size
    large/small, and the "accent" setting of the number that owns it. Labels
    and pinned are overlay-only and dropped."""
    wanted = prefs.get("features") if isinstance(prefs, dict) else None
    if not isinstance(wanted, dict) or not wanted:
        return ""
    by_n = {}
    for entry in catalog.get("features") or []:
        if isinstance(entry, dict) and features._is_int(entry.get("n")):
            by_n[entry["n"]] = entry
    css = ""
    for key, setting in wanted.items():
        try:
            n = int(key)
        except (TypeError, ValueError):
            continue
        if n not in by_n or not isinstance(setting, dict):
            continue
        sel = '[data-feature="%d"]' % n
        if setting.get("hidden") is True and "hidden" not in (by_n[n].get("locked") or []):
            css += sel + "{display:none!important}"
        if setting.get("order") == "first":
            css += sel + "{order:-1}"
        elif setting.get("order") == "last":
            css += sel + "{order:99}"
        if setting.get("text_size") == "large":
            css += sel + "{font-size:1.22em}"
        elif setting.get("text_size") == "small":
            css += sel + "{font-size:.88em}"
    owner = next((n for n in sorted(by_n) if "accent" in (by_n[n].get("owns") or [])), None)
    if owner is not None:
        held = wanted.get(str(owner))
        accent = held.get("accent") if isinstance(held, dict) else None
        if isinstance(accent, str) and accent in ACCENT:
            css += ":root{--accent:%s!important}" % ACCENT[accent]
    return css


def transform(html, prefs=None):
    """The draft's live form. Removes the overlay block (OVERLAY_START …
    OVERLAY_END), the fo-features and fo-prefs blocks, the personal-view
    strip and every marked demo stand-in; keeps every data-feature
    attribute, the page's own scripts, its embedded data and its .assets
    references. `prefs` (default: the page's own fo-prefs) is baked into ONE
    <style id="page-prefs"> before </head>. ValueError when the overlay
    markers are not one pair or a demo stand-in has no end. A page with no
    overlay marker at all is treated as already transformed, so
    transform(transform(x)) == transform(x)."""
    if prefs is None:
        prefs = page_prefs(html)
    css = bake_css(_catalog(html), prefs)
    out, pos = [], 0
    for start, end in _removal_spans(html):
        out.append(html[pos:start])
        pos = end
    out.append(html[pos:])
    text = "".join(out)
    if css:
        style = '<style id="page-prefs">%s</style>\n' % css
        if PAGE_PREFS_RE.search(text):
            text = PAGE_PREFS_RE.sub(lambda m: style, text, count=1)
        else:
            at = text.find("</head>")
            text = text[:at] + style + text[at:] if at >= 0 else style + text
    return text


# --- the data check -------------------------------------------------------------

def _empty(value):
    return value is None or value == "" or value == [] or value == {}


def classify(doc, field):
    """found · empty (null, "", [] or {}) · absent (a segment missing) for one
    data file. An x[] segment walks every item; a null on the way is empty.
    check._in_data is not enough: it calls [] found for a field without []."""
    values = [doc]
    for name, is_list in check._segments(field):
        nxt, saw_empty = [], False
        for value in values:
            if value is None:
                saw_empty = True
                continue
            if not isinstance(value, dict) or name not in value:
                continue
            item = value[name]
            if is_list:
                if isinstance(item, list):
                    saw_empty = saw_empty or not item
                    nxt.extend(item)
                elif item is None:
                    saw_empty = True
            else:
                nxt.append(item)
        if not nxt:
            return "empty" if saw_empty else "absent"
        values = nxt
    return "found" if any(not _empty(v) for v in values) else "empty"


def _outcome(doc):
    result = doc.get("result") if isinstance(doc, dict) else None
    status = result.get("status") if isinstance(result, dict) else None
    return status if isinstance(status, str) and status else "unknown"


def _ordered(groups):
    return [o for o in OUTCOMES if o in groups] + sorted(o for o in groups if o not in OUTCOMES)


def data_check_live(doc, root):
    """(failures, notes). Each critical feature's fields on the REAL files:
    a <run> part's files are grouped by result.status and every file is read;
    a field absent in any file of an outcome, or empty in every file of an
    outcome, fails. Every wired rule's JSON fields must be present (empty
    allowed) in every file. A part with no <run> must resolve "found"
    (critical) or not "absent" (rule). A non-JSON part, an outcome with no
    file, and a rule with no JSON source are notes."""
    failures, notes = [], []

    def note(text):
        if text not in notes:
            notes.append(text)

    files = check.Files(root)
    for entry in doc.get("features") or []:
        if not isinstance(entry, dict):
            continue
        critical = entry.get("critical") is True
        rule = entry.get("kind") == "rule" and entry.get("state") == "wired"
        if not (critical or rule):
            continue
        t = check.tag(entry)
        source = entry.get("source")
        if not (isinstance(source, dict) and features._nonempty_str(source.get("file"))
                and features._nonempty_str(source.get("field"))):
            note("%s: page-only rule, not checked in data" % t if rule
                 else "%s: no data source, not checked in data" % t)
            continue
        pairs = check.split_source(source)
        if rule and not critical and not any(p.endswith(".json") for ps, _ in pairs for p in ps):
            note("%s: page-only rule, not checked in data" % t)
            continue
        for parts, fields in pairs:
            for part in parts:
                if not part.endswith(".json"):
                    note("%s: %s is not JSON, not checked in data" % (t, part))
                    continue
                hits = files.glob(part)
                if not hits:
                    failures.append("%s: %s matches no file" % (t, part))
                    continue
                good = []
                for field in fields:
                    if check.FIELD_RE.match(field):
                        good.append(field)
                    else:
                        note("%s: unparsed field text %r, not checked" % (t, field))
                if RUN_PLACEHOLDER not in part:
                    for field in good:
                        result = check.resolve(files, hits, field)
                        if critical and result != "found":
                            failures.append("%s: %s is %s in %s" % (t, field, result, part))
                        elif not critical and result == "absent":
                            failures.append("%s: %s missing in %s" % (t, field, part))
                    continue
                groups = {}
                for path in hits:
                    loaded = files.load(path)
                    if loaded is check.Files.BAD:
                        note("%s is not valid JSON, skipped" % features._relpath(path, root))
                        continue
                    groups.setdefault(_outcome(loaded), []).append(loaded)
                for outcome in OUTCOMES:
                    if outcome not in groups:
                        note("%s: no run to sample (%s)" % (outcome, part))
                for field in good:
                    for outcome in _ordered(groups):
                        found = [classify(d, field) for d in groups[outcome]]
                        absent = found.count("absent")
                        if absent:
                            failures.append("%s: %s missing on %d of %d %s runs"
                                            % (t, field, absent, len(found), outcome))
                        elif critical and found.count("empty") == len(found):
                            failures.append("%s: %s empty on every %s run (%d)"
                                            % (t, field, outcome, len(found)))
    return failures, notes


# --- the page checks --------------------------------------------------------------

class _Attrs(HTMLParser):
    """Element ids and whether any element carries data-personal-view."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.ids = []
        self.personal_view = False

    def handle_starttag(self, name, attrs):
        for key, value in attrs:
            if key == "id" and value:
                self.ids.append(value.strip())
            elif key == "data-personal-view":
                self.personal_view = True

    def handle_startendtag(self, name, attrs):
        self.handle_starttag(name, attrs)


def _tagged(doc, finding):
    """A validate() finding with the feature tag first ("feature 16: …" →
    "D16: …"), else under "page: the family list …"."""
    match = re.match(r"^feature (\d+): (.*)$", finding, re.S)
    if match:
        n = int(match.group(1))
        for entry in doc.get("features") or []:
            if isinstance(entry, dict) and entry.get("n") == n:
                return "%s: %s" % (check.tag(entry), match.group(2))
    return "page: the family list — %s" % finding


def run_table(family, root):
    """PF-15 (direct by default): the family's run table from
    _templates/<family>.actions.json, {"<n>": (table name, entry)} over
    RUN_TABLES; None when the family keeps no actions file. ValueError when it
    is not JSON or a table is not an object."""
    path = os.path.join(root, features.TEMPLATES, "%s.actions.json" % family)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        doc = json.load(handle)
    if not isinstance(doc, dict):
        raise ValueError("%s.actions.json is not a JSON object" % family)
    table = {}
    for name in RUN_TABLES:
        part = doc.get(name, {})
        if not isinstance(part, dict):
            raise ValueError("%s.actions.json %s is not an object" % (family, name))
        for n, entry in part.items():
            table.setdefault(str(n), []).append((name, entry))
    return table


def _run_problem(family, found):
    """What is wrong with one wired action's run entries, in words; None when complete."""
    if not found:
        return NO_RUN_ENTRY % family
    if len(found) > 1:
        return "run entries in both %s — keep one" % " and ".join(name for name, _ in found)
    name, entry = found[0]
    if not isinstance(entry, dict):
        return "its run entry in %s.actions.json %s is not an object" % (family, name)
    via = entry.get("via")
    if via is not None or name == "via_claude":
        if via != "claude":
            return "a via_claude entry says via: claude (not %r)" % (via,)
        if not features._nonempty_str(entry.get("why")):
            return ("via: claude with no why — write why it is not direct in "
                    "%s.actions.json" % family)
        return None
    if entry.get("kind") not in RUN_KINDS:
        return ("its run entry has no kind (%s) — add it in %s.actions.json direct"
                % (", ".join(RUN_KINDS), family))
    return None


def run_entry_findings(doc, family, table):
    """[(entry, what)] for every wired action of the family list whose run entry
    is missing or incomplete (PF-15 (direct by default)); `table` as run_table()."""
    out = []
    for entry in doc.get("features") or []:
        if not isinstance(entry, dict) or entry.get("kind") != "action" or entry.get("state") != "wired":
            continue
        what = _run_problem(family, (table or {}).get(str(entry.get("n")), []))
        if what:
            out.append((entry, what))
    return out


def _family_checks(doc, html, failures, family=None, root=None):
    """The family list validates; ANCHORS; ACTIONS. Returns False when the
    list is invalid (the anchors and the data are then not checked). With a
    family and a root, ACTIONS also holds every wired action to a complete run
    entry (PF-15 (direct by default)), and the router line is said only for one
    without."""
    findings = features.validate(doc)
    failures.extend(_tagged(doc, f) for f in findings)
    if findings:
        return False
    scan = check.scan_page(html)
    try:
        version = check.pick_version(doc, None)
    except check.Fatal as exc:
        failures.append("page: %s" % exc)
        version = None
    out = dict((name, []) for name in check.SECTIONS)
    check.page_check(doc, scan, version, out)
    for line in out["PAGE"]:
        failures.append("page: the " + line if line.startswith("page has ") else line)
    missing = set(e["n"] for e in doc["features"])   # no run table read: every wired action
    findings = []
    if family:
        try:
            findings = run_entry_findings(doc, family, run_table(family, root))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            failures.append("page: the run table — %s" % exc)
        else:
            missing = set(e["n"] for e, _ in findings)
    for entry in doc["features"]:
        if (entry["kind"] == "action" and entry["state"] == "wired"
                and str(entry["n"]) in scan.numbers and entry["n"] in missing):
            failures.append("%s: actions wait for PF-4 (page starter kit)'s router; "
                            "act(n) is not built" % check.tag(entry))
    failures.extend("%s: %s" % (check.tag(e), what) for e, what in findings)
    return True


def _demo_problems(html, skip):
    out = []
    for match in DEMO_TEXT_RE.finditer(html):
        if _inside(match.start(), skip):
            continue
        line = "page: unmarked demo stand-in (%s)" % html[match.start():match.start() + 40]
        if line not in out:
            out.append(line)
    return out


def _live_form_problems(text, expected=None):
    """The live form's own checks; `expected` is the data-feature count it
    must keep (None: not compared)."""
    out = []
    for marker in (OVERLAY_START, OVERLAY_END):
        if marker in text:
            out.append("page: the live form still carries %s" % marker)
    for marker in (DEMO_START, DEMO_END):
        if marker in text:
            out.append("page: the live form still carries a demo stand-in (%s)" % marker)
    scan = _Attrs()
    scan.feed(text)
    scan.close()
    for name in scan.ids:
        if name.startswith(("fo-", "ov-")):
            out.append("page: the live form still has the overlay element id=%r" % name)
        elif name.startswith("demo-"):
            out.append("page: the live form still has a demo element id=%r" % name)
    if scan.personal_view:
        out.append("page: the live form still has the personal-view strip "
                   "(data-personal-view)")
    for word in ("Demo:", "DEMO:"):
        if word in text:
            out.append("page: the live form still says %r" % word)
    kept = feature_count(text)
    if expected is not None and kept != expected:
        out.append("page: the live form has %d data-feature attributes, not %d"
                   % (kept, expected))
    return out


def feature_count(text):
    """The `data-feature="` occurrences outside the baked <style id="page-prefs">
    (its selectors name numbers; they are not attributes)."""
    return PAGE_PREFS_RE.sub("", text).count(FEATURE_ATTR)


def _read_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _setup(page, person, root, runner):
    root = os.path.abspath(root or features.ROOT)
    runner = runner or features.run_git
    person = features._person(person, root, runner)
    return root, runner, person, features._relpath(page, root)


def _check(draft, person, root, runner):
    """check_live's work, plus what go_live needs (the live form, the draft's
    log lines, the doc, the base)."""
    root, runner, person, rel = _setup(draft, person, root, runner)
    ctx = {"ok": False, "failures": [], "notes": [], "family": None, "draft": rel,
           "live": None, "refused": None, "unreadable": None, "root": root,
           "runner": runner, "person": person}
    if not person:
        ctx["refused"] = "no person — pass --person or set git config user.email"
        return ctx
    problem = features._draft_problem(rel, person)
    if problem:
        ctx["refused"] = problem
        return ctx
    family = features.DRAFT_RE.match(rel).group(2)
    ctx["family"], ctx["live"] = family, live_path(rel)
    list_rel = "%s/%s.features.json" % (features.TEMPLATES, family)
    tmpl_rel = "%s/%s.html" % (features.TEMPLATES, family)
    for need in (rel, list_rel, tmpl_rel):
        if not os.path.isfile(os.path.join(root, need)):
            ctx["refused"] = "%s does not exist" % need
            return ctx
    log_rel = _log_rel(rel)
    try:
        html = _read_text(os.path.join(root, rel))
        template = _read_text(os.path.join(root, tmpl_rel))
        doc = features.load(os.path.join(root, list_rel))
        lines = (features.read_changes(os.path.join(root, log_rel))
                 if os.path.isfile(os.path.join(root, log_rel)) else [])
    except (OSError, UnicodeDecodeError) as exc:
        ctx["unreadable"] = "UNREADABLE: %s" % exc
        return ctx
    except features.LoadError as exc:
        ctx["unreadable"] = str(exc)
        return ctx
    failures, notes = ctx["failures"], ctx["notes"]

    # ALWAYS: the family list, the anchors, the actions.
    valid = _family_checks(doc, html, failures, family, root)
    notes.append(NOTE_COVERAGE)
    # ALWAYS: the overlay untouched, against the family template.
    try:
        mine, theirs = _overlay_span(html), _overlay_span(template)
    except ValueError as exc:
        mine, theirs = None, None
        failures.append("page: %s" % exc)
    else:
        if mine is None:
            failures.append("page: the overlay block is missing (%s)" % OVERLAY_START)
        elif theirs is None:
            failures.append("page: %s carries no overlay block to compare" % tmpl_rel)
        elif html[mine[0]:mine[1]] != template[theirs[0]:theirs[1]]:
            failures.append("page: the overlay block was edited; it is component-owned")
    # ALWAYS: the act.js block (PF-15 (direct by default)) untouched, against the family template.
    try:
        act, act_tmpl = _act_span(html), _act_span(template)
    except ValueError as exc:
        failures.append("page: %s" % exc)
    else:
        if act is None and "pfAct(" in html:
            failures.append("page: the buttons call pfAct but the act.js block is missing (%s)"
                            % ACT_START)
        elif act is not None and (act_tmpl is None or
                                  html[act[0]:act[1]] != template[act_tmpl[0]:act_tmpl[1]]):
            failures.append("page: the act.js block was edited; it is component-owned")
    # ALWAYS: no unmarked demo stand-in outside the overlay and the marked spans.
    try:
        skip = ([mine] if mine else []) + _demo_spans(html)
    except ValueError as exc:
        failures.append("page: %s" % exc)
        skip = [mine] if mine else []
    failures.extend(_demo_problems(html, skip))
    # The draft's change lines must be valid live-log lines before anything moves.
    objs = []
    if valid:
        for finding in features.validate_changes(lines, doc):
            failures.append("page: %s %s" % (log_rel, finding))
        for line in lines:
            try:
                objs.append(json.loads(line))
            except ValueError:
                pass
    # DATA.
    if valid:
        found, data_notes = data_check_live(doc, root)
        failures.extend(found)
        notes.extend(data_notes)
    else:
        notes.append("anchors and data not checked: the family list is invalid")
    # LIVE FORM.
    text = None
    try:
        spans = _removal_spans(html)
        text = transform(html)
    except ValueError as exc:
        failures.append("page: the live form cannot be made — %s" % exc)
    if text is not None:
        expected = html.count(FEATURE_ATTR) - sum(html[s:e].count(FEATURE_ATTR)
                                                  for s, e in spans)
        failures.extend(_live_form_problems(text, expected))
        if "const DATA" in text:
            notes.append(NOTE_DATA)
        refs = text.count("%s.assets/" % family)
        notes.append("%d %s.assets picture reference%s kept; Drive-id loads wait for "
                     "PF-4 (page starter kit) + LD-64 (records Drive ids)"
                     % (refs, family, "" if refs == 1 else "s"))
    sha = SHA_RE.search(html)
    ctx.update(ok=not failures, text=text, objs=objs, base=sha.group(1) if sha else None)
    return ctx


def check_live(draft, *, person=None, root=None, runner=None):
    """Is this draft ready to go live? {"ok", "failures", "notes", "family",
    "draft", "live"}, plus "refused" (not the person's draft, or a file
    missing: no check run) and "unreadable" (a file that cannot be read)."""
    ctx = _check(draft, person, root, runner)
    return dict((k, ctx[k]) for k in ("ok", "failures", "notes", "family", "draft",
                                      "live", "refused", "unreadable"))


# --- writing --------------------------------------------------------------------

def _stamp(now):
    stamp = now or datetime.datetime.now(datetime.timezone.utc)
    if not isinstance(stamp, str):
        stamp = stamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    return stamp, stamp[:10]


def _write_atomic(path, text):
    handle, temp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".live-", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            out.write(text)
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.remove(temp)
        raise


def _append(path, text):
    lead = ""
    if os.path.isfile(path) and os.path.getsize(path):
        with open(path, encoding="utf-8") as handle:
            lead = "" if handle.read().endswith("\n") else "\n"
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(lead + text if text else "")


def _parsed(path):
    if not os.path.isfile(path):
        return []
    out = []
    for line in features.read_changes(path):
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def _shared(paths, message, root, runner, share):
    if not share:
        return "not shared"
    error = features._share(paths, message, root, runner)
    return "shared" if error is None else "not shared: %s" % error


def _refused(why):
    return {"result": "refused", "lines": ["refused: %s" % why], "written": [], "shared": ""}


def _not_live(failures):
    return {"result": "not live",
            "lines": ["not live: %d failure%s" % (len(failures), "" if len(failures) == 1 else "s")]
            + list(failures), "written": [], "shared": ""}


def go_live(draft, *, person=None, root=None, runner=None, now=None, share=True):
    """check_live, then — only when it passes — (i) the old live page (if
    any) moves to drafts/<family>--<UTC date>.html, (ii) the live form is
    written to <p>/<family>.html, (iii) the draft's change lines not already
    in <p>/<family>.changes.jsonl are appended to it, (iv) one "live" line
    goes to <p>/<family>.live.jsonl, (v) exactly those paths are shared.
    The draft and its log are never touched. A failing check changes
    nothing on disk."""
    ctx = _check(draft, person, root, runner)
    if ctx["refused"] or ctx["unreadable"]:
        return _refused(ctx["refused"] or ctx["unreadable"])
    if not ctx["ok"]:
        return _not_live(ctx["failures"])
    root, runner, person, family = ctx["root"], ctx["runner"], ctx["person"], ctx["family"]
    at, date = _stamp(now)
    live_rel = ctx["live"]
    log_rel = _log_rel(live_rel)
    record_rel = _live_log_rel(person, family)
    old = None
    if os.path.isfile(os.path.join(root, live_rel)):
        old = _archive_rel(root, person, family, date)
        os.replace(os.path.join(root, live_rel), os.path.join(root, old))
    _write_atomic(os.path.join(root, live_rel), ctx["text"])
    have = _parsed(os.path.join(root, log_rel))
    fresh = []
    for obj in ctx["objs"]:
        if obj not in have and obj not in fresh:
            fresh.append(obj)
    _append(os.path.join(root, log_rel), features.dumps_changes(fresh))
    record = {"kind": "live", "at": at, "by": person, "from": ctx["draft"],
              "base": ctx["base"], "old": old, "changes": len(fresh),
              "actions": actions_blob(family, root)}
    _append(os.path.join(root, record_rel), features.dumps_changes([record]))
    written = [live_rel, log_rel, record_rel] + ([old] if old else [])
    lines = ["live: %s · %s" % (live_rel, "old live kept at %s" % old if old else "first live"),
             "%d change line%s logged" % (len(fresh), "" if len(fresh) == 1 else "s")]
    lines.extend("note: %s" % n for n in ctx["notes"])
    return {"result": "live", "lines": lines, "written": written,
            "shared": _shared(written, "page: live %s (%s)" % (family, person),
                              root, runner, share)}


def _head(html):
    end = html.find("</head>")
    return html[:end] if end >= 0 else ""


def first_open(page, *, person=None, root=None, runner=None, now=None, share=True):
    """A PREPARED live page (PREPARED_META in its <head>) opened for the first
    time: rerun on this machine the checks that apply to a live-form page
    (the family list, ANCHORS, ACTIONS, DATA, LIVE FORM, on the page as it
    is). Pass → the mark is removed, one "first-open" line goes to
    <p>/<family>.live.jsonl, both are shared. No mark → "already live",
    nothing changes. Fail → "not live", nothing changes."""
    root, runner, person, rel = _setup(page, person, root, runner)
    if not person:
        return _refused("no person — pass --person or set git config user.email")
    match = LIVE_RE.match(rel)
    if not match or match.group(1) != person or match.group(1) == "_templates":
        return _refused("%s is not %s's live page (%s/%s/<family>.html)"
                        % (rel, person, features.VIEWERS, person))
    family = match.group(2)
    list_rel = "%s/%s.features.json" % (features.TEMPLATES, family)
    for need in (rel, list_rel):
        if not os.path.isfile(os.path.join(root, need)):
            return _refused("%s does not exist" % need)
    try:
        html = _read_text(os.path.join(root, rel))
        doc = features.load(os.path.join(root, list_rel))
    except (OSError, UnicodeDecodeError) as exc:
        return _refused("UNREADABLE: %s" % exc)
    except features.LoadError as exc:
        return _refused(str(exc))
    if PREPARED_META not in _head(html):
        return {"result": "already live", "lines": ["already live: %s (not prepared)" % rel],
                "written": [], "shared": ""}
    failures, notes = [], []
    if _family_checks(doc, html, failures, family, root):
        found, notes = data_check_live(doc, root)
        failures.extend(found)
    failures.extend(_live_form_problems(html))
    if failures:
        return _not_live(failures)
    at, _ = _stamp(now)
    cut = html.replace(PREPARED_META + "\n", "", 1) if (PREPARED_META + "\n") in _head(html) \
        else html.replace(PREPARED_META, "", 1)
    _write_atomic(os.path.join(root, rel), cut)
    record_rel = _live_log_rel(person, family)
    sha = SHA_RE.search(html)
    record = {"kind": "first-open", "at": at, "by": person, "from": rel,
              "base": sha.group(1) if sha else None, "old": None, "changes": 0,
              "actions": actions_blob(family, root)}
    _append(os.path.join(root, record_rel), features.dumps_changes([record]))
    written = [rel, record_rel]
    lines = ["live: %s · first open checked on this machine" % rel]
    lines.extend("note: %s" % n for n in [NOTE_COVERAGE] + notes)
    return {"result": "live", "lines": lines, "written": written,
            "shared": _shared(written, "page: first open %s (%s)" % (family, person),
                              root, runner, share)}


def validate_live_log(lines):
    """Every defect in a <p>/<family>.live.jsonl, named "line 2: …". `lines`
    are str (parsed here) or objects."""
    out = []
    for i, line in enumerate(lines, 1):
        name = "line %d" % i
        if isinstance(line, str):
            try:
                line = json.loads(line)
            except ValueError as exc:
                out.append("%s: not JSON — %s" % (name, exc))
                continue
        if not isinstance(line, dict):
            out.append("%s: not an object" % name)
            continue
        out.extend(features._unknown_keys(line, LIVE_KEYS, name))
        for key in LIVE_KEYS:
            if key not in line and key not in LIVE_OPTIONAL:
                out.append("%s: `%s` is missing" % (name, key))
        if "kind" in line and line["kind"] not in LIVE_KINDS:
            out.append("%s: kind %r is not one of %s" % (name, line["kind"], " | ".join(LIVE_KINDS)))
        if "at" in line and not (isinstance(line["at"], str) and features.AT_RE.match(line["at"])):
            out.append("%s: at %r is not a UTC time" % (name, line["at"]))
        if "by" in line and not features._nonempty_str(line["by"]):
            out.append("%s: `by` is empty or not a string" % name)
        for key in ("from", "old"):
            if key in line and not (line[key] is None or isinstance(line[key], str)):
                out.append("%s: `%s` is neither a string nor null" % (name, key))
        for key in ("base", "actions"):
            if key in line and not (line[key] is None or (
                    isinstance(line[key], str) and SHA40_RE.match(line[key]))):
                out.append("%s: %s %r is neither a 40-hex sha nor null" % (name, key, line[key]))
        if "changes" in line and not (features._is_int(line["changes"]) and line["changes"] >= 0):
            out.append("%s: changes %r is not an integer >= 0" % (name, line["changes"]))
    return out
