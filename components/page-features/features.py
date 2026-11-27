#!/usr/bin/env python3
"""PF-1 (page-features skeleton): check a page's features.json against the v1
contract (features.schema.json beside this file), and convert the run-detail
seed into that contract.

    python3 features.py <features.json>
        exit 0 valid · 2 invalid (every finding printed, each naming its entry)
        · 3 missing, unreadable or not JSON
    python3 features.py --from-seed <seed.json> --out <file>
        writes from_seed(seed) as json.dumps(..., indent=1, ensure_ascii=False)

Stdlib only, Python 3.9. The number is a feature's identity; `where` only
locates an element on a page that carries no data-feature="n" tag. `status`
holds only draft | approved | deprecated (builder card rule 5); how built a
feature is goes in `state`.

PF-1b (feature anchors): v1.1, backward compatible. `"schema"` stays 1; a
file opts in with `"schema_minor": 1`. Each feature may carry `anchor`, the
page's data-feature value, which always equals str(n); in v1.1 every wired
feature must carry one. A file may keep `changes`, the requests people made
to it, each addressed by a feature number. v1 files validate as before.

PF-1c (plain-words changes): v1.2, backward compatible. `"schema"` stays 1; a
file opts in with `"schema_minor": 2` and every v1.1 rule still applies. The
file may keep `retired`, numbers taken out of use and reserved forever (a
retired n is never a feature again). A feature may carry `added_by` (the
person who asked for the number), `added`, `frame`, `owns`, `locked` and
`needs` (the data a not-built number waits for: data, where, written_by,
component). A not-built feature with `added_by` requires `needs`; `needs` on
any other state is a finding. A change line may carry `resolved: "claude"`
with `match` (the person named no number; their Claude chose it, and says
why), and `kind: "missing"` with `needs` (the request names data no source
holds). Each finding is also classed `format` (the mapping or the shape is
wrong) or `content` (a value only the list's owner can fix): validate_kinds.

    python3 features.py --convert <in.json> --out <out.json> [--findings <md>]
        convert(): the prototype family-list format → v1.2; exit 0 when no
        format finding is left (content findings go, by number, to the
        report: --findings, default examples/family-conversion-findings.md)
        · 2 format findings left · 3 unreadable
    python3 features.py --convert-changes <file.changes.jsonl>
        convert_changes(), in place: route "B" → "claude-code"
    python3 features.py --changes <file.changes.jsonl> <family.features.json>
        validate_changes(): exit 0 valid · 2 findings · 3 unreadable
    python3 features.py sync <page.html> <family.features.json> [--check]
        rewrites the page's one embedded fo-features block from the list;
        --check writes nothing: exit 0 in sync · 1 DRIFT, the differing numbers
    python3 features.py change <draft page> --n N --said TEXT [--person P]
            [--resolved claude --match TEXT] [--missing --needs JSON]
            [--family-list PATH]
        logs one change line beside the draft, then git add / commit / push
        of exactly those paths; exit 0 saved (shared or not) · 2 refused
    python3 features.py autosave [--person P]
        commits and pushes the person's own viewers folder, nothing else

PF-7 (working versions): a v1.2 feature may carry `critical: true`, set only
by the family's owner: the going-live check must find that number's field on
the real data files of every outcome. Only a wired feature, never a layout
one, may be critical; any value but true is a finding. No schema_minor bump.
Live versus draft is the folder (live.py, beside this file):

    python3 features.py check-live <draft page> [--person P]
        exit 0 "ready to go live: <draft> → <live>" + notes · 2 failures, one
        per line, each starting with its feature tag (D16: …) or "page:", or
        refused · 3 unreadable
    python3 features.py live <draft page> [--person P] [--no-share]
        the check, then the draft's live form written to <person>/<family>.html
        (the old live kept under drafts/), logged and shared; exit 0 live · 2
        not live or refused
    python3 features.py first-open <live page> [--person P] [--no-share]
        a PREPARED page's checks rerun on this machine; exit 0 live or already
        live · 2 not live or refused
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

STATUS_WORDS = ["draft", "approved", "deprecated"]
STATE_WORDS = ["wired", "after-card", "not-built"]
KINDS = {"data": "D", "rule": "R", "media": "M", "layout": "L", "action": "A"}

FILE_REQUIRED = ["schema", "title", "status", "kinds", "state_words", "features"]
FILE_OPTIONAL = ["page", "versions", "checked_against", "owner", "schema_minor",
                 "changes"]
ENTRY_REQUIRED = ["n", "name", "kind", "state", "status", "source"]
ENTRY_OPTIONAL = ["place", "note", "card", "where", "anchor"]
KIND_KEYS = ["letter", "name", "means"]
SOURCE_KEYS = ["component", "file", "field"]
WHERE_KEYS = ["sel", "text"]
SOURCE_NULL_KINDS = ("layout", "action", "rule")
NAME_MAX = 60
CARD_RE = re.compile(r"^[A-Z]{1,6}-\d+[a-z]?$")
FILE_SPLIT_RE = re.compile(r" · | → ")

# PF-1b (feature anchors), v1.1. "box" (an in-page change box) was dropped at
# re-filing on developer's word; "note" is a mark applied by the person's Claude.
SCHEMA_MINOR = 2
CHANGE_ROUTES = ["claude-code", "note"]
CHANGE_KEYS = ["n", "said", "at", "by", "route"]
SAID_MAX = 2000
AT_RE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d(:\d\d(\.\d+)?)?Z$")

# PF-1c (plain-words changes), v1.2: allowed only when schema_minor is 2.
FILE_OPTIONAL_V1_2 = ["retired"]
ENTRY_OPTIONAL_V1_2 = ["added_by", "added", "frame", "owns", "locked", "needs",
                       "critical"]
CHANGE_OPTIONAL = ["resolved", "match", "kind", "needs"]
RETIRED_REQUIRED = ["n", "name", "retired", "why"]
RETIRED_OPTIONAL = ["by"]
NEEDS_REQUIRED = ["data", "where"]
NEEDS_OPTIONAL = ["written_by", "component"]
DATE_RE = re.compile(r"^\d{4}-\d\d-\d\d$")
# PF-1d (auto-log page changes): a change line autosave wrote from a commit.
CHANGE_OPTIONAL = CHANGE_OPTIONAL + ["commit", "logged", "note"]
CHANGE_LOGGED = ["auto", "backfill"]
CHANGE_KINDS = ["missing", "unnumbered"]
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")

# A content finding names a value only the list's owner can fix; every other
# finding is format (a key, a word or a shape a mapping can put right).
CONTENT_PATTERNS = [
    re.compile(r": name is \d+ characters, over \d+$"),
    re.compile(r": source\.file is not repo-relative: "),
    re.compile(r": source\.\w+ is missing or empty$"),
    re.compile(r": a [\w-]+ \w+ feature needs a source, not null$"),
    re.compile(r": a wired feature needs an anchor in v1\.1$"),
    re.compile(r": card .* is not a card id"),
    re.compile(r": n \d+ is used twice"),
    re.compile(r": n \d+ is retired and must not be a feature"),
]


class LoadError(Exception):
    """A features file that is missing, unreadable or not JSON (exit 3)."""


def load(path):
    """Read a features file. Raises LoadError saying what went wrong."""
    if not os.path.isfile(path):
        raise LoadError("MISSING: %s" % path)
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise LoadError("UNREADABLE: %s — %s" % (path, exc))
    try:
        return json.loads(text)
    except ValueError as exc:
        raise LoadError("UNREADABLE: %s is not valid JSON — %s" % (path, exc))


def _nonempty_str(value):
    return isinstance(value, str) and value.strip() != ""


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _path_problem(part):
    """Why `part` is not a repo-relative path, or None."""
    if part == "":
        return "an empty part"
    if part.startswith("/"):
        return "%r starts with /" % part
    if part.startswith("~"):
        return "%r starts with ~" % part
    if ".." in part:
        return "%r contains .." % part
    return None


def _unknown_keys(obj, allowed, where):
    return ["%s: unknown key %r" % (where, k) for k in obj if k not in allowed]


def _minors():
    return tuple(range(SCHEMA_MINOR + 1))


def _needs_problems(needs, where):
    """Findings for a `needs` block: data and where required, written_by and
    component optional, every value a non-empty string, no other key."""
    if not isinstance(needs, dict):
        return ["%s: `needs` is not an object" % where]
    out = _unknown_keys(needs, NEEDS_REQUIRED + NEEDS_OPTIONAL, "%s: needs" % where)
    for key in NEEDS_REQUIRED:
        if key not in needs:
            out.append("%s: needs.%s is missing" % (where, key))
    for key in NEEDS_REQUIRED + NEEDS_OPTIONAL:
        if key in needs and not _nonempty_str(needs[key]):
            out.append("%s: needs.%s is empty or not a string" % (where, key))
    return out


def _check_retired(retired):
    out = []
    if not isinstance(retired, list):
        return ["file: `retired` is not a list"]
    seen = set()
    for i, item in enumerate(retired, 1):
        name = "retired %d" % i
        if not isinstance(item, dict):
            out.append("%s: not an object" % name)
            continue
        out.extend(_unknown_keys(item, RETIRED_REQUIRED + RETIRED_OPTIONAL, name))
        for key in RETIRED_REQUIRED:
            if key not in item:
                out.append("%s: `%s` is missing" % (name, key))
        if "n" in item:
            n = item["n"]
            if not (_is_int(n) and n >= 1):
                out.append("%s: n %r is not an integer >= 1" % (name, n))
            elif n in seen:
                out.append("%s: n %d is retired twice" % (name, n))
            else:
                seen.add(n)
        for key in ("name", "why", "by"):
            if key in item and not _nonempty_str(item[key]):
                out.append("%s: `%s` is empty or not a string" % (name, key))
        if "retired" in item and not (isinstance(item["retired"], str)
                                      and DATE_RE.match(item["retired"])):
            out.append("%s: retired %r is not a date (YYYY-MM-DD)"
                       % (name, item["retired"]))
    return out


def _retired_numbers(doc):
    """The retired numbers of a v1.2 file (an empty set otherwise)."""
    if _schema_minor(doc) < 2 or not isinstance(doc.get("retired"), list):
        return set()
    return {r["n"] for r in doc["retired"]
            if isinstance(r, dict) and _is_int(r.get("n"))}


def _check_file_level(doc):
    out = []
    minor = _schema_minor(doc)
    optional = FILE_OPTIONAL + (FILE_OPTIONAL_V1_2 if minor >= 2 else [])
    out.extend(_unknown_keys(doc, FILE_REQUIRED + optional, "file"))
    for key in FILE_REQUIRED:
        if key not in doc:
            out.append("file: `%s` is missing" % key)

    if "schema" in doc and not (_is_int(doc["schema"]) and doc["schema"] == 1):
        out.append("file: schema %r is not 1" % (doc["schema"],))
    if "schema_minor" in doc and not (_is_int(doc["schema_minor"])
                                      and doc["schema_minor"] in _minors()):
        out.append("file: schema_minor %r is not %s or %d"
                   % (doc["schema_minor"], ", ".join(str(m) for m in _minors()[:-1]),
                      SCHEMA_MINOR))
    if minor >= 2 and "retired" in doc:
        out.extend(_check_retired(doc["retired"]))
    if "changes" in doc and not isinstance(doc["changes"], list):
        out.append("file: `changes` is not a list")
    if "title" in doc and not _nonempty_str(doc["title"]):
        out.append("file: `title` is empty or not a string")
    if "status" in doc and doc["status"] not in STATUS_WORDS:
        out.append("file: status %r is not one of %s"
                   % (doc["status"], " | ".join(STATUS_WORDS)))
    for key in ("checked_against", "owner"):
        if key in doc and not isinstance(doc[key], str):
            out.append("file: `%s` is not a string" % key)

    kinds = doc.get("kinds")
    if "kinds" in doc:
        if not isinstance(kinds, dict):
            out.append("file: `kinds` is not an object")
        else:
            for name in KINDS:
                if name not in kinds:
                    out.append("file: kinds is missing %r" % name)
            for name in kinds:
                if name not in KINDS:
                    out.append("file: kinds has %r, not one of the five" % name)
            if set(kinds) == set(KINDS) and list(kinds) != list(KINDS):
                out.append("file: kinds are not in the order %s"
                           % ", ".join(KINDS))
            for name, spec in kinds.items():
                if name not in KINDS:
                    continue
                where = "file: kind %r" % name
                if not isinstance(spec, dict):
                    out.append("%s is not an object" % where)
                    continue
                out.extend(_unknown_keys(spec, KIND_KEYS, where))
                if spec.get("letter") != KINDS[name]:
                    out.append("%s has letter %r, not %r"
                               % (where, spec.get("letter"), KINDS[name]))
                for key in ("name", "means"):
                    if not _nonempty_str(spec.get(key)):
                        out.append("%s: `%s` is missing or empty" % (where, key))

    if "state_words" in doc:
        words = doc["state_words"]
        if not isinstance(words, dict):
            out.append("file: `state_words` is not an object")
        else:
            for word in STATE_WORDS:
                if word not in words:
                    out.append("file: state_words is missing %r" % word)
            for word, meaning in words.items():
                if word not in STATE_WORDS:
                    out.append("file: state_words has %r, not one of %s"
                               % (word, " | ".join(STATE_WORDS)))
                elif not _nonempty_str(meaning):
                    out.append("file: state_words %r has no meaning" % word)

    if "page" not in doc and "versions" not in doc:
        out.append("file: neither `page` nor `versions` — at least one names the page")
    if "page" in doc:
        page = doc["page"]
        if not isinstance(page, str):
            out.append("file: `page` is not a string")
        else:
            problem = _path_problem(page.strip())
            if problem:
                out.append("file: page is not a repo path: %s" % problem)
    if "versions" in doc:
        versions = doc["versions"]
        if not isinstance(versions, dict) or not versions:
            out.append("file: `versions` is not a non-empty object")
        else:
            for label, path in versions.items():
                if not isinstance(path, str):
                    out.append("file: version %r is not a string" % label)
                    continue
                problem = _path_problem(path.strip())
                if problem:
                    out.append("file: version %r is not a repo path: %s"
                               % (label, problem))

    if "features" in doc and not isinstance(doc["features"], list):
        out.append("file: `features` is not a list")
    return out


def _labels(doc):
    """The version labels `where` may use, or None when there is nothing to
    check against (no versions and no page: a file-level finding covers it)."""
    versions = doc.get("versions")
    if isinstance(versions, dict) and versions:
        return set(versions)
    if "versions" in doc:
        return None
    if "page" in doc:
        return set()
    return None


def _schema_minor(doc):
    """The file's minor version: 0 when absent, and 0 when invalid (the
    file-level finding names it, so entries are not flagged twice)."""
    minor = doc.get("schema_minor", 0)
    return minor if _is_int(minor) and minor in _minors() else 0


def _check_entry_v1_2(entry, name):
    """The v1.2 entry keys: added_by, added, frame, owns, locked, needs,
    critical."""
    out = []
    if "critical" in entry:
        if entry["critical"] is not True:
            out.append("%s: critical %r is not true (leave it out when the "
                       "feature is not critical)" % (name, entry["critical"]))
        if entry.get("state") != "wired":
            out.append("%s: `critical` is only for a wired feature, not %r"
                       % (name, entry.get("state")))
        if entry.get("kind") == "layout":
            out.append("%s: `critical` is not for a layout feature" % name)
    if "added_by" in entry and not _nonempty_str(entry["added_by"]):
        out.append("%s: `added_by` is empty or not a string" % name)
    if "added" in entry and not (isinstance(entry["added"], str)
                                 and DATE_RE.match(entry["added"])):
        out.append("%s: added %r is not a date (YYYY-MM-DD)" % (name, entry["added"]))
    if "frame" in entry and not (entry["frame"] is None
                                 or isinstance(entry["frame"], str)):
        out.append("%s: `frame` is neither a string nor null" % name)
    for key in ("owns", "locked"):
        if key in entry:
            value = entry[key]
            if not (isinstance(value, list) and all(_nonempty_str(v) for v in value)):
                out.append("%s: `%s` is not a list of setting names" % (name, key))
    state = entry.get("state")
    if "needs" in entry:
        if state != "not-built":
            out.append("%s: `needs` is only for a not-built feature, not %r"
                       % (name, state))
        out.extend(_needs_problems(entry["needs"], name))
    elif state == "not-built" and "added_by" in entry:
        out.append("%s: a not-built feature added by a person needs `needs` "
                   "(data, where, written_by)" % name)
    return out


def _check_entry(entry, name, labels, minor=0):
    out = []
    optional = ENTRY_OPTIONAL + (ENTRY_OPTIONAL_V1_2 if minor >= 2 else [])
    out.extend(_unknown_keys(entry, ENTRY_REQUIRED + optional, name))
    for key in ENTRY_REQUIRED:
        if key not in entry:
            out.append("%s: `%s` is missing" % (name, key))

    if "name" in entry:
        title = entry["name"]
        if not _nonempty_str(title):
            out.append("%s: `name` is empty or not a string" % name)
        elif len(title) > NAME_MAX:
            out.append("%s: name is %d characters, over %d"
                       % (name, len(title), NAME_MAX))

    kind = entry.get("kind")
    if "kind" in entry and kind not in KINDS:
        out.append("%s: kind %r is not one of %s"
                   % (name, kind, " | ".join(KINDS)))

    state = entry.get("state")
    if "state" in entry and state not in STATE_WORDS:
        extra = " (a status word: status is not a state)" if state in STATUS_WORDS else ""
        out.append("%s: state %r is not one of %s%s"
                   % (name, state, " | ".join(STATE_WORDS), extra))

    if "status" in entry and entry["status"] not in STATUS_WORDS:
        extra = (" (a state word: it belongs in `state`)"
                 if entry["status"] in STATE_WORDS else "")
        out.append("%s: status %r is not one of %s%s"
                   % (name, entry["status"], " | ".join(STATUS_WORDS), extra))

    if "source" in entry:
        source = entry["source"]
        if source is None:
            if kind in ("data", "media") and state in ("wired", "after-card"):
                out.append("%s: a %s %s feature needs a source, not null"
                           % (name, state, kind))
        elif not isinstance(source, dict):
            out.append("%s: `source` is neither an object nor null" % name)
        else:
            out.extend(_unknown_keys(source, SOURCE_KEYS, "%s: source" % name))
            for key in SOURCE_KEYS:
                if not _nonempty_str(source.get(key)):
                    out.append("%s: source.%s is missing or empty" % (name, key))
            if _nonempty_str(source.get("file")):
                for part in FILE_SPLIT_RE.split(source["file"]):
                    problem = _path_problem(part.strip())
                    if problem:
                        out.append("%s: source.file is not repo-relative: %s"
                                   % (name, problem))

    for key in ("place", "note"):
        if key in entry and not isinstance(entry[key], str):
            out.append("%s: `%s` is not a string" % (name, key))
    if "card" in entry and not (isinstance(entry["card"], str)
                                and CARD_RE.match(entry["card"])):
        out.append("%s: card %r is not a card id (^[A-Z]{1,6}-\\d+[a-z]?$)" % (name, entry["card"]))

    if "anchor" in entry:
        anchor = entry["anchor"]
        n = entry.get("n")
        if not isinstance(anchor, str):
            out.append("%s: anchor is not a string" % name)
        elif _is_int(n) and n >= 1 and anchor != str(n):
            out.append("%s: anchor %r is not %r (the data-feature value is the "
                       "feature's number)" % (name, anchor, str(n)))
    elif minor >= 1 and state == "wired":
        out.append("%s: a wired feature needs an anchor in v1.1" % name)

    if "where" in entry:
        where = entry["where"]
        if not isinstance(where, dict):
            out.append("%s: `where` is not an object" % name)
        else:
            for label, spot in where.items():
                at = "%s: where %r" % (name, label)
                if labels is not None and label not in labels:
                    out.append("%s is not a label in `versions`" % at)
                if spot is None:
                    continue
                if not isinstance(spot, dict):
                    out.append("%s is neither an object nor null" % at)
                    continue
                out.extend(_unknown_keys(spot, WHERE_KEYS, at))
                if not _nonempty_str(spot.get("sel")):
                    out.append("%s: `sel` is missing or empty" % at)
                if "text" not in spot:
                    out.append("%s: `text` is missing (a string or null)" % at)
                elif spot["text"] is not None and not isinstance(spot["text"], str):
                    out.append("%s: `text` is neither a string nor null" % at)
    if minor >= 2:
        out.extend(_check_entry_v1_2(entry, name))
    return out


def _check_change_v1_2(change, name):
    """The v1.2 change keys: resolved + match, kind "missing" + needs."""
    out = []
    if "resolved" in change:
        if change["resolved"] != "claude":
            out.append("%s: resolved %r is not 'claude'" % (name, change["resolved"]))
        if "match" not in change:
            out.append("%s: `match` is missing (a resolved change says why "
                       "this number, in one sentence)" % name)
    if "match" in change and not _nonempty_str(change["match"]):
        out.append("%s: `match` is empty or not a string" % name)
    unnumbered = "kind" in change and change["kind"] == "unnumbered"
    if unnumbered:
        if change.get("n") is not None:
            out.append("%s: kind 'unnumbered' needs n null" % name)
        if "commit" not in change:
            out.append("%s: `commit` is missing (an unnumbered line names its "
                       "commit)" % name)
    elif "kind" in change:
        if change["kind"] != "missing":
            out.append("%s: kind %r is not 'missing'" % (name, change["kind"]))
        elif "needs" not in change:
            out.append("%s: `needs` is missing (a missing-data change names "
                       "the data, where it lives and who writes it)" % name)
    if "needs" in change:
        out.extend(_needs_problems(change["needs"], name))
    # PF-1d (auto-log page changes): commit, logged, note.
    if "commit" in change and not (isinstance(change["commit"], str)
                                   and COMMIT_RE.match(change["commit"])):
        out.append("%s: commit %r is not a 7-40 character hex sha"
                   % (name, change["commit"]))
    if "logged" in change:
        if change["logged"] not in CHANGE_LOGGED:
            out.append("%s: logged %r is not auto | backfill" % (name, change["logged"]))
        if "commit" not in change and not unnumbered:
            out.append("%s: `commit` is missing (a logged line names its commit)"
                       % name)
    if "note" in change and not _nonempty_str(change["note"]):
        out.append("%s: `note` is empty or not a string" % name)
    return out


def _check_changes(changes, numbers, minor=0, retired=(), label="changes"):
    """Each request in the `changes` log as one finding per defect, named
    "changes 2: ..." ("line 2: ..." for a person's changes.jsonl). `numbers`
    is the file's feature numbers, or None when `features` is not a list (a
    file-level finding covers that). From minor 2 the v1.2 keys are allowed
    and a retired number is named as retired."""
    out = []
    allowed = CHANGE_KEYS + (CHANGE_OPTIONAL if minor >= 2 else [])
    for i, change in enumerate(changes, 1):
        name = "%s %d" % (label, i)
        if not isinstance(change, dict):
            out.append("%s: not an object" % name)
            continue
        out.extend(_unknown_keys(change, allowed, name))
        for key in CHANGE_KEYS:
            if key not in change:
                out.append("%s: `%s` is missing" % (name, key))
        if "n" in change:
            n = change["n"]
            if n is None and minor >= 2 and change.get("kind") == "unnumbered":
                pass  # PF-1d (auto-log page changes): a commit with no number
            elif not _is_int(n):
                out.append("%s: n %r is not an integer" % (name, n))
            elif n in retired:
                out.append("%s: n %d is retired" % (name, n))
            elif numbers is not None and n not in numbers:
                out.append("%s: n %r is not a feature number" % (name, n))
        if "said" in change:
            said = change["said"]
            if not _nonempty_str(said):
                out.append("%s: `said` is empty or not a string" % name)
            elif len(said) > SAID_MAX:
                out.append("%s: said is %d characters, over %d"
                           % (name, len(said), SAID_MAX))
        if "at" in change and not (isinstance(change["at"], str)
                                   and AT_RE.match(change["at"])):
            out.append("%s: at %r is not a UTC time (YYYY-MM-DDTHH:MM[:SS[.fff]]Z)"
                       % (name, change["at"]))
        if "by" in change and not _nonempty_str(change["by"]):
            out.append("%s: `by` is empty or not a string" % name)
        if "route" in change and change["route"] not in CHANGE_ROUTES:
            out.append("%s: route %r is not one of %s"
                       % (name, change["route"], " | ".join(CHANGE_ROUTES)))
        if minor >= 2:
            out.extend(_check_change_v1_2(change, name))
    return out


def validate(doc):
    """Every defect in `doc` as one finding, each naming its entry
    ("feature 3: ...", "entry 4: ..." when the number itself is bad,
    "changes 2: ..." for the change log, or "file: ..."). An empty list
    means valid."""
    if not isinstance(doc, dict):
        return ["file: the document is not a JSON object"]
    out = _check_file_level(doc)
    changes = doc.get("changes")
    features = doc.get("features")
    minor = _schema_minor(doc)
    retired = _retired_numbers(doc)
    if not isinstance(features, list):
        if isinstance(changes, list):
            out.extend(_check_changes(changes, None, minor, retired))
        return out
    labels = _labels(doc)
    seen = {}
    for i, entry in enumerate(features, 1):
        if not isinstance(entry, dict):
            out.append("entry %d: not an object" % i)
            continue
        n = entry.get("n")
        if _is_int(n) and n >= 1:
            name = "feature %d" % n
            if n in seen:
                out.append("%s: n %d is used twice (entries %d and %d)"
                           % (name, n, seen[n], i))
            else:
                seen[n] = i
        else:
            name = "entry %d" % i
            if "n" in entry:
                out.append("%s: n %r is not an integer >= 1" % (name, n))
        if _is_int(n) and n in retired:
            out.append("%s: n %d is retired and must not be a feature "
                       "(reserved forever)" % (name, n))
        out.extend(_check_entry(entry, name, labels, minor))
    if isinstance(changes, list):
        out.extend(_check_changes(changes, set(seen), minor, retired))
    return out


def finding_kind(finding):
    """"content" for a finding only the list's owner can fix (a value: a
    long name, an API route as a source file, a wired feature with no page
    tag), else "format"."""
    for pattern in CONTENT_PATTERNS:
        if pattern.search(finding):
            return "content"
    return "format"


def validate_kinds(doc):
    """validate(doc) with each finding classed: [{"kind", "text"}, ...]."""
    return [{"kind": finding_kind(t), "text": t} for t in validate(doc)]


def validate_changes(lines, doc):
    """Every defect in a person's <family>--<name>.changes.jsonl, read against
    its family list, named "line 2: ...". `lines` holds the parsed objects
    (a str is parsed here; one that is not JSON is a finding). The change
    log is a v1.2 file, so the v1.2 change keys always apply; a line whose
    n is retired, or not a feature, is a finding."""
    objs, out = [], []
    for i, line in enumerate(lines, 1):
        if isinstance(line, str):
            try:
                line = json.loads(line)
            except ValueError as exc:
                out.append("line %d: not JSON — %s" % (i, exc))
                line = None
        objs.append(line)
    features = doc.get("features") if isinstance(doc, dict) else None
    numbers = None
    if isinstance(features, list):
        numbers = {e["n"] for e in features if isinstance(e, dict) and _is_int(e.get("n"))}
    retired = set()
    if isinstance(doc, dict) and isinstance(doc.get("retired"), list):
        retired = {r["n"] for r in doc["retired"]
                   if isinstance(r, dict) and _is_int(r.get("n"))}
    found = _check_changes(objs, numbers, SCHEMA_MINOR, retired, label="line")
    bad = {"line %d: not an object" % i for i, o in enumerate(objs, 1) if o is None}
    out.extend(f for f in found if f not in bad)
    return sorted(out, key=lambda f: int(f.split(":")[0].split()[1]))


def read_changes(path):
    """The non-empty lines of a changes.jsonl as strings. LoadError if the
    file is missing or unreadable."""
    if not os.path.isfile(path):
        raise LoadError("MISSING: %s" % path)
    try:
        with open(path, encoding="utf-8") as handle:
            return [line for line in handle.read().splitlines() if line.strip()]
    except (OSError, UnicodeDecodeError) as exc:
        raise LoadError("UNREADABLE: %s — %s" % (path, exc))


# ------------------------------------------------------------- converter

STATE_FROM_PROTOTYPE = {"wired": "wired", "after card": "after-card",
                        "not built": "not-built"}
ANCHOR_RE = re.compile(r'^data-feature="(\d+)"$')
DROP_FILE = ("demo", "overlay", "exempt")
DROP_ENTRY_IF_EMPTY = ("frame", "owns", "locked")
TEMPLATES = "platform/views/viewers/_templates"


def _copy(value):
    return json.loads(json.dumps(value))


def _state_word(word):
    if word in STATE_FROM_PROTOTYPE:
        return STATE_FROM_PROTOTYPE[word]
    return word.replace(" ", "-") if isinstance(word, str) else word


def _retired_entry(item):
    if not isinstance(item, dict):
        return _copy(item)
    renamed = {{"was": "name", "reason": "why"}.get(k, k): v for k, v in item.items()}
    out = {k: renamed[k] for k in RETIRED_REQUIRED + RETIRED_OPTIONAL if k in renamed}
    for key, value in renamed.items():
        if key not in out:
            out[key] = value
    return _copy(out)


def _entry_from_prototype(entry):
    if not isinstance(entry, dict):
        return _copy(entry)
    out = {}
    converted = "state" in entry
    for key, value in entry.items():
        if key == "status" and not converted and (
                value in STATE_FROM_PROTOTYPE or value in STATE_WORDS):
            out["state"] = _state_word(value)
            out["status"] = "draft"
        elif key == "anchor":
            match = ANCHOR_RE.match(value) if isinstance(value, str) else None
            if match:
                out["anchor"] = match.group(1)
            elif value is not None:
                out["anchor"] = value
        elif key == "demo":
            continue
        elif key in DROP_ENTRY_IF_EMPTY and value in (None, "", []):
            continue
        else:
            out[key] = _copy(value)
    return out


def convert(doc, family=None):
    """The one-time converter: ◆ PLAN's prototype family-list format → v1.2.

    File: schema → 1, then `"schema_minor": 2` and (when absent) `"status":
    "draft"`; `status_words` → `state_words` (after card → after-card, not
    built → not-built); `retired` entries normalised (was → name, reason →
    why); `demo`, `overlay` and `exempt` dropped. With `family`, `versions`
    becomes {"A": "platform/views/viewers/_templates/<family>.html"} (the old
    value is not kept). Each feature: its status word → `state` with
    `"status": "draft"` after it; anchor 'data-feature="N"' → "N", a null
    anchor dropped; `demo` and any null or empty frame / owns / locked
    dropped. Everything else is copied in order; `doc` is never mutated, and
    convert(convert(x)) == convert(x).
    """
    if not isinstance(doc, dict) or not isinstance(doc.get("features"), list):
        raise ValueError("a family list is an object with a `features` list")
    out = {}
    for key, value in doc.items():
        if key in DROP_FILE or key == "schema_minor":
            continue
        if key == "schema":
            out["schema"] = 1
            out["schema_minor"] = 2
            if "status" not in doc:
                out["status"] = "draft"
        elif key == "status_words":
            if "state_words" not in doc:
                out["state_words"] = {_state_word(k): v for k, v in value.items()}
        elif key == "versions" and family:
            out["versions"] = {"A": "%s/%s.html" % (TEMPLATES, family)}
        elif key == "retired" and isinstance(value, list):
            out["retired"] = [_retired_entry(r) for r in value]
        elif key == "features":
            out["features"] = [_entry_from_prototype(e) for e in value]
        else:
            out[key] = _copy(value)
    if "schema" not in doc:
        out["schema"] = 1
        out["schema_minor"] = 2
        if "status" not in doc:
            out["status"] = "draft"
    if family and "versions" not in out:
        out["versions"] = {"A": "%s/%s.html" % (TEMPLATES, family)}
    return out


def family_of(path):
    """outlier-demo from .../outlier-demo.features.json."""
    base = os.path.basename(path)
    suffix = ".features.json"
    return base[:-len(suffix)] if base.endswith(suffix) else os.path.splitext(base)[0]


def convert_changes(lines):
    """A person's change log in the prototype's words → v1.2: route "B" (the
    person's own Claude Code) → "claude-code". `lines` are the parsed objects
    (a str is parsed); returns new objects in the same key order."""
    out = []
    for line in lines:
        obj = json.loads(line) if isinstance(line, str) else _copy(line)
        if isinstance(obj, dict) and obj.get("route") == "B":
            obj["route"] = "claude-code"
        out.append(obj)
    return out


def dumps_changes(lines):
    """One JSON object per line, the way the change log is written."""
    return "".join(json.dumps(obj, ensure_ascii=False) + "\n" for obj in lines)


REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "examples", "family-conversion-findings.md")
REPORT_HEAD = (
    "# Family-list conversion — content findings\n"
    "\n"
    "Written by `features.py --convert` (PF-1c (plain-words changes)); each run\n"
    "rewrites only its own family's section. A content finding names a value\n"
    "only the list's owner can fix. The converter fixes format only, so every\n"
    "family list keeps these values exactly as they were: fix them by hand in\n"
    "the list, then run the converter again to clear the section.\n")


def _finding_number(text):
    match = re.match(r"^(?:feature|entry|retired|changes) (\d+):", text)
    return int(match.group(1)) if match else 0


def report_section(family, source, findings):
    """One family's section: its content findings by number."""
    lines = ["## %s" % family, "", "Source: `%s` · %d content finding%s"
             % (source, len(findings), "" if len(findings) == 1 else "s"), ""]
    if not findings:
        lines.append("None.")
    for text in sorted(findings, key=_finding_number):
        n = _finding_number(text)
        lines.append("- %s: %s" % (n if n else "file", text))
    return "\n".join(lines) + "\n"


def write_report(path, family, source, findings):
    """Rewrite `family`'s section of the report at `path`, keeping every
    other family's section; sections stay in name order."""
    sections = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        for chunk in re.split(r"(?m)^(?=## )", text)[1:]:
            name = chunk.splitlines()[0][3:].strip()
            sections[name] = chunk.rstrip("\n") + "\n"
    sections[family] = report_section(family, source, findings)
    body = "\n".join(sections[k] for k in sorted(sections))
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(REPORT_HEAD + "\n" + body)


# ------------------------------------------------------------- sync

FO_BLOCK_RE = re.compile(
    r'(<script type="application/json" id="fo-features">)(.*?)(</script>)', re.S)


def sync_text(html, doc):
    """The page with its one embedded fo-features block rewritten from the
    family list: json.dumps(doc, ensure_ascii=False), every "<" written as
    \\u003c so the JSON can never close the script. ValueError when the page
    has no such block or more than one."""
    blocks = FO_BLOCK_RE.findall(html)
    if len(blocks) != 1:
        raise ValueError("the page has %d fo-features blocks, not one" % len(blocks))
    payload = json.dumps(doc, ensure_ascii=False).replace("<", "\\u003c")
    return FO_BLOCK_RE.sub(lambda m: m.group(1) + payload + m.group(3), html, count=1)


# ------------------------------------------------------------- change = commit

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIEWERS = "platform/views/viewers"
SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
DRAFT_RE = re.compile(r"^%s/([^/]+)/drafts/(%s)--(%s)\.html$" % (VIEWERS, SLUG, SLUG))


def run_git(argv, cwd):
    """The default runner: (returncode, stdout, stderr)."""
    proc = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)
    return proc.returncode, proc.stdout, proc.stderr


