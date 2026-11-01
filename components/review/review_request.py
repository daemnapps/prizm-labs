#!/usr/bin/env python3
"""File a review request in ONE call, and read a request's state by FOLDING it.

Card RV-2 (review request module). The grammar is RV-1 (review kind
manifest)'s, frozen verbatim in `team/plans/dev-dayu.md` batch 54; this file
mirrors the parts it must validate and NEVER edits the manifest.

TWO DOORS, ONE RECORD — the card's claim, and the reason this module is
shaped the way it is. Any Claude Code session standing in a clone writes the
record file into `platform/data/records/review/` and commits it, handling no
secret at all. The mini's session, which HAS a review key in its environment,
POSTs `/api/review` instead so the record is readable the moment the link is
handed over (`review_post`'s reason, OR-2 (mint round)). A record that came
through one door must be indistinguishable from a record that came through
the other, so the composition, the serialization and the filename are each
written ONCE here — `record()`, `render()`, `filename()` — and both routes
call them. The declared test proves the equality with the API path stubbed at
its transport seam, and grounds its stub by re-composing a REAL API-written
record off the plane byte for byte.

WHERE THE TWO DOORS GENUINELY DIFFER, stated rather than papered over: the
server stamps `created` from its own clock, so the API route's bytes are the
predicted bytes for the instant this module names. Byte-equality is a claim
about the same input at the same instant — the composition, never the clock.

STATUS IS FOLDED, ALWAYS, AND NEVER STORED (the card's never, and the plane's
rule 1). No record carries a status field. `fold()` derives it from the
append-only records: no close = open, the latest close wins, the latest
verdict per reviewer. It lives here ONCE — RV-3 (on_accept adapter),
RV-6 (reference panels) and RV-10 (PM review integration) IMPORT it rather
than re-deriving it, because two surfaces disagreeing about one request's
state is the failure the records plane exists to prevent.

`seen` IS AN EVENT, NEVER A VERDICT (card RV-16a; the team's ruling of 2026-09-09,
the one the frozen manifest has taken). A reviewer OPENED the request — no
judgment, no close, and no satisfying the close rule's "one reviewer". The
fold answers it as `seen_by[]`, one entry per reviewer however many times they
looked, and nothing else in the fold moves on it. The three verdict words are
UNCHANGED; a fourth one would be RV-15 (choice verdict) and is not ruled.

TWO OPTIONAL FIELDS, DECLARED AND CHECKED (card RV-23; the team's rulings A and B
of 2026-09-09, the second amendment this freeze has taken). A verdict MAY carry
`anchors: [{quote, prefix, suffix, comment, row?}]` — the reviewer's words tied
to the words that provoked them, a text-quote selector and NEVER a line number,
because a repo path carries no version and a line number rots the moment
somebody edits above it. A repo `asset` pointer MAY carry `at` — the commit half
of a REF PAIR, for the same reason. BOTH ARE OPTIONAL AND STAY OPTIONAL: a
record carrying neither is byte-identical to what this module filed before they
existed, which is the card's acceptance criterion and not a side effect. The
shapes are MIRRORED here for validation only — the manifest owns them — and
checked at the write door, so a malformed anchor is refused BY NAME rather than
stored. THE VERDICT IS STILL ONE PER REQUEST: this is a field, not a per-row
verdict.

A BATCH IS A LANE, NOT A NEW WORD (card RV-14). Six ads sent as one act are
six requests sharing one lane minted for the batch — `file_request(batch=[…])`,
one request per asset, one commit. The manifest needs no change to allow it:
the verdict vocabulary is closed at three words on purpose and the LANE
vocabulary is explicitly open ("a lane outside this list is legal and groups a
queue, it never refuses a request"). So there is no batch field, no tally and
no score anywhere below — pick-N is approve the picks and reject the rest, and
the group is read back through `list_open(lane=…)`, which already existed.

NO SECRET IS EVER READ FROM A FILE. The review key comes from the process
environment and from nowhere else — not `~/.workflow-worker.env`, not a
dotfile, not an argument default. It is never logged, never returned, never
written into a record. `mytasks.py` reads the file as a convenience; this
module deliberately does not, per the card. No MCP dependency; stdlib only.

Standalone use (prints the record it WOULD file; writes nothing, posts
nothing):

    python3 components/review/review_request.py --dry-run \\
        --title "The RV-2 (review request module) module" --type md \\
        --warehouse repo --ref components/review/review_request.py \\
        --lane dev-qc --reviewer dayu --by dayu
"""

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from importlib import util as _importlib_util
from pathlib import Path

VERSION = "review-request/1"

# RV-1 (review kind manifest)'s kind. Named here, never edited here.
KIND = "review"

# The review app's own host — the POST target. `dashboard.company.com`
# is the custom domain a PERSON is given; the two are separate facts and the
# link a person opens is RV-10 (PM review integration)'s to mint, not this
# module's, so nothing here fabricates one.
REVIEW_API = "https://review-app-ecomm-ops.vercel.app"

# The ONE environment name that carries the review key. Absent -> git route.
KEY_ENV = "REVIEWER_KEY_TEAM"

# ---- the frozen grammar (batch 54), mirrored for validation only -----------
# A field beyond this block is a RULING, never a maker's judgment — the never
# on RV-1 (review kind manifest), which owns the manifest file. When that file
# is present the declared test cross-checks these tuples against it.
#
# `seen` IS THE ONE RULING THE FREEZE HAS TAKEN (the team, 2026-09-09, card RV-16a):
# a reviewer OPENED the request. It carries no judgment, closes nothing, and
# never satisfies the close rule's "one reviewer" — see `fold()`, which is where
# the whole of its meaning lives. VERDICTS ARE UNCHANGED by it: it is an event,
# not a verdict word.
#
# `url` IS THE OTHER RULING (the team, 2026-09-10, card RV-34 (url and viewport)):
# a thing that lives somewhere the platform does not own — a Figma file, a
# Netlify preview, any link — whose `ref` IS the url, tracking params stripped.
# It exists so `blob` can keep its honest meaning: a blob is a capture WE MADE
# AND HOLD, and until this word existed a Figma link could only be filed as one,
# which is a lie about provenance that nothing catches. LAST IN THE TUPLE ON
# PURPOSE: the manifest's `asset` note declares the words in this order and the
# viewer's lifted copy is compared against that note character for character.
#
# `page` IS THE RULING AFTER IT (the team, 2026-09-10, card RV-47 (type page)): a
# DEPLOYED WEB PAGE, FRAMED AT A DECLARED WIDTH, beside `link` — a thing we
# deliberately do NOT embed, a Figma frame whose comments belong in Figma. ONE
# VALUE AND NO NEW WAREHOUSE WORD: both species are warehouse `url`, and the
# distinction is not where the thing lives but whether the panel EMBEDS it,
# which is why it is a `type` value. THE SPECIES IS DECLARED, NEVER INFERRED —
# nothing here, or anywhere else, reads a species off a hostname. LAST IN THE
# TUPLE for the reason `url` is last in its own: the declared test compares
# this tuple with the manifest's list ELEMENT FOR ELEMENT.
EVENTS = ("request", "verdict", "close", "seen")
TYPES = ("text", "md", "image", "video", "doc", "link", "page")
WAREHOUSES = ("repo", "drive", "blob", "supabase", "url")
VERDICTS = ("approve", "reject", "fix")
DECISIONS = ("accepted", "rejected", "parked")

# THE VIEWPORT (card RV-34 (url and viewport), the team's ruling of 2026-09-10) —
# at what width the thing under review was meant to be read. OPTIONAL on the
# pointer, and ABSENT MEANS UNSTATED, never `desktop`: nothing in this module
# defaults it, writes it as a stored null, or reads its absence as a value.
# Mirrored for validation only — the manifest owns the vocabulary.
VIEWPORTS = ("mobile", "desktop")

