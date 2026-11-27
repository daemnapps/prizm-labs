#!/usr/bin/env python3
"""text_check.py — baseline text QC, emitted as a portable findings bundle.

Cards RV-36 (text check) and UQ-1 (portable bundle).

WHAT IT IS. The typo, the wrong price and the leftover `TBD` get pointed at BY
THE WORDS THEY ARE IN, before a human spends attention on them. A request's
text goes in; a list of RV-23 (anchors declared) anchors comes out
(`{quote, prefix, suffix, comment, row?}`), and `write_bundle` makes each one a
review-kind `verdict` record filed unchanged as the machine reviewer
`claude-prereview` through RV-7 (claude prereview adapter)'s path. The same
records and no extra claim render into one self-contained HTML page.

PROPOSES, NEVER PASSES; NEVER CLOSES. RV-7 (claude prereview adapter)'s three
nevers hold here, and the FIRST one is enforced by what this module refuses to
compose rather than by a comment:

    NEVER A PASS        the grammar the plane freezes offers `approve | reject
                        | fix`, so "no findings" has no honest spelling as a
                        verdict — and the answer is that A CLEAN DOCUMENT IS
                        FILED AS NOTHING AT ALL (`file_findings` returns
                        `filed: False`). A runner that could pass something
                        would be a reviewer, and nobody ruled that. Findings
                        file `fix`, which is a proposal a person overrules.
    NEVER A PERSON      the reviewer is `claude-prereview`, and the filing goes
                        through `prereview_adapter`, whose `refuse_if_a_person`
                        stops it if that name ever becomes one (OR-5 (verdict
                        attribution)).
    NEVER A CLOSE       one event, `verdict`, and no `decision` — so this can
                        never close a request and never counts toward the close
                        rule's one named reviewer.

FALSE POSITIVES ARE THE PRODUCT RISK, NOT MISSES, and that ruling is the whole
architecture of this file. A runner that flags six non-problems per document
gets switched off by the person it was built for, and the one real finding goes
with it. So:

    ONE CHECK PER ROW OF `CHECKS`, each with its own name, and every finding
    carries the name of the check that made it. A check is REMOVED by deleting
    its row — the card's kill ("a runner earns its checks one at a time") is a
    one-line edit, not a refactor, and `checks_off` in the brand dictionary
    turns one off for one brand without touching this file.

    EVERY ANCHOR IS VERIFIED AGAINST THE TEXT IT CAME FROM. `anchor()` slices
    quote, prefix and suffix out of the unit's own characters, so a quote that
    does not resolve cannot be composed. The model tier drops any quote it
    cannot find verbatim — a model-invented quote is a false positive by
    construction, and dropping it costs a miss instead.

    WHITESPACE CHECKS ARE SOURCE-GATED. Two spaces between words mean
    something in markdown and nothing in HTML (a browser collapses them), so
    `double-space` and `quote-style` run only where whitespace is AUTHORED.
    That is a fact about the source, not a threshold being tuned.

THE DICTIONARY IS PER BRAND AND THIS MODULE IS BRAND-AGNOSTIC (workspace rule
7). Canonical names, the prices the brand actually uses, banned and required
phrasings, the brand's own vocabulary and its CTA words live in
`brands/<brand>/qc-dictionary.json`. NO BRAND NAME APPEARS HERE — the brand is
an argument, the path is composed from it, and the declared test asserts the
absence by reading this source. `brands/` is the fourth data home
(components/CLAUDE.md rule-9 (brand home)); an absent dictionary is not an
error, it is a smaller run, and `dictionary_checks` say which checks went quiet.

THE TEXT SOURCES, AND WHY THERE IS NO WAREHOUSE FOR TEXT BYTES:

    md | text | doc   the file, read out of the checkout at the `repo` pointer,
                      path confined to it (a record is DATA, never a path into
                      the filesystem at large — workspace rule 8).
    page | link       THE BUILT HTML AT THE URL THE RECORD CARRIES, fetched and
                      reduced to its rendered words. RV-35 (page capture) says
                      it in its own file: there is no warehouse that serves
                      text bytes and this lane deliberately does not add one; a
                      screenshot cannot be spell-checked. Version binding is
                      the FILER's — a blob url at a commit is pinned, a deploy
                      preview is not, and this module never pretends otherwise.
    a Figma frame     RV-43 (figma text read)'s rows, passed in. One unit per
                      TEXT layer, `row` carrying the node id, so a finding on a
                      design points at the layer and not at a picture of it.

THE MODEL TIER IS ONE METERED CALL THROUGH WM-34 (infer action), on the cheap
text model, and it is the ONLY check that costs anything or leaves the machine.
Everything else is stdlib and free. WM-34 (infer action) refuses before the
call when the `infer` grant holds no key, so on a machine without one this
runner DEGRADES to its deterministic tier and says so in `tiers` — the card's
own fallback ("below that it runs DICTIONARY-ONLY"), reached by the absence of
a credential rather than by a switch.

Standalone use (writes only under `--out`; filing remains an explicit reader):

    python3 text_check.py --item RQ-… --dry-run
    python3 text_check.py --item RQ-… --text-file page.html --out findings
"""
import argparse
import calendar
import hashlib
import json
import os
import re
import socket
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from html import escape as html_escape
from html.parser import HTMLParser
from importlib import util as _importlib_util
from pathlib import Path

VERSION = "text-check/1"

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def _repo_root(start=None):
    p = Path(start or __file__).resolve()
    for anc in [p, *p.parents]:
        if (anc / ".git").exists():
            return anc
    from clone_root import resolve_ws
    return resolve_ws()


WS = _repo_root()
WORKER_HOME = WS / "platform/workers/mini-worker"
if str(WORKER_HOME) not in sys.path:
    # The resident owns the engine; the worker still owns the filing and metered
    # adapters. Append so an already-loaded worker module keeps one identity.
    sys.path.append(str(WORKER_HOME))

# ---- the dictionary's home, composed from the caller's brand ----------------
# The PATH is this module's (one shape for every brand); the BRAND is the
# caller's, and the words are the brand's own. That split is workspace rule 7
# in one line, and the declared test asserts no brand name is on this side of
# it by reading the source of this file.
DICT_HOME = "brands/%s/qc-dictionary.json"
DICT_SCHEMA = 1

# ---- the model tier's ONE model ---------------------------------------------
# A REGISTRY ID (components/models/models.json), never a vendor id and never an
# endpoint — WM-34 (infer action) refuses anything else by name. The cheap text
# model, which is what the card asked for: this tier reads marketing copy and
# says which sentence is ungrammatical, which is pattern work at volume, and
# the expensive failure here is a confident false positive rather than a missed
# nuance. Not in models.json's `stages` map on purpose: that map's values are
# ids passed to `claude --model`, and this one is spent through OpenRouter.
MODEL = "glm-5.3-flash"
MODEL_MAX_TOKENS = 4000
# The words handed to the model in one call. The page this was measured on is
# ~285 KB of HTML and ~14 KB of rendered words, so one call carries a whole
# page; a longer document is truncated AND SAYS SO rather than silently losing
# its tail.
MODEL_MAX_CHARS = 60000

REVIEWER_NOTE = (
    "Machine text QC by RV-36 (text check), filed as the machine reviewer "
    "`%s` and never as a person (OR-5 (verdict attribution)). EVERY FINDING IS "
    "A PROPOSAL ANCHORED TO THE WORDS IT IS ABOUT: it closes nothing, it does "
    "not count toward the close rule's one named reviewer, and a clean "
    "document is filed as nothing at all rather than as a pass.")

# ---- the neighbourhood an anchor carries ------------------------------------
# RV-23 (anchors declared): "the exact neighbourhood first, then the quote
# alone". Wide enough that a repeated phrase resolves to the right instance,
# short enough that a page of anchors still fits the plane's verdict cap.
NEIGHBOURHOOD = 40
QUOTE_MAX = 200


class Refused(ValueError):
    """This text will not be checked, and NOTHING was filed.

    Every raise names the reason in its first word, the same vocabulary RV-7
    (claude prereview adapter) writes its refusals in."""

    def __init__(self, reason, detail=""):
        self.reason, self.detail = reason, detail
        super().__init__("%s — %s" % (reason, detail) if detail else reason)


_MODS = {}


def _sibling(name):
    """A module from THIS directory, imported ordinarily.

    ORDINARILY, AND THAT MATTERS MORE THAN IT LOOKS: loading a sibling by path
    would mint a SECOND module object with its own `Refused` class, so a caller
    that catches `prereview_adapter.Refused` would miss the one this module
    provoked. Two identities for one refusal is a bug waiting for the worst
    moment, and one `import` avoids it. The worker's own directory is already
    on `sys.path` above."""
    if name not in _MODS:
        try:
            _MODS[name] = __import__(name)
        except ImportError as e:
            raise ImportError(
                "%s is missing beside %s — RV-36 (text check) REUSES it rather "
                "than carrying a copy (the card's shared parts): %s"
                % (name, HERE, e))
    return _MODS[name]


def prereview():
    """RV-7 (claude prereview adapter) — the filing path and the identity."""
    return _sibling("prereview_adapter")


def infer():
    """WM-34 (infer action) — the metered call, and the only thing here that
    leaves the machine."""
    return _sibling("infer_run")