def _first_line(stdout, stderr):
    for text in (stderr, stdout):
        for line in (text or "").splitlines():
            if line.strip():
                return line.strip()
    return "git gave no message"


def _person(person, root, runner):
    """`person`, else whoever team/people/<id>/identity.json lists the git email
    under — run_kit.people, never the email's local part (LD-77 (one person
    resolver), absorbing PF-10 (identity person rule)); "" when unmapped."""
    if person:
        return person
    kit = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "run-kit")
    if kit not in sys.path:
        sys.path.append(kit)
    from run_kit import people
    code, out, _ = runner(["git", "config", "user.email"], root)
    return people.try_person_of(root, out if code == 0 else "") or ""


def _relpath(path, root):
    full = path if os.path.isabs(path) else os.path.join(root, path)
    rel = os.path.relpath(os.path.normpath(full), os.path.normpath(root))
    return rel.replace(os.sep, "/")


def _draft_problem(page, person):
    """Why `page` (repo-relative) is not this person's own draft, or None."""
    if page.startswith("../") or page == "..":
        return "%s is outside the workspace" % page
    if page.startswith(TEMPLATES + "/"):
        return ("%s is a family template under _templates/; a person changes "
                "their own draft, never the template" % page)
    match = DRAFT_RE.match(page)
    if not match:
        if re.match(r"^%s/[^/]+/[^/]+\.html$" % VIEWERS, page):
            return ("%s is a live page; a change goes to a draft, "
                    "%s/<person>/drafts/<family>--<name>.html" % (page, VIEWERS))
        return ("%s is not a draft page (%s/<person>/drafts/<family>--<name>.html)"
                % (page, VIEWERS))
    if match.group(1) != person:
        return "%s is %s's draft, not %s's" % (page, match.group(1), person)
    return None


