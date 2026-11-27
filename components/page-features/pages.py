#!/usr/bin/env python3
"""PF-8 (show my pages): one person's pages, read-only.

    python3 features.py pages [--person P]

Per family list (_templates/<family>.features.json): the person's LIVE page
<p>/<family>.html (when it went live and from which template base, read from
<p>/<family>.live.jsonl; drift = that base against the template's blob now;
how many distinct numbers it carries), or that it is PREPARED (PF-9 (share
check)'s mark, live.PREPARED_META in its <head>); each DRAFT
<p>/drafts/<family>--<name>.html (made from the template, an old live, or a
sharer; its change count and newest change line); and "available" where the
person has neither. Then the person's other pages, then notes. Every page
carries its save state: saved / not saved (uncommitted) / not shared
(committed, not on the last fetched origin/main).

PF-19 (behind notice): a live page whose base is not the template's blob now
is BEHIND: its entry carries "behind" {since, commits, line} — the template's
commits after the one that made the base (subjects, newest first), the date of
the first of them, and the line "Your page is behind the team version since
<date> — say 'catch up my <family> page'" (the page server's strip, the home
page and render() say that same line) — and "buttons", the reason its direct
buttons copy a request instead (live.stale_actions), or None.

READ-ONLY BY DESIGN: reads <p>/, <p>/drafts/, _templates/*.features.json,
_templates/<family>.html and .actions.json, and writes nothing. Git only
through the runner (features.run_git by default) and only `status
--porcelain`, `log --name-only` (one each per run), `hash-object` (one per
family with a page) and `log --raw` of the template (one per live page that
is behind); a person with no folder runs no git at all. Saving is PF-1c
(plain-words changes)'s `features.py autosave`. Stdlib only, Python 3.9.
"""
import argparse
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
import check  # noqa: E402,F401  PF-3 (feature check), same component

NUMBER_RE = re.compile(r'data-feature="(\d+)"')
OLD_LIVE_RE = re.compile(r"^(\d{4}-\d\d-\d\d)(-\d+)?$")
PERSON_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
SAID_SHOWN = 60
NOTE_UPDATE = "update available: waits for PF-9 (share check)'s named mode"
NOTE_SNAPSHOTS = "snapshots: none recorded"
NOTE_FETCH = ("not shared is against the last fetched origin/main; "
              "this command never fetches")
NOTE_SAVE = "to save and share: features.py autosave"
STANDING_NOTES = [NOTE_UPDATE, NOTE_SNAPSHOTS, NOTE_FETCH]
# PF-19 (behind notice)
BEHIND = "Your page is behind the team version since %s — say 'catch up my %s page'"
BEHIND_UNDATED = "Your page is behind the team version — say 'catch up my %s page'"
LOG_FORMAT = "--format=%x1e%H%x1f%cI%x1f%s"
SAVED, NOT_SAVED, NOT_SHARED = "saved", "not saved", "not shared"


def _read_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _families(root):
    """[(family, owner or None)] from _templates/*.features.json, by name.
    features.LoadError when a list cannot be read."""
    out = []
    pattern = os.path.join(root, features.TEMPLATES, "*.features.json")
    for path in sorted(glob.glob(pattern)):
        doc = features.load(path)
        owner = doc.get("owner") if isinstance(doc, dict) else None
        out.append((features.family_of(path), owner if features._nonempty_str(owner) else None))
    return out


def _numbers(text):
    """Distinct n over data-feature="<n>" in the page text, outside the baked
    page-prefs style (as live.feature_count counts)."""
    return len(set(NUMBER_RE.findall(live.PAGE_PREFS_RE.sub("", text))))


def _template_blob(family, root, runner, notes):
    rel = "%s/%s.html" % (features.TEMPLATES, family)
    if not os.path.isfile(os.path.join(root, rel)):
        notes.append("%s does not exist; drift unknown" % rel)
        return None
    code, out, err = runner(["git", "hash-object", "--", rel], root)
    blob = out.strip() if code == 0 else ""
    if not live.SHA40_RE.match(blob):
        notes.append("%s: no blob id (%s); drift unknown" % (rel, features._first_line(out, err)))
        return None
    return blob


