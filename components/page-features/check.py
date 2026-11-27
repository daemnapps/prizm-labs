#!/usr/bin/env python3
"""PF-3 (feature check): prove a page and its features.json still agree, and
that every wired data or media feature points at a real field in today's data.

    python3 check.py <page.html> --features <features.json>
                     [--version <label>] [--root <repo>] [--strict]

    exit 0 clean · 1 a PAGE miss or a DEAD line (or an UNCHECKABLE, COVERAGE
    or ANCHORS line under --strict), each on its own line · 2 features.json invalid, or the version
    is unknown or not chosen · 3 the page, the features file or a wired
    source file is missing

The page check reads the static DOM with html.parser: data-feature numbers,
ids, classes and tag names, plus the text of every <script> block. The data
check reads JSON only (v1); a non-JSON source is UNCHECKABLE, never DEAD.
Rule (R) features are listed under RULES and never resolved: a rule lives in
the page, not in data. PF-3b (coverage and anchors): COVERAGE names each
top-level region (a direct child of <body>) with no data-feature on or inside
it, data-feature-skip regions counted apart; ANCHORS names each feature whose
data-feature="n" sits on no element or on more than one; an anchor inside a
<template> counts once per template (a row a script repeats is not a second anchor). Stdlib only, Python 3.9. Read only: writes no file.
"""
import argparse
import glob
import json
import os
import re
import sys
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
sys.path.append(os.path.join(os.path.dirname(HERE), "run-kit"))  # appended, never ahead

import features  # noqa: E402  PF-1 (page-features skeleton), same component
from run_kit import paths  # noqa: E402  the one workspace locator (builder card rule 3)

KINDS = features.KINDS
SIMPLE_TAG_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9-]*$")
SIMPLE_NAME_RE = re.compile(r"^([#.])([A-Za-z_-][A-Za-z0-9_-]*)$")
FIELD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*(\[[^\]]*\])?"
                      r"(\.[A-Za-z_][A-Za-z0-9_-]*(\[[^\]]*\])?)*$")
SEGMENT_RE = re.compile(r"(?:^|\.)([A-Za-z_][A-Za-z0-9_-]*)(\[[^\]]*\])?")
TRAILING_PAREN_RE = re.compile(r"\s*\([^()]*\)\s*$")
PLACEHOLDER_RE = re.compile(r"<[^<>/]+>")
SECTIONS = ["PAGE", "DEAD", "MISSING", "UNCHECKABLE", "LOCATOR NOT CHECKED",
            "NOT ON THIS VERSION", "COVERAGE", "ANCHORS", "RULES", "AFTER-CARD", "NOT-BUILT"]
RULE_NOTE = ("a rule lives in the page: promoting it means moving it into the "
             "component's data (it becomes D) or flagging it page-only.")


class Fatal(Exception):
    """Stop before the checks: (exit code, message)."""

    def __init__(self, code, message):
        Exception.__init__(self, message)
        self.code = code


def tag(entry):
    return "%s%s" % (KINDS.get(entry.get("kind"), "?"), entry.get("n"))


def label(entry):
    return "%s %s" % (tag(entry), entry.get("name"))


# --- the page ---------------------------------------------------------------