def _share(paths, message, root, runner):
    """git add / commit / push of exactly `paths`; one pull --no-rebase and
    one more push when the push is rejected. Returns None when shared, else
    the first line of git's error."""
    code, out, err = runner(["git", "add", "--"] + paths, root)
    if code != 0:
        return _first_line(out, err)
    code, out, err = runner(["git", "commit", "-m", message, "--"] + paths, root)
    if code != 0:
        return _first_line(out, err)
    code, out, err = runner(["git", "push"], root)
    if code == 0:
        return None
    code, out, err = runner(["git", "pull", "--no-rebase"], root)
    if code != 0:
        return _first_line(out, err)
    code, out, err = runner(["git", "push"], root)
    return None if code == 0 else _first_line(out, err)


def change(page, n, said, *, person=None, resolved=None, match=None, missing=False,
           needs=None, family_list=None, root=None, runner=None, now=None):
    """Log one change to a person's draft and share it: one line appended to
    the draft's <family>--<name>.changes.jsonl (checked against the family
    list first), then git add / commit / push of the page, the log and — only
    when `family_list` was passed because a number was added — that list.
    Returns "saved and shared", "saved, not shared: <git's first line>" or
    "refused: <why>"."""
    root = root or ROOT
    runner = runner or run_git
    person = _person(person, root, runner)
    if not person:
        return "refused: no person — pass --person or set git config user.email"
    rel = _relpath(page, root)
    problem = _draft_problem(rel, person)
    if problem:
        return "refused: %s" % problem
    if not os.path.isfile(os.path.join(root, rel)):
        return "refused: %s does not exist" % rel
    family = DRAFT_RE.match(rel).group(2)
    log = rel[:-len(".html")] + ".changes.jsonl"
    list_rel = (_relpath(family_list, root) if family_list
                else "%s/%s.features.json" % (TEMPLATES, family))
    try:
        doc = load(os.path.join(root, list_rel))
    except LoadError as exc:
        return "refused: %s" % exc
    stamp = now or datetime.datetime.now(datetime.timezone.utc)
    if not isinstance(stamp, str):
        stamp = stamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    line = {"n": n, "said": said, "at": stamp, "by": person, "route": "claude-code"}
    if resolved is not None:
        line["resolved"] = resolved
    if match is not None:
        line["match"] = match
    if missing:
        line["kind"] = "missing"
    if needs is not None:
        line["needs"] = needs
    findings = validate_changes([line], doc)
    if findings:
        return "refused: %s" % "; ".join(findings)
    log_path = os.path.join(root, log)
    lead = ""
    if os.path.isfile(log_path) and os.path.getsize(log_path):
        with open(log_path, encoding="utf-8") as handle:
            lead = "" if handle.read().endswith("\n") else "\n"
    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(lead + dumps_changes([line]))
    paths = [rel, log] + ([list_rel] if family_list else [])
    error = _share(paths, "page: %s %d (%s)" % (family, n, person), root, runner)
    return "saved and shared" if error is None else "saved, not shared: %s" % error


