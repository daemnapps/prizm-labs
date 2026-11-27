#!/usr/bin/env python3
"""PF-3c (family compare): every person's version of one page family, side by
side, by number. Read-only.

    python3 features.py compare <family> [--json]

Versions are every person's live page and drafts of the family, as PF-8 (show
my pages)'s pages.list_pages finds them, one person folder at a time under
platform/views/viewers/ (the folders /page-compare listed). Rows are the
numbers of _templates/<family>.features.json (retired numbers are not rows),
plus any number a version's page or change log carries that the list does
not. Each cell is one word:

    added    the row's `added_by` is this version's person, and the version's
             change log names the number or its page carries it; a number
             the list does not have at all is `added` wherever it shows up
    changed  the version's own change log (<page>.changes.jsonl) names it
    kept     the version's page carries data-feature="<n>"
    hidden   the team page (_templates/<family>.html) carries it, this
             version's page does not
    —        neither the team page nor this version carries it (not built,
             or not anchored), so it is not judged

The anchors are read the way pages.py counts them (pages.NUMBER_RE over the
page text without the baked page-prefs style, as live.feature_count and
draft.py's catch-up do), so a data-feature written by a page's own script
counts; check.py's static-DOM scan does not see those. Then one summary line
per version: n changed, n hidden, n added. --json prints the same as data.

READ-ONLY BY DESIGN: reads the family list, the team page, each version's page
and change log, and pages.list_pages' own reads; writes nothing. Git only
through pages.list_pages (read-only verbs). Stdlib only, Python 3.9.

    exit 0 printed · 2 unknown family (named, with the families that exist) or
    a bad argument · 3 a family list, page or change log that cannot be read
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import features  # noqa: E402  PF-1 (page-features skeleton), same component
import live  # noqa: E402  PF-7 (working versions), same component
import pages  # noqa: E402  PF-8 (show my pages), same component

ADDED, CHANGED, KEPT, HIDDEN, NOT_JUDGED = "added", "changed", "kept", "hidden", "—"
CELLS = [ADDED, CHANGED, KEPT, HIDDEN, NOT_JUDGED]
NAME_SHOWN = 32
LEGEND = ("added = this person asked for the number (added_by) and it is in their version; "
          "changed = named in the version's change log; kept = on the page; "
          "hidden = on the team page, not on this one; — = on neither, not judged")


class Unreadable(Exception):
    """A file compare needs and cannot read (exit 3)."""


def _read(path, rel):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise Unreadable("UNREADABLE: %s — %s" % (rel, exc))


def _anchored(text):
    """The numbers a page carries as data-feature="<n>", counted as pages.py counts them."""
    return set(int(n) for n in pages.NUMBER_RE.findall(live.PAGE_PREFS_RE.sub("", text)))


def _logged(rel, root, notes):
    """The numbers a version's change log names; no log is no changes."""
    log_rel = live._log_rel(rel)
    path = os.path.join(root, log_rel)
    if not os.path.isfile(path):
        return set()
    try:
        lines = features.read_changes(path)
    except features.LoadError as exc:
        raise Unreadable(str(exc))
    out = set()
    for i, line in enumerate(lines, 1):
        try:
            obj = json.loads(line)
        except ValueError:
            obj = None
        n = obj.get("n") if isinstance(obj, dict) else None
        if features._is_int(n):
            out.add(n)
        else:
            notes.append("%s line %d: names no number; skipped" % (log_rel, i))
    return out


def _versions(family, root, runner):
    """[(id, person, kind, name, path)] — every person's live page and drafts of the family,
    from pages.list_pages, people by folder name."""
    top = os.path.join(root, features.VIEWERS)
    out = []
    for person in sorted(os.listdir(top)) if os.path.isdir(top) else []:
        if (person.startswith("_") or not pages.PERSON_RE.match(person)
                or not os.path.isdir(os.path.join(top, person))):
            continue
        result = pages.list_pages(person=person, root=root, runner=runner)
        for fam in result["families"]:
            if fam["family"] != family:
                continue
            if fam["live"]:
                out.append(("%s/live" % person, person, "live", "live", fam["live"]["path"]))
            for draft in fam["drafts"]:
                out.append(("%s/%s" % (person, draft["name"]), person, "draft", draft["name"],
                            draft["path"]))
    return out


def _cell(n, added_by, listed, person, logged, anchored, on_team):
    mine = (added_by == person or not listed) and (n in logged or n in anchored)
    if mine:
        return ADDED
    if n in logged:
        return CHANGED
    if n in anchored:
        return KEPT
    return HIDDEN if n in on_team else NOT_JUDGED