class PageScan(HTMLParser):
    """The static DOM's data-feature values, ids, classes and tag names, and
    separately the text of every <script> block."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.numbers, self.ids, self.classes, self.tags = [], set(), set(), set()
        self.scripts = []
        self._in_script = False

    def handle_starttag(self, name, attrs):
        self.tags.add(name.lower())
        for key, value in attrs:
            if value is None:
                continue
            if key == "data-feature":
                self.numbers.append(value.strip())
            elif key == "id":
                self.ids.add(value.strip())
            elif key == "class":
                self.classes.update(value.split())
        if name.lower() == "script":
            self._in_script = True
            self.scripts.append("")

    def handle_startendtag(self, name, attrs):
        self.handle_starttag(name, attrs)
        if name.lower() == "script":
            self._in_script = False

    def handle_endtag(self, name):
        if name.lower() == "script":
            self._in_script = False

    def handle_data(self, data):
        if self._in_script:
            self.scripts[-1] += data


# PF-3b (coverage and anchors): the page's top-level regions and where each anchor sits, from the static HTML

HEAD_TAGS = {"html", "head", "body", "title", "meta", "link", "base", "script", "style", "noscript", "template"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class RegionScan(HTMLParser):
    """Each top-level region (a direct child of <body>, or of the document when there is no <body>): its tag, id,
    classes, first words and whether a data-feature sits on it or inside it. Also every data-feature outside
    <template> and <script>, counted. A `hidden` region is no region; a data-feature-skip one is counted apart."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.regions, self.skipped, self.anchors = [], 0, {}
        self.in_templates, self.template_no = {}, 0       # n -> {template number: count}: rows a script draws
        self.stack, self.saw_body, self.inert = [], False, 0

    def handle_starttag(self, name, attrs):
        name = name.lower()
        a = dict((k, v if v is not None else "") for k, v in attrs)
        if self.inert:
            f = dict(attrs).get("data-feature")
            if f and self.template_no and not any(t in ("script", "style") for t, _ in self.stack):
                per = self.in_templates.setdefault(f.strip(), {})
                per[self.template_no] = per.get(self.template_no, 0) + 1
            if name not in VOID_TAGS:
                self.stack.append((name, None))
            self.inert += name in ("template", "script", "style")
            return
        if name == "body":
            self.saw_body = True
        f = a.get("data-feature", "").strip()
        if f:
            self.anchors[f] = self.anchors.get(f, 0) + 1
        region = None
        parent = self.stack[-1][0] if self.stack else None
        top = parent == "body" if self.saw_body else all(t in ("html",) for t, _ in self.stack)
        if top and name not in HEAD_TAGS and "hidden" not in a:
            if "data-feature-skip" in a:
                self.skipped += 1
            else:
                region = {"tag": name, "id": a.get("id", ""), "cls": a.get("class", "").split(),
                          "numbered": bool(f), "text": ""}
                self.regions.append(region)
        elif f:
            for _, r in self.stack:
                if r is not None:
                    r["numbered"] = True
        if name in ("template", "script", "style"):
            self.inert = 1
            if name == "template":
                self.template_no += 1
        if name not in VOID_TAGS:
            self.stack.append((name, region))

    def handle_startendtag(self, name, attrs):
        self.handle_starttag(name, attrs)
        if name.lower() not in VOID_TAGS:
            self.handle_endtag(name)

    def handle_endtag(self, name):
        name = name.lower()
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == name:
                for t, _ in self.stack[i:]:
                    if t in ("template", "script", "style") and self.inert:
                        self.inert -= 1
                del self.stack[i:]
                return

    def handle_data(self, data):
        if self.inert:
            return
        for _, r in self.stack:
            if r is not None and len(r["text"]) < 40:
                r["text"] = (r["text"] + " " + " ".join(data.split())).strip()[:40]


def region_check(doc, text, out):
    """Fill COVERAGE and ANCHORS by number; return how many regions were skipped by data-feature-skip."""
    scan = RegionScan()
    scan.feed(text)
    scan.close()
    for r in scan.regions:
        if not r["numbered"]:
            name = r["tag"] + ("#" + r["id"] if r["id"] else "") + "".join("." + c for c in r["cls"][:2])
            out["COVERAGE"].append('%s "%s": no data-feature on it or inside it (number it, or mark it '
                                   'data-feature-skip)' % (name, r["text"]))
    for entry in doc["features"]:
        count = scan.anchors.get(str(entry["n"]), 0)
        drawn = scan.in_templates.get(str(entry["n"]), {})
        if count > 1:
            out["ANCHORS"].append('%s: data-feature="%d" on %d elements, not one' % (label(entry), entry["n"], count))
        elif any(c > 1 for c in drawn.values()):
            out["ANCHORS"].append('%s: data-feature="%d" on %d elements of one <template>, not one'
                                  % (label(entry), entry["n"], max(drawn.values())))
        elif count == 0 and not drawn and "where" not in entry:
            out["ANCHORS"].append('%s: data-feature="%d" on no element' % (label(entry), entry["n"]))
    return scan.skipped