def _merge_in_progress(root):
    dot_git = os.path.join(root, ".git")
    if os.path.isfile(os.path.join(dot_git, "MERGE_HEAD")):
        return True
    if os.path.isfile(dot_git):  # a worktree: .git names the real git dir
        with open(dot_git, encoding="utf-8") as handle:
            text = handle.read().strip()
        if text.startswith("gitdir:"):
            gitdir = text[len("gitdir:"):].strip()
            if not os.path.isabs(gitdir):
                gitdir = os.path.join(root, gitdir)
            return os.path.isfile(os.path.join(gitdir, "MERGE_HEAD"))
    return False


def _porcelain_paths(text, prefix):
    paths = []
    for line in text.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        if path.startswith(prefix) and path not in paths:
            paths.append(path)
    return paths


def autosave(root=None, person=None, runner=None, log_commits=False):
    """Commit and share the person's own viewers folder and nothing else.
    "" when there is nothing to do (no folder, or nothing uncommitted);
    "skipped: a merge is in progress"; "saved and shared (N files)"; or
    "not shared: <git's first line>"."""
    root = root or ROOT
    runner = runner or run_git
    person = _person(person, root, runner)
    if not person:
        return ""
    prefix = "%s/%s/" % (VIEWERS, person)
    if not os.path.isdir(os.path.join(root, prefix)):
        return ""
    if _merge_in_progress(root):
        return "skipped: a merge is in progress"
    if log_commits:  # PF-1d (auto-log page changes); lazy import, no cycle
        import autolog
        autolog.autolog(root, person, git_runner=runner)
    code, out, err = runner(["git", "status", "--porcelain", "--", prefix], root)
    if code != 0:
        return "not shared: %s" % _first_line(out, err)
    paths = _porcelain_paths(out, prefix)
    if not paths:
        return ""
    error = _share(paths, "page: autosave (%s)" % person, root, runner)
    if error is not None:
        return "not shared: %s" % error
    return "saved and shared (%d file%s)" % (len(paths), "" if len(paths) == 1 else "s")


