#!/usr/bin/env python3
"""The draft verb (/page-draft): make a NEW draft of a page family, from the
family template or from the person's OWN live page, and share it.

    python3 features.py draft <family | page path> [--live] [--name N]
            [--person P] [--no-share]
        exit 0 the draft was made (shared or not) · 2 refused or a bad argument

    <family>                  the family template, _templates/<family>.html
    <family> --live           the person's own live page, <p>/<family>.html
    a path                    _templates/<family>.html or <p>/<family>.html;
                              another person's live page and any draft are
                              refused (developer's page rulings, 2026-10-21: drafts
                              come only from your own live page or the template)

Writes exactly two new files, never overwriting either:
    platform/views/viewers/<p>/drafts/<family>--<name>.html
    platform/views/viewers/<p>/drafts/<family>--<name>.changes.jsonl  (empty)
then git add / commit / push of exactly those two paths (features._share,
the way `change` does). <name> is --name, or today's UTC date as YYYYMMDD
(-2, -3 … when taken); the compact form keeps it apart from the dated
drafts going live leaves behind (<family>--YYYY-MM-DD, "old live" in PF-8
(show my pages)). An explicit name already taken is refused.

The base stamp is PV-1 (personal-view skill)'s, by its public functions:
a template draft is personal_view.personal_text(template, family,
blob_sha(template)) — byte for byte what the family's --demo drafts are. A
live page carries no strip (the live form drops it), so a draft of it gets
personal_view.banner(family, base) placed by place_strip, where base is the
template blob the live page was cut from (the last line of
<p>/<family>.live.jsonl); with no base recorded it gets no strip, and says so.

Stdlib only, Python 3.9. Git only through the runner (features.run_git by
default); a refusal writes nothing and runs no git beyond `config user.email`.

PF-19b (catch up), the mechanical half of "catch up my <family> page" (the
.claude/ skill on top replays each change's words through /page-change):

    python3 features.py catchup <family> [--person P] [--json] [--no-share]
    python3 features.py catchup <family> --status [--person P] [--json]
    python3 features.py catchup-mark <draft> <step> applied|skipped|needs-a-person
            [--why TEXT] [--person P] [--json] [--no-share]
        exit 0 made / marked / shown · 2 refused or a bad argument

catchup reads the person's live page, the newest line of its live.jsonl
(`from`, `base`) and the change log to replay — the live page's own
<family>.changes.jsonl when it has lines, else the `from` draft's — then makes
a NEW draft of today's template (make_draft, named catchup-<YYYYMMDD>, -2 …
when taken) and says which case it is:
    no changes        the log is empty and the live page is byte for byte what
                      going live made from its base template (live.transform of
                      that template's draft): "nothing to replay"
    changes to replay the log has lines: each is printed in order (step, n,
                      said, by, at) and written to the plan
                      drafts/<family>--catchup-<date>.catchup.json, state "todo";
                      a number gone from today's list, or whose anchor the old
                      page carried and today's template does not, is "skipped"
                      with its why; a line naming no number "needs-a-person"
    hand edits        the log is empty and the live page differs (or its base
                      cannot be read): compare side by side, the differences
                      summarised; no merge is ever guessed
The live page, its logs and every existing draft are never written. Plan
entries carry `state` (builder card rule 5: status words are draft / approved
/ deprecated only). catchup-mark records one step's outcome; "applied" needs a
change line for that number in the new draft's own log (/page-change wrote it),
kept as the entry's `replay`. Going live from a catch-up draft carries those
lines into the live log beside the ones they replayed, so a later catch-up
drops every line an earlier plan names as a `replay`: each change replays once.
"""
import argparse
import difflib
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import features  # noqa: E402  PF-1 (page-features skeleton), same component
import live  # noqa: E402  PF-7 (working versions), same component

PV_DIR = os.path.join(features.ROOT, "new-workflow-design", "builds", "personal-views")
PERSON_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
SLUG_RE = re.compile(r"^%s$" % features.SLUG)
TEMPLATE_RE = re.compile(r"^%s/(%s)\.html$" % (features.TEMPLATES, features.SLUG))
NOTE_NO_SIDEBAR = ("made from a live page, which carries no sidebar (the live form strips "
                   "it): the numbers stay on the page, but going live from this draft fails "
                   "the overlay check until the sidebar is back — restoring it is not built")