def review_request():
    """RV-2 (review request module) — the ONE writer and the ONE fold.

    Loaded BY PATH, not imported: it lives in `components/review/`, and this
    file does not put a component's folder on the worker's `sys.path` — the
    same choice `prereview_adapter` made for the same module."""
    if "rr" not in _MODS:
        p = WS / "components/review/review_request.py"
        if not p.is_file():
            raise ImportError(
                "%s is missing — RV-36 (text check) files through RV-2 (review "
                "request module)'s writer and folds with its fold; it carries "
                "no copy of either." % p)
        spec = _importlib_util.spec_from_file_location("review_request", p)
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MODS["rr"] = mod
    return _MODS["rr"]


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ============================================================================
# THE DICTIONARY — brand content, read from the brand's own home
# ============================================================================
def dict_path(brand, root=None):
    """`brands/<brand>/qc-dictionary.json` for a brand NAME the caller gives.

    The name is bounded to one path segment: a brand is a folder name and a
    record is data, so `../../etc` is refused rather than resolved (the same
    rule `resolve_asset`'s `repo` arm keeps)."""
    name = str(brand or "").strip().lower()
    if not re.match(r"^[a-z0-9][a-z0-9_-]{0,40}$", name):
        raise Refused("brand-not-a-folder-name",
                      "%r is not a brand folder name — the dictionary lives at "
                      "%s and a brand is ONE path segment"
                      % (str(brand)[:40], DICT_HOME))
    return (Path(root) if root else WS) / (DICT_HOME % name)


def load_dictionary(brand=None, path=None, root=None):
    """The brand's QC dictionary, or the EMPTY one.

    AN ABSENT DICTIONARY IS NOT AN ERROR. It is a smaller run: the checks that
    need brand words go quiet, `report()["dictionary"]` says the file was not
    found, and every check that needs no brand content still runs. The
    alternative — refusing to check a brand nobody has seeded yet — would make
    the first useful day of this runner wait on a data entry task."""
    p = Path(path) if path else dict_path(brand, root=root)
    out = {"path": str(p), "found": False, "brand": str(brand or ""),
           "status": "", "names": [], "banned": [], "required": [],
           "cta": [], "words": [], "never_prices": [], "checks_off": []}
    if not p.is_file():
        return out if path else _overlay_products(out, brand, root)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Refused("dictionary-unreadable", "%s: %s" % (p, e))
    if not isinstance(doc, dict):
        raise Refused("dictionary-unreadable",
                      "%s is not a json object" % p)
    schema = doc.get("schema")
    if schema is not None and int(schema) != DICT_SCHEMA:
        raise Refused("dictionary-schema",
                      "%s declares schema %r and this runner reads %d"
                      % (p, schema, DICT_SCHEMA))
    out["found"] = True
    out["brand"] = str(doc.get("brand") or brand or "")
    out["status"] = str(doc.get("status") or "").strip().lower()
    for key in ("banned", "required", "cta", "words", "never_prices",
                "checks_off"):
        val = doc.get(key)
        if isinstance(val, list):
            out[key] = val
    names = doc.get("names")
    if isinstance(names, list):
        for row in names:
            if not isinstance(row, dict):
                continue
            canon = str(row.get("canonical") or "").strip()
            if not canon:
                continue
            out["names"].append({
                "canonical": canon,
                "wrong": [str(w) for w in (row.get("wrong") or [])
                          if str(w).strip()],
                "prices": [str(v) for v in (row.get("prices") or [])
                           if str(v).strip()],
                "comment": str(row.get("comment") or "")})
    return out if path else _overlay_products(out, brand, root)


# THE BRAND'S LIVE PRODUCTS, FROM THE ONE SHARED READ — HE-3 (shared brand
# facts), 2026-10-02. Every live product title the brand's catalogue carries
# becomes a `names` row when the dictionary does not already name it, so the
# canonical spelling is known to this runner whether or not anyone seeded a
# dictionary. AN OVERLAY ROW CHANGES NO FINDING BY ITSELF: it carries no wrong
# spellings and NO PRICES — prices stay offer-bank-only (designer, 2026-10-01),
# so `prices` is always empty and `never_prices` is never touched — and it
# leaves `found`, `status` and `path` alone, so an unseeded brand's dictionary
# checks still say "no dictionary for this brand" and no truth is stamped. A
# dictionary read by `path` is taken as given and gets no overlay.
def _brand_facts():
    """marketing-chain-checks' `brand_facts`, imported on first use and only
    then; ImportError when it is not in this checkout."""
    if "brand_facts" not in _MODS:
        home = next((d / "components" / "marketing-chain-checks"
                     for d in HERE.parents
                     if (d / "components" / "marketing-chain-checks").is_dir()),
                    None)
        if home is None:
            raise ImportError("components/marketing-chain-checks not found "
                              "upward of %s" % HERE)
        if str(home) not in sys.path:
            sys.path.append(str(home))  # appended: the worker's modules win
        from marketing_chain_checks.facts import brand_facts
        _MODS["brand_facts"] = brand_facts
    return _MODS["brand_facts"]


def _overlay_products(out, brand, root=None):
    try:
        titles = _brand_facts()(str(brand).strip().lower(),
                                root=Path(root) if root else WS)["products"]
    except (ImportError, OSError):
        return out              # no shared read here: the dictionary as it was
    have = {r["canonical"].lower() for r in out["names"]}
    for title in titles:
        canon = str(title or "").strip()
        if not canon or canon.lower() in have:
            continue
        have.add(canon.lower())
        out["names"].append({
            "canonical": canon, "wrong": [], "prices": [],
            "comment": "a live product in the brand's catalogue"})
    return out