# `RQ-<id>`, one item per request. `--` is the record filename's field
# separator, so an id may never contain it — the pattern allows single
# hyphens and `file_record` refuses a doubled one alongside this match.
ITEM_RE = re.compile(r"^RQ-[A-Za-z0-9][A-Za-z0-9._-]{0,60}$")
PERSON_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,30}$")
LANE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
# THE BATCH LANE (card RV-14): `<lane>/b-<yyyymmddHHMMSS>`, the shared lane a
# batch is filed on. LEGAL WITHOUT A MANIFEST CHANGE, and that is the whole
# reason the card needs none: the kind manifest enumerates three pilot lanes
# and says of them "the vocabulary is OPEN … a lane outside this list is legal
# and groups a queue, it never refuses a request". It declares no lane PATTERN,
# so the shape is this module's to accept; it is kept to the minted form so the
# only nested lane in existence is one `mint_batch_lane` wrote, and never an
# arbitrary path a caller invented.
BATCH_LANE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}/b-\d{14}$")
DUE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

RECORDS_REL = "platform/data/records/review"
MANIFEST_REL = "platform/data/kinds/review.json"

# THE MEDIA INVENTORY's row shape, as the manifest declares it (card RV-2b):
# `{name, type, ref, warehouse, bytes?, role?}`, the two marked `?` optional.
# Mirrored for validation only — the manifest owns it, this file never edits
# it, and the order here is the order a row is written in.
MEDIA_ROW_FIELDS = ("name", "type", "ref", "warehouse", "bytes", "role")
# What a row cannot be SERVED without: `name` is the exact string the media
# route matches on, `ref` is the pointer it resolves and `warehouse` says which
# door that pointer opens. A row missing any of them names nothing servable, so
# it is refused BY NAME rather than filed (RV-66 (writer enforces the frozen
# grammar): the manifest's row is `{name, type, ref, warehouse, bytes?, role?}`,
# and before that card this line required only the first two).
MEDIA_ROW_REQUIRED = ("name", "ref", "warehouse")
# `type` IS REQUIRED ONLY WHERE THE MEDIA ROUTE SERVES BYTES (the team 2026-09-27,
# "Release the 7", RV-66 (writer enforces the frozen grammar), option a): the
# route serves a row with the content type the record declares, never sniffed,
# so a served row without one is refused. A `url` row is a LINK and is never
# byte-served — the manifest's own `media` note: "a request whose asset needs
# no byte-serving (... a link) carries no `media`" — and RV-39 (link choice)'s
# form files a `page` request's reference row without a `type` on purpose. The
# exemption is exactly `url`; every other warehouse word requires `type`, and
# this is NOT a copy of the route's table of streamable warehouses, which would
# drift the first time the route learns one.
MEDIA_TYPE_OPTIONAL_WAREHOUSES = ("url",)

# THE ONE OPEN VOCABULARY in the manifest's `verdict_fields`: `lane` declares
# three `values`, and its note says "the vocabulary is OPEN ... a lane outside
# this list is legal and groups a queue, it never refuses a request". So
# `validate` never refuses a lane for its word — `request_verdict`'s lane
# pattern is the lane's only check, as it always was.
OPEN_VOCABULARIES = ("lane",)

# THE ANCHOR SHAPE — `anchors: [{quote, prefix, suffix, comment, row?}]`, as the
# manifest declares it (card RV-23, the team's ruling A of 2026-09-09, the second
# amendment this freeze has taken). Mirrored for validation only: the manifest
# owns the shape, this file never edits it, and the order here is the order the
# manifest writes it in. The declared test reads the shape OFF THE MANIFEST and
# compares it with these tuples, so a drift fails there rather than in a record.
ANCHOR_FIELDS = ("quote", "prefix", "suffix", "comment", "row")
# `row` is the ONE optional key: it names WHICH TEXT the anchor lives in, and is
# omitted when the request has a single text.
ANCHOR_OPTIONAL = ("row",)
# THE NEIGHBOURHOOD. Present on every anchor — the whole reason an anchor is a
# quote and not a line number is that it re-finds itself, and it re-finds itself
# by its neighbourhood first — but ALLOWED TO BE EMPTY, because a quote at the
# very start or the very end of a text has no words on that side and refusing
# one would refuse the first sentence of every document.
ANCHOR_NEIGHBOURHOOD = ("prefix", "suffix")

# THE REF PAIR's second half (card RV-23, the team's ruling B): a repo `asset`
# pointer MAY name the commit it was read at. A COMMIT, never a branch and never
# a tag — a branch name moves, and a pointer that moves is the rot the pair
# exists to stop.
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")

# The verdict cap is ai-dev's number (record-validate.mjs MAX_VERDICT_BYTES),
# mirrored ONCE in the repo by WM-25 (verdict cap one source) and LOADED from
# there — never re-typed. Loaded by path rather than by import so this file
# does not put the worker's whole directory on `sys.path`.
def _load_cap():
    here = Path(__file__).resolve()
    for parent in here.parents:
        caps = parent / "platform/workers/mini-worker/plane_caps.py"
        if caps.is_file():
            spec = _importlib_util.spec_from_file_location("plane_caps", caps)
            mod = _importlib_util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return int(mod.MAX_VERDICT_BYTES)
    raise ImportError(
        "plane_caps.py not found above %s — the verdict cap has ONE home "
        "(WM-25 (verdict cap one source)) and this module will not carry a "
        "second copy of the number." % here)


MAX_VERDICT_BYTES = _load_cap()


class Refused(ValueError):
    """The request cannot be filed and NOTHING has been written or posted.

    Every raise names the field a person can act on. Refusing before the write
    is the whole point: a malformed record refused by the API after a git
    commit would leave the two doors disagreeing."""


class BatchPartial(Refused):
    """A batch stopped PART-WAY on the write — some requests landed, some did
    not (RV-66 (writer enforces the frozen grammar), finding rev-6).

    Every refusal the batch can see coming still happens before the first
    write; this is the one it cannot — the API answering 503 to the third POST
    of four. The plane is append-only, so what landed stands, and the caller is
    handed exactly that: `receipts`, the per-request dicts `file_record`
    returned for the requests that DID land, in batch order (possibly empty),
    and `unfiled`, the item ids that did NOT, in batch order."""

    def __init__(self, message, receipts, unfiled):
        Refused.__init__(self, message)
        self.receipts = list(receipts)
        self.unfiled = list(unfiled)


# THE KIND MANIFEST'S `verdict_fields`, READ — never copied — so the grammar
# `validate` enforces is the frozen one and nothing else (RV-66 (writer enforces
# the frozen grammar)). Found by walking up from THIS FILE, the `_load_cap`
# pattern; parsed once per process; opened read-only. A module with no manifest
# above it refuses rather than filing unchecked.
_VERDICT_FIELDS = None


def _verdict_fields():
    global _VERDICT_FIELDS
    if _VERDICT_FIELDS is not None:
        return _VERDICT_FIELDS
    here = Path(__file__).resolve()
    rel = MANIFEST_REL
    for parent in here.parents:
        manifest = parent / rel
        if manifest.is_file():
            _VERDICT_FIELDS = json.loads(
                manifest.read_text(encoding="utf-8"))["verdict_fields"]
            return _VERDICT_FIELDS
    raise Refused(
        "%s not found above %s — the frozen grammar has ONE home and this "
        "writer will not file a record it cannot check against it. Nothing "
        "was filed." % (rel, here))


# ---- time, identity, home --------------------------------------------------
def now_iso():
    """The plane's `created` shape: 2026-09-08T05:13:12Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp(created):
    """`created` -> the record filename's stamp: 20260908T051312Z."""
    return str(created).replace("-", "").replace(":", "")