def _pv():
    """PV-1 (personal-view skill)'s engine, imported by its public functions."""
    if PV_DIR not in sys.path:
        sys.path.insert(0, PV_DIR)
    import personal_view
    return personal_view


def _refused(why):
    return {"result": "refused", "lines": ["refused: %s" % why], "written": [], "shared": ""}


def _resolve(source, from_live, person, root):
    """(family, source rel, "template" | "live") or (None, why, None)."""
    if SLUG_RE.match(source or "") and "/" not in source:
        family = source
        if from_live:
            return family, "%s/%s/%s.html" % (features.VIEWERS, person, family), "live"
        return family, "%s/%s.html" % (features.TEMPLATES, family), "template"
    rel = features._relpath(source, root)
    if rel.startswith("../") or rel == "..":
        return None, "%s is outside the workspace" % rel, None
    match = TEMPLATE_RE.match(rel)
    if match:
        if from_live:
            return None, "%s is the family template, not a live page; drop --live" % rel, None
        return match.group(1), rel, "template"
    if features.DRAFT_RE.match(rel):
        return None, ("%s is a draft; a draft is made from your own live page or the "
                      "family template" % rel), None
    match = live.LIVE_RE.match(rel)
    if match and match.group(1) != "_templates":
        if match.group(1) != person:
            return None, ("%s is %s's live page; a draft is made only from your own live "
                          "page or the family template" % (rel, match.group(1))), None
        return match.group(2), rel, "live"
    return None, ("%s is neither a family name, a family template (%s/<family>.html) nor "
                  "your live page (%s/%s/<family>.html)"
                  % (source, features.TEMPLATES, features.VIEWERS, person)), None


def _live_base(person, family, root):
    """The template blob the live page was cut from: `base` on the last valid
    line of <p>/<family>.live.jsonl, or None."""
    path = os.path.join(root, live._live_log_rel(person, family))
    if not os.path.isfile(path):
        return None
    try:
        lines = features.read_changes(path)
    except features.LoadError:
        return None
    for line in reversed(lines):
        if live.validate_live_log([line]):
            continue
        base = json.loads(line).get("base")
        if base:
            return base
    return None


def _target(root, person, family, name, date):
    """(html rel, log rel) or (None, why) — never a taken name."""
    def rels(n):
        base = "%s/%s/drafts/%s--%s" % (features.VIEWERS, person, family, n)
        return base + ".html", base + ".changes.jsonl"

    def taken(pair):
        return any(os.path.exists(os.path.join(root, r)) for r in pair)

    if name is not None:
        if not SLUG_RE.match(name):
            return None, ("name %r is not lowercase words joined by hyphens "
                          "(a-z, 0-9, -)" % name)
        pair = rels(name)
        if taken(pair):
            return None, "%s already exists; a draft is never overwritten — pick another name" % (
                pair[0] if os.path.exists(os.path.join(root, pair[0])) else pair[1])
        return pair, None
    pair, i = rels(date), 1
    while taken(pair):
        i += 1
        pair = rels("%s-%d" % (date, i))
    return pair, None


