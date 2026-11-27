#!/usr/bin/env python3
"""PF-1d (auto-log page changes): a page change is logged even when a
person's Claude committed it with plain git.

    autolog(repo_root, person, git_runner=None, dry_run=False)
        -> [{"page", "log", "entry"}, ...], oldest commit first

Reads every non-merge commit reachable from HEAD that modifies one of the
person's drafts (platform/views/viewers/<person>/drafts/<family>--<name>.html
whose family list sits in _templates/) and has no line in that draft's
<family>--<name>.changes.jsonl. For each, it reads the data-feature numbers on
the changed lines (or on the innermost numbered element around a line) and
appends one line per number: said = the commit subject, commit = the sha,
logged "auto". No number left → one line with n null, kind "unnumbered".

Git is read only (log and show, through `git_runner`, cwd = repo_root); the
lines it appends are uncommitted files under viewers/<person>/, so
`features.py autosave` commits them with everything else. A failing git call
returns what was done so far; a problem with one commit skips that commit,
with one line on stderr. Stdlib only, Python 3.9.
"""
import datetime
import json
import os
import re
import sys
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import features  # noqa: E402  PF-1 (page-features skeleton), same component

ROUTE = "claude-code"
SHA_KEEP = 10
NUMBER_RE = re.compile(r"""data-feature\s*=\s*["']?(\d+)""")
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "param", "source", "track", "wbr"}
SHOW = ["git", "show", "--no-color", "--no-ext-diff", "--no-renames", "--no-textconv"]


class _GitFailed(Exception):
    """A git call that did not exit 0: autolog stops and returns what it did."""


def _warn(text):
    sys.stderr.write("autolog: %s\n" % text)


def _git(runner, argv, root):
    code, out, err = runner(argv, root)
    if code != 0:
        raise _GitFailed("%s: %s" % (" ".join(argv[:3]), features._first_line(out, err)))
    return out


class _Spans(HTMLParser):
    """Every element's first and last line, its depth and its data-feature
    number (None when it carries none). Void elements close themselves; an
    end tag closes every element opened inside it; whatever is still open at
    the end runs to the last line."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.open = []
        self.spans = []

    def _number(self, attrs):
        for key, value in attrs:
            if key == "data-feature" and value is not None and value.strip().isdigit():
                return int(value.strip())
        return None

    def _closed(self, attrs):
        line = self.getpos()[0]
        end = line + (self.get_starttag_text() or "").count("\n")
        self.spans.append((line, end, len(self.open), self._number(attrs)))

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            self._closed(attrs)
        else:
            self.open.append((tag, self.getpos()[0], self._number(attrs)))

    def handle_startendtag(self, tag, attrs):
        self._closed(attrs)

    def handle_endtag(self, tag):
        line = self.getpos()[0]
        for i in range(len(self.open) - 1, -1, -1):
            if self.open[i][0] == tag:
                while len(self.open) > i:
                    _, start, n = self.open.pop()
                    self.spans.append((start, line, len(self.open), n))
                return

    def finish(self, last):
        self.close()
        while self.open:
            _, start, n = self.open.pop()
            self.spans.append((start, last, len(self.open), n))
        return self.spans


def _numbers_in(text, lines):
    """The data-feature numbers of the changed `lines` (1-based) of one
    version of a page: those written on the line, else the innermost
    enclosing element's that carries one."""
    rows = text.split("\n")
    spans = None
    out = set()
    for line in lines:
        row = rows[line - 1] if 0 < line <= len(rows) else ""
        found = {int(m) for m in NUMBER_RE.findall(row)}
        if not found:
            if spans is None:
                parser = _Spans()
                parser.feed(text)
                spans = [s for s in parser.finish(len(rows)) if s[3] is not None]
            around = [s for s in spans if s[0] <= line <= s[1]]
            if around:
                found = {max(around, key=lambda s: (s[2], s[0]))[3]}
        out |= found
    return out


def _hunks(diff):
    """(removed line numbers in the parent, added line numbers in the commit)
    from a -U0 diff."""
    removed, added = [], []
    for row in diff.splitlines():
        match = HUNK_RE.match(row)
        if not match:
            continue
        old, old_n, new, new_n = match.groups()
        removed.extend(range(int(old), int(old) + int(1 if old_n is None else old_n)))
        added.extend(range(int(new), int(new) + int(1 if new_n is None else new_n)))
    return removed, added


def _added_lines(diff):
    """The JSON objects a -U0 diff adds (a line that is not JSON is skipped)."""
    out = []
    for row in diff.splitlines():
        if row.startswith("+") and not row.startswith("+++"):
            try:
                obj = json.loads(row[1:])
            except ValueError:
                continue
            if isinstance(obj, dict):
                out.append(obj)
    return out


def _same_commit(a, b):
    """True when either sha is a prefix of the other, both 7+ hex."""
    if not (isinstance(a, str) and isinstance(b, str)):
        return False
    a, b = a.strip().lower(), b.strip().lower()
    if not (features.COMMIT_RE.match(a) and features.COMMIT_RE.match(b)):
        return False
    return a.startswith(b) or b.startswith(a)


def _log_lines(path):
    if not os.path.isfile(path):
        return []
    out = []
    try:
        with open(path, encoding="utf-8") as handle:
            for row in handle.read().splitlines():
                try:
                    obj = json.loads(row)
                except ValueError:
                    continue
                if isinstance(obj, dict):
                    out.append(obj)
    except (OSError, UnicodeDecodeError):
        return out
    return out


def _append(path, entries):
    lead = ""
    if os.path.isfile(path) and os.path.getsize(path):
        with open(path, encoding="utf-8") as handle:
            lead = "" if handle.read().endswith("\n") else "\n"
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(lead + features.dumps_changes(entries))