def from_seed(seed):
    """The conversion: a new document in the v1 contract from a seed catalog.

    `status_words` becomes `state_words` (spaces in each key → hyphens);
    `"status": "draft"` goes in right after `schema`. In every entry `status`
    becomes `state` (spaces → hyphens) in the same place, with
    `"status": "draft"` right after it. Everything else is copied unchanged
    and in order; the seed is never mutated.
    """
    if not isinstance(seed, dict) or not isinstance(seed.get("features"), list):
        raise ValueError("a seed is an object with a `features` list")
    doc = {}
    for key, value in seed.items():
        if key == "status_words":
            doc["state_words"] = {k.replace(" ", "-"): v for k, v in value.items()}
        elif key == "features":
            doc["features"] = [_entry_from_seed(e) for e in value]
        else:
            doc[key] = json.loads(json.dumps(value))
        if key == "schema":
            doc["status"] = "draft"
    return doc


def _entry_from_seed(entry):
    out = {}
    for key, value in entry.items():
        if key == "status":
            out["state"] = value.replace(" ", "-") if isinstance(value, str) else value
            out["status"] = "draft"
        else:
            out[key] = json.loads(json.dumps(value))
    return out


def dumps(doc):
    """The one serialisation this component writes."""
    return json.dumps(doc, indent=1, ensure_ascii=False) + "\n"


