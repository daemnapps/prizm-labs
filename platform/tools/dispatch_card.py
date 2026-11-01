#!/usr/bin/env python3
"""dispatch_card.py — a card-holder files their OWN implement request.

Card CLI-18 (dispatch skill), 2026-09-08. The skill half is
`.claude/skills/dispatch/SKILL.md`; this is the module it calls.

WHY IT EXISTS. the developer granted the ops lead the right to dispatch ONE card — RV-11
(drive projection) — after her own test. Dispatching, until this file, meant
hand-writing a `workflow-requests` JSON record: the shape, the `tests` array,
`IMPL_TEST_MAX`, the `repo` field, the interpreter-by-suffix rule. The lead
does it from memory and got it wrong three times on 2026-09-05, at the cost of
three maker runs. A grant to dispatch is not usable while dispatching means
composing JSON by hand, because the holder has to ask the lead — which puts the
grant back through the very seat it was meant to bypass.

WHAT IT DOES, AND THE HARD EDGES OF THAT.

  * It takes a CARD ID, finds the card in its registered deck, and files ONE
    record on the `workflow-requests` kind. That is the whole act.
  * `requested_by` and the record's `reviewer` are the person RUNNING it,
    derived from `git config user.email` and from nothing else. There is no
    `--by` flag: records are append-only, so an authorship this tool got wrong
    would be permanent, and a flag that lets one person file as another is
    exactly the authority this card refuses to mint.
  * IT NEVER MERGES. Duty 5 — the human binds at merge — is untouched, and
    every refusal below says so out loud.
  * It never edits a card. Updating a card is the author's act. A card missing
    its `Declared test` line is REFUSED here, not repaired here.
  * It never promotes anything (`team/promoted-surfaces.json` is a human's
    commit) and it holds no second copy of the dispatch record shape — it
    writes what `platform/data/kinds/workflow-requests.json` declares and what
    the worker's own reader accepts.

THE GATE, WHICH IS THE POINT OF THE CARD. `team/dispatch-grants.json` is DATA,
in ONE place, read at run time, naming person -> card ids. An ungranted card is
refused BY NAME with the words "ask the lead". The file mints no authority: a
person with no row can run this and file nothing, and the gate fails CLOSED on
anything it cannot parse.

THE REPLAY PAIR (WM-36, 2026-09-09). `--base-ref` and `--branch-prefix` put the
worker's two optional replay fields onto the verdict this tool writes, so a
pilot harness replaying a merged card from its pre-merge parent uses THE SAME
DISPATCH PATH as everyone else. Without them the harness would hand-compose
request records, which is a second write path for the dispatch shape — and
killing the second write path is why this file exists at all. Neither flag =
today's record, byte for byte: no key is added, and the worker's own defaults
(unchanged, forever) apply. Their SHAPE rules are the worker's
`impl_base_ref` / `impl_branch_prefix`, asked for rather than copied; whether a
ref RESOLVES is deliberately NOT asked here — the only clone whose answer
matters is the worker's, which refuses an unresolvable base by name before it
makes the maker's tree.

WHAT `--base-ref` NOW TURNS ON (WM-39, 2026-09-09). Naming a base does not just
move the starting point: it makes the maker's tree a REPOSITORY OF ITS OWN
holding exactly that one commit, because a shared checkout left the build the
replayed card had already shipped one `git show` away. Nothing changes for a
dispatch that names no base.

THE MODEL ROUTE (WM-53, 2026-09-11). `--route claude|codex` puts the worker's
optional `route` field onto the verdict, so ONE card builds on the gateway while
the rest of the queue stays on Claude. Until this flag the route was a GLOBAL
swap — two file copies on the machine — which made a model test an
all-or-nothing act on the whole queue. Absent = today's record, byte for byte:
no key is added and the worker's own default route applies. The rule is the
worker's `impl_route`, asked for rather than copied, and an unknown route is
REFUSED HERE BY NAME rather than quietly filed as a Claude run. No key or
credential is handled here — the codex route's env file carries a base url and
no secret, and this tool never reads it.

VALIDATION IS IMPORTED, NEVER RESTATED. The four defects the worker rejects
before it spends a maker run — unknown card, no declared test, more than
`IMPL_TEST_MAX` tests, a suffix with no fixed interpreter — are caught HERE,
before the record is written, using the worker's OWN functions:
`impl_declared_tests`, `impl_test_interpreter`, `impl_test_specs`,
`IMPL_TEST_MAX`, `IMPL_REPOS`, `NAME_RE`, `REQUESTER_RE`. A second copy of a
validation rule is the wound CLI-15d (closes flag) closed once already; this
file does not reopen it. The candidate row is `dispatch-precheck`.

EXTERNAL DEPENDENCIES (greppable):
  platform/workers/mini-worker/worker.py   the validation rules, imported
  team/dispatch-grants.json                the gate (data)
  team/id-tags.json                        the item slug's words
  new-workflow-design/workflows.json       deck + repo resolution
  platform/data/kinds/workflow-requests.json   the record shape
  platform/data/records/workflow-requests/     where the record lands

USAGE
    python3 platform/tools/dispatch_card.py RV-11
    python3 platform/tools/dispatch_card.py RV-11 --dry-run
    python3 platform/tools/dispatch_card.py RV-11 --note "gate met: her test is in"
    python3 platform/tools/dispatch_card.py RV-11 --base-ref 8f3c1d2 --branch-prefix pilot/a2/
    python3 platform/tools/dispatch_card.py RV-11 --route codex

Exit 0 filed (or a clean dry run), 1 refused, 2 usage. `--json` prints the
whole decision as one document for a caller that parses instead of reads.
"""
import argparse
import fnmatch
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