def repo_root(start=None):
    """The workspace root, found from THIS FILE, never from the cwd — the same
    move `mytasks.py` makes, and for the same reason: the module knows where it
    lives and everything it reads is beside it."""
    here = Path(start or __file__).resolve()
    for d in [here] + list(here.parents):
        if (d / "CLAUDE.md").is_file() and (d / "platform" / "data").is_dir():
            return d
    return None


def has_key(env=None):
    """Is a review key in the environment? The ROUTE decision, and nothing
    else — the key itself never leaves `_key()`."""
    return _key(env) is not None


def _key(env=None):
    """The review key, from the process environment ONLY (the card's never: no
    secret read from a file). Never logged, never returned to a caller, never
    written into a record."""
    return (dict(os.environ if env is None else env)
            .get(KEY_ENV, "") or "").strip() or None


# ---- the one composition, the one serialization, the one name --------------
def record(item, verdict, reviewer, notes="", created=None):
    """The record envelope, exactly as the plane holds it.

    KEY ORDER IS PART OF THE BYTES. `schema, kind, reviewer, item, verdict,
    notes, created, via` is what `/api/review` writes (read off a real record
    on the plane, not assumed), and a dict literal preserves it."""
    return {"schema": 1, "kind": KIND, "reviewer": reviewer, "item": item,
            "verdict": verdict, "notes": notes,
            "created": created or now_iso(), "via": VERSION}


def render(rec):
    """The record's BYTES. `JSON.stringify(rec, null, 2)` on the API side:
    two-space indent, non-ASCII kept as itself, NO trailing newline."""
    return json.dumps(rec, indent=2, ensure_ascii=False).encode("utf-8")


def filename(rec):
    """`<stamp>--<reviewer>--<item>.json`, the plane's name for a record."""
    return "%s--%s--%s.json" % (stamp(rec["created"]), rec["reviewer"],
                                rec["item"])


def _stamp14(created=None):
    """`yyyymmddHHMMSS` — the time part an id is minted from. ONE copy, so an
    item id and the batch lane minted in the same call cannot disagree about
    what instant they name."""
    return stamp(created or now_iso())[:15].replace("T", "")[:14]


def mint_item(title, created=None):
    """`RQ-<yyyymmddHHMMSS>-<slug>` — time-based by the same ruling that
    shapes a task id (`TSK-<yyyymmddHHMMSS>-<slug>`, pm.html `taskId()`):
    sequential ids need a coordinator, timestamps do not, and nothing is ever
    renumbered. Round two is a NEW id on the same asset pointer, so an id is
    minted per request and never reused."""
    slug = re.sub(r"^-+|-+$", "",
                  re.sub(r"[^a-z0-9]+", "-", str(title or "").lower())[:40])
    return "RQ-%s-%s" % (_stamp14(created), slug or "request")


def mint_batch_lane(lane, created=None):
    """`<lane>/b-<yyyymmddHHMMSS>` — THE SHARED LANE A BATCH IS FILED ON.

    A lane is a LABEL, never a gate, and its vocabulary is OPEN by the
    manifest's own words — so grouping six ads into one act needs no new field
    and no new verdict word, only a lane the six of them share. The batch id is
    time-based for the same reason an item id is (`mint_item`): sequential ids
    need a coordinator, timestamps do not.

    THE COLLISION THIS DOES NOT PREVENT, stated rather than papered over: two
    batches filed on the SAME base lane in the SAME second mint the same lane
    and read back as one group. That is a grouping label, not an id — no record
    is lost, nothing is overwritten, and the item ids stay distinct."""
    lane = str(lane or "").strip().lower()
    if not LANE_RE.match(lane):
        raise Refused("lane %r is not a lane label ([a-z0-9-]) to mint a batch "
                      "lane from. Nothing was filed." % lane[:40])
    return "%s/b-%s" % (lane, _stamp14(created))


# ---- validation ------------------------------------------------------------
# FOUR VALIDATORS ARE PUBLIC (card RV-67): `people`, `asset`, `anchors` and
# `capped` are what qc-checks' filing calls on this module, so renaming one is
# a contract change a test notices rather than a silent break. Each keeps its
# old private name as a pure alias; this module's own calls still use those.
def people(reviewers, field):
    if isinstance(reviewers, str):
        reviewers = [reviewers]
    out = [str(r).strip().lower() for r in (reviewers or []) if str(r).strip()]
    if not out:
        raise Refused("%s is empty — a request names who is asked, so the "
                      "queue can answer 'what is waiting on me'. Nothing was "
                      "filed." % field)
    bad = [r for r in out if not PERSON_RE.match(r)]
    if bad:
        raise Refused("%s %r is not a person id ([a-z0-9-]). Nothing was "
                      "filed." % (field, bad[0][:40]))
    return out


_people = people   # RV-67 (review public validators): a pure alias


def asset(asset):
    """{warehouse, ref, title, at?} — the pointer, checked for SHAPE only.

    Deliberately NOT checked: whether a `repo` ref exists on disk. A request
    may legitimately be filed from a checkout that does not carry the file, and
    refusing one would be a rule no card ruled. RV-1 (review kind manifest)'s
    seed test is where resolvability is proven."""
    if not isinstance(asset, dict):
        raise Refused("asset must be {warehouse, ref, title}. Nothing was filed.")
    wh = str(asset.get("warehouse") or "").strip().lower()
    if wh not in WAREHOUSES:
        raise Refused("warehouse %r is not one the grammar declares (%s). "
                      "Nothing was filed."
                      % (str(asset.get("warehouse"))[:40], "|".join(WAREHOUSES)))
    ref = str(asset.get("ref") or "").strip()
    if not ref:
        raise Refused("asset.ref is empty — the pointer IS the thing under "
                      "review. Nothing was filed.")
    title = str(asset.get("title") or "").strip()
    if not title:
        raise Refused("asset.title is empty — a reviewer must know what they "
                      "are being asked to judge without opening the id. "
                      "Nothing was filed.")
    out = {"warehouse": wh, "ref": ref, "title": title[:200]}
    # `at` LAST, and only when given, so a pointer without one keeps the exact
    # bytes it had before the field existed (the card's acceptance criterion:
    # the OLD behaviour, not the new field). An optional given as None is NOT
    # given — dropped, never defaulted, never written as a stored null, the
    # same rule `_media` states for its own optionals.
    if asset.get("at") is not None:
        out["at"] = _at(asset["at"], wh)
    # `viewport` AFTER `at`, and on the same terms (card RV-34 (url and
    # viewport)): a pointer that names neither keeps the exact bytes it had
    # before either key existed. ABSENT IS UNSTATED — an optional given as None
    # is NOT given, so it is dropped rather than defaulted to `desktop`.
    if asset.get("viewport") is not None:
        out["viewport"] = _viewport(asset["viewport"])
    return out


_asset = asset   # RV-67 (review public validators): a pure alias


def _viewport(viewport):
    """AT WHAT WIDTH THE THING WAS MEANT TO BE READ (card RV-34, the team's ruling
    of 2026-09-10). OPTIONAL, NEVER REQUIRED, and absent means UNSTATED.

    IT IS NOT NARROWED TO `url`, and that is deliberate: the ruling put it on
    THE POINTER, not on one warehouse's pointer, and a repo path that renders
    as a page has a width the same way a Netlify preview does. `at` is narrow
    because a Drive id and a link carry their own version or none — a reason
    about VERSIONS that says nothing about WIDTHS.

    A THIRD WORD IS A RULING. Two words were ruled, so a value outside them is
    refused BY NAME rather than stored: an unruled `tablet` sitting quietly on
    the plane is exactly the drift the freeze exists to stop."""
    value = str(viewport).strip().lower()
    if value not in VIEWPORTS:
        raise Refused("asset.viewport %r is not one the grammar declares (%s) "
                      "— two words were ruled and a third is a RULING, never a "
                      "filer's move. Omit it to leave the width UNSTATED, which "
                      "is what absent means. Nothing was filed."
                      % (str(viewport)[:40], "|".join(VIEWPORTS)))
    return value