def make_draft(source, *, from_live=False, name=None, person=None, root=None, runner=None,
               now=None, share=True):
    """{"result": "draft" | "refused", "lines", "written", "shared"}; see the
    module docstring."""
    root = os.path.abspath(root or features.ROOT)
    runner = runner or features.run_git
    person = features._person(person, root, runner)
    if not person:
        return _refused("no person — pass --person or set git config user.email")
    if not PERSON_RE.match(person) or person.startswith("_"):
        return _refused("%r is not a person's folder name" % person)
    family, src, kind = _resolve(source, from_live, person, root)
    if family is None:
        return _refused(src)
    list_rel = "%s/%s.features.json" % (features.TEMPLATES, family)
    if not os.path.isfile(os.path.join(root, list_rel)):
        return _refused("%s is not a page family: %s does not exist" % (family, list_rel))
    try:
        features.load(os.path.join(root, list_rel))
    except features.LoadError as exc:
        return _refused(str(exc))
    if not os.path.isfile(os.path.join(root, src)):
        if kind == "live":
            return _refused("you have no live %s page (%s); make a draft of the template "
                            "instead" % (family, src))
        return _refused("%s does not exist" % src)
    try:
        with open(os.path.join(root, src), "rb") as handle:
            data = handle.read()
        text = data.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _refused("UNREADABLE: %s — %s" % (src, exc))
    _, date = live._stamp(now)
    pair, why = _target(root, person, family, name, date.replace("-", ""))
    if why:
        return _refused(why)
    html_rel, log_rel = pair
    pv = _pv()
    notes = []
    if kind == "template":
        out = pv.personal_text(text, family, pv.blob_sha(data))
        made = "the %s template" % family
    else:
        if live.PREPARED_META in live._head(text):
            return _refused("%s is prepared, not yet opened on this machine: run "
                            "features.py first-open %s first" % (src, src))
        made = "your live page %s" % src
        base = _live_base(person, family, root)
        if pv.stamped_sha(text) or "data-personal-view" in text:
            out = text
        elif base:
            out = pv.place_strip(text, pv.banner(family, base))
        else:
            out = text
            notes.append("no base recorded in %s; the draft carries no base stamp"
                         % live._live_log_rel(person, family))
        notes.append(NOTE_NO_SIDEBAR)
    os.makedirs(os.path.dirname(os.path.join(root, html_rel)), exist_ok=True)
    with open(os.path.join(root, html_rel), "x", encoding="utf-8") as handle:
        handle.write(out)
    with open(os.path.join(root, log_rel), "x", encoding="utf-8"):
        pass
    written = [html_rel, log_rel]
    lines = ["draft: %s · from %s" % (html_rel, made),
             "change log: %s (empty)" % log_rel]
    lines.extend("note: %s" % n for n in notes)
    if not share:
        shared = "not shared"
    else:
        error = features._share(written, "page: draft %s (%s)" % (
            os.path.basename(html_rel)[:-len(".html")], person), root, runner)
        shared = "shared" if error is None else "not shared: %s" % error
    return {"result": "draft", "lines": lines, "written": written, "shared": shared}


def main(argv=None, *, root=None, runner=None, now=None):
    """exit 0 draft made · 2 refused or a bad argument."""
    parser = argparse.ArgumentParser(prog="features.py draft", add_help=False)
    parser.add_argument("source")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--name")
    parser.add_argument("--person")
    parser.add_argument("--no-share", action="store_true")
    try:
        opts = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    except SystemExit:
        return 2
    result = make_draft(opts.source, from_live=opts.live, name=opts.name, person=opts.person,
                        root=root, runner=runner, now=now, share=not opts.no_share)
    for line in result["lines"]:
        print(line)
    if result["shared"]:
        print(result["shared"])
    return 0 if result["result"] == "draft" else 2


# --- PF-19b (catch up) ------------------------------------------------------------------------------------------

CATCHUP_STATES = ["todo", "applied", "skipped", "needs-a-person"]
MARKS = CATCHUP_STATES[1:]
CASE_NONE, CASE_REPLAY, CASE_HAND = "no changes", "changes to replay", "hand edits"
SAY_NONE = "nothing to replay: the new draft IS your page on today's template — say 'make this draft live'"
SAY_HAND = ("your page was changed by hand; compare side by side (/page-compare) — "
            "the differences are below, and no merge is guessed")
SAY_REPLAY = ("replay each change through /page-change on the new draft, in order, then mark it: "
              "features.py catchup-mark %s <step> applied|skipped|needs-a-person [--why TEXT]")
SAY_DONE = "every change is marked — show the draft, then say 'make this draft live' (/page-live)"
DIFF_SHOWN = 8
DIFF_TEXT = 70


def _plan_rel(draft_rel):
    return draft_rel[:-len(".html")] + ".catchup.json"


def _anchored(text, n):
    return ('data-feature="%d"' % n) in live.PAGE_PREFS_RE.sub("", text)