def scan_page(text):
    scan = PageScan()
    scan.feed(text)
    scan.close()
    return scan


def _in_script(scripts, name):
    pattern = re.compile(r"""(class|id)\s*=\s*["'][^"']*(?<![\w-])%s(?![\w-])"""
                         % re.escape(name))
    return any(pattern.search(s) for s in scripts)


def page_check(doc, scan, version, out):
    """Fill out's PAGE, LOCATOR NOT CHECKED and NOT ON THIS VERSION; return
    how many features were found on the page."""
    entries = doc["features"]
    known = set(e["n"] for e in entries)
    seen_numbers = set()
    for raw in scan.numbers:
        n = int(raw) if raw.isdigit() else None
        if n is not None:
            seen_numbers.add(n)
        if n is None or n not in known:
            out["PAGE"].append("page has data-feature=%s, features.json has no feature %s"
                               % (raw, raw))
    found = 0
    for entry in entries:
        if entry["n"] in seen_numbers:
            found += 1
            continue
        if "where" not in entry or version is None:
            out["PAGE"].append("%s: not on the page — no data-feature=\"%d\" and no where"
                               % (label(entry), entry["n"]))
            continue
        where = entry["where"]
        if version not in where or where[version] is None:
            out["NOT ON THIS VERSION"].append("%s: declared absent from version %s"
                                              % (label(entry), version))
            continue
        spot = where[version]
        sel = spot["sel"].strip()
        simple_name = SIMPLE_NAME_RE.match(sel)
        if spot.get("text") is not None or not (SIMPLE_TAG_RE.match(sel) or simple_name):
            out["LOCATOR NOT CHECKED"].append(
                "%s: version %s selector %r — selector too complex for a static check"
                % (label(entry), version, sel))
            continue
        if simple_name:
            kind, name = simple_name.groups()
            in_dom = name in (scan.ids if kind == "#" else scan.classes)
        else:
            name, in_dom = sel.lower(), sel.lower() in scan.tags
        if in_dom:
            found += 1
        elif simple_name and _in_script(scan.scripts, name):
            out["LOCATOR NOT CHECKED"].append("%s: version %s selector %r — built by script"
                                              % (label(entry), version, sel))
        else:
            out["PAGE"].append("%s: version %s selector %r found nowhere on the page"
                               % (label(entry), version, sel))
    return found


# --- the data ---------------------------------------------------------------

class Files(object):
    """Lazily loaded, cached JSON files under the root."""

    BAD = object()

    def __init__(self, root):
        self.root = root
        self.cache = {}
        self.matches = {}

    def glob(self, pattern):
        if pattern not in self.matches:
            spec = PLACEHOLDER_RE.sub("*", pattern)
            self.matches[pattern] = sorted(glob.glob(os.path.join(self.root, spec)))
        return self.matches[pattern]

    def load(self, path):
        if path not in self.cache:
            try:
                with open(path, encoding="utf-8") as handle:
                    self.cache[path] = json.load(handle)
            except (OSError, ValueError):
                self.cache[path] = self.BAD
        return self.cache[path]


def _segments(field):
    return [(m.group(1), m.group(2) is not None) for m in SEGMENT_RE.finditer(field)]


def _is_schema(doc):
    return isinstance(doc, dict) and ("$schema" in doc or "properties" in doc)


def _in_schema(doc, segments):
    node = doc
    for name, is_list in segments:
        props = node.get("properties") if isinstance(node, dict) else None
        if not isinstance(props, dict) or not isinstance(props.get(name), dict):
            return "absent"
        node = props[name]
        if is_list:
            node = node.get("items")
            if not isinstance(node, dict):
                return "absent"
    return "found"