def _family_list(root, family, cache):
    if family not in cache:
        path = os.path.join(root, features.TEMPLATES, "%s.features.json" % family)
        try:
            cache[family] = features.load(path) if os.path.isfile(path) else None
        except features.LoadError:
            cache[family] = None
    return cache[family]


def _foreign(path, person):
    """True for a path under _templates/ or another person's viewers folder."""
    prefix = features.VIEWERS + "/"
    if not path.startswith(prefix):
        return False
    rest = path[len(prefix):]
    return "/" in rest and rest.split("/", 1)[0] != person


def _numbers_of(doc):
    features_list = doc.get("features") if isinstance(doc, dict) else None
    numbers = {e["n"] for e in features_list or []
               if isinstance(e, dict) and features._is_int(e.get("n"))}
    retired = set()
    if isinstance(doc, dict) and isinstance(doc.get("retired"), list):
        retired = {r["n"] for r in doc["retired"]
                   if isinstance(r, dict) and features._is_int(r.get("n"))}
    return numbers - retired


def _commit(sha, root, person, runner, cache):
    """(header, [(page, family), ...], statuses) for one candidate commit, or
    None when it is out of scope."""
    out = _git(runner, SHOW + ["--name-status", "--format=%H%x1f%at%x1f%s", sha], root)
    rows = out.split("\n")
    head = rows[0].split("\x1f")
    if len(head) != 3:
        raise ValueError("git show gave no header for %s" % sha)
    statuses = {}
    for row in rows[1:]:
        if "\t" not in row:
            continue
        status, path = row.split("\t", 1)
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        statuses[path] = status.strip()
    if any(_foreign(p, person) for p in statuses):
        return None
    pages = []
    for path in sorted(statuses):
        match = features.DRAFT_RE.match(path)
        if (statuses[path] == "M" and match and match.group(1) == person
                and _family_list(root, match.group(2), cache) is not None):
            pages.append((path, match.group(2)))
    return head, pages, statuses


def _already_logged(sha, log_rel, statuses, root, runner):
    for line in _log_lines(os.path.join(root, log_rel)):
        if _same_commit(line.get("commit"), sha):
            return True
    if statuses.get(log_rel) in ("A", "M"):
        diff = _git(runner, SHOW + ["--format=", "-U0", sha, "--", log_rel], root)
        if any("logged" not in line for line in _added_lines(diff)):
            return True
    return False


def _entries(head, page, person, doc, root, runner):
    sha, stamp, subject = head
    diff = _git(runner, SHOW + ["--format=", "-U0", sha, "--", page], root)
    removed, added = _hunks(diff)
    found = set()
    if removed:
        found |= _numbers_in(_git(runner, ["git", "show", "--no-textconv",
                                           "%s^:%s" % (sha, page)], root), removed)
    if added:
        found |= _numbers_in(_git(runner, ["git", "show", "--no-textconv",
                                           "%s:%s" % (sha, page)], root), added)
    found &= _numbers_of(doc)
    at = datetime.datetime.fromtimestamp(int(stamp), datetime.timezone.utc)
    base = {"said": subject.strip()[:features.SAID_MAX],
            "at": at.strftime("%Y-%m-%dT%H:%M:%SZ"), "by": person, "route": ROUTE}
    short = sha[:SHA_KEEP]
    if not found:
        line = {"n": None}
        line.update(base)
        line.update({"kind": "unnumbered", "commit": short, "logged": "auto"})
        return [line]
    out = []
    for n in sorted(found):
        line = {"n": n}
        line.update(base)
        line.update({"commit": short, "logged": "auto"})
        out.append(line)
    return out


def autolog(repo_root, person, git_runner=None, dry_run=False):
    """Log every unlogged commit that changed one of `person`'s drafts; see
    the module docstring. Returns what it wrote (or, with dry_run, would
    write), oldest commit first."""
    runner = git_runner or features.run_git
    done = []
    if not person:
        return done
    drafts = "%s/%s/drafts/" % (features.VIEWERS, person)
    cache = {}
    try:
        listing = _git(runner, ["git", "log", "--no-merges", "--full-history",
                                "--no-renames", "--diff-filter=M", "--reverse",
                                "--format=%H", "HEAD", "--", drafts], repo_root)
    except _GitFailed as exc:
        _warn(str(exc))
        return done
    for sha in [s.strip() for s in listing.splitlines() if s.strip()]:
        try:
            found = _commit(sha, repo_root, person, runner, cache)
            if found is None:
                continue
            head, pages, statuses = found
            for page, family in pages:
                log_rel = page[:-len(".html")] + ".changes.jsonl"
                if _already_logged(sha, log_rel, statuses, repo_root, runner):
                    continue
                doc = _family_list(repo_root, family, cache)
                keep = []
                for entry in _entries(head, page, person, doc, repo_root, runner):
                    findings = features.validate_changes([entry], doc)
                    if findings:
                        _warn("%s %s: not written — %s"
                              % (sha[:SHA_KEEP], page, "; ".join(findings)))
                        continue
                    keep.append(entry)
                if keep and not dry_run:
                    _append(os.path.join(repo_root, log_rel), keep)
                done.extend({"page": page, "log": log_rel, "entry": e} for e in keep)
        except _GitFailed as exc:
            _warn("%s: %s" % (sha[:SHA_KEEP], exc))
            return done
        except Exception as exc:  # bad data in one commit never stops the rest
            _warn("%s skipped — %s: %s" % (sha[:SHA_KEEP], type(exc).__name__, exc))
    return done