def summary(doc):
    counts = {name: 0 for name in KINDS}
    for entry in doc["features"]:
        counts[entry["kind"]] += 1
    return "valid: %d features (%s)" % (
        len(doc["features"]),
        " · ".join("%s %d" % (KINDS[k], counts[k]) for k in KINDS))


USAGE = ("usage: features.py <features.json>\n"
         "       features.py --from-seed <seed.json> --out <file>\n"
         "       features.py --convert <in.json> --out <out.json> [--findings <md>]\n"
         "       features.py --convert-changes <file.changes.jsonl>\n"
         "       features.py --changes <file.changes.jsonl> <family.features.json>\n"
         "       features.py sync <page.html> <family.features.json> [--check]\n"
         "       features.py change <draft page> --n N --said TEXT [--person P]\n"
         "           [--resolved claude --match TEXT] [--missing --needs JSON]\n"
         "           [--family-list PATH]\n"
         "       features.py autosave [--person P]\n"
         "       features.py check-live <draft page> [--person P]\n"
         "       features.py live <draft page> [--person P] [--no-share]\n"
         "       features.py first-open <live page> [--person P] [--no-share]")


def _print_findings(findings):
    print("INVALID — %d finding%s:" % (len(findings), "" if len(findings) == 1 else "s"))
    for line in findings:
        print("  %s" % line)