def _at(at, warehouse):
    """THE REF PAIR (card RV-23, the team's ruling B): a path AND the commit it was
    read at. OPTIONAL, NEVER REQUIRED.

    The reason is the one that makes an anchor a quote: a repo path carries NO
    VERSION, so `ref` alone names whatever that path holds today, and a
    reviewer's words can end up attached to a file nobody can reconstruct.

    A COMMIT, NEVER A BRANCH OR A TAG. `main` would satisfy "name a version"
    while naming a moving target, which is the exact rot the pair exists to
    stop — so the shape is checked and a name that cannot pin anything is
    refused BY NAME rather than stored.

    ONLY A `repo` POINTER HAS ONE. A Drive file id, a blob url and a supabase
    pointer carry their own version or none at all, so an `at` beside them
    names nothing; the manifest says the REPO pointer gains the field and this
    reads it no wider than that.

    RV-34 (url and viewport) ADDED A FIFTH WAREHOUSE AND CHANGED NOTHING HERE.
    A `url` is the strongest case for the rule, not an exception to it: version
    binding for a link is the CAPTURE (RV-35 (page capture)), never a commit —
    a deploy preview redeploys on every push and a Figma file changes under
    you, so a commit beside a link names a version of something else. Anyone
    reaching for `at` on a `url` has mistaken a link for a version, and the
    refusal below names their warehouse back to them."""
    if warehouse != "repo":
        raise Refused("asset.at is the commit half of a REF PAIR and only a "
                      "`repo` pointer has one — this asset names warehouse %r, "
                      "which carries its own version or none. Nothing was "
                      "filed." % str(warehouse)[:40])
    at = str(at).strip()
    if not COMMIT_RE.match(at):
        raise Refused("asset.at %r is not a commit (hex, 7-40) — a ref pair is "
                      "a path AND a commit, and a branch or a tag MOVES, which "
                      "is the rot the pair exists to stop. Nothing was filed."
                      % at[:60])
    return at


def anchors(anchors):
    """ANCHORED COMMENTS, checked for SHAPE and never rewritten (card RV-23,
    the team's ruling A) — `[{quote, prefix, suffix, comment, row?}]`.

    An anchor is a TEXT-QUOTE SELECTOR, NEVER A LINE NUMBER: a repo path
    carries no version and a line number rots the moment somebody edits above
    it, while a quote with its neighbourhood re-finds itself — and when it
    genuinely cannot, the panel says "not found in this version" rather than
    silently pointing at the wrong line. Resolution order is the exact
    neighbourhood first, then the quote alone.

    NOTHING HERE IS STRIPPED OR NORMALIZED, and that is not laziness. The
    selector resolves by MATCHING, so the whitespace inside a `quote`, a
    `prefix` or a `suffix` is part of the selector — a writer that trimmed them
    would hand back an anchor that no longer resolves against the text it was
    taken from. So this refuses or passes through; it never edits. (`_media`
    normalizes because a media row is a pointer and its whitespace means
    nothing; an anchor's means everything.)

    A KEY THIS SHAPE DOES NOT NAME IS REFUSED, which is where `_media` rides an
    unknown key through instead — the difference is deliberate. A media row's
    shape is the manifest's to widen and the route serves what it names; an
    anchor's shape IS the ruling, and a sixth key on one is a ruling nobody has
    made. The refusal is where that surfaces, and it costs one line to relax.

    NO NEW CAP AND NO NEW NUMBER: how much an anchors list may weigh is already
    answered by `capped` against the plane's own MAX_VERDICT_BYTES, which
    every record passes through."""
    if not isinstance(anchors, (list, tuple)):
        raise Refused("anchors must be a LIST of anchors, one per commented "
                      "passage — %s. Nothing was filed." % _type_name(anchors))
    for i, a in enumerate(anchors):
        where = "anchors[%d]" % i
        if not isinstance(a, dict):
            raise Refused("%s must be an anchor {quote, prefix, suffix, "
                          "comment, row?} — %s. Nothing was filed."
                          % (where, _type_name(a)))
        for field in ANCHOR_FIELDS:
            if field in ANCHOR_OPTIONAL and a.get(field) is None:
                continue                     # an optional given as None is not
                                             # given
            if field not in a:
                raise Refused(
                    "%s.%s is missing — an anchor is a text-quote selector "
                    "{quote, prefix, suffix, comment, row?} and only `row` is "
                    "optional. Nothing was filed." % (where, field))
            value = a[field]
            if not isinstance(value, str):
                raise Refused("%s.%s must be text — %s. Nothing was filed."
                              % (where, field, _type_name(value)))
            if field not in ANCHOR_NEIGHBOURHOOD and not value.strip():
                raise Refused(
                    "%s.%s is empty — an anchor with no %s %s. Nothing was "
                    "filed." % (where, field, field, {
                        "quote": "selects nothing and can never re-find itself",
                        "comment": "says nothing about the words it selected",
                        "row": "names no text; leave it out on a single-text "
                               "request rather than sending an empty one",
                    }[field]))
        for field in a:
            if field not in ANCHOR_FIELDS:
                raise Refused(
                    "%s.%s is not part of the anchor shape the manifest "
                    "declares (%s) — a sixth key on an anchor is a RULING, "
                    "never a maker's judgment. Nothing was filed."
                    % (where, field, ", ".join(ANCHOR_FIELDS)))
    return anchors


_anchors = anchors   # RV-67 (review public validators): a pure alias