def went_live_form(family, base, root, runner):
    """What going live made from the template blob `base`: live.transform of that template's draft
    (personal_view.personal_text, the way make_draft cuts one). (text, None), or (None, why) when there is no
    base or its blob cannot be read. Reads the template file when it is the base, else `git cat-file blob`."""
    if not base:
        return None, "no base template is recorded for the live page"
    tmpl = os.path.join(root, features.TEMPLATES, "%s.html" % family)
    if live.blob_id(tmpl) == base:
        with open(tmpl, "rb") as handle:
            text = handle.read().decode("utf-8")
    else:
        code, out, err = runner(["git", "cat-file", "blob", base], root)
        if code != 0:
            return None, "the base template %s cannot be read here (%s)" % (
                base[:10], features._first_line(out, err))
        text = out
    try:
        return live.transform(_pv().personal_text(text, family, base)), None
    except ValueError as exc:
        return None, "the base template's live form cannot be made — %s" % exc


def diff_summary(have, want):
    """How the live page (`have`) differs from what going live made (`want`): the changed-line count
    (personal_view.drift_lines) and the first DIFF_SHOWN differences, each "line N added|removed|changed: …"."""
    a, b = want.splitlines(), have.splitlines()
    spots = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        word = {"insert": "added", "delete": "removed", "replace": "changed"}[tag]
        text = (b[j1] if j2 > j1 else a[i1]).strip()
        spots.append("line %d %s: %s" % (j1 + 1, word, text[:DIFF_TEXT]))
    return {"lines": _pv().drift_lines(have, want), "spots": spots}


def _entries(objs, doc, live_text, new_text):
    """The plan's entries, in log order: todo, or skipped / needs-a-person when that is plain without a person."""
    numbers = set(e.get("n") for e in doc.get("features") or [] if isinstance(e, dict))
    retired = set(r.get("n") for r in doc.get("retired") or [] if isinstance(r, dict))
    out = []
    for step, obj in enumerate(objs, 1):
        n = obj.get("n")
        state, why = "todo", None
        if not features._is_int(n):
            state, why = "needs-a-person", "the change names no number"
        elif n in retired or n not in numbers:
            state, why = "skipped", "number %d is not on today's list (removed or retired)" % n
        elif _anchored(live_text, n) and not _anchored(new_text, n):
            state, why = "skipped", "number %d's place is gone from today's template" % n
        out.append({"step": step, "n": n, "said": obj.get("said"), "by": obj.get("by"), "at": obj.get("at"),
                    "state": state, "why": why, "line": obj})
    return out


def _entry_line(e):
    said = e["said"] if isinstance(e["said"], str) else ""
    line = "  %d. [%s] n %s · %s · by %s · %s" % (e["step"], e["state"], e["n"], said, e["by"], e["at"])
    return line + ("\n     why: %s" % e["why"] if e.get("why") else "")


def _tally(entries):
    count = dict((s, sum(1 for e in entries if e["state"] == s)) for s in CATCHUP_STATES)
    return "%d change%s: %d applied · %d skipped · %d need a person · %d to do" % (
        len(entries), "" if len(entries) == 1 else "s", count["applied"], count["skipped"],
        count["needs-a-person"], count["todo"])


def _setup_person(person, root, runner):
    root = os.path.abspath(root or features.ROOT)
    runner = runner or features.run_git
    person = features._person(person, root, runner)
    if not person:
        return root, runner, None, "no person — pass --person or set git config user.email"
    if not PERSON_RE.match(person) or person.startswith("_"):
        return root, runner, None, "%r is not a person's folder name" % person
    return root, runner, person, None


def _catchup_refused(why):
    out = _refused(why)
    out.update(case=None, draft=None, plan=None, changes=[], diff=None)
    return out