def _drift(base, now):
    if base is None or now is None:
        return "unknown"
    return "yes" if base != now else "no"


def behind_line(family, since):
    """PF-19 (behind notice): the one line a behind live page is said with, everywhere."""
    return (BEHIND % (since, family)) if since else (BEHIND_UNDATED % family)


def _since_base(family, base, root, runner, notes):
    """PF-19 (behind notice): {since, commits, line} for a live page cut from `base`: the template's commits after
    the one that wrote that blob (subjects only, newest first) and the date of the first of them. One `git log
    --raw` of the template; a base its history never wrote, or a log that fails, names no commits (a note says
    which)."""
    rel = "%s/%s.html" % (features.TEMPLATES, family)
    code, out, err = runner(["git", "log", "--no-abbrev", "--raw", LOG_FORMAT, "--", rel], root)
    commits, dates, found = [], [], False
    if code != 0:
        notes.append("%s: no history (%s); the commits since the page's base unknown"
                     % (rel, features._first_line(out, err)))
    else:
        for chunk in (out or "").split("\x1e")[1:]:
            lines = chunk.split("\n")
            head = lines[0].split("\x1f")
            if len(head) < 3:
                continue
            wrote = [parts[3] for parts in (line.split() for line in lines[1:] if line.startswith(":"))
                     if len(parts) >= 5]
            if base in wrote:
                found = True
                break
            commits.append(head[2])
            dates.append(head[1][:10])
        if not found:
            notes.append("%s: its history never wrote the base %s; the commits since it unknown" % (rel, base[:12]))
            commits, dates = [], []
    since = dates[-1] if dates else None
    return {"since": since, "commits": commits, "line": behind_line(family, since)}


def _last_live_line(rel, root, notes):
    """The last valid line of <p>/<family>.live.jsonl, or None."""
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        notes.append("%s does not exist; went live unknown" % rel)
        return None
    try:
        lines = features.read_changes(path)
    except features.LoadError as exc:
        notes.append("%s; went live unknown" % exc)
        return None
    findings = live.validate_live_log(lines)
    bad = set()
    for finding in findings:
        match = re.match(r"^line (\d+):", finding)
        if match:
            bad.add(int(match.group(1)))
    if findings:
        notes.append("%s: %d invalid line%s skipped — %s" % (
            rel, len(bad), "" if len(bad) == 1 else "s", "; ".join(findings)))
    good = [json.loads(line) for i, line in enumerate(lines, 1) if i not in bad]
    return good[-1] if good else None


def _newest(rel, lines, notes):
    try:
        obj = json.loads(lines[-1])
    except ValueError:
        obj = None
    if not isinstance(obj, dict):
        notes.append("%s: its last line is not a JSON object; newest unknown" % rel)
        return None
    n = obj.get("n")
    said = obj.get("said")
    said = said if isinstance(said, str) else ""
    return "%s · %s · %s" % (n if features._is_int(n) else "no number",
                             obj.get("at") if isinstance(obj.get("at"), str) else "no time",
                             said[:SAID_SHOWN])


def _made_from(name, base):
    match = OLD_LIVE_RE.match(name)
    if match:
        return "old live %s" % match.group(1)
    if name.startswith("from-") and len(name) > len("from-"):
        return "shared by %s" % name[len("from-"):]
    return "template" if base else "unknown"


def _draft(rel, name, root, notes):
    path = os.path.join(root, rel)
    try:
        stamp = live.SHA_RE.search(_read_text(path))
    except (OSError, UnicodeDecodeError) as exc:
        notes.append("%s: unreadable — %s" % (rel, exc))
        stamp = None
    base = stamp.group(1) if stamp else None
    log_rel = live._log_rel(rel)
    changes, newest, lines = 0, None, []
    if not os.path.isfile(os.path.join(root, log_rel)):
        notes.append("%s does not exist; 0 changes" % log_rel)
    else:
        try:
            lines = features.read_changes(os.path.join(root, log_rel))
        except features.LoadError as exc:
            notes.append("%s; 0 changes shown" % exc)
    if lines:
        changes = len(lines)
        newest = _newest(log_rel, lines, notes)
    return {"name": name, "path": rel, "made_from": _made_from(name, base), "base": base,
            "drift": "unknown", "changes": changes, "newest": newest,
            "_paths": [rel, log_rel]}