def _media(rows):
    """THE MEDIA INVENTORY — one row per file the platform must serve.

    THE INVENTORY IS THE ALLOWLIST, in the manifest's own words: "a file no row
    names is refused, never fetched". That is the whole security model, and it
    is why this writer builds no second allowlist of its own and opens no file:
    every value in a row is a pointer the caller already holds (media is never
    bytes — workspace rule 3).

    VALIDATED NO STRICTER THAN THE MANIFEST DECLARES, which is RV-2b's kill:
    a validated row refused that the platform would in fact serve means the
    shape is being read stricter than `platform/data/kinds/review.json` writes
    it. So `name`, `ref` and `warehouse` are required — a row missing any of
    them names nothing servable — and `type` is required on every row the
    media route SERVES, which is every warehouse but `url` (RV-66 (writer
    enforces the frozen grammar), ruled 2026-09-27: see
    `MEDIA_TYPE_OPTIONAL_WAREHOUSES`). `type` on a `url` row, `bytes` and
    `role` are checked only when given (and a `None` is NOT given: it is
    dropped, never defaulted and never written as a null), and a key this
    grammar does not name RIDES THROUGH rather than being refused or silently
    dropped: the row shape is the manifest's to widen, and refusing a field it
    may already allow is exactly the failure the kill names.
    `warehouse` is checked against the same words `asset` uses — FIVE since
    RV-34 (url and viewport) — because the manifest says it is the same word
    and a sixth warehouse is a ruling, not a row a filer may invent. It is read
    FIRST, before the fields are walked in their written order, because it
    decides whether that row's `type` is required. A `url` row names something
    the platform does not serve byte by byte, which the manifest's own `media`
    note already covers: an inventory is for the files the platform must
    serve, and a link needs none.
    """
    if not isinstance(rows, (list, tuple)):
        raise Refused("media must be a LIST of rows, one per file the platform "
                      "must serve — %s. Nothing was filed."
                      % _type_name(rows))
    out = []
    for i, row in enumerate(rows):
        where = "media[%d]" % i
        if not isinstance(row, dict):
            raise Refused("%s must be a row {name, type, ref, warehouse, "
                          "bytes?, role?} — %s. Nothing was filed."
                          % (where, _type_name(row)))
        warehouse = str(row.get("warehouse") or "").strip().lower()
        if not warehouse:
            raise Refused(
                "%s.warehouse is empty — a media row IS the allowlist entry, "
                "and a row that does not say where it lives (%s) names nothing "
                "the platform can serve. Nothing was filed."
                % (where, "|".join(WAREHOUSES)))
        if warehouse not in WAREHOUSES:
            raise Refused(
                "%s.warehouse %r is not one the grammar declares (%s) "
                "— it is the same word `asset` uses. Nothing was filed."
                % (where, str(row.get("warehouse"))[:40],
                   "|".join(WAREHOUSES)))
        type_required = warehouse not in MEDIA_TYPE_OPTIONAL_WAREHOUSES
        clean = {}
        for field in MEDIA_ROW_FIELDS:
            required = field in MEDIA_ROW_REQUIRED or (
                field == "type" and type_required)
            if field not in row and not required:
                continue
            value = row.get(field)
            if value is None and not required:
                continue                     # an optional given as None is not
                                             # given — never a default, never a
                                             # refusal, and never a stored null
            if field == "warehouse":
                value = warehouse
            elif field == "type" and required:
                value = str(value or "").strip()
                if not value:
                    raise Refused(
                        "%s.type is empty — a %s row is SERVED by the media "
                        "route, which sends the content type the record "
                        "declares and never sniffs one; only a `url` row (a "
                        "link, never byte-served) may leave it out. Nothing "
                        "was filed." % (where, warehouse))
            elif required:
                value = str(value or "").strip()
                if not value:
                    raise Refused(
                        "%s.%s is empty — a media row IS the allowlist entry, "
                        "and a row without a %s names nothing the platform can "
                        "serve. Nothing was filed." % (where, field, field))
            elif field == "bytes":
                if isinstance(value, bool) or not isinstance(value, int) \
                        or value < 0:
                    raise Refused("%s.bytes %r is not a size in bytes. Nothing "
                                  "was filed." % (where, str(value)[:40]))
            else:                            # type, role — words, never sniffed
                value = str(value or "").strip()
                if not value:
                    raise Refused("%s.%s is present but empty — leave it out or "
                                  "say what it is. Nothing was filed."
                                  % (where, field))
            clean[field] = value
        for field in row:                    # a key the grammar may widen to
            if field not in MEDIA_ROW_FIELDS:
                clean[field] = row[field]
        out.append(clean)
    return out


def _type_name(value):
    """The word a refusal uses for what it was handed. A refusal names the
    field AND what arrived there, so a caller can act on it without a
    traceback."""
    return "got %s" % type(value).__name__


def request_verdict(asset, type, reviewers, lane, due=None, on_accept=None,
                    media=None):
    """The `event: request` body, validated against the frozen grammar.

    NOTHING BEYOND THE FROZEN BLOCK IS PUT IN IT — event, type, asset,
    reviewers, lane, and the optionals due / on_accept / media. A field beyond
    that is a ruling, never a maker's judgment. So the REQUESTER is not a
    verdict field: the record envelope's `reviewer` is who filed it, exactly as
    it is for a verdict or a close, and the requester's own words ride in the
    envelope's `notes`.

    `media` IS IN THAT FROZEN BLOCK and always has been — the manifest declares
    the field, its row shape and the allowlist rule, and points the media route
    at `verdict.media`. RV-2b added the WRITER, not the field: a request filed
    without `media` carries no such key and is byte-identical to what this
    module wrote before it (the card's one invariant). `media=[]` is an
    inventory that names nothing, and is filed as the caller wrote it.

    `type` is the grammar's own field name, kept 1:1 so the skill's documented
    call and the record's field read the same word."""
    if type not in TYPES:
        raise Refused("type %r is not one the grammar declares (%s). Nothing "
                      "was filed." % (str(type)[:40], "|".join(TYPES)))
    lane = str(lane or "").strip().lower()
    if not (LANE_RE.match(lane) or BATCH_LANE_RE.match(lane)):
        raise Refused("lane %r is not a lane label ([a-z0-9-]) or a minted "
                      "batch lane (`<lane>/b-<yyyymmddHHMMSS>`); it is a LABEL, "
                      "never a gate. Nothing was filed." % lane[:60])
    v = {"event": "request", "type": type, "asset": _asset(asset),
         "reviewers": _people(reviewers, "reviewers"), "lane": lane}
    if due is not None:
        if not DUE_RE.match(str(due)):
            raise Refused("due %r is not YYYY-MM-DD. Nothing was filed."
                          % str(due)[:40])
        v["due"] = str(due)
    if on_accept is not None:
        if not isinstance(on_accept, dict) or not on_accept.get("action"):
            raise Refused("on_accept must be an object naming an `action` — "
                          "RV-3 (on_accept adapter) files exactly what the "
                          "request declared and never more. Nothing was filed.")
        v["on_accept"] = on_accept
    if media is not None:
        # LAST, after the two older optionals, so a request with no `media`
        # keeps the exact bytes it had before this parameter existed. It also
        # leaves the prefix `reviewRequestBody()` in pm.html composes — event,
        # type, asset, reviewers, lane, due, on_accept — key-for-key where it
        # is, so the panel's writer stays field-comparable with this one; that
        # composer writes no inventory today, and appending is where it would.
        v["media"] = _media(media)
    return v


def capped(verdict):
    body = json.dumps(verdict, ensure_ascii=False).encode("utf-8")
    if len(body) > MAX_VERDICT_BYTES:
        raise Refused(
            "the verdict is %d bytes and the plane's cap is %d "
            "(WM-25 (verdict cap one source), ai-dev's MAX_VERDICT_BYTES): the "
            "API would refuse it 400, so the git door must refuse it too or the "
            "two doors stop agreeing. Shorten the note or point at the words "
            "instead of carrying them. Nothing was filed." %
            (len(body), MAX_VERDICT_BYTES))
    return verdict


_capped = capped   # RV-67 (review public validators): a pure alias


def _blank(value):
    """A required field that is absent, None, "", [] or {} is not carried."""
    return value is None or (isinstance(value, (str, list, tuple, dict))
                             and len(value) == 0)


def _grammar(verdict, fields):
    """The manifest's own two rules over `verdict_fields`, enforced as written
    (RV-66 (writer enforces the frozen grammar), finding rev-1): every entry's
    `required_when: "<key>=<value>"` and every entry's `values`, except the
    vocabularies the manifest itself declares OPEN."""
    event = verdict.get("event")
    for entry in fields:
        key = entry.get("key")
        when = entry.get("required_when")
        if when:
            on, _, want = str(when).partition("=")
            if verdict.get(on) == want and _blank(verdict.get(key)):
                words = entry.get("values")
                raise Refused(
                    "a `%s` record must carry `%s`%s — the frozen manifest "
                    "declares it `required_when: %s`. Nothing was filed."
                    % (event, key,
                       " (%s)" % "|".join(words) if words else "", when))
        words = entry.get("values")
        if words and key in verdict and key not in OPEN_VOCABULARIES \
                and verdict[key] not in words:
            raise Refused(
                "%s %r is not one the grammar declares (%s). Nothing was "
                "filed." % (key, str(verdict[key])[:40], "|".join(words)))