def catch_up(family, *, person=None, root=None, runner=None, now=None, share=True):
    """{"result": "catch-up" | "refused", "case", "lines", "written", "shared", "draft", "plan", "changes",
    "diff"}; see the module docstring. A refusal writes nothing."""
    root, runner, person, why = _setup_person(person, root, runner)
    if why:
        return _catchup_refused(why)
    if not SLUG_RE.match(family or ""):
        return _catchup_refused("%r is not a family name (lowercase words joined by hyphens)" % family)
    list_rel = "%s/%s.features.json" % (features.TEMPLATES, family)
    live_rel = "%s/%s/%s.html" % (features.VIEWERS, person, family)
    if not os.path.isfile(os.path.join(root, list_rel)):
        return _catchup_refused("%s is not a page family: %s does not exist" % (family, list_rel))
    if not os.path.isfile(os.path.join(root, live_rel)):
        return _catchup_refused("you have no live %s page (%s): nothing to catch up — make a draft of the "
                                "template instead" % (family, live_rel))
    try:
        doc = features.load(os.path.join(root, list_rel))
        live_text = live._read_text(os.path.join(root, live_rel))
    except features.LoadError as exc:
        return _catchup_refused(str(exc))
    except (OSError, UnicodeDecodeError) as exc:
        return _catchup_refused("UNREADABLE: %s — %s" % (live_rel, exc))
    if live.PREPARED_META in live._head(live_text):
        return _catchup_refused("%s is prepared, not yet opened on this machine: run features.py first-open %s "
                                "first" % (live_rel, live_rel))
    last = live.last_live(person, family, root) or {}
    from_rel, base = last.get("from"), last.get("base")
    source, lines = None, []
    for rel in [live._log_rel(live_rel)] + ([live._log_rel(from_rel)] if from_rel else []):
        if os.path.isfile(os.path.join(root, rel)):
            try:
                lines = features.read_changes(os.path.join(root, rel))
            except features.LoadError as exc:
                return _catchup_refused(str(exc))
            if lines:
                source = rel
                break
    objs = []
    for i, line in enumerate(lines, 1):
        try:
            obj = json.loads(line)
        except ValueError as exc:
            return _catchup_refused("%s line %d is not JSON (%s); fix the log first" % (source, i, exc))
        if not isinstance(obj, dict):
            return _catchup_refused("%s line %d is not an object; fix the log first" % (source, i))
        objs.append(obj)
    replays = _replays(root, person, family)
    objs = [obj for obj in objs if obj not in replays]
    went, went_why = (None, None) if objs else went_live_form(family, base, root, runner)
    _, date = live._stamp(now)
    (stem, _), _ = _target(root, person, family, None, "catchup-" + date.replace("-", ""))
    name = os.path.basename(stem)[len(family) + 2:-len(".html")]
    made = make_draft(family, name=name, person=person, root=root, runner=runner, now=now, share=False)
    if made["result"] != "draft":
        return _catchup_refused(made["lines"][0][len("refused: "):])
    draft_rel, written = made["written"][0], list(made["written"])
    new_text = live._read_text(os.path.join(root, draft_rel))
    out = {"result": "catch-up", "lines": [made["lines"][0]], "written": written, "shared": "",
           "draft": draft_rel, "plan": None, "changes": [], "diff": None}
    if objs:
        entries = _entries(objs, doc, live_text, new_text)
        plan_rel = _plan_rel(draft_rel)
        at, _ = live._stamp(now)
        plan = {"kind": "catchup", "family": family, "person": person, "made": at, "draft": draft_rel,
                "live": live_rel, "went_live": last.get("at"), "base": base,
                "template": live.blob_id(os.path.join(root, features.TEMPLATES, "%s.html" % family)),
                "source": source, "changes": entries}
        with open(os.path.join(root, plan_rel), "x", encoding="utf-8") as handle:
            handle.write(features.dumps(plan))
        written.append(plan_rel)
        out.update(case=CASE_REPLAY, plan=plan_rel, changes=entries)
        out["lines"] += ["case: %s — %d from %s" % (CASE_REPLAY, len(entries), source)]
        out["lines"] += [_entry_line(e) for e in entries]
        out["lines"] += ["plan: %s · %s" % (plan_rel, _tally(entries)), SAY_REPLAY % draft_rel]
    elif went is not None and went == live_text:
        out.update(case=CASE_NONE)
        out["lines"] += ["case: %s — the change log is empty and %s is what going live made from its base "
                         "template %s" % (CASE_NONE, live_rel, base[:10]), SAY_NONE]
    else:
        out.update(case=CASE_HAND)
        out["lines"] += ["case: %s — the change log is empty and %s %s" % (
            CASE_HAND, live_rel, "differs from what going live made from its base template %s" % base[:10]
            if went is not None else "cannot be shown unchanged: %s" % went_why), SAY_HAND]
        out["lines"].append("compare: %s with %s" % (live_rel, draft_rel))
        if went is not None:
            out["diff"] = diff_summary(live_text, went)
            spots = out["diff"]["spots"]
            out["lines"].append("%d line%s differ:" % (out["diff"]["lines"], "" if out["diff"]["lines"] == 1
                                                       else "s"))
            out["lines"] += ["  %s" % s for s in spots[:DIFF_SHOWN]]
            if len(spots) > DIFF_SHOWN:
                out["lines"].append("  … %d more" % (len(spots) - DIFF_SHOWN))
    out["lines"] += [line for line in made["lines"][1:] if line.startswith("note:")]
    out["lines"].append("the live page %s is untouched" % live_rel)
    if share:
        error = features._share(written, "page: catch up %s (%s)" % (family, person), root, runner)
        out["shared"] = "shared" if error is None else "not shared: %s" % error
    else:
        out["shared"] = "not shared"
    return out


