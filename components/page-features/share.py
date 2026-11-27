#!/usr/bin/env python3
"""PF-9 (share check), TEMPLATE MODE: before a page is shared, prove it works
for someone else, at VIEW and USE level, with fix steps by owner.

    VIEW  every D/M/R number on the page is reachable from another machine:
          not after-card, not read from lab code (builder card rule 12), its
          repo files in git; plus the page text itself, through `scan`
    USE   VIEW, plus every wired action on the page through a declared
          component door (never a person's own lab server)

The page-text scan is ONE SEAM, share_check(..., scan=None): this module
classifies no address itself. scan=None leaves VIEW at best "not proven"; the
CLI uses components/system-integration/page_scan.py's scan() when that file
exists (PF-9b (page scan)), else none, and says which.

PF-9c (share warns): template mode writes when the page's integrity holds —
only a HARD blocker (a wired action whose door is lab code, or the overlay
block edited) stops it, and every other finding prints as a "won't work on
another machine yet" warning with its fix and owner. A wired action through a
components/ door is not a blocker: the page copies a request and the person's
own Claude carries it out (the 10-21 ruling).

PF-15 (direct by default): in a family that keeps a run table
(_templates/<family>.actions.json), a wired action with no complete run entry
— `direct` with a kind, or `via_claude` with a written why — is a third HARD
blocker, by number (live.run_entry_findings). A family with no actions file has
no table to read here; going live (live.check_live) still refuses its buttons.

    python3 features.py share <draft page> [--person P] [--no-share]
        exit 0 the draft became _templates/<family>.html (owner only) · 2
        blocked, refused or a bad argument · 3 unreadable

Named mode (/page-share <name>…: PREPARED pages in a recipient's folder) is
not here; it waits for PF-7 (working versions)'s PREPARED state. Stdlib only,
Python 3.9. Git only through the runner: read-only ls-files and hash-object,
and for the act features._share (add / commit / push of exactly the paths).
"""
import argparse
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import features  # noqa: E402  PF-1 (page-features skeleton), same component
import live  # noqa: E402  PF-7 (working versions), same component
import check  # noqa: E402  PF-3 (feature check), same component

VIEW_KINDS = ("data", "media", "rule")
PLACEHOLDER_RE = re.compile(r"<[^<>]*>")
LAB_RE = re.compile(r"^lab/([^/]+)/.")
COMPONENT_RE = re.compile(r"^components/[^/]+/.")
FEATURE_ON_PAGE_RE = re.compile(r'data-feature="(\d+)"')

FIX_LAB_VIEW = ("graduate it via /system-fit → /system-ready → /system-review, or put "
                "the data in git and read it through PF-4 (page starter kit), or drop "
                "the number")
FIX_LAB_USE = "graduate it via /system-fit → /system-ready → /system-review, or share to view"
FIX_NOT_IN_GIT = "put it in git (read through PF-4 (page starter kit)) or drop the number"
FIX_NO_DOOR = "route it through a declared component door, or share to view"
FIX_RUN_ENTRY = ("give it a run entry in %s.actions.json: `direct` with its kind (quick, job, "
                 "confirm-job, external), or `via_claude` with a written why")
NOTE_NO_SCAN = ("page addresses not scanned: system-integration has no check that takes "
                "a page (.claude/skills/system-ready/SKILL.md:301-303, "
                "components/system-integration/conventions.md:188); a page target "
                "there is designer's engine")
NOTE_KEYS = ("keys: no feature names a key; checked when PF-4 (page starter kit) "
             "declares a page's keys")
NOTE_BUTTONS = ("buttons: %d through a component door — the page copies a request, the "
                "person's Claude carries it out")
PAGE_SCAN = "components/system-integration/page_scan.py"
NOTE_SCAN = "page addresses scanned by %s (PF-9b (page scan))" % PAGE_SCAN
SNAPSHOT = "snapshot: a frozen copy can always be published as a claude.ai artifact (snapshot only)"
WARNINGS = "won't work on another machine yet (%d):"


# --- paths ------------------------------------------------------------------

def _family_of(rel):
    """The family a page belongs to (template, draft or live page), or None."""
    match = features.DRAFT_RE.match(rel)
    if match:
        return match.group(2)
    match = live.LIVE_RE.match(rel)
    return match.group(2) if match else None