GRANTS_REL = "team/dispatch-grants.json"
REGISTRY_REL = "new-workflow-design/workflows.json"
ID_TAGS_REL = "team/id-tags.json"
KIND_REL = "platform/data/kinds/workflow-requests.json"
RECORDS_REL = "platform/data/records/workflow-requests"
WORKER_REL = "platform/workers/mini-worker/worker.py"

GRANTS_SCHEMA = 1

# The standing sentence on EVERY refusal. The card asks for it by name: this
# tool files a request and stops, and a refusal is the right moment to say so.
NEVER_MERGES = ("/dispatch files a request and nothing else — it never merges "
                "(duty 5, the human binds at merge, is untouched), never "
                "promotes, and never edits a card.")

# card_text_for()'s OWN pattern, in worker.py. Kept as one literal so the
# declared test can assert the two are the same string: the worker pastes the
# card into the maker's prompt with this, and a record filed against a
# different reading of "where does the card end" would carry a different card
# than the one that gets built.
CARD_SECTION_RE = r"^### {cid}\b[\s\S]*?(?=^### |\Z)"

# The `Declared test:` (or `Declared tests:`) bullet AND its indented
# continuation lines — the paths routinely wrap onto the next line.
DECLARED_BLOCK_RE = re.compile(
    r"^- Declared tests?\b[^\n]*(?:\n[ \t]+[^\n]*)*", re.M)
# A declared test is a BACKTICKED REPO-RELATIVE PATH. The `/` is required, not
# incidental: the worker runs `<interpreter> <repo-relative path>` in the
# worktree, so a bare filename is not something it can run, and the same
# Declared-test prose routinely backticks non-path things (`pm.html`,
# `expect_exit`) that must not become tests.
DECLARED_PATH_RE = re.compile(r"`([A-Za-z0-9._][A-Za-z0-9._/-]*/[A-Za-z0-9._-]+\.[A-Za-z0-9]+)`")

CARD_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+$")


class Refused(Exception):
    """A named refusal. `name` is stable and machine-readable; `reason` is what
    a person reads. Nothing is written when this is raised — that is the whole
    contract of raising it."""

    def __init__(self, name, reason):
        super().__init__(reason)
        self.name = name
        self.reason = reason


# ---------------------------------------------------------------- the worker --

_worker = None