def _load_plan(path):
    with open(path, encoding="utf-8") as handle:
        plan = json.load(handle)
    if not isinstance(plan, dict) or not isinstance(plan.get("changes"), list):
        raise ValueError("not a catch-up plan (no `changes` list)")
    return plan


def _plans(root, person, family):
    """[(made, rel, plan)] for every readable catch-up plan of the person's family drafts."""
    out = []
    pattern = os.path.join(root, features.VIEWERS, person, "drafts", "%s--*.catchup.json" % family)
    for path in sorted(glob.glob(pattern)):
        try:
            plan = _load_plan(path)
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        out.append((str(plan.get("made") or ""), features._relpath(path, root), plan))
    return out


def _replays(root, person, family):
    """Every change line an earlier catch-up's /page-change wrote (its plan's `replay`): going live from that
    draft carried them into the live log beside the lines they replayed, so they are never replayed again."""
    return [e["replay"] for _, _, plan in _plans(root, person, family) for e in plan["changes"]
            if isinstance(e, dict) and isinstance(e.get("replay"), dict)]


def catchup_mark(draft_rel, step, state, *, why=None, person=None, root=None, runner=None, now=None,
                 share=True):
    """Record one replayed change's outcome in the draft's plan: {"result": "marked" | "refused", "lines",
    "written", "shared", "plan"}. "applied" needs a change line for that number in the draft's own log beyond
    those already counted as applied. A refusal writes nothing."""
    root, runner, person, problem = _setup_person(person, root, runner)
    if problem:
        return dict(_refused(problem), plan=None)
    rel = features._relpath(draft_rel, root)
    problem = features._draft_problem(rel, person)
    if problem:
        return dict(_refused(problem), plan=None)
    if state not in MARKS:
        return dict(_refused("%r is not one of %s" % (state, " | ".join(MARKS))), plan=None)
    plan_rel = _plan_rel(rel)
    if not os.path.isfile(os.path.join(root, plan_rel)):
        family = features.DRAFT_RE.match(rel).group(2)
        return dict(_refused("%s has no catch-up plan (%s): say 'catch up my %s page' first"
                             % (rel, plan_rel, family)), plan=None)
    try:
        plan = _load_plan(os.path.join(root, plan_rel))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return dict(_refused("UNREADABLE: %s — %s" % (plan_rel, exc)), plan=None)
    entry = next((e for e in plan["changes"] if isinstance(e, dict) and e.get("step") == step), None)
    if entry is None:
        return dict(_refused("%s has no step %s (steps 1–%d)" % (plan_rel, step, len(plan["changes"]))),
                    plan=None)
    replay = None
    if state == "applied":
        log_rel = live._log_rel(rel)
        try:
            logged = live._parsed(os.path.join(root, log_rel))
        except features.LoadError as exc:
            return dict(_refused(str(exc)), plan=None)
        claimed = [e.get("replay") for e in plan["changes"] if isinstance(e, dict) and e is not entry]
        replay = next((obj for obj in logged if isinstance(obj, dict) and obj.get("n") == entry["n"]
                       and obj not in claimed), None)
        if replay is None:
            return dict(_refused("no change line for number %s in %s yet: replay step %d through /page-change "
                                 "first" % (entry["n"], log_rel, step)), plan=None)
    at, _ = live._stamp(now)
    entry.pop("replay", None)
    if replay is not None:
        entry["replay"] = replay   # the line /page-change wrote; a later catch-up never replays it again
    entry["state"] = state
    if why is not None:
        entry["why"] = why
    entry["marked"], entry["marked_by"] = at, person
    live._write_atomic(os.path.join(root, plan_rel), features.dumps(plan))
    entries = [e for e in plan["changes"] if isinstance(e, dict)]
    lines = ["step %d (n %s): %s%s" % (step, entry["n"], state, " — %s" % entry["why"] if entry.get("why")
                                       else ""), "plan: %s · %s" % (plan_rel, _tally(entries))]
    if not any(e.get("state") == "todo" for e in entries):
        lines.append(SAY_DONE)
    if share:
        error = features._share([plan_rel], "page: catch up %s step %d %s (%s)" % (
            plan.get("family"), step, state, person), root, runner)
        shared = "shared" if error is None else "not shared: %s" % error
    else:
        shared = "not shared"
    return {"result": "marked", "lines": lines, "written": [plan_rel], "shared": shared, "plan": plan_rel}