def _live(rel, family, person, root, notes):
    path = os.path.join(root, rel)
    try:
        text = _read_text(path)
    except (OSError, UnicodeDecodeError) as exc:
        notes.append("%s: unreadable — %s" % (rel, exc))
        text = ""
    record_rel = live._live_log_rel(person, family)
    last = _last_live_line(record_rel, root, notes)
    return {"path": rel, "prepared": live.PREPARED_META in live._head(text),
            "went_live": last["at"] if last else None,
            "base": last["base"] if last else None, "now": None, "drift": "unknown",
            "numbers": _numbers(text), "behind": None, "buttons": live.stale_actions(rel, root),
            "_paths": [rel, live._log_rel(rel), record_rel]}


def _listed(path, paths):
    """True when git named `path` itself or a folder holding it."""
    for item in paths:
        if item == path or (item.endswith("/") and path.startswith(item)):
            return True
    return False


def _save_states(pages, prefix, root, runner):
    """One status and one log call for every page; each page's "save"."""
    code, out, err = runner(["git", "status", "--porcelain", "--", prefix], root)
    status_error = None if code == 0 else features._first_line(out, err)
    unsaved = features._porcelain_paths(out, prefix) if code == 0 else []
    code, out, err = runner(["git", "log", "--name-only", "--format=", "origin/main..HEAD",
                             "--", prefix], root)
    log_error = None if code == 0 else features._first_line(out, err)
    unshared = [line.strip() for line in out.splitlines() if line.strip()] if code == 0 else []
    error = status_error or log_error
    for page in pages:
        if error is not None:
            page["save"] = "unknown (%s)" % error
        elif any(_listed(p, unsaved) for p in page["_paths"]):
            page["save"] = NOT_SAVED
        elif any(_listed(p, unshared) for p in page["_paths"]):
            page["save"] = NOT_SHARED
        else:
            page["save"] = SAVED


def list_pages(*, person=None, root=None, runner=None):
    """The person's pages; see the module docstring. Writes nothing.
    features.LoadError when a family list cannot be read."""
    root = os.path.abspath(root or features.ROOT)
    runner = runner or features.run_git
    person = features._person(person, root, runner)
    result = {"person": person or "", "refused": None, "families": [], "other": [],
              "notes": []}
    if not person:
        result["refused"] = "no person — pass --person or set git config user.email"
        return result
    if not PERSON_RE.match(person) or person.startswith("_"):
        result["refused"] = "%r is not a person's folder name" % person
        return result
    families = _families(root)
    known = set(f for f, _ in families)
    prefix = "%s/%s/" % (features.VIEWERS, person)
    folder = os.path.join(root, prefix)
    notes = []
    if not os.path.isdir(folder):
        notes.append("%s does not exist: no pages yet" % prefix)
    lives, drafts, other = {}, {}, []
    if os.path.isdir(folder):
        for path in sorted(glob.glob(os.path.join(folder, "*.html"))):
            rel = features._relpath(path, root)
            family = os.path.basename(path)[:-len(".html")]
            if family in known:
                lives[family] = _live(rel, family, person, root, notes)
            else:
                other.append({"path": rel, "_paths": [rel, live._log_rel(rel)]})
        for path in sorted(glob.glob(os.path.join(folder, "drafts", "*.html"))):
            rel = features._relpath(path, root)
            match = features.DRAFT_RE.match(rel)
            if not match:
                notes.append("%s is not named <family>--<name>.html; not listed" % rel)
            elif match.group(2) not in known:
                notes.append("%s: no family list %s.features.json; not listed"
                             % (rel, match.group(2)))
            else:
                drafts.setdefault(match.group(2), []).append(
                    _draft(rel, match.group(3), root, notes))
    for family, owner in families:
        entry = {"family": family, "owner": owner, "live": lives.get(family),
                 "drafts": sorted(drafts.get(family, []), key=lambda d: d["name"])}
        entry["available"] = entry["live"] is None and not entry["drafts"]
        if not entry["available"]:
            now = _template_blob(family, root, runner, notes)
            if entry["live"] is not None:
                entry["live"]["now"] = now
                entry["live"]["drift"] = _drift(entry["live"]["base"], now)
                if entry["live"]["drift"] == "yes":
                    entry["live"]["behind"] = _since_base(family, entry["live"]["base"], root, runner, notes)
            for draft in entry["drafts"]:
                draft["drift"] = _drift(draft["base"], now)
        result["families"].append(entry)
    pages = [f["live"] for f in result["families"] if f["live"]] + [
        d for f in result["families"] for d in f["drafts"]] + other
    if pages:
        _save_states(pages, prefix, root, runner)
    for page in pages:
        page.pop("_paths")
    result["other"] = other
    notes.extend(STANDING_NOTES)
    if any(p["save"] in (NOT_SAVED, NOT_SHARED) for p in pages):
        notes.append(NOTE_SAVE)
    result["notes"] = notes
    return result