def _parts(source):
    """source.file split into parts (" · ", " → "), each with its path."""
    text = source.get("file") if isinstance(source, dict) else None
    if not features._nonempty_str(text):
        return []
    out = []
    for part in features.FILE_SPLIT_RE.split(text):
        part = part.strip()
        if part:
            words = part.split()
            out.append((part, words[0].rstrip(",;:") if words else ""))
    return out


def _repo_path(path):
    return "/" in path and bool(re.match(r"^[A-Za-z0-9]", path))


def _pattern(path):
    """A repo path as a git ls-files pattern: each <…> and … becomes *. A folder
    (ending in /) matches the files under it: a glob ending in / matches nothing
    in git ls-files (the journey D10 false alarm, 2026-11-25)."""
    pattern = PLACEHOLDER_RE.sub("*", path).replace("…", "*")
    return pattern + "*" if pattern.endswith("/") else pattern


def _component(source):
    name = source.get("component") if isinstance(source, dict) else None
    return name if features._nonempty_str(name) else "family owner"


# --- the check ----------------------------------------------------------------

def _verdicts(result, scanned):
    levels = [b["level"] for b in result["blockers"]]
    view = "blocked" if "VIEW" in levels else ("pass" if scanned else "not proven")
    if view == "blocked" or "USE" in levels:
        use = "blocked"
    else:
        use = "not proven" if view == "not proven" else "pass"
    result["view"], result["use"] = view, use


def _result(family, rel):
    return {"family": family, "page": rel, "view": None, "use": None,
            "blockers": [], "notes": [], "refused": None}


def _refused_check(family, rel, why):
    result = _result(family, rel)
    result["refused"] = why
    return result


def _check(page, person, root, runner, scan):
    """share_check's work, plus what share_template needs (root, runner, the
    page text, the family list)."""
    root = os.path.abspath(root or features.ROOT)
    runner = runner or features.run_git
    rel = features._relpath(page, root)
    family = _family_of(rel)
    if not family:
        return _refused_check(None, rel, "%s is not a page of a family (%s/<person>/"
                              "<family>.html, a draft or a template)" % (rel, features.VIEWERS)), None
    list_rel = "%s/%s.features.json" % (features.TEMPLATES, family)
    tmpl_rel = "%s/%s.html" % (features.TEMPLATES, family)
    for need in (rel, list_rel, tmpl_rel):
        if not os.path.isfile(os.path.join(root, need)):
            return _refused_check(family, rel, "%s does not exist" % need), None
    try:
        html = live._read_text(os.path.join(root, rel))
        live._read_text(os.path.join(root, tmpl_rel))
        doc = features.load(os.path.join(root, list_rel))
    except (OSError, UnicodeDecodeError) as exc:
        return _refused_check(family, rel, "UNREADABLE: %s" % exc), None
    except features.LoadError as exc:
        return _refused_check(family, rel, str(exc)), None

    result = _result(family, rel)
    blockers, notes = result["blockers"], result["notes"]

    def block(level, tag, what, fix, owner, hard=False):
        item = {"level": level, "tag": tag, "what": what, "fix": fix, "owner": owner,
                "hard": hard}
        if item not in blockers:
            blockers.append(item)

    def note(text):
        if text not in notes:
            notes.append(text)

    # Every finding blocks VIEW. Only a format finding (a broken shape) stops
    # the rest: a content finding (a value only the owner can fix, PF-1c
    # (plain-words changes)) leaves every entry readable, and the real
    # family lists carry some.
    findings = features.validate(doc)
    owner = doc.get("owner") if isinstance(doc, dict) else None
    owner = owner if features._nonempty_str(owner) else "family owner"
    for finding in findings:
        block("VIEW", "page", "the family list — %s" % finding,
              "fix the family list %s" % list_rel, owner)
    if any(features.finding_kind(f) == "format" for f in findings):
        note("features not checked: the family list has format findings")
        _verdicts(result, scan is not None)
        return result, {"root": root, "runner": runner, "html": html, "doc": doc}

    on_page = set(int(n) for n in FEATURE_ON_PAGE_RE.findall(html))
    doors = 0
    for entry in doc["features"]:
        if entry["n"] not in on_page or entry["state"] == "not-built":
            continue
        kind, source, t = entry["kind"], entry.get("source"), check.tag(entry)
        if kind in VIEW_KINDS:
            if entry["state"] == "after-card":
                block("VIEW", t, "not reachable from another machine yet (after-card)",
                      "build what its note names: %s" % (entry.get("note") or "")[:100],
                      _component(source))
                continue
            for part, path in _parts(source):
                if not _repo_path(path):
                    note("%s: %s is not a repo path, not checked" % (t, part))
                    continue
                lab = LAB_RE.match(path)
                if lab and path.endswith(".html"):
                    note("%s: page-only logic from %s; it travels with the page" % (t, path))
                elif lab:
                    block("VIEW", t, "reads lab code (%s), builder-card rule 12" % path,
                          FIX_LAB_VIEW, lab.group(1))
                else:
                    code, out, _ = runner(["git", "ls-files", "--", _pattern(path)], root)
                    if code != 0 or not out.strip():
                        block("VIEW", t, "%s is not in git; only the machine that made it "
                              "has it" % path, FIX_NOT_IN_GIT, _component(source))
        elif kind == "action" and entry["state"] == "wired":
            parts = _parts(source)
            door = parts[0][1] if parts else ""
            lab = LAB_RE.match(door) if _repo_path(door) else None
            if lab:
                block("USE", t, "calls %s's lab server (%s), builder-card rule 12"
                      % (lab.group(1), door), FIX_LAB_USE, lab.group(1), hard=True)
            elif _repo_path(door) and COMPONENT_RE.match(door):
                doors += 1  # routed through the person's own Claude (10-21 ruling)
            else:
                block("USE", t, "no declared component door", FIX_NO_DOOR, _component(source))

    # PF-15 (direct by default): every wired action of a family that keeps a run
    # table has a complete run entry, or the share is refused (hard), by number.
    try:
        table = live.run_table(family, root)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        block("USE", "page", "the run table — %s" % exc, FIX_RUN_ENTRY % family, owner, hard=True)
    else:
        if table is not None:
            for entry, what in live.run_entry_findings(doc, family, table):
                block("USE", check.tag(entry), what, FIX_RUN_ENTRY % family, owner, hard=True)

    if doors:
        note(NOTE_BUTTONS % doors)
    if scan is None:
        note(NOTE_NO_SCAN)
    else:
        for finding in scan(html):
            block("VIEW", "page", finding, "remove or replace the address on the page "
                  "(read it through PF-4 (page starter kit))", "family owner")
    note(NOTE_KEYS)
    _verdicts(result, scan is not None)
    return result, {"root": root, "runner": runner, "html": html, "doc": doc}