def _main_convert(args):
    if len(args) not in (4, 6) or args[2] != "--out" or (
            len(args) == 6 and args[4] != "--findings"):
        print(USAGE)
        return 2
    try:
        source = load(args[1])
    except LoadError as exc:
        print(exc)
        return 3
    out = args[3]
    try:
        doc = convert(source, family=family_of(out))
    except (ValueError, AttributeError) as exc:
        print("UNCONVERTIBLE: %s" % exc)
        return 2
    kinds = validate_kinds(doc)
    fmt = [k["text"] for k in kinds if k["kind"] == "format"]
    content = [k["text"] for k in kinds if k["kind"] == "content"]
    if fmt:
        print("NOT WRITTEN — %d format finding%s left:"
              % (len(fmt), "" if len(fmt) == 1 else "s"))
        for line in fmt:
            print("  %s" % line)
        return 2
    parent = os.path.dirname(os.path.abspath(out))
    os.makedirs(parent, exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        handle.write(dumps(doc))
    print("wrote %s: %d features" % (out, len(doc["features"])))
    report = args[5] if len(args) == 6 else REPORT
    write_report(report, family_of(out), _relpath(out, ROOT)
                 if os.path.abspath(out).startswith(ROOT + os.sep) else out, content)
    print("%d content finding%s kept as they are, listed in %s"
          % (len(content), "" if len(content) == 1 else "s", report))
    return 0


def _main_convert_changes(args):
    if len(args) != 2:
        print(USAGE)
        return 2
    try:
        lines = read_changes(args[1])
        objs = convert_changes(lines)
    except LoadError as exc:
        print(exc)
        return 3
    except ValueError as exc:
        print("UNREADABLE: %s is not JSON lines — %s" % (args[1], exc))
        return 3
    with open(args[1], "w", encoding="utf-8") as handle:
        handle.write(dumps_changes(objs))
    print("wrote %s: %d lines" % (args[1], len(objs)))
    return 0


def _main_changes(args):
    if len(args) != 3:
        print(USAGE)
        return 2
    try:
        lines = read_changes(args[1])
        doc = load(args[2])
    except LoadError as exc:
        print(exc)
        return 3
    findings = validate_changes(lines, doc)
    if findings:
        _print_findings(findings)
        return 2
    print("valid: %d change%s" % (len(lines), "" if len(lines) == 1 else "s"))
    return 0


def _catalog_drift(html, doc):
    """The feature numbers whose entry differs between the page's embedded catalog and the family list (added or
    gone included), sorted; [] in sync. ValueError as sync_text: no block, or more than one."""
    blocks = FO_BLOCK_RE.findall(html)
    if len(blocks) != 1:
        raise ValueError("the page has %d fo-features blocks, not one" % len(blocks))
    try:
        emb = json.loads(blocks[0][1])
    except ValueError:
        emb = {}

    def by_n(d):
        feats = d.get("features") if isinstance(d, dict) else None
        return {f.get("n"): f for f in feats or [] if isinstance(f, dict)}
    a, b = by_n(emb), by_n(doc)
    numbers = [n for n in set(a) | set(b) if a.get(n) != b.get(n)]
    if not numbers and sync_text(html, doc) != html:
        numbers = ["(the catalog's other fields)"]
    return sorted(numbers, key=lambda n: (not isinstance(n, int), n if isinstance(n, int) else 0, str(n)))


def _main_sync(args):
    """`sync <page> <family>` rewrites the embed; `--check` (PF-26b (emails catalog regenerate)) writes nothing:
    exit 0 in sync · 1 DRIFT, naming the differing numbers · 2 refused · 3 unreadable."""
    check = "--check" in args
    args = [a for a in args if a != "--check"]
    if len(args) != 3:
        print(USAGE)
        return 2
    page = args[1]
    try:
        doc = load(args[2])
        with open(page, encoding="utf-8") as handle:
            html = handle.read()
    except LoadError as exc:
        print(exc)
        return 3
    except (OSError, UnicodeDecodeError) as exc:
        print("UNREADABLE: %s — %s" % (page, exc))
        return 3
    try:
        new = sync_text(html, doc)
        drift = _catalog_drift(html, doc) if check else []
    except ValueError as exc:
        print("NOT SYNCED: %s — %s" % (page, exc))
        return 2
    if check:
        if drift:
            print("DRIFT %s: %s differ from %s (run sync to regenerate)"
                  % (page, ", ".join(str(n) for n in drift), args[2]))
            return 1
        print("in sync %s" % page)
        return 0
    if new == html:
        print("unchanged %s" % page)
        return 0
    with open(page, "w", encoding="utf-8") as handle:
        handle.write(new)
    print("synced %s: %d features" % (page, len(doc.get("features") or [])))
    return 0


def _main_change(args):
    parser = argparse.ArgumentParser(prog="features.py change")
    parser.add_argument("page")
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--said", required=True)
    parser.add_argument("--person")
    parser.add_argument("--resolved", choices=["claude"])
    parser.add_argument("--match")
    parser.add_argument("--missing", action="store_true")
    parser.add_argument("--needs")
    parser.add_argument("--family-list")
    try:
        opts = parser.parse_args(args[1:])
    except SystemExit:
        return 2
    needs = None
    if opts.needs is not None:
        try:
            needs = json.loads(opts.needs)
        except ValueError as exc:
            print("refused: --needs is not JSON — %s" % exc)
            return 2
    result = change(opts.page, opts.n, opts.said, person=opts.person,
                    resolved=opts.resolved, match=opts.match, missing=opts.missing,
                    needs=needs, family_list=opts.family_list)
    print(result)
    return 2 if result.startswith("refused:") else 0


def _main_autosave(args):
    parser = argparse.ArgumentParser(prog="features.py autosave")
    parser.add_argument("--person")
    try:
        opts = parser.parse_args(args[1:])
    except SystemExit:
        return 2
    result = autosave(ROOT, person=opts.person, log_commits=True)
    if result:
        print(result)
    return 0


def _live_args(args, prog, share):
    parser = argparse.ArgumentParser(prog="features.py %s" % prog)
    parser.add_argument("page")
    parser.add_argument("--person")
    if share:
        parser.add_argument("--no-share", action="store_true")
    try:
        return parser.parse_args(args[1:])
    except SystemExit:
        return None


def _main_check_live(args):
    opts = _live_args(args, "check-live", share=False)
    if opts is None:
        return 2
    import live  # PF-7 (working versions); lazy, so the two never import in a cycle
    result = live.check_live(opts.page, person=opts.person)
    if result.get("unreadable"):
        print(result["unreadable"])
        return 3
    if result.get("refused"):
        print("refused: %s" % result["refused"])
        return 2
    if result["ok"]:
        print("ready to go live: %s → %s" % (result["draft"], result["live"]))
    else:
        print("not ready to go live: %d failure%s" % (
            len(result["failures"]), "" if len(result["failures"]) == 1 else "s"))
        for line in result["failures"]:
            print(line)
    for note in result["notes"]:
        print("note: %s" % note)
    return 0 if result["ok"] else 2


def _main_live(args):
    opts = _live_args(args, "live", share=True)
    if opts is None:
        return 2
    import live  # PF-7 (working versions); lazy, no import cycle
    result = live.go_live(opts.page, person=opts.person, share=not opts.no_share)
    for line in result["lines"]:
        print(line)
    if result["shared"]:
        print(result["shared"])
    return 0 if result["result"] == "live" else 2


def _main_first_open(args):
    opts = _live_args(args, "first-open", share=True)
    if opts is None:
        return 2
    import live  # PF-7 (working versions); lazy, no import cycle
    result = live.first_open(opts.page, person=opts.person, share=not opts.no_share)
    for line in result["lines"]:
        print(line)
    if result["shared"]:
        print(result["shared"])
    return 0 if result["result"] in ("live", "already live") else 2


SUBCOMMANDS = {"--convert": _main_convert, "--convert-changes": _main_convert_changes,
               "--changes": _main_changes, "sync": _main_sync,
               "change": _main_change, "autosave": _main_autosave,
               "check-live": _main_check_live, "live": _main_live,
               "first-open": _main_first_open}

def _main_draft(args):  # the draft verb (/page-draft); lazy import, no cycle
    import draft
    return draft.main(args[1:])
SUBCOMMANDS["draft"] = _main_draft
USAGE += "\n       features.py draft <family | page path> [--live] [--name N] [--person P] [--no-share]"

def _main_pages(args):  # PF-8 (show my pages); lazy import, no cycle
    import pages
    return pages.main(args[1:])
SUBCOMMANDS["pages"] = _main_pages
USAGE += "\n       features.py pages [--person P]"

def _main_catchup(args):  # PF-19b (catch up), in draft.py; lazy import, no cycle
    import draft
    return draft.main_catchup(args[1:])
def _main_catchup_mark(args):  # PF-19b (catch up): one replayed change's outcome
    import draft
    return draft.main_mark(args[1:])
SUBCOMMANDS["catchup"] = _main_catchup
SUBCOMMANDS["catchup-mark"] = _main_catchup_mark
USAGE += ("\n       features.py catchup <family> [--status] [--person P] [--json] [--no-share]"
          "\n       features.py catchup-mark <draft page> <step> applied|skipped|needs-a-person [--why TEXT]"
          " [--person P] [--json] [--no-share]")

def main(argv=None):
    # The summary and the findings carry non-ASCII text; a C locale must not
    # turn a finding into a UnicodeEncodeError.
    encoding = (getattr(sys.stdout, "encoding", None) or "").lower().replace("-", "")
    if encoding != "utf8" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in SUBCOMMANDS:
        return SUBCOMMANDS[args[0]](args)
    if args and args[0] == "--from-seed":
        if len(args) != 4 or args[2] != "--out":
            print(USAGE)
            return 2
        try:
            seed = load(args[1])
        except LoadError as exc:
            print(exc)
            return 3
        try:
            doc = from_seed(seed)
        except (ValueError, AttributeError) as exc:
            print("INVALID SEED: %s" % exc)
            return 2
        out = args[3]
        parent = os.path.dirname(os.path.abspath(out))
        os.makedirs(parent, exist_ok=True)
        with open(out, "w", encoding="utf-8") as handle:
            handle.write(dumps(doc))
        print("wrote %s: %d features" % (out, len(doc["features"])))
        return 0

    if len(args) != 1 or args[0].startswith("-"):
        print(USAGE)
        return 2
    try:
        doc = load(args[0])
    except LoadError as exc:
        print(exc)
        return 3
    findings = validate(doc)
    if findings:
        print("INVALID — %d finding%s:"
              % (len(findings), "" if len(findings) == 1 else "s"))
        for line in findings:
            print("  %s" % line)
        content = sum(1 for line in findings if finding_kind(line) == "content")
        print("format %d · content %d" % (len(findings) - content, content))
        return 2
    print(summary(doc))
    return 0

def _main_share(args):  # PF-9 (share check), template mode; lazy import, no cycle
    import share
    return share.main(args[1:])
SUBCOMMANDS["share"] = _main_share
USAGE += "\n       features.py share <draft page> [--person P] [--no-share]"

def _main_promote(args):  # a reviewed draft becomes the family template, owner only; lazy import, no cycle
    import promote
    return promote.main(args[1:])
SUBCOMMANDS["promote"] = _main_promote
USAGE += "\n       features.py promote <draft page> [--person P] [--check] [--no-share]"

def _main_sync_overlay(args):
    """PF-2d (overlay remembers settings): `sync-overlay <page>` rewrites the
    page's overlay block, the <script id="ov-main"> inside the component-owned
    markers (live.OVERLAY_START … OVERLAY_END), with components/page-features/
    overlay.js byte for byte (its CSS rides inside it); every other byte of the
    page stays. Exit 0 synced or unchanged · 2 refused, named (no recognisable
    overlay block, or overlay.js cannot sit inside a <script>) · 3 unreadable."""
    if len(args) != 2 or args[1].startswith("-"):
        print("usage: features.py sync-overlay <page>")
        return 2
    import live  # the overlay markers; lazy, no import cycle
    page, src = args[1], os.path.join(os.path.dirname(os.path.abspath(__file__)), "overlay.js")
    try:
        with open(src, encoding="utf-8", newline="") as handle:
            overlay = handle.read()
        with open(page, encoding="utf-8", newline="") as handle:
            html = handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        print("UNREADABLE: %s" % exc)
        return 3
    if "</script" in overlay.lower():
        print("NOT SYNCED: %s — components/page-features/overlay.js holds \"</script\" and cannot be inlined" % page)
        return 2
    try:
        span = live._overlay_span(html)
    except ValueError as exc:
        span, why = None, str(exc)
    else:
        why = "no overlay markers (%s)" % live.OVERLAY_START
    blocks = []
    if span:
        opener = re.compile(r'<script id="ov-main">')
        for match in opener.finditer(html, span[0], span[1]):
            close = html.find("</script>", match.end(), span[1])
            if close >= 0:
                blocks.append((match.end(), close))
        why = "%d <script id=\"ov-main\"> blocks inside the overlay markers, not one" % len(blocks)
    if len(blocks) != 1:
        print("NOT SYNCED: %s — no recognisable overlay block: %s" % (page, why))
        return 2
    start, end = blocks[0]
    new = html[:start] + overlay + html[end:]
    if new == html:
        print("unchanged %s" % page)
        return 0
    with open(page, "w", encoding="utf-8", newline="") as handle:
        handle.write(new)
    print("synced %s: overlay block from components/page-features/overlay.js (%d characters)" % (page, len(overlay)))
    return 0
SUBCOMMANDS["sync-overlay"] = _main_sync_overlay
USAGE += "\n       features.py sync-overlay <page>"

def _main_compare(args):  # PF-3c (family compare), in compare.py; read-only; lazy import, no cycle
    import compare
    return compare.main(args[1:])
SUBCOMMANDS["compare"] = _main_compare
USAGE += "\n       features.py compare <family> [--json]"

if __name__ == "__main__":
    sys.exit(main())