def _plural(k, word):
    return "%d %s%s" % (k, word, "" if k == 1 else "s")


def render(result):
    """Plain lines for a person; see the module docstring."""
    if result.get("refused"):
        return ["refused: %s" % result["refused"]]
    lines = []
    pad = " " * 12
    for fam in result["families"]:
        if fam["available"]:
            continue
        lines.append(fam["family"])
        page = fam["live"]
        if page and page["prepared"]:
            lines.append("  prepared  %s · goes live on first open: features.py first-open %s · %s"
                         % (page["path"], page["path"], page["save"]))
        elif page:
            lines.append("  live      %s · went live %s · drift %s · %s · %s" % (
                page["path"], page["went_live"] or "unknown", page["drift"],
                _plural(page["numbers"], "number"), page["save"]))
        if page:
            lines.append("%sopen %s" % (pad, page["path"]))
        if page and page.get("behind"):                 # PF-19 (behind notice)
            behind = page["behind"]
            lines.append("%s%s" % (pad, behind["line"]))
            lines.append("%steam commits since your base: %s" % (
                pad, len(behind["commits"]) if behind["commits"] else "none found"))
            lines.extend("%s  %s" % (pad, subject) for subject in behind["commits"])
        if page and page.get("buttons"):
            lines.append("%sbuttons: %s" % (pad, page["buttons"]))
        for draft in fam["drafts"]:
            newest = " · newest %s" % draft["newest"] if draft["newest"] else ""
            lines.append("  draft     %s · %s · from %s · %s%s · %s" % (
                draft["name"], draft["path"], draft["made_from"],
                _plural(draft["changes"], "change"), newest, draft["save"]))
            lines.append("%sopen %s" % (pad, draft["path"]))
    for fam in result["families"]:
        if fam["available"]:
            lines.append("available: %s (%s)" % (
                fam["family"], "owner %s" % fam["owner"] if fam["owner"] else "owner not set"))
    if result["other"]:
        lines.append("other pages:")
        for page in result["other"]:
            lines.append("  %s · %s" % (page["path"], page["save"]))
            lines.append("%sopen %s" % (pad, page["path"]))
    lines.extend("note: %s" % note for note in result["notes"])
    return lines


def main(argv=None, *, root=None, runner=None):
    """exit 0 listed · 2 refused or a bad argument · 3 a family list that
    cannot be read."""
    parser = argparse.ArgumentParser(prog="features.py pages")
    parser.add_argument("--person")
    try:
        opts = parser.parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit:
        return 2
    try:
        result = list_pages(person=opts.person, root=root, runner=runner)
    except features.LoadError as exc:
        print(exc)
        return 3
    for line in render(result):
        print(line)
    return 2 if result["refused"] else 0


if __name__ == "__main__":
    encoding = (getattr(sys.stdout, "encoding", None) or "").lower().replace("-", "")
    if encoding != "utf8" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