# ============================================================================
# THE TEXT — three sources, one unit shape
# ============================================================================
# A UNIT is {"row": str, "text": str, "authored_ws": bool}. `row` is RV-23
# (anchors declared)'s optional key and names WHICH text the anchor lives in —
# a node id for a Figma layer, "" for a single-text request. `authored_ws` says
# whether whitespace in this unit was typed by a person: it is what gates the
# two whitespace checks, and it is a property of the SOURCE, never a setting.
class _Blocks(HTMLParser):
    """Rendered words out of built HTML, one string per block.

    NOT A BROWSER AND NOT PRETENDING TO BE ONE. It drops `script`, `style`,
    `template` and `noscript` wholesale, breaks at the block tags that put a
    line between words, collapses runs of whitespace the way a browser does,
    and keeps nothing else. What it produces is the WORDS A READER SEES, which
    is the only thing a copy check has an opinion about — the DOM a screenshot
    would show is RV-35 (page capture)'s business and not this module's."""

    SKIP = {"script", "style", "template", "noscript", "svg", "head"}
    BREAK = {"p", "div", "section", "article", "header", "footer", "main",
             "aside", "nav", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul",
             "ol", "table", "tr", "td", "th", "br", "hr", "figcaption",
             "blockquote", "form", "option"}

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.blocks, self._buf, self._skip = [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in self.BREAK:
            self._flush()

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self._skip = max(0, self._skip - 1)
        elif tag in self.BREAK:
            self._flush()

    def handle_data(self, data):
        if not self._skip:
            self._buf.append(data)

    def _flush(self):
        words = re.sub(r"[ \t\r\n ]+", " ", "".join(self._buf)).strip()
        self._buf = []
        if words:
            self.blocks.append(words)

    def close(self):
        HTMLParser.close(self)
        self._flush()
        return self.blocks


def units_from_html(html, row=""):
    """Built HTML -> units, one per rendered block.

    ONE UNIT PER BLOCK RATHER THAN ONE PER PAGE, because a block boundary is
    where a sentence genuinely ends: `… rinse clean` `Clean skin …` across two
    headings is not a doubled word, and a whole-page unit would report it as
    one. `authored_ws` is False — a browser collapses the whitespace in an HTML
    text node, so two spaces there are invisible to the reader and flagging
    them would be flagging the build system."""
    parser = _Blocks()
    parser.feed(str(html or ""))
    return [{"row": row, "text": b, "authored_ws": False}
            for b in parser.close()]


def units_from_text(text, row="", markdown=False):
    """Plain text or markdown -> units, one per blank-line-separated block.

    `authored_ws` is True: a person typed the spaces, so a double space is
    theirs and a straight quote beside a curly one is a choice they did not
    make deliberately."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", str(text or ""))]
    return [{"row": row, "text": b, "authored_ws": True} for b in blocks if b]


def units_from_figma(rows):
    """RV-43 (figma text read)'s rows -> units, one per TEXT layer.

    `row` carries the NODE ID, which is the whole reason that card exists: a
    finding on a design points at the layer it lives in, not at a picture of
    it. `authored_ws` is True — a designer typed those characters — but a text
    layer WRAPS where the box was dragged, so the newline Figma reports is
    layout and is normalized to a space before anything reads it (RV-43 (figma
    text read)'s own `normalize` rule, applied here to the unit and never to a
    stored anchor)."""
    out = []
    for row in (rows if isinstance(rows, (list, tuple)) else ()):
        if not isinstance(row, dict):
            continue
        chars = re.sub(r"\s+", " ", str(row.get("characters") or "")).strip()
        if not chars:
            continue
        out.append({"row": str(row.get("node") or ""), "text": chars,
                    "authored_ws": True})
    return out


# ============================================================================
# THE ANCHOR — composed by slicing, never by describing
# ============================================================================
def anchor(unit, start, end, comment, check=""):
    """One RV-23 (anchors declared) anchor over `unit["text"][start:end]`.

    THE QUOTE IS A SLICE OF THE TEXT, which is what makes an anchor that cannot
    resolve impossible to compose here: nothing writes a quote, it is cut out
    of the characters the check was given. `prefix` and `suffix` are the
    neighbourhood on each side and are ALLOWED TO BE EMPTY — a quote at the
    start of a document has no words before it, and RV-23 (anchors declared)
    says so explicitly.

    The comment names the CHECK that made the finding. That is not decoration:
    the kill is per-check, so a reader counting false positives has to be able
    to say which check produced them without guessing."""
    text = unit["text"]
    start, end = max(0, int(start)), min(len(text), int(end))
    quote_end = min(end, start + QUOTE_MAX)
    quote = text[start:quote_end]
    if not quote.strip():
        return None
    out = {"quote": quote,
           "prefix": text[max(0, start - NEIGHBOURHOOD):start],
           "suffix": text[quote_end:quote_end + NEIGHBOURHOOD],
           "comment": ("%s — %s" % (check, comment)) if check else comment}
    if unit.get("row"):
        out["row"] = unit["row"]
    return out


# ============================================================================
# THE CHECKS — one row each, removable one at a time
# ============================================================================
# DOUBLED WORDS. Two letters or more, so "is is" and "to to" are caught; a
# single letter is not, because a list of initials repeats one legitimately.
# The allowlist is the doubles English actually writes — "had had", "that
# that", and the intensifiers. Everything else repeated back to back in
# marketing copy is a paste.
DOUBLE_OK = {"had", "that", "very", "really", "long", "again", "yes", "no",
             "ha", "so", "far", "new", "bye"}
DOUBLE_RE = re.compile(r"\b([A-Za-z][A-Za-z'’]+)(\s+)(\1)\b", re.I)


def check_doubled_word(unit, dic, ctx):
    out = []
    for m in DOUBLE_RE.finditer(unit["text"]):
        if m.group(1).lower() in DOUBLE_OK:
            continue
        out.append(anchor(unit, m.start(), m.end(),
                          "the word %r is written twice in a row" % m.group(1),
                          "doubled-word"))
    return out


# PLACEHOLDER TEXT. The card's own list — lorem, TBD, XX — plus the two
# template forms that reach a built page when a merge field never merged.
# `XX` is matched as a WHOLE WORD only: `XXL` is a size and `20XX` is a year
# written as a placeholder, which is the case worth flagging.
PLACEHOLDER_RE = re.compile(
    r"(?<![A-Za-z0-9])("
    r"lorem\s+ipsum|lorem|ipsum"
    r"|TBD|TBC|TODO|FIXME|FIX\s?ME"
    r"|X{2,}|\?{3,}"
    r"|PLACEHOLDER|INSERT\s+[A-Z]{3,}"
    r"|\{\{[^{}]{0,60}\}\}|\[\[[^\[\]]{0,60}\]\]"
    r"|<[A-Z_]{3,}>"
    r")(?![A-Za-z0-9])")


def check_placeholder(unit, dic, ctx):
    out = []
    for m in PLACEHOLDER_RE.finditer(unit["text"]):
        out.append(anchor(unit, m.start(), m.end(),
                          "%r is placeholder text that reached the page"
                          % m.group(0), "placeholder"))
    return out


# BROKEN CHARACTERS. Three genuinely broken things and nothing stylistic:
# the replacement character, the UTF-8-read-as-latin-1 signatures, and an HTML
# entity that arrived in the RENDERED words (which means it was double-escaped
# — the reader is looking at `&amp;`).
# The signatures are the ones that CANNOT occur in real prose: a replacement
# character, and the two-byte heads UTF-8 leaves behind when it is read as
# latin-1 or cp1252 (`â€` before a punctuation mark, `Â` before a space or a
# latin-1 symbol, `Ã` before one). An accented word in French or Portuguese is
# `Ã` followed by a LETTER and is deliberately not matched.
MOJIBAKE_RE = re.compile(
    "�"
    "|\u00e2\u20ac.|\u00e2\u201a\u00ac"
    "|\u00c2[\u0080-\u00bf ]|\u00c3[\u0080-\u00bf]"
    r"|&(amp|nbsp|quot|apos|lt|gt|#\d{2,5}|#x[0-9a-fA-F]{2,4});")


def check_broken_character(unit, dic, ctx):
    out = []
    for m in MOJIBAKE_RE.finditer(unit["text"]):
        out.append(anchor(unit, m.start(), m.end(),
                          "%r is a broken character — the text was decoded or "
                          "escaped twice" % m.group(0), "broken-character"))
    for i, ch in enumerate(unit["text"]):
        if unicodedata.category(ch) == "Cc" and ch not in "\t\n\r":
            out.append(anchor(unit, i, i + 1,
                              "a control character (U+%04X) is in the copy"
                              % ord(ch), "broken-character"))
    return out


# DOUBLE SPACES. Source-gated: authored whitespace only. In HTML a browser
# collapses them and the reader never sees one, so flagging them there would be
# reporting on the build rather than on the copy.
# The match spans the WHOLE WORD ON EACH SIDE, so the quote a reader is shown
# is "with  two" rather than "h  t" — an anchor is read by a person and a
# selector that starts mid-word reads like a bug in the tool.
DOUBLE_SPACE_RE = re.compile(r"\S+(  +)\S+")


def check_double_space(unit, dic, ctx):
    if not unit.get("authored_ws"):
        return []
    out = []
    for m in DOUBLE_SPACE_RE.finditer(unit["text"]):
        out.append(anchor(unit, m.start(), m.end(),
                          "%d spaces between two words" % len(m.group(1)),
                          "double-space"))
    return out


# QUOTES. Mixed styles in ONE unit — a straight quote beside a curly one is a
# paste seam, and nobody chooses it. Source-gated for the same reason as the
# spaces: an HTML entity-decoded page mixes them for reasons that are the
# template's, not the writer's.
STRAIGHT = set("\"'")
CURLY = set("‘’“”")


def check_quotes(unit, dic, ctx):
    if not unit.get("authored_ws"):
        return []
    text = unit["text"]
    has_straight = [i for i, c in enumerate(text) if c in STRAIGHT]
    has_curly = [i for i, c in enumerate(text) if c in CURLY]
    if not (has_straight and has_curly):
        return []
    i = has_straight[0]
    return [anchor(unit, max(0, i - 1), i + 2,
                   "straight and curly quotes are mixed in the same passage",
                   "quote-style")]


# DATES. Only the two things that are WRONG rather than unfashionable: a date
# the calendar does not have, and a deadline in the past. A style opinion about
# 09/11 versus 11/09 is not a defect and is deliberately not here.
MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"])}
MONTHS.update({m[:3]: n for m, n in list(MONTHS.items())})
DAYS_IN = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30,
           10: 31, 11: 30, 12: 31}
DATE_WORD_RE = re.compile(
    r"\b([A-Za-z]{3,9})\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\b")
DATE_ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
DEADLINE_RE = re.compile(
    r"\b(expires?|ends?|until|through|valid\s+(?:un)?til|deadline|by)\b", re.I)


def check_dates(unit, dic, ctx):
    out, text = [], unit["text"]
    for m in DATE_WORD_RE.finditer(text):
        month = MONTHS.get(m.group(1).lower())
        if month is None:
            continue
        day = int(m.group(2))
        # A written year decides February; with none, Feb 29 gets the doubt.
        last = (calendar.monthrange(int(m.group(3)), month)[1] if m.group(3)
                else DAYS_IN[month])
        if day < 1 or day > last:
            out.append(anchor(unit, m.start(), m.end(),
                              "%s has no day %d" % (m.group(1), day), "dates"))
            continue
        out += _deadline(unit, m, text, ctx, m.group(3), month, day)
    for m in DATE_ISO_RE.finditer(text):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if not (1 <= mo <= 12) or not (
                1 <= d <= calendar.monthrange(y, mo)[1]):
            out.append(anchor(unit, m.start(), m.end(),
                              "%s is not a date on the calendar" % m.group(0),
                              "dates"))
            continue
        out += _deadline(unit, m, text, ctx, str(y), mo, d)
    return out


def _deadline(unit, m, text, ctx, year, month, day):
    """A DATE IN THE PAST, but only where a deadline word says it is one.

    A past date in prose is usually history ("since March 2019"); a past date
    after "expires" is a dead offer on a live page. The deadline word is what
    separates them, and without one this says nothing."""
    if not year:
        return []
    window = text[max(0, m.start() - 60):m.start()]
    if not DEADLINE_RE.search(window):
        return []
    today = ctx.get("today") or datetime.now(timezone.utc).date()
    try:
        when = datetime(int(year), month, day, tzinfo=timezone.utc).date()
    except ValueError:
        return []
    if when >= today:
        return []
    return [anchor(unit, m.start(), m.end(),
                   "this deadline (%s) is in the past as of %s"
                   % (when.isoformat(), today.isoformat()), "dates")]


# TRUNCATION. Only the endings that cannot be a choice: a word cut at a hyphen,
# and a delimiter opened and never closed. A trailing ellipsis is a style every
# advertorial uses and is deliberately not flagged — that was the difference
# between this check and a noisy one.
TRUNC_HYPHEN_RE = re.compile(r"[A-Za-z]-$")
PAIRS = (("(", ")"), ("[", "]"), ("{", "}"), ("“", "”"))


def check_truncation(unit, dic, ctx):
    text = unit["text"].rstrip()
    if not text:
        return []
    out = []
    if TRUNC_HYPHEN_RE.search(text):
        out.append(anchor(unit, max(0, len(text) - 12), len(text),
                          "the passage stops on a hyphen — a word looks cut "
                          "off", "truncation"))
    for opener, closer in PAIRS:
        if text.count(opener) > text.count(closer):
            i = text.rfind(opener)
            out.append(anchor(unit, i, min(len(text), i + 20),
                              "%r is opened and never closed" % opener,
                              "truncation"))
    return out


# NAMES AGAINST THE DICTIONARY. Two things, both brand content: a phrase the
# brand has BANNED (with the brand's own reason), and a WRONG spelling of a
# canonical name. Neither is inferred — an unseeded dictionary makes this check
# silent, which is the honest behaviour for a check whose whole content is
# somebody else's decision.
#
# THE CLASS IS THE ENTRY'S OWN, READ WHERE THE FINDING IS BUILT (UQ-8). One
# class for the whole run meant a deliberate angle that runs hot could only
# ever read as a refusal, and a QC nobody can overrule gets switched off — so
# a banned entry's `class` rides with each of its findings and the default
# stays hard-stop. A value outside the vocabulary REFUSES rather than quietly
# falling back: a mistyped `taste` that silently read as hard-stop would block
# the very entries this exists to unblock.
def _entry_class(row, phrase):
    raw = row.get("class") if isinstance(row, dict) else None
    value = str(raw or "").strip().lower()
    if not value:
        return TAGS[1]
    if value not in ("hard-stop", "taste"):
        raise Refused(
            "dictionary-class",
            "banned entry %r declares class %r — the vocabulary is hard-stop "
            "or taste, and an absent class means hard-stop"
            % (phrase, str(raw)[:40]))
    return value


def check_dictionary_name(unit, dic, ctx):
    out, low = [], unit["text"].lower()
    for row in dic.get("banned") or []:
        phrase = (str(row.get("phrase")) if isinstance(row, dict)
                  else str(row)).strip()
        if not phrase:
            continue
        why = (str(row.get("comment") or "") if isinstance(row, dict) else "")
        classification = _entry_class(row, phrase)
        for m in re.finditer(re.escape(phrase.lower()), low):
            found = anchor(unit, m.start(), m.end(),
                           why or "%r is on the brand's banned list"
                           % phrase, "dictionary-name")
            if classification != TAGS[1]:
                # `_classification` is input-only (see `_finding_input`): the
                # anchor's own shape stays the frozen RV-23 one, and only the
                # record the finding becomes carries the entry's class.
                found["_classification"] = classification
            out.append(found)
    for row in dic.get("names") or []:
        for wrong in row.get("wrong") or []:
            if not str(wrong).strip():
                continue
            for m in re.finditer(re.escape(str(wrong).lower()), low):
                out.append(anchor(
                    unit, m.start(), m.end(),
                    "the canonical name is %r%s"
                    % (row["canonical"],
                       " (%s)" % row["comment"] if row.get("comment") else ""),
                    "dictionary-name"))
    return out


# PRICES AGAINST THE DICTIONARY. THE NARROW VERSION, on purpose: a figure is
# flagged only when it sits BESIDE a canonical product name and is not one of
# the prices that product actually carries. A brand's own offer bank is where
# the reason lives — the one this was measured against says "prices are
# channel-specific by design, never reconcile them into one number" — so a
# check that flagged every figure not on one list would flag the whole funnel.
# `never_prices` is the escape hatch for a figure that is wrong everywhere, and
# it is brand content too.
PRICE_RE = re.compile(r"[$£€]\s?\d[\d,]*(?:\.\d{2})?")
PRICE_WINDOW = 90


def _price_key(s):
    return re.sub(r"[\s,]", "", str(s or "")).rstrip("0").rstrip(".") \
        if "." in str(s) else re.sub(r"[\s,]", "", str(s or ""))


def check_dictionary_price(unit, dic, ctx):
    out, text = [], unit["text"]
    prices = list(PRICE_RE.finditer(text))
    if not prices:
        return []
    never = {_price_key(p) for p in dic.get("never_prices") or []}
    for m in prices:
        if _price_key(m.group(0)) in never:
            out.append(anchor(unit, m.start(), m.end(),
                              "%s is not a price this brand uses anywhere"
                              % m.group(0), "dictionary-price"))
            continue
        window = text[max(0, m.start() - PRICE_WINDOW):
                      m.end() + PRICE_WINDOW].lower()
        for row in dic.get("names") or []:
            if not row.get("prices"):
                continue
            if row["canonical"].lower() not in window:
                continue
            allowed = {_price_key(p) for p in row["prices"]}
            if _price_key(m.group(0)) in allowed:
                continue
            out.append(anchor(
                unit, m.start(), m.end(),
                "%s beside %r is not one of that product's prices (%s)"
                % (m.group(0), row["canonical"], ", ".join(row["prices"])),
                "dictionary-price"))
            break
    return out


# A WORDLIST SPELL CHECK WAS BUILT, MEASURED AND REMOVED — 2026-09-11, card
# RV-36 (text check)'s kill, fired rather than quoted. It is recorded here so
# nobody adds it back on the same reasoning:
#
#   It caught defect 7 of email_lead's eight ("no hussle") and cost 49 false
#   positives on the advertorial and 73 on the landing page — a wall of 2.
#   The cause is not tuneable and not brand data: the only word list on a mac
#   is `/usr/share/dict/words` (web2, lemmas only), which has no `women`, no
#   `using`, no `verified` and no `chamomile`. Inflection-stripping recovered
#   some and could never recover an irregular plural. There is no aspell and
#   no hunspell on the machine.
#
#   So a real spell check needs a real morphological dictionary (hunspell),
#   which is a DEPENDENCY DECISION and not a maker's — and until someone makes
#   it, misspellings are the metered tier's to find. `hussle` is exactly the
#   kind of thing the model tier sees.
#
# REQUIRED PHRASING. The mirror of `banned`, and DOCUMENT-LEVEL: a guarantee
# whose exact wording is the copy standard is missing from the page, not from a
# paragraph. Run once over everything, by `document_checks` below.
def doc_check_required(units, dic, ctx):
    out = []
    whole = "\n".join(u["text"] for u in units).lower()
    for row in dic.get("required") or []:
        phrase = (str(row.get("phrase")) if isinstance(row, dict)
                  else str(row)).strip()
        if not phrase or phrase.lower() in whole:
            continue
        why = (str(row.get("comment") or "") if isinstance(row, dict) else "")
        out.append(_tail_anchor(
            units, "the required phrasing %r is nowhere on this text%s"
            % (phrase, " — %s" % why if why else ""), "required-phrase"))
    return [a for a in out if a]


# MISSING CTA. Document-level and ONE finding at most: a page with no way to
# act is one defect, not one per paragraph. The CTA words are brand content —
# an unseeded dictionary makes this check silent rather than guessing that
# "buy now" is what this brand says.
def doc_check_missing_cta(units, dic, ctx):
    phrases = [str(p).strip().lower() for p in dic.get("cta") or []
               if str(p).strip()]
    if not phrases:
        return []
    whole = "\n".join(u["text"] for u in units).lower()
    if any(p in whole for p in phrases):
        return []
    a = _tail_anchor(units,
                     "no call to action anywhere on this text — none of the "
                     "brand's CTA phrasings (%s) appear"
                     % ", ".join(repr(p) for p in phrases[:6]), "missing-cta")
    return [a] if a else []


def _tail_anchor(units, comment, check):
    """A document-level finding still has to point at words (an anchor with no
    quote resolves to nothing and RV-23 (anchors declared) refuses one), so it
    points at THE END of the text — where a reader looking for the CTA that is
    not there would have stopped."""
    for unit in reversed(units):
        if unit["text"].strip():
            return anchor(unit, max(0, len(unit["text"]) - 60),
                          len(unit["text"]), comment, check)
    return None


# SPELLING AND GRAMMAR — THE ONE METERED CHECK (WM-34 (infer action)).
# Everything above is stdlib, free, and identical on every run. This one
# leaves the machine, costs a fraction of a cent, and is the only check whose
# answer can vary between two runs on the same text — which is exactly why its
# output is VERIFIED against the source before it becomes an anchor.
GRAMMAR_PROMPT = """\
You are proof-reading marketing copy that has already shipped. Find ONLY
outright errors a copy editor would circle in red:

  · a misspelt word
  · a word that is the wrong word (its/it's, rise/rinse, my/by)
  · subject-verb or singular/plural disagreement
  · a broken sentence: a missing or duplicated word, a dangling object

DO NOT report style, tone, punctuation preference, capitalisation of headings,
sentence fragments used deliberately, brand names, or anything you are merely
unsure about. A false alarm costs more than a miss: if it could be correct as
written, SAY NOTHING about it.

The text, one numbered block per line:

{blocks}

Answer with ONE json object and nothing else:
  {{"findings": [{{"block": <the block number>,
                 "quote": "<the exact words from that block, copied
                            character for character, 3 to 12 words>",
                 "comment": "<the correction, under 140 characters>"}}]}}

An empty findings list is a valid and common answer.
"""
JSON_RE = re.compile(r"\{[\s\S]*\}")


def grammar_findings(units, dic, ctx, call=None):
    """The metered tier: one call, and every quote it returns VERIFIED.

    THE VERIFICATION IS THE CHECK'S SAFETY, not a nicety. A model asked for
    exact quotes returns approximate ones, and an anchor whose quote is not in
    the text resolves to "not found in this version" — a finding a person
    cannot act on, which is the worst kind of false positive because it looks
    like a tool defect rather than a wrong opinion. So a quote that is not in
    the block it names is DROPPED, and `report()` says how many were."""
    if not units:
        return [], {"ran": False, "why": "no text"}
    numbered, total = [], 0
    for i, unit in enumerate(units):
        line = "%d. %s" % (i + 1, unit["text"])
        if total + len(line) > MODEL_MAX_CHARS:
            break
        numbered.append(line)
        total += len(line)
    truncated = len(numbered) < len(units)
    prompt = GRAMMAR_PROMPT.format(blocks="\n".join(numbered))
    meta = {"ran": True, "model": MODEL, "blocks_sent": len(numbered),
            "blocks_total": len(units), "truncated": truncated,
            "returned": 0, "dropped": 0, "cost_usd": None, "why": ""}
    try:
        reply, spend = (call or _infer_call)(prompt, ctx)
    except Refused as e:
        meta.update(ran=False, why="%s: %s" % (e.reason, e.detail))
        return [], meta
    meta["cost_usd"] = spend
    m = JSON_RE.search(str(reply or ""))
    if not m:
        meta.update(ran=False, why="the model returned no json object")
        return [], meta
    try:
        doc = json.loads(m.group(0))
    except ValueError as e:
        meta.update(ran=False, why="unparseable json: %s" % e)
        return [], meta
    out = []
    for row in (doc.get("findings") or []) if isinstance(doc, dict) else []:
        if not isinstance(row, dict):
            continue
        meta["returned"] += 1
        quote = str(row.get("quote") or "")
        comment = str(row.get("comment") or "").strip()[:140]
        try:
            idx = int(row.get("block")) - 1
        except (TypeError, ValueError):
            idx = -1
        hit = None
        if 0 <= idx < len(units) and quote.strip():
            at = units[idx]["text"].find(quote)
            if at >= 0:
                hit = anchor(units[idx], at, at + len(quote),
                             comment or "reads as an error", "spelling-grammar")
        if hit is None:
            meta["dropped"] += 1          # a quote that is not in the text
            continue
        out.append(hit)
    return out, meta


def _infer_call(prompt, ctx):
    """ONE metered call through WM-34 (infer action). Returns (reply, usd).

    THE SEAM, and the only thing in this file that opens a socket — the
    declared test replaces it, exactly as `prereview_adapter`'s `fetch` and
    `claude_runner` are replaced in theirs. WM-34 (infer action) owns the
    registry check, the grant, the payload, the cost and the refusal; this
    function owns none of them and re-implements none of them."""
    ir = infer()
    item = str(ctx.get("item") or "text-check")
    run = re.sub(r"[^A-Za-z0-9._-]+", "-", item)[:60] or "text-check"
    try:
        spec = ir.plan(item, {"verdict": {
            "model": MODEL, "run": run, "prompt": prompt,
            "max_tokens": MODEL_MAX_TOKENS, "temperature": 0,
            "requested_by": prereview().REVIEWER}})
    except Exception as e:
        raise Refused("grammar-refused-before-the-call", str(e)[:300])
    try:
        from job_env import scoped_env
        env = scoped_env("infer")
    except Exception:                     # pragma: no cover — standalone use
        env = dict(os.environ)
    key = (env.get(spec["key_env"]) or "").strip()
    if not key:
        # WM-34 (infer action)'s own rail 5, honoured rather than re-decided:
        # a missing key refuses BEFORE the call. This runner then files its
        # deterministic findings, which is the card's DICTIONARY-ONLY fallback
        # reached by the absence of a credential.
        raise Refused("grammar-needs-the-infer-key",
                      "%s is not in this process's `infer` grant, so the "
                      "metered call is refused before it is made. The "
                      "deterministic checks still ran." % spec["key_env"])
    result = ir.execute(spec, key)
    if not result.get("ok"):
        raise Refused("grammar-call-failed",
                      str(result.get("error") or "")[:300])
    spend = ir.cost(spec, result.get("usage") or {})
    return result.get("reply") or "", (spend or {}).get("usd")


# ---- THE TABLE. A check is removed by deleting its row. ----------------------
# Card RV-36 (text check)'s kill, as a data structure: "if the benchmark shows
# more than two false positives per item after one round of dictionary work,
# the check that produces them is REMOVED rather than tuned — a runner earns
# its checks one at a time." `needs_dictionary` says which rows go quiet on a
# brand nobody has seeded, so `report()` can tell a reader that a silent check
# was silent for a reason.
CHECKS = (
    ("doubled-word", check_doubled_word, False),
    ("placeholder", check_placeholder, False),
    ("broken-character", check_broken_character, False),
    ("double-space", check_double_space, False),
    ("quote-style", check_quotes, False),
    ("dates", check_dates, False),
    ("truncation", check_truncation, False),
    ("dictionary-name", check_dictionary_name, True),
    ("dictionary-price", check_dictionary_price, True),
)
DOCUMENT_CHECKS = (
    ("required-phrase", doc_check_required, True),
    ("missing-cta", doc_check_missing_cta, True),
)
GRAMMAR_CHECK = "spelling-grammar"

# EVERY CHECK NAME, for a reader and for the declared test: the test asserts
# that each of these has a fixture that triggers it AND one that must not, so
# adding a row here without a pair of fixtures fails the test rather than
# shipping unmeasured.
CHECK_NAMES = tuple([n for n, _, _ in CHECKS]
                    + [n for n, _, _ in DOCUMENT_CHECKS] + [GRAMMAR_CHECK])


def run_checks(units, dic=None, today=None, item="", grammar=True, call=None):
    """Every check over every unit -> (anchors, report).

    The order is the table's, then the document-level rows, then the metered
    tier, so a reader of a filed verdict meets the free and repeatable findings
    before the paid and variable one."""
    dic = dic if dic is not None else load_dictionary()
    off = {str(x) for x in (dic.get("checks_off") or [])}
    seeded = bool(dic.get("found"))
    ctx = {"today": today, "item": item}
    anchors, per = [], {}
    for name, fn, needs_dict in CHECKS:
        if name in off:
            per[name] = {"ran": False, "why": "off in the brand dictionary"}
            continue
        if needs_dict and not seeded:
            per[name] = {"ran": False, "why": "no dictionary for this brand"}
            continue
        found = []
        for unit in units:
            found += [a for a in fn(unit, dic, ctx) if a]
        per[name] = {"ran": True, "found": len(found)}
        anchors += found
    for name, fn, needs_dict in DOCUMENT_CHECKS:
        if name in off:
            per[name] = {"ran": False, "why": "off in the brand dictionary"}
            continue
        if needs_dict and not seeded:
            per[name] = {"ran": False, "why": "no dictionary for this brand"}
            continue
        found = [a for a in fn(units, dic, ctx) if a]
        per[name] = {"ran": True, "found": len(found)}
        anchors += found
    if grammar and GRAMMAR_CHECK not in off:
        found, meta = grammar_findings(units, dic, ctx, call=call)
        meta["found"] = len(found)
        per[GRAMMAR_CHECK] = meta
        anchors += found
    else:
        per[GRAMMAR_CHECK] = {"ran": False, "why": (
            "off in the brand dictionary" if GRAMMAR_CHECK in off
            else "not asked for")}
    return anchors, {"units": len(units), "anchors": len(anchors),
                     "checks": per, "dictionary": {
                         "path": dic.get("path"), "found": seeded,
                         "brand": dic.get("brand")}}


# ============================================================================
# THE TEXT OF A REQUEST — resolved from the record's own pointer
# ============================================================================
TEXT_TYPES = ("text", "md", "doc")
URL_TYPES = ("page", "link")
FETCH_TIMEOUT = 60
MAX_FETCH_BYTES = 8 * 1024 * 1024


def request_units(request_body, root=None, fetch=None, figma_rows=None):
    """A request's own pointer -> units, or `Refused` BY NAME.

    NO NEW WAREHOUSE AND NO NEW FIELD. `md`/`text`/`doc` on `repo` is a file in
    the checkout; `page`/`link` on `url` is the built HTML AT THAT URL, which is
    where a page's words live and the only honest source for them (RV-35 (page
    capture) declines to invent a text warehouse and says so). An image, a
    video and anything else has no words to check and is refused rather than
    guessed at."""
    body = request_body if isinstance(request_body, dict) else {}
    typ = str(body.get("type") or "").strip().lower()
    asset = body.get("asset") if isinstance(body.get("asset"), dict) else {}
    wh = str(asset.get("warehouse") or "").strip().lower()
    ref = str(asset.get("ref") or "").strip()
    if figma_rows is not None:
        return units_from_figma(figma_rows)
    if typ in TEXT_TYPES:
        if wh != "repo":
            raise Refused("text-not-in-the-checkout",
                          "a %s request's words are read from the checkout and "
                          "this one points at warehouse %r" % (typ, wh))
        base = (Path(root) if root else WS).resolve()
        p = (base / ref).resolve()
        if base not in p.parents or not p.is_file():
            raise Refused("text-not-resolvable",
                          "%r is not a file inside this checkout — a record is "
                          "DATA and never a path into the filesystem at large "
                          "(workspace rule 8)" % ref[:120])
        raw = p.read_text(encoding="utf-8", errors="replace")
        if p.suffix.lower() in (".html", ".htm"):
            return units_from_html(raw)
        return units_from_text(raw, markdown=p.suffix.lower() == ".md")
    if typ in URL_TYPES:
        if wh != "url":
            raise Refused("page-not-a-url",
                          "a %s request carries a `url` pointer and this one "
                          "is warehouse %r" % (typ, wh))
        html = (fetch or _fetch_text)(ref)
        return units_from_html(html)
    raise Refused("type-has-no-words",
                  "type %r carries no text to check — an image goes to vision "
                  "(RV-7 (claude prereview adapter)) and a video is refused by "
                  "name there" % (typ or "unstated"))


def _fetch_text(url):
    """The built HTML at a url. NO CREDENTIAL: exactly what a browser gets.

    The seam the declared test replaces. A url this cannot read is refused BY
    NAME — a page nobody could fetch is never checked as an empty document,
    because "clean" and "unread" are different answers."""
    if not str(url).lower().startswith(("http://", "https://")):
        raise Refused("page-url-not-http",
                      "the pointer is %r; only http(s) is fetched"
                      % str(url)[:120])
    req = urllib.request.Request(url, method="GET", headers={
        "Accept": "text/html,*/*", "X-Client": VERSION})
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as r:
            raw = r.read(MAX_FETCH_BYTES + 1)
    except urllib.error.HTTPError as e:    # pragma: no cover — network
        raise Refused("page-url-refused", "%s %s" % (e.code, url[:120]))
    except Exception as e:                 # pragma: no cover — network
        raise Refused("page-url-unreachable",
                      "%s: %s" % (type(e).__name__, str(e)[:200]))
    if len(raw) > MAX_FETCH_BYTES:
        raise Refused("page-too-large",
                      "%s serves more than %d MB of html"
                      % (url[:120], MAX_FETCH_BYTES // (1024 * 1024)))
    return raw.decode("utf-8", "replace")


def text_from_url(url):
    """Fetch one public URL and return its rendered-text units; write nothing.

    This is the raw-URL seam shared by UQ-5 (voice check) and UQ-6 (avatar
    walk). It deliberately composes the existing fetcher and HTML reducer:
    record-shaped capture remains page_capture.py's separate job.
    """
    return units_from_html(_fetch_text(url))


# ============================================================================
# THE BUNDLE — the portable source; filing and HTML are readers of its records
# ============================================================================
BUNDLE_VERSION = 1
FILED_VERDICT = "fix"
# The checker tag and the DEFAULT class. UQ-8: the class is PER FINDING —
# `_entry_class` reads it off the dictionary entry where each finding is
# built — so this pair is only what a finding with no class of its own falls
# back to, and the default stays hard-stop.
TAGS = ("text-check", "hard-stop")
TRUTH_STATUSES = ("signed", "draft", "provisional")
_RECORD_FIELDS = {"schema", "kind", "reviewer", "item", "verdict", "notes",
                  "created", "via"}


def _anchor_check(a):
    comment = str(a.get("comment") or "")
    return comment.split(" — ", 1)[0].strip() or "text-check"


def compose(anchors, report, rr=None, checker=TAGS[0],
            classification=TAGS[1], note=None):
    """Anchors -> one `event: verdict` body inside the frozen grammar.

    `write_bundle` calls this once per finding. Keeping composition separate
    lets the verdict cap remain the review component's number while leaving the
    bundle writer as the only place that mints complete records. The second
    checker adds its own checker tag, class and note through this same composer;
    the defaults preserve RV-36 (text check)'s byte shape.
    """
    rr = rr or review_request()
    if not anchors:
        raise Refused("nothing-to-file",
                      "no findings, and a runner that could file a PASS would "
                      "be a reviewer (the card's never). Nothing was filed.")
    checks = []
    for a in anchors:
        name = _anchor_check(a)
        if name not in checks:
            checks.append(name)
    if note is None:
        note = ("%d finding(s) on %d block(s) of text, anchored to the words "
                "they are about. A PROPOSAL, never a pass or a close."
                % (len(anchors), report.get("units", 0)))
    body = _body(anchors, str(note), checks, checker=checker,
                 classification=classification)
    try:
        rr.anchors(body["anchors"])
        rr.capped(body)
    except rr.Refused as e:
        raise Refused("anchors-over-the-cap", str(e))
    return body


def _body(anchors, note, checks=(), checker=TAGS[0],
          classification=TAGS[1]):
    checker = str(checker or "").strip()
    classification = str(classification or "").strip()
    if not checker:
        raise Refused("finding-checker-empty", "a finding needs its checker tag")
    if classification not in ("hard-stop", "taste"):
        raise Refused("finding-class",
                      "%r is not hard-stop or taste" % classification)
    reasons = [checker, classification]
    reasons.extend(name for name in checks if name not in reasons)
    return {"event": "verdict", "verdict": FILED_VERDICT,
            "reasons": reasons, "note": note[:800], "anchors": anchors}


def _git_blob_sha(path):
    """The git blob id of the exact bytes read, without invoking git."""
    data = Path(path).read_bytes()
    header = ("blob %d\0" % len(data)).encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def truth_from_dictionary(dic, root=None):
    """The dictionary truth stamp, or `[]` when no dictionary was read."""
    if not dic or not dic.get("found"):
        return []
    p = Path(str(dic.get("path") or ""))
    if not p.is_file():
        raise Refused("truth-file-missing",
                      "%s was reported as read but is not a file" % p)
    status = str(dic.get("status") or "").strip().lower()
    if status not in TRUTH_STATUSES:
        raise Refused(
            "truth-status-missing",
            "%s was read but does not declare status %s; truth is stamped, "
            "never assumed" % (p, "|".join(TRUTH_STATUSES)))
    base = Path(root or WS).resolve()
    try:
        path = str(p.resolve().relative_to(base))
    except ValueError:
        path = str(p.resolve())
    return [{"path": path, "sha": _git_blob_sha(p), "status": status}]


def _git_head_sha(root=None):
    """Resolve HEAD from git files, including a linked-worktree `.git` file."""
    root = Path(root or WS).resolve()
    marker = root / ".git"
    if marker.is_dir():
        gitdir = marker
    elif marker.is_file():
        line = marker.read_text(encoding="utf-8").strip()
        if not line.startswith("gitdir:"):
            raise Refused("engine-sha-unavailable", "%s is not a gitdir" % marker)
        gitdir = Path(line.split(":", 1)[1].strip())
        if not gitdir.is_absolute():
            gitdir = (root / gitdir).resolve()
    else:
        raise Refused("engine-sha-unavailable",
                      "%s has no .git metadata" % root)
    common = gitdir
    common_file = gitdir / "commondir"
    if common_file.is_file():
        common = (gitdir / common_file.read_text(encoding="utf-8").strip()
                  ).resolve()
    head = (gitdir / "HEAD").read_text(encoding="utf-8").strip()
    if re.match(r"^[0-9a-f]{40,64}$", head):
        return head
    if not head.startswith("ref: "):
        raise Refused("engine-sha-unavailable", "HEAD does not name a commit")
    ref = head[5:].strip()
    for home in (gitdir, common):
        p = home / ref
        if p.is_file():
            sha = p.read_text(encoding="utf-8").strip()
            if re.match(r"^[0-9a-f]{40,64}$", sha):
                return sha
    packed = common / "packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="utf-8").splitlines():
            if line.startswith(("#", "^")):
                continue
            bits = line.split(" ", 1)
            if len(bits) == 2 and bits[1] == ref:
                return bits[0]
    raise Refused("engine-sha-unavailable", "%s does not resolve" % ref)


def engine_details(sha=None):
    return {"name": "text_check", "version": VERSION,
            "sha": str(sha or _git_head_sha())}


def run_details(at=None, by=None, host=None):
    return {"at": str(at or _now_iso()),
            "by": str(by or os.environ.get("USER") or "unknown"),
            "host": str(host or socket.gethostname())}


def _clean_truth(truth):
    if not isinstance(truth, (list, tuple)):
        raise Refused("truth-not-a-list", "truth must be a list")
    out = []
    for i, row in enumerate(truth):
        if not isinstance(row, dict):
            raise Refused("truth-not-an-object", "truth[%d] is not an object" % i)
        if set(row) != {"path", "sha", "status"}:
            raise Refused("truth-shape",
                          "truth[%d] must be exactly {path, sha, status}" % i)
        path, sha = str(row["path"]), str(row["sha"]).lower()
        status = str(row["status"]).lower()
        if not path:
            raise Refused("truth-path-empty", "truth[%d].path is empty" % i)
        if not re.match(r"^[0-9a-f]{7,64}$", sha):
            raise Refused("truth-sha-invalid", "truth[%d].sha is not hex" % i)
        if status not in TRUTH_STATUSES:
            raise Refused("truth-status-invalid",
                          "truth[%d].status is not %s" %
                          (i, "|".join(TRUTH_STATUSES)))
        out.append({"path": path, "sha": sha, "status": status})
    return out


def _clean_engine(engine):
    if not isinstance(engine, dict) or set(engine) != {"name", "version", "sha"}:
        raise Refused("engine-shape", "engine must be exactly {name, version, sha}")
    out = {k: str(engine.get(k) or "").strip()
           for k in ("name", "version", "sha")}
    if not out["name"] or not out["version"]:
        raise Refused("engine-empty", "engine name and version are required")
    if not re.match(r"^[0-9a-f]{7,64}$", out["sha"].lower()):
        raise Refused("engine-sha-invalid", "engine.sha is not a git sha")
    out["sha"] = out["sha"].lower()
    return out


def _clean_run(run):
    if not isinstance(run, dict) or set(run) != {"at", "by", "host"}:
        raise Refused("run-shape", "run must be exactly {at, by, host}")
    out = {k: str(run.get(k) or "").strip() for k in ("at", "by", "host")}
    if not all(out.values()):
        raise Refused("run-empty", "run.at, run.by and run.host are required")
    try:
        dt = datetime.fromisoformat(out["at"].replace("Z", "+00:00"))
    except ValueError:
        raise Refused("run-at-invalid", "run.at is not an ISO timestamp")
    if dt.tzinfo is None or dt.utcoffset() != timedelta(0):
        raise Refused("run-at-not-utc", "run.at must carry UTC")
    out["at"] = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return out


def _record_time(run_at, index):
    dt = datetime.fromisoformat(run_at.replace("Z", "+00:00"))
    return (dt + timedelta(microseconds=index)).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ")


def _check_word(engine_name):
    words = {"text_check": "text", "voice_check": "voice",
             "avatar_walk": "avatar-walk", "technical_check": "technical"}
    return words.get(engine_name, engine_name.replace("_", "-"))


def _validate_bundle_record(rec, rr=None):
    rr = rr or review_request()
    if not isinstance(rec, dict) or set(rec) != _RECORD_FIELDS:
        raise Refused("bundle-record-shape",
                      "a record must be an unchanged review record envelope")
    if rec.get("schema") != 1 or rec.get("kind") != rr.KIND:
        raise Refused("bundle-record-kind", "record schema/kind is not review/1")
    item = str(rec.get("item") or "")
    if not rr.ITEM_RE.match(item) or "--" in item:
        raise Refused("bundle-record-item", "%r is not an RQ item" % item)
    reviewer = str(rec.get("reviewer") or "")
    if rr.people(reviewer, "reviewer")[0] != reviewer:
        raise Refused("bundle-record-reviewer", "reviewer was not canonical")
    machine = prereview().REVIEWER
    if reviewer != machine:
        raise Refused("bundle-record-reviewer",
                      "checker records must use machine reviewer %s" % machine)
    created = str(rec.get("created") or "")
    if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
                    r"(?:\.\d{6})?Z$", created):
        raise Refused("bundle-record-created",
                      "record.created must be a UTC timestamp")
    try:
        datetime.fromisoformat(created.replace("Z", "+00:00"))
    except ValueError:
        raise Refused("bundle-record-created",
                      "record.created is not a real UTC timestamp")
    body = rec.get("verdict")
    if not isinstance(body, dict) or body.get("event") != "verdict":
        raise Refused("bundle-record-event", "a finding record must be a verdict")
    allowed = {"event", "verdict", "reasons", "note", "anchors"}
    unknown = set(body) - allowed
    if unknown:
        raise Refused("bundle-record-field",
                      "%s is not a verdict field for checker records" %
                      sorted(unknown)[0])
    if body.get("verdict") != FILED_VERDICT:
        raise Refused("bundle-record-verdict", "a checker verdict is always fix")
    reasons = body.get("reasons")
    if not isinstance(reasons, list) or not reasons:
        raise Refused("bundle-record-reasons", "reasons must name the checker")
    if not any(c in reasons for c in ("hard-stop", "taste")):
        raise Refused("bundle-record-class", "reasons must carry hard-stop or taste")
    anchors = body.get("anchors")
    if anchors is not None:
        rr.anchors(anchors)
    rr.capped(body)
    predicted = rr.record(item, body, reviewer, notes=rec.get("notes"),
                          created=rec.get("created"))
    if predicted != rec:
        raise Refused("bundle-record-not-copyable",
                      "review_request.file_record would transform this record")
    return rec


def _bundle_report(report, truth):
    if not isinstance(report, dict):
        raise Refused("report-not-an-object", "report must be an object")
    try:
        out = json.loads(json.dumps(report, ensure_ascii=False))
    except (TypeError, ValueError) as e:
        raise Refused("report-not-portable", str(e))
    dictionary = out.get("dictionary")
    if isinstance(dictionary, dict):
        # A portable report never leaks the runner's absolute checkout path;
        # truth[] carries the relative, content-addressed source when one ran.
        dictionary["path"] = truth[0]["path"] if truth else None
    return out


def _reviewer_notes(engine_name, reviewer):
    if engine_name == "text_check":
        return REVIEWER_NOTE % reviewer
    check = _check_word(engine_name)
    return (
        "Machine %s QC, filed as the machine reviewer `%s` and never as a "
        "person (OR-5 (verdict attribution)). EVERY FINDING IS A PROPOSAL "
        "ANCHORED TO THE WORDS IT IS ABOUT: it closes nothing, it does not "
        "count toward the close rule's one named reviewer, and a clean asset "
        "is filed as nothing at all rather than as a pass." % (check, reviewer))


def _finding_input(value):
    """Split one writer input into its contract anchor and verdict metadata.

    `_classification` and `_note` are INPUT-ONLY: the bundle's anchors remain
    the frozen RV-23 (anchors declared) shape. This keeps one writer usable by
    checks whose findings differ in class and prose without adding a second
    record composer or changing the ruled writer signature.
    """
    if not isinstance(value, dict):
        raise Refused("finding-not-an-object", "each finding must be an anchor")
    anchor_value = dict(value)
    classification = anchor_value.pop("_classification", TAGS[1])
    note = anchor_value.pop("_note", None)
    return anchor_value, classification, note


def _clean_pointer(asset, rr):
    """ONE review pointer, or THE ORDERED LIST OF THEM (contract §3a).

    The list is developer's amendment of 2026-09-17 ("allow 4b") for a check whose
    unit is the FUNNEL rather than the page: one run, one bundle, findings that
    cite two pages each. THE ORDER IS THE CUSTOMER'S ORDER and is load-bearing,
    so it is preserved exactly as given and never sorted.

    Every element goes through RV-2 (review request module)'s own `asset`, so
    the list form buys no relaxation of the pointer grammar — and a single
    pointer still produces the byte-for-byte envelope it produced before this
    function existed.
    """
    if isinstance(asset, dict):
        return rr.asset(asset)
    if not isinstance(asset, (list, tuple)):
        raise Refused(
            "asset-not-a-pointer",
            "asset must be one review pointer or the ORDERED LIST of them "
            "(findings-bundle contract §3a) — %s" % type(asset).__name__)
    if not asset:
        raise Refused(
            "asset-list-empty",
            "an ordered list of pointers with nothing in it names no funnel")
    return [rr.asset(row) for row in asset]


def write_bundle(out_dir, report, anchors, asset, truth, engine, run, item):
    """Write findings.json + findings.html, and return the JSON envelope.

    `out_dir=None` is the in-memory seam used by the legacy filing adapter: it
    writes nowhere, but still mints records through this one function. Every
    actual bundle write requires the caller's named directory.
    """
    rr = review_request()
    item = str(item or "")
    if not rr.ITEM_RE.match(item) or "--" in item:
        raise Refused("item-not-a-review-request",
                      "%r is not an `RQ-<id>`" % item[:60])
    clean_asset = _clean_pointer(asset, rr)
    clean_truth = _clean_truth(truth)
    clean_engine = _clean_engine(engine)
    clean_run = _clean_run(run)
    clean_report = _bundle_report(report, clean_truth)
    pr = prereview()
    if anchors:
        pr.refuse_if_a_person(WS)
    reviewer = pr.REVIEWER
    checker = clean_engine["name"].replace("_", "-")
    records = []
    for i, finding in enumerate(anchors or []):
        clean_anchor, classification, note = _finding_input(finding)
        if note is None and classification == "taste":
            # UQ-8: a taste record says ADVISORY in its own words, because the
            # note is the surface readers who never open reasons[] do read.
            note = ("A taste finding on %d block(s) of text — ADVISORY, "
                    "worth your eye and never a blocker: it gates nothing."
                    % report.get("units", 0))
        body = compose([clean_anchor], report, rr=rr, checker=checker,
                       classification=classification, note=note)
        rec = rr.record(
            item, body, reviewer,
            notes=_reviewer_notes(clean_engine["name"], reviewer),
            created=_record_time(clean_run["at"], i))
        records.append(_validate_bundle_record(rec, rr=rr))
    bundle = {"bundle": BUNDLE_VERSION,
              "check": _check_word(clean_engine["name"]),
              "asset": clean_asset,
              "truth": clean_truth,
              "engine": clean_engine,
              "run": clean_run,
              "report": clean_report,
              "clean": not records,
              "records": records}
    if out_dir is not None:
        out = Path(out_dir)
        if out.exists() and not out.is_dir():
            raise Refused("out-not-a-directory", "%s is not a directory" % out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "findings.json").write_text(
            json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
        (out / "findings.html").write_text(_bundle_html(bundle), encoding="utf-8")
    return bundle


def _comment_value(value):
    return re.sub(r"\s+", " ", str(value)).replace("--", "—").strip()


def _truth_label(truth, html=False):
    if not truth:
        return "no truth file"
    parts = []
    for row in truth:
        path = Path(row["path"]).name if html else row["path"]
        status = row["status"].upper() if html else row["status"]
        value = "%s @ %s (%s)" % (path, row["sha"][:7], status)
        parts.append(html_escape(value) if html else _comment_value(value))
    return " · ".join(parts)


def _skipped_checks(report):
    checks = report.get("checks") if isinstance(report, dict) else {}
    out = []
    rows = checks.items() if isinstance(checks, dict) else ()
    for name, row in rows:
        if isinstance(row, dict) and row.get("ran") is False:
            out.append((str(name), str(row.get("why") or "not run")))
    return out


def _record_class(body):
    """A record's class, read from the only place it lives: `reasons[]`.

    UQ-8's vocabulary (`hard-stop` | `taste`, the bundle contract's own
    words) — a reader that wants to know how heavy a finding is asks the
    record, never the run."""
    return "hard-stop" if "hard-stop" in (body.get("reasons") or []) \
        else "taste"


def _asset_head(asset):
    """The pointer the header and strip name. For the funnel list it is the
    FIRST page — the customer's own first page — with the rest counted, because
    a strip that named five pointers would say nothing in the space it has."""
    if isinstance(asset, dict):
        return asset, ""
    rest = len(asset) - 1
    return asset[0], ("(+%d more page%s in order)"
                      % (rest, "" if rest == 1 else "s")) if rest else ""


def _bundle_html(bundle):
    asset, more = _asset_head(bundle["asset"])
    engine = bundle["engine"]
    run = bundle["run"]
    count = len(bundle["records"])
    skipped = _skipped_checks(bundle.get("report") or {})
    grammar = (bundle.get("report", {}).get("checks", {})
               .get(GRAMMAR_CHECK, {}))
    deterministic_only = isinstance(grammar, dict) and grammar.get("ran") is False
    header_rows = [
        "<!-- findings-bundle",
        "check:    %s" % _comment_value(bundle["check"]),
        ("asset:    %s · %s %s" % (_comment_value(asset["warehouse"]),
                                    _comment_value(asset["ref"]),
                                    _comment_value(more))).rstrip(),
        "truth:    %s" % _truth_label(bundle["truth"]),
        "engine:   %s %s @ %s" % (_comment_value(engine["name"]),
                                    _comment_value(engine["version"]),
                                    engine["sha"][:7]),
        "run:      %s by %s on %s" % (_comment_value(run["at"]),
                                       _comment_value(run["by"]),
                                       _comment_value(run["host"]))]
    if deterministic_only:
        header_rows.append("mode:     deterministic-only")
    if skipped:
        header_rows.append("skipped:  %s" % "; ".join(
            "%s (%s)" % (_comment_value(name), _comment_value(why))
            for name, why in skipped))
    taste_count = sum(1 for rec in bundle["records"]
                      if _record_class(rec["verdict"]) == "taste")
    detail = ("%d fix · %d hard-stop · %d taste"
              % (count, count - taste_count, taste_count)) if count else "0 fix"
    header_rows.extend([
        "records:  %d (%s) · clean: %s" %
        (count, detail, str(bundle["clean"]).lower()),
        "-->"])
    header = "\n".join(header_rows)
    mode_label = " · deterministic-only" if deterministic_only else ""
    skipped_label = (" · skipped %s" % ", ".join(
        html_escape(name) for name, _ in skipped)) if skipped else ""
    advisory_label = " · %d advisory" % taste_count if taste_count else ""
    strip = ("<div class=\"findings-strip\">Findings · %s · %s · judged "
             "against %s · %d finding%s · %s%s%s%s</div>" %
             (html_escape(bundle["check"]),
              html_escape(("%s %s" % (asset["title"], more)).rstrip()),
              _truth_label(bundle["truth"], html=True), count,
              "" if count == 1 else "s", html_escape(run["at"]), mode_label,
              skipped_label, advisory_label))
    style = """<style>