def validate(verdict, fields=None):
    """THE FROZEN GRAMMAR, AT THE DOOR — raises `Refused`, returns None.

    Every record either door files passes through here first (`file_record`
    calls it before it composes anything, and a batch calls it on every body
    before the first write), and it is public so a caller that composes its own
    body can ask before it files (RV-66 (writer enforces the frozen grammar)).
    `fields` is the manifest's `verdict_fields` list, read off the frozen
    manifest when not given; a test may hand in its own list of the same shape.
    The rules are READ from it, never from a copied list — so a `close` with no
    `decision` and a `verdict` of `bogus` are refused by the manifest's own
    words, and a word the manifest does not declare cannot slip through a
    mirror that forgot it."""
    if not isinstance(verdict, dict):
        raise Refused("the verdict must be an object carrying an `event`. "
                      "Nothing was filed.")
    if str(verdict.get("event")) not in EVENTS:
        raise Refused("event %r is not one of %s — exactly one per record. "
                      "Nothing was filed."
                      % (str(verdict.get("event"))[:40], "|".join(EVENTS)))
    if "status" in verdict:
        raise Refused("a record may not carry `status`: status is FOLDED from "
                      "the records, always (the card's never, and the plane's "
                      "rule 1). Nothing was filed.")
    _grammar(verdict, _verdict_fields() if fields is None else fields)
    # THE TWO OPTIONAL FIELDS RV-23 DECLARES, CHECKED AT THE WRITE DOOR — here,
    # and not in `request_verdict`, because this is the ONE place EVERY record
    # passes through whoever composed it: a request from `file_request`, a
    # verdict or a close from RV-3 (on_accept adapter) and the panels, either
    # door. Anchors ride with a VERDICT (they are appended with it and never
    # edited afterwards), but nothing here refuses them on another event: the
    # ruling declared an optional field and said where it belongs, and turning
    # "belongs" into "refused elsewhere" would be a rule nobody ruled. The SHAPE
    # is what is checked, so a malformed anchor is refused BY NAME rather than
    # stored — which is the whole of the card's done-when.
    if verdict.get("anchors") is not None:
        _anchors(verdict["anchors"])
    asset = verdict.get("asset")
    if isinstance(asset, dict) and asset.get("at") is not None:
        _at(asset["at"], str(asset.get("warehouse") or "").strip().lower())
    # THE POINTER'S OTHER OPTIONAL, RV-34 (url and viewport)'s, checked at the
    # same door and for the same reason: the panels and RV-3 (on_accept adapter)
    # compose their own bodies and file them here, so a check that lived only in
    # `request_verdict` would be a check one of the two doors does not make.
    if isinstance(asset, dict) and asset.get("viewport") is not None:
        _viewport(asset["viewport"])
    # The inventory, for the same reason again: a body a panel composed never
    # went through `request_verdict`, so its rows are checked here too.
    if verdict.get("media") is not None:
        _media(verdict["media"])
    _capped(verdict)


# ---- the write: two doors, one record --------------------------------------
def _urllib_transport(url, data, headers, timeout):
    """The default transport, and the ONLY place this module opens a socket.
    It is a seam so the declared test can prove byte-equality without a
    network — the test replaces this function, not the route logic."""
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def file_record(item, verdict, reviewer, notes="", root=None, env=None,
                now=None, transport=None, commit=True, timeout=60):
    """ONE record onto the review plane, through whichever door is open.

    The primitive under `file_request`, public so RV-3 (on_accept adapter) and
    the panels file their `verdict` and `close` records through this writer
    rather than minting a second one. Returns what was written, never the key.

    ON THE API ROUTE `record`/`bytes`/`filename` are the composition this
    module SENT, and the server stamps `created` from its own clock — read
    them as what the record is, not as a receipt of what the clock said.
    """
    item = str(item or "")
    if not ITEM_RE.match(item) or "--" in item:
        raise Refused("item %r is not an `RQ-<id>` (no `--`, which separates "
                      "the fields of a record filename). Nothing was filed."
                      % item[:60])
    validate(verdict)
    reviewer =_people(reviewer, "reviewer")[0]
    rec = record(item, verdict, notes=notes, reviewer=reviewer,
                 created=now or now_iso())
    body = render(rec)
    out = {"item": item, "record": rec, "bytes": body, "filename": filename(rec),
           "path": None, "route": "git", "committed": False, "response": None}

    if has_key(env):
        out["route"] = "api"
        out["response"] = _post(rec, env=env, transport=transport,
                                timeout=timeout)
        return out

    root = Path(root) if root else repo_root()
    if root is None:
        raise Refused(
            "no review key in the environment (%s) and no workspace clone "
            "above %s — there is no door open. Stand in a clone, or set the "
            "key. Nothing was filed." % (KEY_ENV, Path(__file__).resolve()))
    d = Path(root) / RECORDS_REL
    d.mkdir(parents=True, exist_ok=True)
    path = d / out["filename"]
    if path.exists():
        raise Refused("%s already exists — records are append-only and "
                      "create-never-edit (plane rule 1). Nothing was filed."
                      % path.name)
    path.write_bytes(body)
    out["path"] = str(path)
    if commit:
        out["committed"] = _commit(root, [path], _commit_msg([rec]))
    return out


def _post(rec, env=None, transport=None, timeout=60):
    """The record through `/api/review` — the same immutable record into the
    same `records/<kind>/` home, through the GitHub API instead of this clone.

    The server composes the envelope from what it is sent: `kind`, `item`,
    `verdict` and `notes` from the body, `reviewer` from `X-Reviewer`
    (attribution is client-declared, the team 2026-08-19), `via` from `X-Client`,
    `created` from its own clock. So the headers carry exactly the values this
    module put in the record it composed — that identity is what makes the two
    doors byte-equal, and the declared test asserts it."""
    key = _key(env)
    if not key:                              # pragma: no cover — route-guarded
        raise Refused("no review key in the environment (%s)." % KEY_ENV)
    body = json.dumps({"kind": rec["kind"], "item": rec["item"],
                       "verdict": rec["verdict"], "notes": rec["notes"]},
                      ensure_ascii=False).encode("utf-8")
    headers = {"Authorization": "Bearer %s" % key,
               "X-Reviewer": rec["reviewer"], "X-Client": rec["via"],
               "Accept": "application/json", "Content-Type": "application/json"}
    send = transport or _urllib_transport
    try:
        status, raw = send(REVIEW_API + "/api/review", body, headers, timeout)
    except urllib.error.HTTPError as e:      # pragma: no cover — network
        raise Refused("the review API refused the record: %s %s"
                      % (e.code, e.read()[:200].decode("utf-8", "replace")))
    except OSError as e:                     # pragma: no cover — network
        raise Refused("the review API could not be reached: %s" % e)
    if int(status) >= 400:
        raise Refused("the review API refused the record: %s %s"
                      % (status, raw[:200].decode("utf-8", "replace")))
    try:
        return json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return {"status": int(status)}


def _commit_msg(recs):
    """The commit's words. ONE record keeps exactly the message this module has
    always written; a BATCH says how many and on which lane, because the lane is
    what makes the group a group and the individual titles are in the records."""
    if len(recs) == 1:
        rec = recs[0]
        return "review: %s %s — %s" % (rec["verdict"]["event"], rec["item"],
                                       rec["verdict"].get("asset", {}).get("title")
                                       or rec["verdict"].get("event"))
    return "review: %d requests on %s" % (
        len(recs), recs[0]["verdict"].get("lane") or "one lane")


def _commit(root, paths, msg):
    """Stage the records and commit them — ONE commit, whether it carries one
    record or a batch's four. Never pushes, never touches another path: a review
    request must not carry someone else's working tree with it."""
    rels = [str(Path(p).relative_to(root)) for p in paths]
    for args in (["add", "--"] + rels, ["commit", "-q", "-m", msg, "--"] + rels):
        r = subprocess.run(["git"] + args, cwd=str(root), capture_output=True,
                           text=True, timeout=120)
        if r.returncode != 0:
            return False
    return True