def catchup_status(family, *, person=None, root=None, runner=None):
    """The person's newest catch-up plan for the family: {"result": "plan" | "refused", "lines", "plan",
    "changes"}. Reads only."""
    root, runner, person, problem = _setup_person(person, root, runner)
    if problem:
        return {"result": "refused", "lines": ["refused: %s" % problem], "plan": None, "changes": []}
    found = _plans(root, person, family)
    if not found:
        return {"result": "refused", "lines": ["refused: no catch-up plan for %s — say 'catch up my %s page'"
                                               % (family, family)], "plan": None, "changes": []}
    _, rel, plan = sorted(found, key=lambda f: (f[0], f[1]))[-1]
    entries = [e for e in plan["changes"] if isinstance(e, dict)]
    lines = ["plan: %s · draft %s · from %s" % (rel, plan.get("draft"), plan.get("source"))]
    lines += [_entry_line(e) for e in entries] + [_tally(entries)]
    lines.append(SAY_DONE if not any(e.get("state") == "todo" for e in entries)
                 else SAY_REPLAY % plan.get("draft"))
    return {"result": "plan", "lines": lines, "plan": rel, "changes": entries}


def _print(result, as_json):
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return
    for line in result["lines"]:
        print(line)
    if result.get("shared"):
        print(result["shared"])


def main_catchup(argv=None, *, root=None, runner=None, now=None):
    """features.py catchup: exit 0 made or shown · 2 refused or a bad argument."""
    parser = argparse.ArgumentParser(prog="features.py catchup", add_help=False)
    parser.add_argument("family")
    parser.add_argument("--person")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-share", action="store_true")
    try:
        opts = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    except SystemExit:
        return 2
    if opts.status:
        result = catchup_status(opts.family, person=opts.person, root=root, runner=runner)
    else:
        result = catch_up(opts.family, person=opts.person, root=root, runner=runner, now=now,
                          share=not opts.no_share)
    _print(result, opts.json)
    return 2 if result["result"] == "refused" else 0


def main_mark(argv=None, *, root=None, runner=None, now=None):
    """features.py catchup-mark: exit 0 marked · 2 refused or a bad argument."""
    parser = argparse.ArgumentParser(prog="features.py catchup-mark", add_help=False)
    parser.add_argument("draft")
    parser.add_argument("step", type=int)
    parser.add_argument("state", choices=MARKS)
    parser.add_argument("--why")
    parser.add_argument("--person")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-share", action="store_true")
    try:
        opts = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    except SystemExit:
        return 2
    result = catchup_mark(opts.draft, opts.step, opts.state, why=opts.why, person=opts.person, root=root,
                          runner=runner, now=now, share=not opts.no_share)
    _print(result, opts.json)
    return 0 if result["result"] == "marked" else 2


if __name__ == "__main__":
    sys.exit(main())