def worker(repo=None):
    """worker.py, imported once. The validation rules live there and are used
    from there; this module restates none of them."""
    global _worker
    if _worker is not None:
        return _worker
    path = Path(repo or REPO) / WORKER_REL
    if not path.is_file():
        raise Refused("no-worker", "cannot read %s — the validation rules live "
                                   "there and are never restated here. %s"
                      % (WORKER_REL, NEVER_MERGES))
    here = str(path.parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    spec = importlib.util.spec_from_file_location("_dispatch_worker", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _worker = mod
    return mod


# ----------------------------------------------------------------- identity --

def runner_id(repo=None):
    """The person running this, from `git config user.email` and nothing else.
    Same rule the /review-request skill uses, so one session has one identity
    everywhere."""
    try:
        out = subprocess.run(["git", "config", "user.email"],
                             cwd=str(repo or REPO), capture_output=True,
                             text=True, timeout=10)
        email = (out.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        email = ""
    email = email.strip().lower()
    if not email:
        raise Refused("unknown-runner",
                      "no `git config user.email` in this checkout, so there is "
                      "no person to file as — and a request is never filed "
                      "under a guessed name. Set it, then run again. "
                      + NEVER_MERGES)
    # THE EMAIL'S LOCAL PART IS NOT THE PERSON ID, and assuming it was made one
    # teammate invisible to this tool for two weeks (fixed 2026-09-16, found by
    # the ops lead's own session). `stephanie@…` resolved to `stephanie`; her id
    # everywhere else — the folder, 365 task records, her grant row — is
    # `brand-editor`. The grant the developer made on 2026-09-08 therefore never fired, and it
    # failed CLOSED AND SILENTLY: "Grants held: none", which reads as "you were
    # granted nothing" rather than "your id resolved to a name no row uses".
    #
    # team/people/<id>/identity.json already carries every address, so the
    # mapping is READ rather than guessed. The local part stays as the fallback
    # (it is right for everyone whose email agrees with their id) and the
    # registry wins whenever it has an answer. Fixing it HERE rather than
    # writing `stephanie` into the grants file is deliberate: that would make
    # one file disagree with every other record about who she is.
    who = _id_for_email(email) or email.split("@")[0].strip()
    return who


def _id_for_email(email, repo=None):
    """`team/people/<id>/identity.json` -> the id whose addresses include this
    email, or None. Case-insensitive; returns None on any read problem so the
    caller falls back rather than failing on a malformed profile."""
    people = Path(repo or REPO) / "team" / "people"
    try:
        dirs = sorted(d for d in people.iterdir() if d.is_dir())
    except OSError:
        return None
    for d in dirs:
        try:
            doc = json.loads((d / "identity.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        raw = doc.get("email") or doc.get("emails") or []
        if isinstance(raw, (str, dict)):
            raw = [raw]
        for entry in raw:
            addr = entry.get("address") if isinstance(entry, dict) else entry
            if isinstance(addr, str) and addr.strip().lower() == email:
                return d.name
    return None


# -------------------------------------------------------------- the gate ----

def read_grants(repo=None):
    """person -> [card ids], from team/dispatch-grants.json. FAILS CLOSED: any
    problem reading or parsing this file means nobody is granted anything."""
    path = Path(repo or REPO) / GRANTS_REL
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(doc, dict) or doc.get("schema") != GRANTS_SCHEMA:
        return {}
    rows = doc.get("grants")
    if not isinstance(rows, list):
        return {}
    out = {}
    for row in rows:
        if not isinstance(row, dict):
            return {}                       # one bad entry closes the file
        person = row.get("person")
        cards = row.get("cards")
        if (not isinstance(person, str) or not re.match(r"^[a-z0-9-]{1,40}$", person)
                or not isinstance(cards, list)
                or not all(isinstance(c, str) and c.strip() for c in cards)
                or not isinstance(row.get("granted_by"), str)
                or not isinstance(row.get("granted_on"), str)):
            return {}
        out.setdefault(person, []).extend(c.strip() for c in cards)
    return out


def check_grant(person, card_id, repo=None):
    """The gate. Raises Refused('not-granted') — with the words "ask the lead" —
    for anything not named for this person. Nothing has been read from any deck
    at this point: an ungranted person learns nothing here, not even whether the
    card exists."""
    granted = read_grants(repo).get(person, [])
    # PATTERNS, ruled by the developer 2026-09-18 (batch 390, his own commit fa9388ca3),
    # verbatim "wildcard. And generalize for UQ, RV, PM families if she doesnt
    # have it already". Until that ruling the match was exact and every batch an
    # owner carded came back to him for a fresh commit.
    #
    # WHY fnmatch AND NOT re: a grant line is written by a human in a JSON file,
    # and `UQ-*` is what a person means by "her family". A regex there would make
    # a mis-typed grant a silently BROADER one — `UQ-.*` reads fine and `UQ-.`
    # matches nothing, but `.` in a glob is a literal dot and cannot widen by
    # accident. fnmatch has no alternation, no backreferences and no catastrophic
    # backtracking, so the worst a typo does is match less.
    #
    # EXACT IDS STILL WORK UNCHANGED: a pattern with no metacharacter IS the
    # exact match it was before, so every existing row behaves byte for byte as
    # it did — developer's six ids, brand-editor's RV-11 (drive projection). fnmatchcase on
    # lowered strings, so the case-insensitivity that `_rules` promises is kept
    # and is not left to the platform (plain fnmatch is case-insensitive only on
    # some filesystems, which would make this gate behave differently on a Mac
    # and on CI — the one thing a permission gate must never do).
    if any(fnmatch.fnmatchcase(card_id.lower(), c.lower()) for c in granted):
        return
    held = ", ".join(sorted(granted)) if granted else "none"
    raise Refused("not-granted",
                  "%s is not granted %s — ask the lead. Grants held: %s. The "
                  "grant list is %s and only a human commit changes it. %s"
                  % (person, card_id, held, GRANTS_REL, NEVER_MERGES))


# ------------------------------------------------------------- the registry --

def registry_rows(repo=None):
    path = Path(repo or REPO) / REGISTRY_REL
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        rows = doc["workflows"]
    except (OSError, ValueError, KeyError, TypeError):
        raise Refused("no-registry",
                      "cannot read %s, so no card id can be resolved to a deck. %s"
                      % (REGISTRY_REL, NEVER_MERGES))
    return [r for r in rows if isinstance(r, dict) and r.get("name")]


def card_section(deck_text, card_id):
    """The card, VERBATIM, out of its deck — the same span the worker pastes
    into the maker's prompt, read with the worker's own pattern.

    Case-insensitive on the id ONLY so that `rv-11` typed at a prompt finds
    `### RV-11`; the caller then carries the DECK's own spelling onto the
    record, because the worker's reader is case-sensitive and a record saying
    `rv-11` would find no card at all."""
    m = re.search(CARD_SECTION_RE.format(cid=re.escape(card_id)), deck_text,
                  re.M | re.I)
    return m.group(0) if m else None


def canonical_id(card_text, fallback):
    """The id as the DECK spells it, off the matched `###` heading."""
    m = re.match(r"^###\s+(\S+)", card_text)
    return m.group(1) if m else fallback


def find_card(card_id, repo=None):
    """(row, card_text, canonical id) for `card_id`. The registered PREFIX picks
    the deck; every other registered deck is then swept, so a card filed under a
    build whose prefix does not match still resolves rather than reading as
    unknown."""
    root = Path(repo or REPO)
    rows = registry_rows(repo)
    prefix = card_id.split("-")[0].upper()
    ordered = ([r for r in rows if str(r.get("prefix", "")).upper() == prefix]
               + [r for r in rows if str(r.get("prefix", "")).upper() != prefix])
    for row in ordered:
        rel = row.get("cards_file") or ("new-workflow-design/builds/%s/task-cards.md"
                                        % row["name"])
        deck = root / rel
        if not deck.is_file():
            continue
        text = card_section(deck.read_text(encoding="utf-8"), card_id)
        if text:
            text = text.rstrip()
            return row, text, canonical_id(text, card_id)
    known = ", ".join(sorted({str(r["prefix"]) for r in rows if r.get("prefix")}))
    raise Refused("unknown-card",
                  "no `### %s` heading in any registered deck (%s). Known card "
                  "prefixes: %s. A card that is not in a deck is not a card yet "
                  "— and writing it there is its author's act, never this "
                  "tool's. %s" % (card_id, REGISTRY_REL, known, NEVER_MERGES))


# --------------------------------------------------- the card's declared tests --

def declared_paths(card_text):
    """The repo-relative test paths off the card's `Declared test` bullet, in
    the order the card names them, de-duplicated. Raises when the card has no
    such bullet, or has one that names no path."""
    block = DECLARED_BLOCK_RE.search(card_text)
    if not block:
        raise Refused("no-declared-test",
                      "the card carries no `- Declared test:` line, so there is "
                      "nothing to declare and the request would be filed with no "
                      "test at all. Adding that line is the CARD AUTHOR's act, "
                      "not this tool's. %s" % NEVER_MERGES)
    seen, paths = set(), []
    for p in DECLARED_PATH_RE.findall(block.group(0)):
        if p not in seen:
            seen.add(p)
            paths.append(p)
    if not paths:
        raise Refused("no-declared-test",
                      "the card's `Declared test` line names no backticked "
                      "repo-relative path (it describes the test in prose only), "
                      "so there is nothing runnable to declare. Naming the path "
                      "on the card is its author's act. %s" % NEVER_MERGES)
    return paths


def declared_tests(card_id, paths, repo=None):
    """`paths` -> the request's `tests` array, refused by name on each of the
    things the worker rejects before it spends. Every rule below is the
    worker's own function; none is restated here."""
    w = worker(repo)
    if len(paths) > w.IMPL_TEST_MAX:
        raise Refused("too-many-tests",
                      "the card declares %d tests and the worker's cap is "
                      "IMPL_TEST_MAX = %d, so this request would be rejected "
                      "before the maker ran: %s. %s"
                      % (len(paths), w.IMPL_TEST_MAX, ", ".join(paths), NEVER_MERGES))
    for p in paths:
        problem = w.impl_test_interpreter(p)[1]
        if problem:
            raise Refused("bad-test-suffix",
                          "declared test `%s`: %s. The interpreter is fixed by "
                          "suffix on a closed map and a request may never name "
                          "one, so the worker would reject this before spend. %s"
                          % (p, problem, NEVER_MERGES))
    tests = [{"name": (card_id if len(paths) == 1
                       else "%s %s" % (card_id, Path(p).name))[:80],
              "test": p,
              "expect_exit": 0}
             for p in paths]
    # Belt AND braces, and deliberately not a third copy: the same specs the
    # worker builds, so an absolute path, a `..`, a whitespace-bearing command
    # line or an unknown field is refused here by the rule that would have
    # refused it there.
    bad = [s for s in w.impl_test_specs(tests) if s.get("error")]
    if bad:
        raise Refused("bad-test-declaration",
                      "the worker's own validation rejects this declaration "
                      "before spend: %s. %s"
                      % ("; ".join("%s: %s" % (s.get("label"), s["error"])
                                   for s in bad[:4]), NEVER_MERGES))
    # `tests` must survive the worker's reader as a real declaration, not as
    # "nothing declared" — the one shape check that is about the RECORD rather
    # than the paths.
    raw, err = w.impl_declared_tests({"tests": tests})
    if err or raw is None:
        raise Refused("bad-test-declaration",
                      "the declaration does not read as declared tests: %s. %s"
                      % (err or "empty", NEVER_MERGES))
    return tests


# ------------------------------------------------------------- the record ----

def id_tag(card_id, repo=None):
    """The card's stored 1-3 word tag, so every reference to it says the same
    words. Empty when the card has none — coining one is a filing act."""
    try:
        tags = json.loads((Path(repo or REPO) / ID_TAGS_REL).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    if not isinstance(tags, dict):
        return ""
    for k, v in tags.items():
        if str(k).lower() == card_id.lower() and isinstance(v, str):
            return v
    return ""


def item_slug(card_id, tag, title=""):
    """`impl-rv10c-review-create-form` — the house form, reproduced rather than
    invented: the card id lowercased with the hyphen closed up when a digit
    follows it (RV-10c -> rv10c, INV-C7 -> inv-c7), then the card's stored tag
    in kebab-case. Capped so the filename's item segment still satisfies the
    worker's NAME_RE."""
    ident = re.sub(r"^([a-z]+)-(?=\d)", r"\1", card_id.lower())
    words = re.sub(r"[^a-z0-9]+", "-", (tag or title).lower()).strip("-")
    slug = "-".join(x for x in ("impl", ident, words) if x)
    slug = re.sub(r"-+", "-", slug).strip("-")[:41]
    return slug.rstrip("-")


def card_title(card_text):
    """The card's own title, minus the id and any trailing parenthetical."""
    head = card_text.splitlines()[0] if card_text else ""
    head = re.sub(r"^###\s*\S+\s*[—–-]\s*", "", head).strip()
    return re.sub(r"\s*\([^()]*\)\s*$", "", head).strip()


def resolve_repo(row, repo=None):
    """The build's target repo, off the registry row, defaulted and then
    checked against the worker's OWN table of repos it can build."""
    w = worker(repo)
    name = str(row.get("repo") or w.IMPL_DEFAULT_REPO).strip()
    if name not in w.IMPL_REPOS:
        raise Refused("unknown-repo",
                      "the registry row for build `%s` names repo `%s`, which "
                      "the worker cannot build — known: %s. %s"
                      % (row.get("name"), name, ", ".join(sorted(w.IMPL_REPOS)),
                         NEVER_MERGES))
    return name


def replay_fields(base_ref, branch_prefix, repo=None):
    """WM-36's two flags -> the verdict fields to APPEND, or `{}`.

    Neither given -> `{}`, so the record is byte for byte today's. Each one's
    shape is checked by the WORKER's own function; this file holds no copy of
    the pattern and no copy of the defaults, which is why absent means absent
    here rather than "the default, written out again".

    RESOLUTION IS NOT CHECKED HERE. Whether a base exists is a question about
    the clone the maker will build in, not the one this tool runs in, and the
    worker refuses an unresolvable base by name before any worktree is made."""
    w = worker(repo)
    out = {}
    if base_ref:
        ref, problem = w.impl_base_ref({"base_ref": base_ref})
        if problem:
            raise Refused("bad-base-ref",
                          "%s. The worker would refuse this request before the "
                          "maker ran, so it is refused here instead. %s"
                          % (problem, NEVER_MERGES))
        out["base_ref"] = ref
    if branch_prefix:
        prefix, problem = w.impl_branch_prefix({"branch_prefix": branch_prefix})
        if problem:
            raise Refused("bad-branch-prefix",
                          "%s. The branch is built WITH its prefix and never "
                          "renamed afterwards, so a prefix the worker will not "
                          "build from is refused here. %s"
                          % (problem, NEVER_MERGES))
        out["branch_prefix"] = prefix
    return out


def route_field(route, repo=None):
    """WM-53's flag -> the verdict field to APPEND, or `{}`.

    Not given -> `{}`, so the record is byte for byte today's — absent means
    absent here, never "the default, written out again". The SHAPE rule is the
    worker's `impl_route`; this file holds no copy of the route names and no
    copy of the default. An unknown route is refused rather than filed, because
    the worker would refuse it before the maker ran and a request that can only
    end in a refusal is not worth a record."""
    if not route:
        return {}
    w = worker(repo)
    name, problem = w.impl_route({"route": route})
    if problem:
        raise Refused("bad-route",
                      "%s. The worker would refuse this request before the "
                      "maker ran, so it is refused here instead. %s"
                      % (problem, NEVER_MERGES))
    return {"route": name}


def build_record(card_id, card_text, row, tests, person, repo_name, tag,
                 note="", repo=None, replay=None, route=None):
    w = worker(repo)
    build = row["name"]
    if not w.NAME_RE.match(build):
        raise Refused("bad-build-name",
                      "the registry row names build `%s`, which the worker's "
                      "reader will not accept. %s" % (build, NEVER_MERGES))
    if not w.REQUESTER_RE.match(person):
        raise Refused("unknown-runner",
                      "`%s` is not a person id the records plane accepts, and a "
                      "request is never filed under a name that cannot be "
                      "resolved to a person. %s" % (person, NEVER_MERGES))
    item = item_slug(card_id, tag, card_title(card_text))
    if not w.NAME_RE.match(item):
        raise Refused("bad-item-name",
                      "`%s` is not an item name the worker's queue reader will "
                      "pick up. %s" % (item, NEVER_MERGES))
    named = "%s (%s)" % (card_id, tag) if tag else card_id
    cards_file = row.get("cards_file") or ("new-workflow-design/builds/%s/task-cards.md"
                                           % build)
    instruction = ("Build %s — read '### %s' in %s IN FULL. REPO: %s.\n\n"
                   "Dispatched by %s under the grant recorded in %s. The card is "
                   "the spec; its text as dispatched is on this record as "
                   "`card_text`.\n\n"
                   "Declared test(s), read from the card's own `Declared test` "
                   "line: %s.\n\n"
                   "IF THE CARD IS AMBIGUOUS, BLOCK — do not improvise."
                   % (named, card_id, cards_file, repo_name, person, GRANTS_REL,
                      ", ".join(t["test"] for t in tests)))
    if note:
        instruction += "\n\nFROM %s: %s" % (person.upper(), note.strip())
    return {
        "schema": 1,
        "kind": "workflow-requests",
        "reviewer": person,
        "item": item,
        # WM-36's pair is APPENDED, never inserted, and only when it was asked
        # for: a request that named neither carries the exact key set and order
        # this tool has always written.
        "verdict": {
            "action": "implement",
            "name": build,
            "cards": [card_id],
            "instruction": instruction,
            "tests": tests,
            "requested_by": person,
            "repo": repo_name,
            **(replay or {}),
            # WM-53's route on the same terms, and appended after the replay
            # pair: a request that named no route carries the exact key set and
            # order this tool has always written.
            **(route or {}),
        },
        # The card AS DISPATCHED, verbatim from the deck. Inert to the worker
        # (it reads the deck itself) and load-bearing for a reader: a card
        # edited after the fact leaves this record saying what was actually
        # asked for.
        "card_text": card_text,
        "notes": ("Filed by %s with /dispatch under the grant in %s (card %s). "
                  "The skill files a request and nothing else: no merge, no "
                  "promotion, no edit to the card." % (person, GRANTS_REL, named)),
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "via": "dispatch-skill/%s" % card_id,
    }


def record_filename(record):
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return "%s--%s--%s.json" % (ts, record["reviewer"], record["item"])


# ------------------------------------------------------------------- the act --

def dispatch(card_id, person=None, note="", dry_run=False, repo=None,
             base_ref="", branch_prefix="", route=""):
    """CARD ID -> one filed `workflow-requests` record.

    Returns {"ok": True, "record": …, "path": … | None, "card": …}. Every
    refusal raises Refused BEFORE anything is written; there is no path through
    this function that writes a partial record.

    `base_ref` / `branch_prefix` (WM-36) are the replay pair. Blank for both —
    the default — is today's record exactly. `route` (WM-53) is the model route
    for this one card; blank is today's record exactly too."""
    root = Path(repo or REPO)
    card_id = (card_id or "").strip()
    if not CARD_ID_RE.match(card_id):
        raise Refused("unknown-card",
                      "`%s` is not a card id — a card id looks like RV-11 or "
                      "CLI-15d. %s" % (card_id[:40], NEVER_MERGES))
    person = (person or runner_id(root)).strip().lower()

    # THE GATE FIRST, before any deck is opened. An ungranted person gets one
    # answer and learns nothing else.
    check_grant(person, card_id, root)

    row, card_text, card_id = find_card(card_id, root)
    paths = declared_paths(card_text)
    tests = declared_tests(card_id, paths, root)
    repo_name = resolve_repo(row, root)
    tag = id_tag(card_id, root)
    replay = replay_fields(base_ref, branch_prefix, root)
    route_extra = route_field(route, root)
    record = build_record(card_id, card_text, row, tests, person, repo_name,
                          tag, note=note, repo=root, replay=replay,
                          route=route_extra)

    out = {"ok": True, "record": record, "path": None,
           "card": card_id, "build": row["name"], "person": person,
           "tests": [t["test"] for t in tests], "repo": repo_name,
           "tag": tag}
    out.update(replay)      # absent unless asked for, so `--json` is unchanged
    out.update(route_extra)                             # WM-53, same terms
    if dry_run:
        return out
    out["path"] = write_record(record, root)
    return out


def write_record(record, root=None, records_rel=RECORDS_REL):
    """THE request-record writer: one file under RECORDS_REL, atomically, and
    its repo-relative path back. SI-15 (mini flag)'s system-check queue writes
    through here too — one writer, never a second copy of it. SI-17 (system
    runs filed)'s filer names its own plane with `records_rel`; absent, the
    folder is RECORDS_REL exactly as before."""
    root = Path(root or REPO)
    dest = root / records_rel
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / record_filename(record)
    tmp = path.parent / (path.name + ".tmp")
    tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    os.replace(tmp, path)
    return str(path.relative_to(root))


# ---------------------------------------------------------------------- cli --

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="dispatch_card.py",
        description="File your own implement request for ONE card you are "
                    "granted. Files a request and nothing else — never a "
                    "merge, never a promotion, never an edit to a card.")
    ap.add_argument("card", nargs="?", help="the CARD ID, e.g. RV-11")
    ap.add_argument("--note", default="", help="one line of context for the maker")
    ap.add_argument("--dry-run", action="store_true",
                    help="show the record that WOULD be filed; write nothing")
    ap.add_argument("--json", action="store_true", help="print one JSON document")
    # WM-36: absent = the worker's own default, unchanged. The defaults are
    # named in worker.py and nowhere else, so there is nothing to print here.
    ap.add_argument("--base-ref", default="", metavar="REF",
                    help="replay: the commit or ref the maker's tree is built "
                         "from — naming one also makes that tree a repository "
                         "of its own holding only that commit (WM-39) "
                         "(absent = the worker's default)")
    ap.add_argument("--branch-prefix", default="", metavar="PREFIX",
                    help="replay: the prefix the branch is BUILT with, "
                         "separator included (absent = the worker's default)")
    # WM-53: the route rides the DISPATCH, not the machine. The route names
    # are the worker's and are not restated here, so this help line says what
    # the flag is for and the worker says what it accepts.
    ap.add_argument("--route", default="", metavar="ROUTE",
                    help="the model route this ONE card builds on — the worker "
                         "names the routes it accepts and refuses any other by "
                         "name (absent = the worker's default route)")
    ap.add_argument("--repo-root", default=None, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if not args.card:
        ap.print_usage(sys.stderr)
        return 2
    root = Path(args.repo_root) if args.repo_root else REPO
    try:
        out = dispatch(args.card, note=args.note, dry_run=args.dry_run, repo=root,
                       base_ref=args.base_ref, branch_prefix=args.branch_prefix,
                       route=args.route)
    except Refused as r:
        if args.json:
            print(json.dumps({"ok": False, "refusal": r.name, "reason": r.reason},
                             indent=2))
        else:
            print("REFUSED (%s): %s" % (r.name, r.reason), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    named = "%s (%s)" % (out["card"], out["tag"]) if out["tag"] else out["card"]
    if args.dry_run:
        print("DRY RUN — nothing written.")
    print("%s → build %s, repo %s, requested_by %s"
          % (named, out["build"], out["repo"], out["person"]))
    print("tests: %s" % ", ".join(out["tests"]))
    print("item:  %s" % out["record"]["item"])
    if "route" in out:
        print("route: %s — this card only; the queue's default is untouched"
              % out["route"])
    if "base_ref" in out or "branch_prefix" in out:
        print("replay: base %s, branch prefix %s"
              % (out.get("base_ref", "<worker default>"),
                 out.get("branch_prefix", "<worker default>")))
    if out["path"]:
        print("filed: %s" % out["path"])
        print("The mini's worker picks it up on its next 60s tick. It files a "
              "request and nothing else — a human still merges.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