def file_request(asset, type, reviewers, lane, requested_by, item=None,
                 due=None, on_accept=None, media=None, notes="", root=None,
                 env=None, now=None, transport=None, commit=True, batch=None):
    """FILE A REVIEW REQUEST. One call, no secret handled, either door.

    Returns {item, route, record, bytes, filename, path, committed, response}.
    `route` is "git" (record written into platform/data/records/review/ and
    committed) or "api" (POSTed to /api/review) — chosen by whether a review
    key is in the environment, never by an argument, so the same call in any
    session does the right thing.

    `requested_by` is REQUIRED and has no default — it becomes the record's
    `reviewer`, which is who filed it. Attribution is client-declared (the team,
    2026-08-19) and a defaulted name is a misattributed one; the caller knows
    who it is and says so. The requester's own words go in `notes`.

    `media` is the OPTIONAL inventory (RV-2b): one row per file the platform
    must serve for this request, `{name, type, ref, warehouse, bytes?, role?}`.
    Nothing is fetched, opened or copied here — the rows are pointers, and they
    are also the ALLOWLIST, so a Drive image with no row is a picture the panel
    never shows. Omit it and the record is byte-identical to what this module
    filed before the parameter existed.

    `batch` is the OPTIONAL list of assets (card RV-14). Given one, this files
    ONE REQUEST PER ASSET on a single lane minted for the batch
    (`<lane>/b-<yyyymmddHHMMSS>`) in ONE commit, and returns a LIST of the same
    per-request dicts — six ads sent as one act, judged as one group. Pass
    `asset=None` when you pass a batch: the assets are IN the batch, and a call
    naming both would have two answers to "what is under review". Everything
    else — `type`, `reviewers`, `lane`, `due`, `on_accept`, `media`, `notes` —
    is SHARED by every request in the batch, which is the whole of the rule and
    the reason no new shape was invented for it.

    THE BATCH IS A LANE AND NOTHING ELSE. There is no batch field on a record,
    no tally, no scoring, no "best of": pick-N is expressed as approve the picks
    and reject the rest, in the same three verdict words, and the group is read
    back through `list_open(lane=…)` — the grouping path that already existed.
    A single (non-batch) request is untouched by any of it.
    """
    created = now or now_iso()
    if batch is not None:
        return _file_batch(batch, asset, type, reviewers, lane, requested_by,
                           item=item, due=due, on_accept=on_accept, media=media,
                           notes=notes, root=root, env=env, created=created,
                           transport=transport, commit=commit)
    verdict = request_verdict(asset, type, reviewers, lane, due=due,
                              on_accept=on_accept, media=media)
    item = str(item) if item else mint_item(verdict["asset"]["title"], created)
    return file_record(item, verdict, requested_by, notes=notes,
                       root=root, env=env, now=created, transport=transport,
                       commit=commit)


def _file_batch(batch, asset, type, reviewers, lane, requested_by, item=None,
                due=None, on_accept=None, media=None, notes="", root=None,
                env=None, created=None, transport=None, commit=True):
    """ONE REQUEST PER ASSET on one minted lane, in ONE commit.

    ALL OR NOTHING, which is why this validates and mints EVERYTHING before it
    writes anything: a half-filed batch is the worst outcome available — the
    group the team judges is silently short an ad, and the plane is append-only so
    the missing one cannot be slotted in. Every refusal below therefore happens
    before the first byte is written, and says `Nothing was filed`. The one
    exception is a door that fails DURING the write — the API refusing a later
    POST — which raises `BatchPartial` with the receipts of what landed.

    No second grouping path is written here: the group is the lane, and reading
    it back is `list_open(lane=…)`, unchanged."""
    if asset is not None:
        raise Refused("a batch names its assets in `batch` — pass `asset=None` "
                      "alongside it. A call carrying both has two answers to "
                      "what is under review. Nothing was filed.")
    if item is not None:
        raise Refused("`item` names ONE request and a batch files several — "
                      "each asset mints its own id. Nothing was filed.")
    if not isinstance(batch, (list, tuple)):
        raise Refused("batch must be a LIST of assets, one per request to file "
                      "— %s. Nothing was filed." % _type_name(batch))
    if not batch:
        raise Refused("batch is empty — a batch of no assets asks for nothing. "
                      "Nothing was filed.")

    # ONE instant for the whole batch: the lane, the ids and every record are
    # minted from it, so a batch filed across a second boundary is still one
    # group with one name.
    created = created or now_iso()
    batch_lane = mint_batch_lane(lane, created)
    verdicts = [request_verdict(a, type, reviewers, batch_lane, due=due,
                                on_accept=on_accept, media=media)
                for a in batch]
    for v in verdicts:
        validate(v)             # every one against the frozen grammar and the
                                # plane's cap, HERE, so a request the API would
                                # refuse 400 cannot be the third of four and
                                # split the group

    items, seen = [], set()
    for v in verdicts:
        # Two ads may honestly carry one title, and refusing that would be a
        # rule no card ruled — so a repeat is disambiguated by POSITION rather
        # than colliding on a filename halfway through the write.
        base = mint_item(v["asset"]["title"], created)
        candidate, n = base, 1
        while candidate in seen:
            n += 1
            candidate = "%s-%d" % (base, n)
        seen.add(candidate)
        items.append(candidate)

    if not has_key(env):
        root = Path(root) if root else repo_root()
        if root is not None:
            d = Path(root) / RECORDS_REL
            who = _people(requested_by, "requested_by")[0]
            for it, v in zip(items, verdicts):
                name = filename(record(it, v, who, notes=notes, created=created))
                if (d / name).exists():
                    raise Refused(
                        "%s already exists — records are append-only and "
                        "create-never-edit (plane rule 1), and a batch is filed "
                        "whole or not at all. Nothing was filed." % name)

    # THE ONE REFUSAL NOTHING ABOVE CAN SEE COMING (RV-66 (writer enforces the
    # frozen grammar), finding rev-6): on the API door each request is its own
    # POST, so a 503 on the third of four leaves two landed on an append-only
    # plane. That is said as it is — the receipts of what landed and the ids of
    # what did not — never as "Nothing was filed".
    outs = []
    for n, (it, v) in enumerate(zip(items, verdicts)):
        try:
            outs.append(file_record(it, v, requested_by, notes=notes, root=root,
                                    env=env, now=created, transport=transport,
                                    commit=False))
        except Refused as e:
            reason = str(e).replace("Nothing was filed.", "").strip()
            raise BatchPartial(
                "the batch on %s stopped at request %d of %d: %d landed and "
                "%d did not, the first unfiled being %s — %s %s"
                % (batch_lane, n + 1, len(items), len(outs), len(items) - n,
                   it, reason,
                   "Nothing was filed." if not outs else
                   "The plane is append-only, so the landed requests stand; "
                   "file the unfiled assets again on their own."),
                outs, items[n:])
    if commit and outs[0]["route"] == "git":
        ok = _commit(root, [o["path"] for o in outs],
                     _commit_msg([o["record"] for o in outs]))
        for o in outs:
            o["committed"] = ok
    return outs


# ---- the read: THE fold, one home ------------------------------------------
def read_records(root=None, item=None):
    """Every review record in a clone, oldest filename first.

    The clone is the record (never-flex #2: git is the write path and the
    record). A reader with an API in hand passes its own list to `fold()`
    instead — the fold does not care where the records came from."""
    root = Path(root) if root else repo_root()
    if root is None:
        return []
    d = Path(root) / RECORDS_REL
    if not d.is_dir():
        return []
    out = []
    for p in sorted(d.glob("*.json")):
        if p.name.startswith("README"):
            continue
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue                 # an unparseable record is not a status
        if not isinstance(rec, dict) or rec.get("kind") != KIND:
            continue
        if item is None or rec.get("item") == item:
            out.append(rec)
    return out