:root{color-scheme:light dark;font:16px/1.5 system-ui,sans-serif}
body{max-width:920px;margin:0 auto;padding:24px;background:#f7f7f5;color:#222}
.findings-strip{padding:12px 16px;border:1px solid #999;background:#fff;font-weight:650}
.finding{margin-top:16px;padding:18px;border:1px solid #bbb;background:#fff}
.finding h2{margin:0 0 10px;font-size:1rem}.quote{font-size:1.05rem}
.context{color:#666}mark{padding:2px 3px;background:#ffe58a;color:#111}
.comment{font-weight:600}.meta{color:#666;font-size:.875rem}
@media(prefers-color-scheme:dark){body{background:#181818;color:#eee}.findings-strip,.finding{background:#242424;border-color:#555}.context,.meta{color:#aaa}}
</style>"""
    blocks = []
    checker_tag = engine["name"].replace("_", "-")
    for rec in bundle["records"]:
        body = rec["verdict"]
        check = next((r for r in body["reasons"]
                      if r not in (checker_tag, "hard-stop", "taste")),
                     checker_tag)
        classification = _record_class(body)
        anchors = []
        for a in body.get("anchors") or []:
            anchors.append(
                "<div class=\"quote\"><span class=\"context\">%s</span>"
                "<mark>%s</mark><span class=\"context\">%s</span></div>"
                "<p class=\"comment\">%s</p>" %
                (html_escape(a["prefix"]), html_escape(a["quote"]),
                 html_escape(a["suffix"]), html_escape(a["comment"])))
        note = ("<p class=\"note\">%s</p>" % html_escape(body["note"])
                if body.get("note") else "")
        blocks.append(
            "<article class=\"finding\"><h2>%s</h2>%s%s"
            "<p class=\"meta\">%s · %s · %s</p></article>" %
            (html_escape(check), "".join(anchors), note,
             html_escape("advisory (taste)" if classification == "taste"
                         else classification),
             html_escape(rec["reviewer"]),
             html_escape(rec["item"])))
    return header + "\n" + strip + "\n" + style + "\n" + "\n".join(blocks)


def _read_bundle(bundle):
    if isinstance(bundle, dict):
        return bundle
    p = Path(bundle)
    if p.is_dir():
        p = p / "findings.json"
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Refused("bundle-unreadable", "%s: %s" % (p, e))
    if not isinstance(doc, dict):
        raise Refused("bundle-unreadable", "%s is not an object" % p)
    return doc


def file_findings(bundle, root=None, write=True, rr=None, env=None):
    """Copy a bundle's records to the review plane without transforming them."""
    rr = rr or review_request()
    doc = _read_bundle(bundle)
    records = doc.get("records")
    if not isinstance(records, list):
        raise Refused("bundle-records-not-a-list", "records must be a list")
    if bool(doc.get("clean")) != (not records):
        raise Refused("bundle-clean-mismatch", "clean must equal records == []")
    for rec in records:
        _validate_bundle_record(rec, rr=rr)
    out = {"records": records, "paths": [], "path": None, "filed": False}
    if not records or not write:
        return out
    if env is not None and rr.has_key(env):
        raise Refused("bundle-copy-needs-git-door",
                      "the API stamps its own time, so it cannot copy records "
                      "byte-for-byte")
    base = Path(root) if root else WS
    prereview().refuse_if_a_person(base)
    destinations = [base / rr.RECORDS_REL / rr.filename(rec) for rec in records]
    if len(set(destinations)) != len(destinations):
        raise Refused("bundle-record-collision",
                      "two bundle records resolve to the same plane path")
    existing = next((p for p in destinations if p.exists()), None)
    if existing is not None:
        raise Refused("bundle-record-exists",
                      "%s already exists; no partial copy was written" %
                      existing.name)
    for rec in records:
        res = rr.file_record(rec["item"], rec["verdict"], rec["reviewer"],
                             notes=rec["notes"], root=str(base), env={},
                             now=rec["created"], commit=False)
        if res["record"] != rec:
            raise Refused("bundle-record-transformed",
                          "file_record changed a bundle record")
        out["paths"].append(res["path"])
    out["path"] = out["paths"][0] if out["paths"] else None
    out["filed"] = bool(out["paths"])
    if records:
        out["verdict"] = records[0]["verdict"]
    return out


def check_request(item, records, root=None, brand=None, dictionary=None,
                  fetch=None, figma_rows=None, grammar=True, call=None,
                  write=True, now=None, rr=None, today=None, out_dir=None,
                  by=None, host=None, engine_sha=None, file_records=None):
    """Check one request, optionally write its bundle, then file exact records.

    A clean document still gets a bundle when `out_dir` is named, but its empty
    `records[]` makes `file_findings` a no-op. `file_records=False` is the
    portable-only CLI path; omitted preserves the worker adapter's filing
    behavior. `brand` comes only from the caller; this engine never infers one
    from copy.
    """
    rr = rr or review_request()
    base = Path(root) if root else WS
    state = rr.fold(records)
    if not state["request"]:
        raise Refused("no-request", "no request record on %s" % item)
    if state["status"] != "open":
        raise Refused("already-closed",
                      "%s closed %r — a machine check is read BEFORE the vote"
                      % (item, state["decision"]))
    units = request_units(state["request"], root=base, fetch=fetch,
                          figma_rows=figma_rows)
    dic = (dictionary if dictionary is not None
           else load_dictionary(brand=brand, root=base) if brand
           else load_dictionary(path=os.devnull))
    anchors, report = run_checks(units, dic=dic, today=today, item=item,
                                 grammar=grammar, call=call)
    if anchors:
        prereview().refuse_if_a_person(base)
    bundle = write_bundle(
        out_dir if write else None, report, anchors, state["request"]["asset"],
        truth_from_dictionary(dic, root=base), engine_details(engine_sha),
        run_details(at=now, by=by, host=host), item)
    filed = file_findings(
        bundle, root=base,
        write=write if file_records is None else bool(file_records), rr=rr)
    out = {"item": item, "report": report, "anchors": anchors,
           "bundle": bundle, "records": bundle["records"],
           "clean": bundle["clean"], "filed": filed["filed"],
           "path": filed["path"], "paths": filed["paths"],
           "reviewer": prereview().REVIEWER}
    if bundle["records"]:
        out["verdict"] = bundle["records"][0]["verdict"]
    else:
        out["why"] = ("no findings — NOTHING IS FILED, because the only "
                      "clean-document verdict the grammar offers is `approve` "
                      "and a runner does not get to pass anything")
    return out


def _local_asset(path, root=None):
    base = Path(root or WS).resolve()
    p = Path(path).resolve()
    if base not in p.parents:
        raise Refused("asset-not-in-checkout",
                      "%s cannot be represented as a repo asset" % p)
    return {"warehouse": "repo", "ref": str(p.relative_to(base)),
            "title": p.name}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="RV-36 (text check) — anchored text QC, never a pass")
    ap.add_argument("--root", default=None)
    ap.add_argument("--item", default=None, help="a review request id")
    ap.add_argument("--text-file", default=None,
                    help="check a local file instead of a request")
    ap.add_argument("--html", action="store_true",
                    help="read --text-file as built html")
    ap.add_argument("--brand", default=None,
                    help="whose qc-dictionary.json to read")
    ap.add_argument("--no-grammar", action="store_true",
                    help="deterministic checks only; nothing is metered")
    ap.add_argument("--out", default=None,
                    help="write findings.json and findings.html here")
    ap.add_argument("--by", default=None,
                    help="identity that asked for this run (default: $USER)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the findings; write nothing")
    a = ap.parse_args(argv)
    base = Path(a.root) if a.root else WS
    try:
        dic = (load_dictionary(brand=a.brand, root=base) if a.brand
               else load_dictionary(path=os.devnull))
        if a.text_file:
            raw = Path(a.text_file).read_text(encoding="utf-8",
                                              errors="replace")
            units = (units_from_html(raw) if a.html or
                     a.text_file.lower().endswith((".html", ".htm"))
                     else units_from_text(raw))
            anchors, report = run_checks(units, dic=dic, item=a.text_file,
                                         grammar=not a.no_grammar)
            if a.out and not a.dry_run:
                if not a.item:
                    ap.error("--out with --text-file needs --item RQ-…")
                if anchors:
                    prereview().refuse_if_a_person(base)
                write_bundle(a.out, report, anchors,
                             _local_asset(a.text_file, root=base),
                             truth_from_dictionary(dic, root=base),
                             engine_details(), run_details(by=a.by), a.item)
            # UQ-1 (portable bundle) preserves this byte shape: --dry-run and
            # the legacy local invocation still print report + anchors, never
            # the envelope.
            print(json.dumps({"report": report, "anchors": anchors}, indent=2,
                             ensure_ascii=False))
            return 0
        if not a.item:
            ap.error("give --item or --text-file")
        if not a.dry_run and not a.out:
            ap.error("--item writes a portable bundle, so give --out <dir>")
        rr = review_request()
        out = check_request(a.item, rr.read_records(root=str(base), item=a.item),
                            root=base, brand=a.brand, dictionary=dic,
                            grammar=not a.no_grammar, write=not a.dry_run,
                            out_dir=a.out, by=a.by, rr=rr, file_records=False)
    except Refused as e:
        print("REFUSED: %s" % e, file=sys.stderr)
        return 2
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":           # pragma: no cover — a human at a terminal
    raise SystemExit(main())