def _in_data(doc, segments):
    """found · empty (an x[] was an empty list everywhere it was reached) · absent."""
    values, empty = [doc], False
    for name, is_list in segments:
        nxt = []
        for value in values:
            if not isinstance(value, dict) or name not in value:
                continue
            if is_list:
                items = value[name]
                if not isinstance(items, list):
                    continue
                if not items:
                    empty = True
                nxt.extend(items)
            else:
                nxt.append(value[name])
        values = nxt
        if not values:
            return "empty" if empty else "absent"
    return "found"


def resolve(files, paths_, field):
    """found · empty · absent across the matching files, stopping at the first hit."""
    segments = _segments(field)
    empty = False
    for path in paths_:
        doc = files.load(path)
        if doc is Files.BAD:
            continue
        result = _in_schema(doc, segments) if _is_schema(doc) else _in_data(doc, segments)
        if result == "found":
            return "found"
        empty = empty or result == "empty"
    return "empty" if empty else "absent"


def split_source(source):
    """[(file pattern, [field, ...]), ...] — paired by position when the counts
    match, else every group against every file (a field then resolves when any
    of the files carries it)."""
    text = source["field"].strip()
    text = TRAILING_PAREN_RE.sub("", text)
    text = text.split(" + ", 1)[0].strip()
    groups = [[f.strip() for f in g.split(", ") if f.strip()] for g in text.split(" · ")]
    parts = [p.split(" → ")[-1].strip() for p in source["file"].split(" · ")]
    if len(parts) == len(groups):
        return [([p], g) for p, g in zip(parts, groups)]
    every = [f for g in groups for f in g]
    return [(parts, every)]


def data_check(doc, files, out):
    bad_seen = set()
    for entry in doc["features"]:
        if entry["state"] != "wired" or entry["kind"] not in ("data", "media"):
            continue
        if not entry.get("source"):
            continue
        t = tag(entry)
        for parts, fields in split_source(entry["source"]):
            matched = []
            for part in parts:
                if not part.endswith(".json"):
                    out["UNCHECKABLE"].append("%s: %s is not JSON (v1 reads JSON only)"
                                              % (t, part))
                    continue
                hits = files.glob(part)
                if not hits:
                    out["MISSING"].append("%s: %s matches no file under %s"
                                          % (t, part, files.root))
                    continue
                matched.append((part, hits))
            if not matched:
                continue
            pattern = " · ".join(p for p, _ in matched)
            hits = [h for _, hs in matched for h in hs]
            for field in fields:
                if not FIELD_RE.match(field):
                    out["UNCHECKABLE"].append("%s: %s unparsed field text %r"
                                              % (t, pattern, field))
                    continue
                result = resolve(files, hits, field)
                if result == "empty":
                    out["DEAD"].append("%s: %s field %s is unproven (empty array)"
                                       % (t, pattern, field))
                elif result == "absent":
                    out["DEAD"].append("%s: %s has no field %s" % (t, pattern, field))
            for path in hits:
                if files.cache.get(path) is Files.BAD and path not in bad_seen:
                    bad_seen.add(path)
                    out["UNCHECKABLE"].append("%s: %s is not valid JSON — skipped"
                                              % (t, os.path.relpath(path, files.root)))


# --- the listed sections ----------------------------------------------------