def share_check(page, *, person=None, root=None, runner=None, scan=None):
    """Would this page work for someone else? {"family", "page", "view",
    "use", "blockers": [{"level", "tag", "what", "fix", "owner", "hard"}],
    "notes", "refused"}. view/use: "pass" · "not proven" · "blocked"; they
    report and no longer gate template mode, which stops only on a blocker
    with hard True (a lab-code door, an edited overlay). `person` is
    not needed by the check; it is accepted so every caller passes the same
    words. `scan` is a callable(page_text) -> [finding]; each finding is a
    VIEW blocker (not hard) "page: <finding>"; None (no page target in system-
    integration yet) leaves VIEW at best "not proven"."""
    result, _ = _check(page, person, root, runner, scan)
    return result


def render(result):
    """The check as lines: the verdicts with their blockers, the fix steps
    grouped by (fix, owner), the snapshot line, the notes."""
    if result.get("refused"):
        return ["refused: %s" % result["refused"]]
    lines = []
    for level, verdict in (("VIEW", result["view"]), ("USE", result["use"])):
        lines.append("%s %s" % (level, verdict))
        for b in result["blockers"]:
            if b["level"] == level:
                lines.append("  %s: %s" % (b["tag"], b["what"]))
    groups = []
    for b in result["blockers"]:
        key = (b["fix"], b["owner"])
        for group in groups:
            if group[0] == key:
                if b["tag"] not in group[1]:
                    group[1].append(b["tag"])
                break
        else:
            groups.append((key, [b["tag"]]))
    if groups:
        lines.append("fix steps:")
        for i, ((fix, owner), tags) in enumerate(groups, 1):
            lines.append("  %d. %s (owner %s) — %s" % (i, fix, owner, ", ".join(tags)))
    lines.append(SNAPSHOT)
    lines.extend("note: %s" % n for n in result["notes"])
    return lines