def _events(records):
    """Records carrying one of the grammar's events, in `created` order.

    The sort is STABLE, so records sharing a `created` keep the order they
    arrived in — filename order from `read_records`, the caller's order from an
    API list. Same ordering rule as `fold_task()` in pm.html and mytasks.py."""
    evs = [r for r in records
           if isinstance(r, dict) and isinstance(r.get("verdict"), dict)
           and r["verdict"].get("event") in EVENTS]
    return sorted(evs, key=lambda r: str(r.get("created") or ""))


def fold(records):
    """THE FOLD. Records for ONE item -> its state. Never stored, always derived.

    - a request with no close is OPEN;
    - the LATEST close wins (and closes it), whatever came before;
    - the LATEST verdict per reviewer is that reviewer's verdict — a reviewer
      who votes twice has one vote, their last;
    - a second `request` record on the same id is an EDIT, so the latest one is
      the request;
    - `request_notes` is THE ENVELOPE'S OWN WORDS on the latest request — the
      ask (RV-17 (ask structure)), when the filer wrote one;
    - `seen_by` is WHO LOOKED, one entry per reviewer in the order they FIRST
      looked, however many times they looked after that.

    `request_notes` was added by card RV-32 (ask in the fold), because a reader
    that folds a request and then cannot say what was asked of them is not a
    fold of the request — the ask rides in the ENVELOPE and the fold carried
    only the verdict block. It is carried WHOLE AND UNPARSED: whether a filer's
    words are an ask in RV-17's four lines or their own commentary is a
    RENDERING question, and a fold that answered it would be a second place the
    answer could differ from. Nothing else about this answer moves on it.

    `seen` CHANGES NOTHING ELSE ABOUT THIS ANSWER, and that is the ruling, not a
    shortcut (the team, 2026-09-09, card RV-16a). It carries no judgment, so it
    never enters `verdicts`; it never closes, so `status`, `decision` and
    `accepted` cannot move on it; and it never satisfies the close rule's "one
    reviewer", because that rule reads `verdicts` and a `seen` is not one. A
    request whose only records are `request` + `seen` folds to OPEN with an
    empty `verdicts` — "he has seen it and not decided", which is the whole
    reason the event exists. AT MOST ONE PER REVIEWER PER REQUEST is a fold
    property, not a refusal at the door: the plane is append-only, so a second
    `seen` from one person is filed and then DEDUPED here, exactly as a second
    verdict is collapsed to the latest.

    This is the only implementation. RV-3 (on_accept adapter), RV-6 (reference
    panels) and RV-10 (PM review integration) import it; a second copy is the
    defect this function exists to prevent."""
    evs = _events(records)
    state = {"item": None, "status": "open", "request": None, "requested_by": None,
             "request_notes": "", "close": None, "decision": None, "accepted": False,
             "verdicts": {}, "seen_by": [], "records": len(evs)}
    for r in evs:
        v = r["verdict"]
        state["item"] = r.get("item") or state["item"]
        if v["event"] == "request":
            state["request"] = v                       # latest request = the edit
            # WHO ASKED is the envelope's `reviewer` — the filer — because the
            # frozen block declares no requester field and none is invented.
            state["requested_by"] = r.get("reviewer")
            # AND WHAT THEY ASKED FOR, from the same envelope and for the same
            # reason: the frozen block declares no ask field, so the ask lives
            # in `notes` (RV-17 (ask structure)) and a reader that dropped it
            # could not tell an absent ask from one it never carried.
            state["request_notes"] = "" if r.get("notes") is None else str(r["notes"])
        elif v["event"] == "verdict":
            who = str(r.get("reviewer") or "").strip().lower()
            if who:
                state["verdicts"][who] = r             # latest per reviewer
        elif v["event"] == "close":
            state["close"] = r                         # latest close wins
        elif v["event"] == "seen":
            who = str(r.get("reviewer") or "").strip().lower()
            if who and who not in state["seen_by"]:
                state["seen_by"].append(who)           # once per reviewer, in
                                                       # the order they first
                                                       # looked
    if state["close"] is not None:
        state["status"] = "closed"
        state["decision"] = state["close"]["verdict"].get("decision")
        state["accepted"] = state["decision"] == "accepted"
    return state


def latest_verdicts(records):
    """{reviewer: the verdict RECORD} — one per reviewer, their latest.

    Takes ONE item's records (`read_records(item=...)`, or a list from the
    API). A reviewer who votes twice has one vote here, their last."""
    return fold(records)["verdicts"]


def is_accepted(records):
    """True ONLY when the latest close decided `accepted`.

    `rejected`, `parked`, and no close at all are all False — the three are
    different states and only one of them starts RV-3 (on_accept adapter)'s
    next run."""
    return fold(records)["accepted"]


def list_open(records=None, root=None, reviewer=None, lane=None):
    """Every OPEN request, folded, oldest first.

    Discovery is a kind-wide read (no merged index record — the 2026-09-08
    ruling and WM-24 (index truncation) struck that shape; RV-8 (review queue
    index view) is the declared index view over the same records)."""
    recs = records if records is not None else read_records(root=root)
    by_item = {}
    for r in recs:
        if isinstance(r, dict) and r.get("item"):
            by_item.setdefault(r["item"], []).append(r)
    out = []
    for item, rs in by_item.items():
        state = fold(rs)
        if state["status"] != "open" or not state["request"]:
            continue
        req = state["request"]
        if reviewer and str(reviewer).lower() not in req.get("reviewers", []):
            continue
        if lane and req.get("lane") != str(lane).lower():
            continue
        state["item"] = state["item"] or item
        state["created"] = min(str(r.get("created") or "") for r in rs)
        out.append(state)
    return sorted(out, key=lambda s: (s.get("created") or "", s["item"]))


# ---- a person at a terminal -------------------------------------------------
def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description="file a review request")
    p.add_argument("--title", required=True)
    p.add_argument("--type", required=True, choices=list(TYPES))
    p.add_argument("--warehouse", required=True, choices=list(WAREHOUSES))
    p.add_argument("--ref", required=True)
    # RV-34 (url and viewport): OPTIONAL, and omitted means UNSTATED. There is
    # no default here on purpose — argparse's `default=None` is what carries
    # "the filer said nothing" all the way to `_asset`, which drops it.
    p.add_argument("--viewport", default=None, choices=list(VIEWPORTS))
    p.add_argument("--lane", required=True)
    p.add_argument("--reviewer", action="append", default=[])
    p.add_argument("--by", required=True, help="the person filing")
    p.add_argument("--due", default=None)
    p.add_argument("--notes", default="", help="the requester's own words")
    p.add_argument("--item", default=None)
    p.add_argument("--no-commit", action="store_true")
    p.add_argument("--dry-run", action="store_true",
                   help="print the record; write nothing, post nothing")
    a = p.parse_args(argv)
    asset = {"warehouse": a.warehouse, "ref": a.ref, "title": a.title}
    if a.viewport is not None:
        asset["viewport"] = a.viewport
    try:
        if a.dry_run:
            created = now_iso()
            v = request_verdict(asset, a.type, a.reviewer, a.lane, due=a.due)
            rec = record(a.item or mint_item(a.title, created), v,
                         _people(a.by, "--by")[0], notes=a.notes,
                         created=created)
            print(filename(rec))
            print(render(rec).decode("utf-8"))
            return 0
        out = file_request(asset, a.type, a.reviewer, a.lane, a.by,
                           item=a.item, due=a.due, notes=a.notes,
                           commit=not a.no_commit)
    except Refused as e:
        print("REFUSED: %s" % e, file=sys.stderr)
        return 2
    print("%s filed via %s%s" % (out["item"], out["route"],
                                 "" if out["route"] == "api" else
                                 (" (committed)" if out["committed"]
                                  else " (NOT committed)")))
    if out["path"]:
        print(out["path"])
    return 0


if __name__ == "__main__":           # pragma: no cover — a human at a terminal
    raise SystemExit(main())