def listed_sections(doc, root, out):
    for entry in doc["features"]:
        if entry["kind"] != "rule":
            continue
        source = entry.get("source")
        if source:
            out["RULES"].append("%s: rule in the page — %s → %s"
                                % (label(entry), source["file"], source["field"]))
        else:
            out["RULES"].append("%s: page-only (no source)" % label(entry))
    out["RULES"].append(RULE_NOTE)

    tags_path = os.path.join(root, "team", "id-tags.json")
    try:
        with open(tags_path, encoding="utf-8") as handle:
            id_tags = json.load(handle)
        if not isinstance(id_tags, dict):
            raise ValueError("not an object")
    except (OSError, ValueError):
        id_tags = None
    for entry in doc["features"]:
        if entry["state"] == "after-card":
            card = entry.get("card")
            if not card:
                out["AFTER-CARD"].append("%s: warning: no card id" % label(entry))
            elif id_tags is None:
                out["AFTER-CARD"].append("%s: warning: card %s not on file (%s unreadable)"
                                         % (label(entry), card, tags_path))
            elif card in id_tags:
                out["AFTER-CARD"].append("%s: card %s (%s)" % (label(entry), card, id_tags[card]))
            else:
                out["AFTER-CARD"].append("%s: warning: card %s not on file" % (label(entry), card))
        elif entry["state"] == "not-built":
            out["NOT-BUILT"].append(label(entry))


# --- the command ------------------------------------------------------------

def read_page(path):
    if not os.path.isfile(path):
        raise Fatal(3, "MISSING: %s" % path)
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise Fatal(3, "UNREADABLE: %s — %s" % (path, exc))


def pick_version(doc, asked):
    versions = doc.get("versions")
    labels = sorted(versions) if isinstance(versions, dict) else []
    if asked is not None:
        if asked not in labels:
            raise Fatal(2, "version %r is not in versions (labels: %s)"
                        % (asked, ", ".join(labels) or "none"))
        return asked
    if len(labels) == 1:
        return labels[0]
    if len(labels) > 1:
        raise Fatal(2, "features.json has %d versions — pass --version (labels: %s)"
                    % (len(labels), ", ".join(labels)))
    return None


def run(args):
    """Every check, then (exit code, report lines)."""
    page_text = read_page(args.page)
    try:
        doc = features.load(args.features)
    except features.LoadError as exc:
        raise Fatal(3, str(exc))
    findings = features.validate(doc)
    if findings:
        raise Fatal(2, "INVALID — %d finding%s:\n%s" % (
            len(findings), "" if len(findings) == 1 else "s",
            "\n".join("  %s" % f for f in findings)))
    version = pick_version(doc, args.version)
    if args.root:
        root = os.path.abspath(args.root)
    else:
        try:
            root = str(paths.repo(HERE))
        except FileNotFoundError as exc:
            raise Fatal(3, "MISSING: %s — pass --root" % exc)

    out = dict((name, []) for name in SECTIONS)
    on_page = page_check(doc, scan_page(page_text), version, out)
    skipped = region_check(doc, page_text, out)
    data_check(doc, Files(root), out)
    listed_sections(doc, root, out)

    if out["MISSING"]:
        code = 3
    elif out["PAGE"] or out["DEAD"] or (args.strict and (out["UNCHECKABLE"] or out["COVERAGE"] or out["ANCHORS"])):
        code = 1
    else:
        code = 0
    lines = []
    for name in SECTIONS:
        items = out[name]
        count = len(items) - (1 if name == "RULES" else 0)
        lines.append("%s — %d%s" % (name, count, " (%d skipped by data-feature-skip)" % skipped
                                    if name == "COVERAGE" and skipped else ""))
        lines.extend("  %s" % item for item in items or ["(none)"])
    rules = sum(1 for e in doc["features"] if e["kind"] == "rule")
    lines.append("page %s: %d on page · %d dead · %d uncheckable · %d rules · exit %d"
                 % (args.page, on_page, len(out["DEAD"]), len(out["UNCHECKABLE"]), rules, code))
    return code, lines


def main(argv=None):
    # Report lines carry non-ASCII text; a C locale must not turn one into a
    # UnicodeEncodeError.
    encoding = (getattr(sys.stdout, "encoding", None) or "").lower().replace("-", "")
    if encoding != "utf8" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        prog="check.py", description="PF-3 (feature check): page and data against features.json")
    parser.add_argument("page")
    parser.add_argument("--features", required=True)
    parser.add_argument("--version")
    parser.add_argument("--root")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    try:
        code, lines = run(args)
    except Fatal as exc:
        print(exc)
        return exc.code
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