# --- template mode --------------------------------------------------------------

def _refused(why, check_result=None):
    return {"result": "refused", "check": check_result, "lines": ["refused: %s" % why],
            "written": [], "shared": ""}


def _grown(html, start, end):
    """A span that fills its own line takes the line's newline with it."""
    if (start == 0 or html[start - 1] == "\n") and end < len(html) and html[end] == "\n":
        end += 1
    return start, end


def template_form(draft, template):
    """The draft as its family's template: the personal-view element removed
    and its fo-prefs block replaced by the template's own; every other byte
    unchanged."""
    spans = []
    for match in live.PV_OPEN_RE.finditer(draft):
        if not live._inside(match.start(), spans):
            spans.append(_grown(draft, match.start(),
                                live._element_end(draft, match.group(1), match.end())))
    theirs = live.FO_PREFS_RE.search(template)
    swaps = []
    for match in live.FO_PREFS_RE.finditer(draft):
        if live._inside(match.start(), spans):
            continue
        if theirs:
            swaps.append((match.start(), match.end(), theirs.group(0)))
        else:
            start, end = _grown(draft, match.start(), match.end())
            swaps.append((start, end, ""))
    edits = sorted([(s, e, "") for s, e in spans] + swaps)
    out, pos = [], 0
    for start, end, text in edits:
        if start < pos:
            continue
        out.append(draft[pos:start])
        out.append(text)
        pos = end
    out.append(draft[pos:])
    return "".join(out)


def share_template(page, *, person=None, root=None, runner=None, scan=None, share=True):
    """Template mode (/page-share, no names; OWNER ONLY): the share check on
    the person's own draft, then — when no blocker is hard — the draft's
    template form written to _templates/<family>.html and shared, every other
    blocker printed as a warning with its fix and owner. A hard blocker writes
    nothing. {"result": "template" | "blocked" | "refused", "check", "lines",
    "written", "shared"}."""
    root = os.path.abspath(root or features.ROOT)
    runner = runner or features.run_git
    person = features._person(person, root, runner)
    if not person:
        return _refused("no person — pass --person or set git config user.email")
    rel = features._relpath(page, root)
    problem = features._draft_problem(rel, person)
    if problem:
        return _refused("%s; template mode shares from your own draft" % problem)
    family = features.DRAFT_RE.match(rel).group(2)
    list_rel = "%s/%s.features.json" % (features.TEMPLATES, family)
    tmpl_rel = "%s/%s.html" % (features.TEMPLATES, family)
    for need in (rel, list_rel, tmpl_rel):
        if not os.path.isfile(os.path.join(root, need)):
            return _refused("%s does not exist" % need)

    result, ctx = _check(rel, person, root, runner, scan)
    if result["refused"]:
        return _refused(result["refused"], result)
    doc, html = ctx["doc"], ctx["html"]
    try:
        template = live._read_text(os.path.join(root, tmpl_rel))
    except (OSError, UnicodeDecodeError) as exc:
        return _refused("UNREADABLE: %s" % exc, result)
    owner = doc.get("owner") if isinstance(doc, dict) else None
    if not features._nonempty_str(owner):
        return _refused("%s has no owner in its family list; template mode is owner only"
                        % family, result)
    if owner != person:
        return _refused("only %s shares %s as its template" % (owner, family), result)
    stamp = live.SHA_RE.search(html)
    code, out, err = runner(["git", "hash-object", "--", tmpl_rel], root)
    if code != 0:
        return _refused("cannot hash %s: %s" % (tmpl_rel, features._first_line(out, err)),
                        result)
    now = out.strip()
    base = stamp.group(1) if stamp else None
    if base != now:
        return _refused("the template changed since this draft was cut (base %s → now %s); "
                        "cut a new draft" % (base[:7] if base else "none", now[:7]), result)
    try:
        mine, theirs = live._overlay_span(html), live._overlay_span(template)
        edited = ((html[mine[0]:mine[1]] if mine else None)
                  != (template[theirs[0]:theirs[1]] if theirs else None))
        what = "the overlay block was edited; it is component-owned"
    except ValueError as exc:
        edited, what = True, str(exc)
    if edited:
        result["blockers"].append({"level": "VIEW", "tag": "page", "what": what,
                                   "fix": "cut a new draft (the overlay is component-owned)",
                                   "owner": "page-features", "hard": True})
        _verdicts(result, scan is not None)

    hard = [b for b in result["blockers"] if b.get("hard")]
    warns = [b for b in result["blockers"] if not b.get("hard")]
    tail = []
    if warns:
        tail.append(WARNINGS % len(warns))
        tail.extend("  %s: %s — fix: %s (%s)" % (b["tag"], b["what"], b["fix"], b["owner"])
                    for b in warns)
    tail.extend("note: %s" % n for n in result["notes"])
    if hard:
        lines = ["blocked: %s stays as it is — nothing written" % tmpl_rel]
        for b in hard:
            lines.extend(["  %s: %s" % (b["tag"], b["what"]),
                          "    fix: %s (%s)" % (b["fix"], b["owner"])])
        return {"result": "blocked", "check": result, "lines": lines + tail,
                "written": [], "shared": ""}
    live._write_atomic(os.path.join(root, tmpl_rel), template_form(html, template))
    lines = ["template: %s is now %s's version of %s" % (tmpl_rel, person, family)]
    shared = (live._shared([tmpl_rel], "page: template %s from %s" % (family, person),
                           root, runner, True) if share else "not shared")
    return {"result": "template", "check": result, "lines": lines + tail,
            "written": [tmpl_rel], "shared": shared}