def compare(family, *, root=None, runner=None):
    """The family's versions by number; see the module docstring. Writes nothing.
    {"family", "refused", "families", "versions", "rows", "notes"}; "refused" names an
    unknown family. Unreadable when a page or change log cannot be read;
    features.LoadError when a family list cannot be."""
    root = os.path.abspath(root or features.ROOT)
    runner = runner or features.run_git
    known = [f for f, _ in pages._families(root)]
    result = {"family": family, "refused": None, "families": known, "template": None,
              "versions": [], "rows": [], "notes": []}
    if family not in known:
        result["refused"] = "%r is not a page family (families: %s)" % (
            family, ", ".join(known) or "none")
        return result
    doc = features.load(os.path.join(root, features.TEMPLATES, "%s.features.json" % family))
    entries = [e for e in (doc.get("features") if isinstance(doc, dict) else None) or []
               if isinstance(e, dict) and features._is_int(e.get("n"))]
    retired = features._retired_numbers(doc) if isinstance(doc, dict) else set()
    team_rel = "%s/%s.html" % (features.TEMPLATES, family)
    result["template"] = team_rel
    on_team = _anchored(_read(os.path.join(root, team_rel), team_rel))
    notes = result["notes"]
    seen = []
    for vid, person, kind, name, rel in _versions(family, root, runner):
        anchored = _anchored(_read(os.path.join(root, rel), rel))
        seen.append({"id": vid, "person": person, "kind": kind, "name": name, "path": rel,
                     "_logged": _logged(rel, root, notes), "_anchored": anchored})
    by_n = dict((e["n"], e) for e in entries if e["n"] not in retired)
    extra = set()
    for v in seen:
        extra |= (v["_logged"] | v["_anchored"])
    extra = sorted(n for n in extra if n not in by_n and n not in retired)
    for n in sorted(by_n) + extra:
        entry = by_n.get(n)
        listed = entry is not None
        added_by = entry.get("added_by") if listed else None
        added_by = added_by if features._nonempty_str(added_by) else None
        cells = dict((v["id"], _cell(n, added_by, listed, v["person"], v["_logged"],
                                     v["_anchored"], on_team)) for v in seen)
        result["rows"].append({
            "n": n, "tag": "%s%d" % (features.KINDS.get(entry.get("kind"), "?") if listed else "?", n),
            "name": entry.get("name") if listed and isinstance(entry.get("name"), str) else None,
            "listed": listed, "added_by": added_by, "cells": cells})
        if not listed:
            notes.append("%d is not on %s.features.json: a version carries it" % (n, family))
    for v in seen:
        v.pop("_logged")
        v.pop("_anchored")
        for word in (CHANGED, HIDDEN, ADDED):
            v[word] = sum(1 for r in result["rows"] if r["cells"][v["id"]] == word)
        result["versions"].append(v)
    return result


def _summary(v):
    return "%s: %d changed, %d hidden, %d added · %s" % (
        v["id"], v[CHANGED], v[HIDDEN], v[ADDED], v["path"])


def render(result):
    """Plain lines: the table, then one summary line per version, the legend, notes."""
    if result.get("refused"):
        return ["refused: %s" % result["refused"]]
    versions = result["versions"]
    lines = ["%s — %d version%s, %d number%s; the team page is %s" % (
        result["family"], len(versions), "" if len(versions) == 1 else "s",
        len(result["rows"]), "" if len(result["rows"]) == 1 else "s", result["template"])]
    if not versions:
        lines.append("no one has a live page or a draft of %s yet" % result["family"])
    else:
        head = ["number", "name", "added by"] + [v["id"] for v in versions]
        body = []
        for row in result["rows"]:
            name = row["name"] or "(not on the family list)"
            if len(name) > NAME_SHOWN:
                name = name[:NAME_SHOWN - 1] + "…"
            body.append([row["tag"], name, row["added_by"] or ""]
                        + [row["cells"][v["id"]] for v in versions])
        widths = [max(len(r[i]) for r in [head] + body) for i in range(len(head))]
        for r in [head] + body:
            lines.append("  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip())
        lines.append("")
        lines.extend(_summary(v) for v in versions)
        lines.append("key: %s" % LEGEND)
    lines.extend("note: %s" % note for note in result["notes"])
    return lines


def main(argv=None, *, root=None, runner=None):
    """exit 0 printed · 2 unknown family or a bad argument · 3 unreadable."""
    parser = argparse.ArgumentParser(prog="features.py compare")
    parser.add_argument("family")
    parser.add_argument("--json", action="store_true")
    try:
        opts = parser.parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit:
        return 2
    try:
        result = compare(opts.family, root=root, runner=runner)
    except (features.LoadError, Unreadable) as exc:
        print(exc)
        return 3
    if opts.json:
        print(json.dumps(result, indent=1, ensure_ascii=False))
    else:
        for line in render(result):
            print(line)
    return 2 if result["refused"] else 0


if __name__ == "__main__":
    encoding = (getattr(sys.stdout, "encoding", None) or "").lower().replace("-", "")
    if encoding != "utf8" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