# --- the CLI --------------------------------------------------------------------

def _family_doc(page, root):
    """The page's family list, or None when it cannot be read."""
    family = _family_of(features._relpath(page, root))
    if not family:
        return None
    try:
        return features.load(os.path.join(root, features.TEMPLATES,
                                          "%s.features.json" % family))
    except (OSError, UnicodeDecodeError, features.LoadError):
        return None


def _load_scan(root, page):
    """(scan, note): PF-9b (page scan)'s scan(page_text, features_doc) from
    components/system-integration/page_scan.py, loaded by file path and
    adapted to the one-argument slot; (None, None) when the file is absent;
    (None, a note naming the error) when it does not load. A scan that
    raises when called becomes one warning, never a crash."""
    path = os.path.join(root, PAGE_SCAN)
    if not os.path.isfile(path):
        return None, None
    try:
        spec = importlib.util.spec_from_file_location("page_scan", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        found = module.scan
    except Exception as exc:  # a broken scan never stops the share
        return None, "page scan not loaded from %s: %s: %s" % (PAGE_SCAN, type(exc).__name__, exc)

    def one(text):
        try:
            return list(found(text, _family_doc(page, root)))
        except Exception as exc:
            return ["the page scan raised %s: %s; addresses not checked"
                    % (type(exc).__name__, exc)]
    return one, NOTE_SCAN


def main(argv=None, *, root=None, runner=None, scan=None):
    """`<draft page> [--person P] [--no-share]` (argv excludes "share"):
    exit 0 template · 2 blocked, refused or a bad argument · 3 unreadable.
    With no `scan` given, PF-9b (page scan)'s scan is used when its file
    exists, and the output says which."""
    parser = argparse.ArgumentParser(prog="features.py share", add_help=False)
    parser.add_argument("page")
    parser.add_argument("--person")
    parser.add_argument("--no-share", action="store_true")
    try:
        opts = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    except SystemExit:
        return 2
    root = os.path.abspath(root or features.ROOT)
    said = None
    if scan is None:
        scan, said = _load_scan(root, opts.page)
    result = share_template(opts.page, person=opts.person, root=root, runner=runner,
                            scan=scan, share=not opts.no_share)
    lines, unscanned = result["lines"], "note: %s" % NOTE_NO_SCAN
    if said and unscanned in lines:  # a scan that would not load replaces the no-scan note
        lines[lines.index(unscanned)] = "note: %s" % said
    elif said and result["result"] != "refused":
        lines.append("note: %s" % said)
    for line in result["lines"]:
        print(line)
    if result["shared"]:
        print(result["shared"])
    if result["result"] == "template":
        return 0
    if result["result"] == "refused" and result["lines"][0].startswith("refused: UNREADABLE"):
        return 3
    return 2


if __name__ == "__main__":
    sys.exit(main())
