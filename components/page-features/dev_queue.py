#!/usr/bin/env python3
"""PF-18 (dev-queue view): the data behind the dev-queue page family — the team's dev work, read from git in the repo
it is run in (the page server's own copy), never the records plane's API.

    python3 components/page-features/dev_queue.py [--root <repo>] [--cutoff 2026-10-27T00:00:00Z]
                                                  [--deck <glob> ...] [--now <ISO time>]

Prints one JSON object on stdout and writes nothing. The page server runs it for /data/dev-queue
(_templates/dev-queue.sources.json: cache_s, watch on the decks, the request records and the decision log).

What it reads, all from <repo>:
    decks        every card heading ("### <ID> — <title> (<note>)") of the decks the registry
                 new-workflow-design/workflows.json names, plus new-workflow-design/builds/*/task-cards.md and any
                 components/ deck (DECK_GLOBS); --deck replaces the globs and the registry with its own list
    requests     platform/data/records/workflow-requests/*--impl-*.json: a person's implement request names its
                 cards, the worker's records give the item's status
    merges       git log subjects "merge <ID> (<tag>) …" (also "merge: <ID> (…" and a seat's "lead: merge <ID> (…"):
                 merge truth is the merge commit
    direct       a commit whose subject starts "<ID> (<tag>)", for a card built straight on main (PF-4 (page starter
                 kit) is one); it counts only when no merge commit names the card
    heading      PF-18i (landed counts): a card heading saying LANDED, MERGED or CLOSED with a 7-40 hex sha after it
                 (before the next ";") of a commit reachable from HEAD, for a card built in a person's own session;
                 shipped at that commit's committer time, only when no merge or direct commit counts. One git log for
                 every heading sha, one rev-list of HEAD when any resolves; a sha that is not a commit on HEAD is
                 ignored and named once in `sources.warnings`
    decisions    the-org/decision-log.md entries ("- YYYY-MM-DD — …", their "  KILL:" line)
    commits      human commits since the cutoff whose subject names no card id: "Shipped without a card"
    issues       platform/data/records/tasks/*.json: PM tasks tagged `dev` (PF-18c (issue queue)), folded the tasks
                 kind's way (created order, latest wins per field, comments and links accumulate)
It never runs cards_status.py (over 5 minutes on the mini) and reads no cards-status record.

The board, per card: Up next (chips from heading words: APPROVED → Approved; DISPATCH WAITS or NOT DISPATCHED →
Waiting for a go; HELD → Held), In progress (chips from the item's newest worker status: Building · Ready to merge ·
Check first · Failed), Shipped (merged on or after the cutoff, or an EARLY_REVIEW_FAMILIES card merged any time, with
the review line "email_lead ✓ · designer –"), Flagged (an Up next, In progress or Shipped card with an open Question or
Issue from anyone, `flag_stage` before-build · while-building · after-ship: PF-18j (people data)), Reviewed (both of
the card's own reviewers' latest mark is Understood and nothing is open). PF-18f (earlier PF review): a card of any
other family shipped before the cutoff is left off the board.
PF-18j (people data), per card: `assignee` (the newest `assign` record's person, or None), `developer` (the assignee,
else built_by) and `reviewers`, the two of REVIEW_TEAM (developer, email_lead, designer) who are not the developer; a developer
outside REVIEW_TEAM, or none, keeps REVIEWERS (email_lead, designer). Nothing waits on a mark: no state, chip or dispatch
moves on one. PF-18m (open issues only), the assigner rule: whoever assigned a card (the `--by` on its newest assign
record) is not one of its reviewers either; a self-assignment changes nothing, an unassigned card keeps the rule above.
PF-18k (people views page), per card: `private` (the heading holds the word PRIVATE, exact, upper case, its own word);
a private card has `reviewers: []`, so it asks no one for a mark. The page draws it in its developer's view only.
Each card names who asked for the build (PF-18g (built by)): `built_by` (a person id) and `built_by_from` (the rule
that found it), first of: "heading" the approver in the card's heading (the person before "typed" or "relayed", the
decision-log reader's own pattern, approver_res); "request" the filer of the card's newest implement request (the
`--<person>--` in its file name, never mini-worker); "commit" the author of a card's own commit on main (a direct
commit, or the commit its heading names: PF-18i (landed counts)), through run_kit.people, when it has no request; else
None. `owner` stays the heading's "owner <Name>" (the build owner).
The Issue queue (PF-18c (issue queue)) is `issues`: every dev-tagged task, one entry each, with its queue state
(ISSUE_STATES: Raised · Discussing · Carded · Fixed (PF-18l (fixed move)) · Won't do, a follow-up Raised → Done); a
card carries the issues carded into it (`from_issues`, "from issue …"), the open issues raised on it, and its
follow-ups and context notes.
DQ-5 (human acts): `acts` is every OPEN follow-up (a dev-tagged task of kind follow-up, Raised), wherever it hangs —
no parent, an issue or a card — with its `assignees` (the page draws it in each one's Up next group), `urgent` (the
task's `priority` field is "urgent", set by dev_issues.py priority; newest edit wins) and `on` (the parent: {type
card|issue, id, tag|alias, title} or None). A ticked-done follow-up is not an act: it leaves the board, never Shipped,
never reviewed. Only tasks tagged dev are read at all; no other PM task reaches the board.
dev_issues.py writes those tasks; this file only reads them.

PF-18b (review marks): the marks are review records (RV-1 (review kind manifest), the frozen grammar), read with
RV-2 (review request module)'s read_records and fold, loaded by path; one item per card, RQ-dev-queue-<card id>, and
no request record (so no review queue lists them: nothing gates on a mark). Each person's mark is their latest
verdict (the fold's own rule):
    Understood   event verdict, verdict approve, reasons ["understood"]
    Question     event verdict, verdict fix,     reasons ["question"]
    Issue        event verdict, verdict reject,  reasons ["issue"]
    Resolve      event close,   decision accepted, reasons ["resolve", "of:<raiser>"] — it resolves that person's open
                 Question or Issue filed before it (an earlier second); only the raiser or developer may file it
    Note         event seen,                     reasons ["note"], the one line as its note (required, ≤200) —
                 DQ-3 (note mark): on any card; no judgment, so never in the fold's verdicts: it never moves a
                 card, flags, needs or takes a Resolve ("nothing to resolve"), counts as review or asks anyone for
                 one. Each card's `notes` is each person's latest, newest first; every note is "noted" in its history
    python3 components/page-features/dev_queue.py mark <card id> understood|question|issue|resolve|note --by <person>
                                                  [--note <one line>] [--of <raiser>] [--root <repo>] [--no-commit]
files ONE record through file_record (git commit in the repo, or the review API when a review key is in the
environment) and refuses a card not on the board (another family's card shipped before the cutoff, a hidden card);
Understood is refused on a card the board does not show as shipped, Question, Issue and Resolve take an Up next or
In progress card too (PF-18j (people data)). The page server's /act runs it (SCRIPTS "review",
_templates/dev-queue.actions.json), with the server's own person as --by.
    python3 components/page-features/dev_queue.py mark <follow-up task> done --by <person> [--note <one line>]
                                                  [--root <repo>] [--no-commit]
DQ-8 (act panel): the act panel's Done (feature 26) rides the same review route as the marks: `done` is not a mark
(no review record) but the one ACT_WORDS verb; it calls dev_issues.py's own `done` (its main, by import), which
refuses anyone but an assignee of the follow-up or developer and names why, then commits the records it wrote by path.
    python3 components/page-features/dev_queue.py assign <card id> developer|email_lead|designer|none [--urgent]
                                                  --by <person> [--root <repo>] [--no-commit]
PF-18j (people data): ONE record on the same item through the same writer. The frozen grammar has no assignment and no
comment event, so it is a `seen` (no judgment: never in the fold's verdicts or close) with reasons ["assign"] and the
person, or "none", as its note; the newest wins. developer assigns in Claude; no page button.
DQ-4 (prompts and urgent): `assign … --urgent` rides the same record as a second reason word "urgent"; per card
`urgent` is true only while the newest assign record names an assignee and carries it (a later plain assign clears it;
an unassigned card has no priority, so `none --urgent` is refused). Per card `importance` is the text of the first
"- Importance: …" line under its heading (the lead's carding practice from DQ-4 on), or None; old cards are not
backfilled.

Baseline: every card of BASELINE_FAMILIES plus any card with activity (carded, a request record, a merge, a commit
naming it) on or after CUTOFF, the one setting. Card ids match exactly with their letter suffix: PF-4b is never PF-4.
PF-18h (hidden cards): a card in HIDDEN_CARDS is left off the board (no tile, no column, `mark` refuses it); a decision
naming it still lists, a commit naming it still counts as carded, and `hidden_cards` is the count only, never the list.
PF-18m (open issues only): a card whose heading holds CLOSED_NO_BUILD ("CLOSED — NO BUILD", exact) is off the board the
same way and listed by id in `closed_no_build`. Family DQ (Dev-queue) is baseline and early-review, and every PF-18*
card reports `family` "DQ" (FAMILY_ALIASES); its id, and so its marks, merges and requests, is unchanged.
Stdlib only, Python 3.9.
"""
import argparse
import datetime
import glob
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(os.path.dirname(HERE), "run-kit"))   # appended, never ahead
from run_kit import paths  # noqa: E402  the one workspace locator (builder card rule 3)
from run_kit import people  # noqa: E402  the one person resolver, LD-77 (one person resolver)

CUTOFF = "2026-10-27T00:00:00Z"          # developer's baseline ruling: "starting from two days ago" (the one setting)
BASELINE_FAMILIES = ("PF", "DQ")        # "from the PF family's start"; DQ (Dev-queue) from DQ-1, PF-18m (open issues only)
# PF-18f (earlier PF review): these families' cards shipped before the cutoff go to Shipped for review like any
# other (developer: "the only cards that i want email_lead and designer to review are from the PF family"); () takes them off
# the board again (the card's kill: no mark from either reviewer two weeks after launch).
EARLY_REVIEW_FAMILIES = ("PF", "DQ")
# PF-18m (open issues only): every PF-18* card (PF-18 (dev-queue view) and its lettered follow-ups) reports this
# family in the data and the Family filter; its id is unchanged, so marks, merges and requests read the real id
FAMILY_ALIASES = ((re.compile(r"^PF-18[a-z]*$"), "DQ"),)
# PF-18h (hidden cards): these cards never reach the board (no tile, no column, no mark), developer: "remove DB7 from the
# shipped queue in this dev queue"; Shipped without a card and Decisions still read them. Past 5 ids → a family rule
# instead (the card's kill), asked of developer.
HIDDEN_CARDS = ("DB-7",)
# PF-18m (open issues only): a card whose heading holds these exact words is off the board like HIDDEN_CARDS (no tile,
# no column, no stat, no mark) and listed in `closed_no_build`; a heading with no ship sha would sit in Up next for ever
CLOSED_NO_BUILD = "CLOSED — NO BUILD"
REVIEWERS = ("email_lead", "designer")       # a card whose developer is outside REVIEW_TEAM, or none (the fold, ruling 5)
# PF-18j (people data): a card's two reviewers are the two of these who are not its developer (developer: "two of us
# reviewing the work of who has developed it. including myself"); the assignee is one of them, or none
REVIEW_TEAM = ("developer", "email_lead", "designer")
REGISTRY = "new-workflow-design/workflows.json"
DECK_GLOBS = ("new-workflow-design/builds/*/task-cards.md", "components/*/task-cards.md",
              "components/*/*/task-cards.md")
REQUESTS = "platform/data/records/workflow-requests"
DECISION_LOG = "the-org/decision-log.md"
ID_TAGS = "team/id-tags.json"
PEOPLE_DIR = "team/people"
# Commits a machine or a seat writes (records, recompiles, studio status, lead/plan/strat notes): never "Shipped
# without a card". Matched as "<prefix>:" or "<prefix>(…):" at the start of the subject.
MACHINE_PREFIXES = ("atlas", "atlas trigger", "studio", "red tests", "prereview", "cards status", "runs filer",
                    "review", "mini runs", "impl", "creative-queue", "ad-runs", "language", "task index",
                    "gpt backlog", "candidate scan", "dashboard refresh", "claude update check",
                    "ad check warehouse", "lead", "plan", "strat", "note", "design", "park", "stream",
                    "mini-debug", "records", "inbox", "triage")

ID = r"[A-Z][A-Z0-9]*-[A-Z]?\d+[a-z]*"
ID_RE = re.compile(r"(?<![A-Za-z0-9-])(%s)(?![A-Za-z0-9])" % ID)
TAGGED_ID_RE = re.compile(r"(?<![A-Za-z0-9-])(%s) \(([^()]{1,60})\)" % ID)
HEADING_RE = re.compile(r"^### (%s) — (.+)$" % ID)
MERGE_RE = re.compile(r"^(?:[a-z][a-z-]*:\s+)?merge:?\s+(%s)\s*\(" % ID)   # "lead: merge PF-4b (…)" too
DIRECT_RE = re.compile(r"^(%s) \(" % ID)
# PF-18i (landed counts): the heading's ship words, each read up to the next ";", and the first sha after one
LANDED_RE = re.compile(r"\b(?:LANDED|MERGED|CLOSED)\b([^;]*)")
SHA_RE = re.compile(r"(?<![0-9A-Za-z])([0-9a-f]{7,40})(?![0-9A-Za-z])")
IMPL_SUBJECT_RE = re.compile(r"^impl\([^)]*\):\s+(%s)(?![A-Za-z0-9])" % ID)
MACHINE_RE = re.compile(r"^(?:%s)(?:\([^)]*\))?:" % "|".join(re.escape(p) for p in MACHINE_PREFIXES), re.I)
DECISION_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2}) — (.+)$")
CARDED_RE = re.compile(r"\bcarded (\d{4}-\d{2}-\d{2})")
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
OWNER_RE = re.compile(r"\bowner:?\s+([A-Z][a-z]+)")
FILE_STAMP_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z--")
PENDING = (("held", re.compile(r"\bHELD\b")),
           ("waiting", re.compile(r"\bDISPATCH WAITS\b|\bNOT DISPATCHED\b")),
           ("approved", re.compile(r"\bAPPROVED\b")))
PRIVATE_RE = re.compile(r"\bPRIVATE\b")   # PF-18k (people views page): case-sensitive; "private" in a sentence is not it
CHIPS = {"queued": "Building", "running": "Building", "cap-retry-due": "Building", "done": "Ready to merge",
         "done-unverified": "Check first", "records-unpushed": "Check first", "failed": "Failed"}
SEP = "\x1f"
GIT_TIMEOUT = 120

# PF-18c (issue queue): issues are PM tasks tagged `dev` (developer, 2026-10-29: "issues as PM tasks"), one more tag naming
# what the item is. The queue words map onto the tasks kind's own statuses; no status is added (the kind's standing
# rule) and the kind manifest is untouched.
TASKS = "platform/data/records/tasks"
DEV_TAG = "dev"
ITEM_KINDS = ("issue", "follow-up", "context")
ISSUE_STATES = {"proposed": "raised", "todo": "discussing", "in_progress": "discussing", "in_review": "discussing",
                "dropped": "wont-do"}             # done → carded with a card link, fixed (PF-18l), else closed
# PF-18l (fixed move): the tasks kind allows no commit link type (card|dispatch|branch|inbox|record|url), so a fix
# rides on the status note "fixed at <short sha>: <subject>" and a comment "Fixed at commit <full sha>".
FIXED_NOTE_RE = re.compile(r"fixed at ([0-9a-f]{7,40}): ?([\s\S]*)\Z")
FIXED_COMMENT = "Fixed at commit "
FOLLOW_UP_STATES = {"proposed": "raised", "todo": "raised", "in_progress": "raised", "in_review": "raised",
                    "done": "done", "dropped": "wont-do"}
FIX_PREFIX = "Proposed fix: "                     # a comment on an issue: a proposed fix, before carding
CONTEXT_PREFIX = "Context: "                      # a comment on an issue: a fact
PRIORITY_URGENT = "urgent"     # DQ-5 (human acts): a follow-up's tasks `priority` value for Urgent ("" for plain)
BODY_RE = re.compile(r"(?:\A|\n\n)Source session: ([^\n]*)\nQuote \(([^)\n]*)\):\n([\s\S]*)\Z")

# PF-18b (review marks): the review module, loaded by path (its CLAUDE.md's public surface), and the mark words as
# the frozen review grammar carries them; the first reason names the mark.
REVIEW_MODULE = os.path.join(os.path.dirname(HERE), "review", "review_request.py")
MARK_ITEM = "RQ-dev-queue-"
MARKS = {"understood": {"event": "verdict", "verdict": "approve"},
         "question": {"event": "verdict", "verdict": "fix"},
         "issue": {"event": "verdict", "verdict": "reject"},
         "resolve": {"event": "close", "decision": "accepted"},
         # DQ-3 (note mark): the assign trick from PF-18j (people data), a no-judgment `seen` with the fixed first
         # reason "note"; never a verdict or a close, so never a flag, a review or a Resolve
         "note": {"event": "seen"}}
NOTE = "note"
FLAGS = ("question", "issue")
RESOLVERS = ("developer",)                    # Resolve belongs to whoever raised the mark, and developer
# DQ-8 (act panel): the `mark` verb's one word that is not a review mark: Done on a human act, through dev_issues.py
ACT_WORDS = ("done",)
OF = "of:"
NOTE_MAX = 200
# PF-18j (people data): the frozen grammar has no assignment event and no comment event, so an assignment is its one
# event that carries no judgment, `seen` (it never enters the fold's verdicts or close), with the fixed reason word
# "assign" and the person (or "none") as the note; newest wins
ASSIGN = {"event": "seen", "reasons": ["assign"]}
NONE = "none"
# DQ-4 (prompts and urgent): the assignment's second reason word; Urgent = someone is blocked now, or money or a
# customer is at risk (the fold's meaning); everything else is plain, no label
URGENT = "urgent"
# DQ-4 (prompts and urgent): a card's "- Importance: <evidence>" body line, the lead's carding practice
IMPORTANCE_RE = re.compile(r"^- Importance:\s*(.+?)\s*$")
# PF-18j (people data): a card in Flagged says where it was: its state's stage
FLAG_STAGES = {"up-next": "before-build", "in-progress": "while-building", "shipped": "after-ship"}


def utc(stamp):
    """An ISO time (Z, an offset, or a bare date) as UTC "YYYY-MM-DDTHH:MM:SSZ"; None when it is not one."""
    if not isinstance(stamp, str) or not stamp.strip():
        return None
    s = stamp.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        s += "T00:00:00+00:00"
    s = re.sub(r"Z$", "+00:00", s)
    try:
        t = datetime.datetime.fromisoformat(s)
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=datetime.timezone.utc)
    return t.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def family_of(card_id):
    return card_id[:card_id.rindex("-")]


def shown_family(card_id):
    """The family a card reports (`family`): its id's prefix, or its FAMILY_ALIASES family (PF-18m (open issues
    only): a PF-18* card is DQ)."""
    for rx, fam in FAMILY_ALIASES:
        if rx.match(card_id):
            return fam
    return family_of(card_id)


def cut(text, n):
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[:n - 1].rstrip() + "…"


def read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


# --- people -------------------------------------------------------------------------------------------------------

def people_of(root):
    """{id: display name} for every team/people/<id>/identity.json."""
    out = {}
    for f in sorted(glob.glob(os.path.join(root, PEOPLE_DIR, "*", "identity.json"))):
        pid = os.path.basename(os.path.dirname(f))
        out[pid] = pid[:1].upper() + pid[1:]
    return out


def approver_res(names):
    """(by_re, any_re) over the team's names: by_re finds the person before "typed" or "relayed" ("developer typed to the
    lead", "developer, relayed verbatim by ◆ PLAN"), any_re any person named. One pattern for the decision log's decider
    and a card heading's approver (PF-18g (built by))."""
    who = "|".join(re.escape(n[:1].upper() + n[1:]) for n in sorted(names)) or "developer"
    return (re.compile(r"\b(%s)\b[^.;:]{0,40}?\b(typed|relayed)\b" % who), re.compile(r"\b(%s)\b" % who))


class Authors(object):
    """git author email → person id through run_kit.people, one lookup per address."""

    def __init__(self, root):
        self.root, self.seen = root, {}

    def __call__(self, email, name):
        key = (email or "").strip().casefold()
        if key not in self.seen:
            self.seen[key] = people.try_person_of(self.root, email) if key else None
        return self.seen[key] or (name or "unknown").split()[0].lower()


# --- decks --------------------------------------------------------------------------------------------------------

def deck_paths(root, globs=None):
    """The deck files, repo-relative and sorted: the registry's cards_file entries and DECK_GLOBS, or `globs` alone."""
    found = set()
    if globs is None:
        reg = read_json(os.path.join(root, REGISTRY))
        for row in (reg or {}).get("workflows") or []:
            cf = row.get("cards_file") if isinstance(row, dict) else None
            if isinstance(cf, str) and cf.strip() and os.path.isfile(os.path.join(root, cf.strip())):
                found.add(cf.strip())
        globs = DECK_GLOBS
    for g in globs:
        for f in glob.glob(os.path.join(root, g)):
            if os.path.isfile(f):
                found.add(os.path.relpath(f, root).replace(os.sep, "/"))
    return sorted(found)


def pending_of(heading):
    """approved · waiting · held from the heading's own words, or None; HELD outranks a wait, a wait outranks
    APPROVED (a card approved but waiting on another card's merge is waiting)."""
    for word, rx in PENDING:
        if rx.search(heading):
            return word
    return None


def parse_heading(line, tags, names, by_re=None):
    m = HEADING_RE.match(line.rstrip("\n"))
    if not m:
        return None
    cid, rest = m.group(1), m.group(2).strip()
    at = rest.find(" (carded")
    title, note = (rest[:at], rest[at + 1:]) if at >= 0 else (rest, "")
    tag = tags.get(cid)
    head = title.split(":", 1)[0].strip() if ":" in title else ""
    if not tag:
        tag = head if head and len(head.split()) <= 4 else " ".join(title.split()[:3])
    if head and head.lower() == tag.lower():
        title = title.split(":", 1)[1].strip()
    owner = None
    for o in OWNER_RE.finditer(note or rest):
        if o.group(1).lower() in names:
            owner = o.group(1).lower()
            break
    # PF-18g (built by): rule (a), the approver the heading names; build() tries the request, then the commit
    a = (by_re or approver_res(names)[0]).search(note or rest)
    carded = CARDED_RE.search(rest) or DATE_RE.search(rest)
    return {"id": cid, "tag": tag, "title": cut(title, 300), "family": shown_family(cid), "owner": owner,
            "built_by": a.group(1).lower() if a else None, "built_by_from": "heading" if a else None,
            "carded_on": carded.group(1) if carded else None, "pending": pending_of(rest),
            "private": bool(PRIVATE_RE.search(rest)), "note": cut(note, 600), "landed": landed_of(rest),
            "closed_no_build": CLOSED_NO_BUILD in rest, "importance": None}


def landed_of(heading):
    """PF-18i (landed counts): the shas a heading ships at, in its order: the first 7-40 hex sha after each LANDED,
    MERGED or CLOSED, before the next ";" or the heading's end. build() drops the field after resolving it."""
    out = []
    for m in LANDED_RE.finditer(heading):
        s = SHA_RE.search(m.group(1))
        if s and s.group(1) not in out:
            out.append(s.group(1))
    return out


def read_cards(root, decks, tags, names):
    """{id: card} from every deck; the first deck (sorted) to carry an id keeps it. DQ-4 (prompts and urgent): the
    first "- Importance:" line under a kept card's heading, before the next heading, is its `importance`."""
    cards, by_re = {}, approver_res(names)[0]
    for rel in decks:
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        cur = None
        for line in lines:
            if line.startswith("#"):
                cur = None
            if not line.startswith("### "):
                m = IMPORTANCE_RE.match(line) if cur is not None and cur["importance"] is None else None
                if m:
                    cur["importance"] = cut(m.group(1), 600)
                continue
            c = parse_heading(line, tags, names, by_re)
            if c and c["id"] not in cards:
                c["deck"] = rel
                cards[c["id"]] = cur = c
    return cards


# --- request records ----------------------------------------------------------------------------------------------

def read_requests(root):
    """({card id: [request, …] newest first}, {item: [worker record, …] newest first}, files read).
    A request is {item, at, by, filer}, filer the `--<person>--` of its file name (PF-18g (built by)); a worker
    record {at, status, detail, by}."""
    by_card, by_item, n = {}, {}, 0
    for f in sorted(glob.glob(os.path.join(root, REQUESTS, "*--impl-*.json"))):
        d = read_json(f)
        n += 1
        if not isinstance(d, dict) or not str(d.get("item") or "").startswith("impl-"):
            continue
        v = d.get("verdict")
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except ValueError:
                v = {}
        if not isinstance(v, dict):
            continue
        stamp = FILE_STAMP_RE.match(os.path.basename(f))
        item = d["item"]
        at = utc(d.get("created")) or (utc("%s-%s-%sT%s:%s:%sZ" % stamp.groups()) if stamp else None)
        if "status" in v:
            by_item.setdefault(item, []).append({"at": at, "status": str(v.get("status")),
                                                 "detail": cut(v.get("detail"), 200), "by": d.get("reviewer")})
        elif v.get("action") == "cancel":
            by_item.setdefault(item, []).append({"at": at, "status": "cancelled", "detail": "", "by": d.get("reviewer")})
        elif v.get("action") == "implement":
            parts = os.path.basename(f).split("--")
            filer = parts[1] if stamp and len(parts) >= 3 else None
            for cid in v.get("cards") or []:
                if isinstance(cid, str) and ID_RE.fullmatch(cid):
                    by_card.setdefault(cid, []).append({"item": item, "at": at, "by": d.get("reviewer"),
                                                        "filer": filer})
    for rows in list(by_card.values()) + list(by_item.values()):
        rows.sort(key=lambda r: r["at"] or "", reverse=True)
    return by_card, by_item, n


# --- git ----------------------------------------------------------------------------------------------------------

def git(root, *args):
    p = subprocess.run(["git"] + list(args), cwd=root, capture_output=True, text=True, timeout=GIT_TIMEOUT)
    if p.returncode:
        raise RuntimeError("git %s: %s" % (args[0], (p.stderr or p.stdout).strip()[-300:]))
    return p.stdout


def read_log(root, since):
    """[commit] newest first since `since`: {sha, parents, name, email, at (UTC), subject}."""
    out = []
    text = git(root, "log", "--since=%s" % since, "--format=%H" + SEP + "%P" + SEP + "%an" + SEP + "%ae" + SEP +
               "%cI" + SEP + "%s")
    for line in text.splitlines():
        parts = line.split(SEP)
        if len(parts) != 6:
            continue
        out.append({"sha": parts[0], "parents": parts[1].split(), "name": parts[2], "email": parts[3],
                    "at": utc(parts[4]), "subject": parts[5]})
    return out


def heading_ships(root, cards):
    """PF-18i (landed counts): ({card id: (ship, (email, name))}, [warning]) for the cards whose heading names a sha
    (landed_of). ONE git log resolves every sha (--ignore-missing: a sha that is not a commit prints nothing), and one
    rev-list of HEAD, only when any resolved, says which are on HEAD; never a process per card. A card ships at its
    heading's first sha on HEAD; every other sha is ignored and warned once, naming the cards that cite it."""
    want = sorted(set(s for c in cards.values() for s in c["landed"]))
    if not want:
        return {}, []
    try:
        text = git(root, "log", "--no-walk", "--ignore-missing",
                   "--format=%H" + SEP + "%an" + SEP + "%ae" + SEP + "%cI" + SEP + "%s", *(want + ["--"]))
        commits = [line.split(SEP) for line in text.splitlines() if line.count(SEP) == 4]
        on_head = set(git(root, "rev-list", "HEAD").split()) if commits else set()
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        return {}, ["PF-18i (landed counts): heading shas not read: %s" % cut(exc, 200)]
    found = {}
    for short in want:
        hits = [x for x in commits if x[0].startswith(short)]
        if len(hits) == 1 and hits[0][0] in on_head:
            found[short] = hits[0]
    ships, bad = {}, {}
    for cid in sorted(cards):
        for short in cards[cid]["landed"]:
            x = found.get(short)
            if not x:
                # PF-18h (hidden cards), PF-18m (open issues only): never named, warnings included
                if cid not in HIDDEN_CARDS and not cards[cid]["closed_no_build"]:
                    bad.setdefault(short, []).append(cid)
            elif cid not in ships:
                ships[cid] = ({"sha": x[0][:10], "at": utc(x[3]), "subject": cut(x[4], 240), "via": "heading"},
                              (x[2], x[1]))
    warnings = ["heading sha %s (%s) is not a commit on HEAD: ignored" % (short, ", ".join(ids))
                for short, ids in sorted(bad.items())]
    return ships, warnings


def read_files(root, since):
    """{sha: [path, …]} for non-merge commits since `since`."""
    out, sha = {}, None
    for line in git(root, "log", "--since=%s" % since, "--no-merges", "--name-only", "--format=@@%H").splitlines():
        if line.startswith("@@"):
            sha = line[2:].strip()
            out[sha] = []
        elif line.strip() and sha:
            out[sha].append(line.strip())
    return out


def merge_ids(subject):
    """The card ids a merge subject names before its first " — ", each followed by its "(tag)"; [] when the subject
    is not "merge <ID> (…" or "merge: <ID> (…"."""
    if not MERGE_RE.match(subject):
        return []
    head = subject.split(" — ", 1)[0]
    return [m.group(1) for m in TAGGED_ID_RE.finditer(head)]


def area_of(path):
    bits = path.split("/")
    if len(bits) == 1:
        return path
    if bits[0] == "components" and len(bits) > 2:
        return bits[1]
    if bits[0] == "platform" and bits[1:3] == ["views", "viewers"]:
        return "page:" + bits[-1]
    if bits[0] in ("runs", "lab", "brands", "new-workflow-design") and len(bits) > 2:
        return bits[1] if bits[0] != "new-workflow-design" else (bits[2] if len(bits) > 3 else bits[1])
    return bits[0]


def names_a_card(subject, ids):
    """True when the subject names a deck card exactly, or any id written with its tag ("I-241 (drive timeout)")."""
    if TAGGED_ID_RE.search(subject):
        return True
    return any(m.group(1) in ids for m in ID_RE.finditer(subject))


# --- decision log -------------------------------------------------------------------------------------------------

def headline_of(text):
    """The entry's opening capital words ("THE MINI'S DRIVE APP QUITS NOW…"), or its first sentence."""
    words = []
    for w in text.split():
        if re.search(r"[a-z]", w) and not ID_RE.fullmatch(w.strip(".,:;")):
            break
        words.append(w)
        if w.endswith("."):
            break
    head = " ".join(words).rstrip(" ,;:—.")
    if len(words) < 3:
        head = re.split(r"(?<=[a-z0-9)])\. |\s—\s", text, maxsplit=1)[0]
    return cut(head, 160)


def read_decisions(root, names, tags, ids):
    """[decision] newest first: {date, headline, decided_by, how, cards [{id, tag, card}], text, kill}."""
    path = os.path.join(root, DECISION_LOG)
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    entries, cur = [], None
    for line in lines:
        m = DECISION_RE.match(line)
        if m:
            cur = {"date": m.group(1), "body": [m.group(2)], "kill": []}
            entries.append(cur)
        elif cur is not None and line.startswith("  ") and line.strip():
            s = line.strip()
            (cur["kill"] if s.upper().startswith("KILL") or cur["kill"] else cur["body"]).append(s)
        elif not line.strip() or line.startswith("- ") or line.startswith("#"):
            cur = None
    by_re, any_re = approver_res(names)
    out = []
    for e in entries:
        text = " ".join(e["body"])
        m = by_re.search(text)
        decided, how = (m.group(1).lower(), m.group(2)) if m else (None, None)
        if not decided:
            m = any_re.search(text)
            decided = m.group(1).lower() if m else None
        cards, seen = [], set()
        for t in TAGGED_ID_RE.finditer(text):
            if t.group(1) not in seen:
                seen.add(t.group(1))
                cards.append({"id": t.group(1), "tag": tags.get(t.group(1)) or t.group(2), "card": t.group(1) in ids})
        for t in ID_RE.finditer(text):
            if t.group(1) in ids and t.group(1) not in seen:
                seen.add(t.group(1))
                cards.append({"id": t.group(1), "tag": tags.get(t.group(1)) or "", "card": True})
        out.append({"date": e["date"], "headline": headline_of(text), "decided_by": decided, "how": how,
                    "cards": cards, "text": cut(text, 900), "kill": cut(" ".join(e["kill"]), 400)})
    out.sort(key=lambda d: d["date"], reverse=True)
    return out


# --- issues: dev-tagged PM tasks (PF-18c (issue queue)) -----------------------------------------------------------

def read_task_records(root):
    """({item id: [(file name, record), …] in created order}, files read) for every tasks record on disk."""
    by_item, n = {}, 0
    for f in sorted(glob.glob(os.path.join(root, TASKS, "*.json"))):
        n += 1
        r = read_json(f)
        if (not isinstance(r, dict) or r.get("kind") != "tasks" or not isinstance(r.get("verdict"), dict)
                or not isinstance(r.get("item"), str)):
            continue
        by_item.setdefault(r["item"], []).append((os.path.basename(f), r))
    for rows in by_item.values():
        rows.sort(key=lambda x: (str(x[1].get("created") or ""), x[0]))
    return by_item, n


def card_of_ref(ref):
    """The card id a task link's ref names ("<deck>#<ID>" or a bare "<ID>"), or None."""
    tail = str(ref or "").rsplit("#", 1)[-1].strip()
    return tail if ID_RE.fullmatch(tail) else None


def split_body(body):
    """(detail, quote, said_by, session) from a body dev_issues.py wrote; a body written elsewhere is all detail."""
    body = str(body or "")
    m = BODY_RE.search(body)
    if not m:
        return body.strip(), None, None, None
    return body[:m.start()].strip(), m.group(3), m.group(2).strip() or None, m.group(1).strip() or None


def fold_dev(item, rows):
    """One dev-tagged task folded the tasks kind's way, or None when it has no create or no `dev` tag.
    {id, alias, kind, status, state, title, detail, quote, said_by, session, by, created, assignees, parent,
     on_card, carded_as, reason, fixed_at, fixes, context, notes, history, follow_ups}."""
    t, comments, link_events, history = None, [], [], []
    last_status = None
    for name, r in rows:
        v, ev, at, who = r["verdict"], r["verdict"].get("event"), r.get("created"), r.get("reviewer")
        if ev == "create" and isinstance(v.get("item"), dict):
            t = json.loads(json.dumps(v["item"]))
            history.append({"at": at, "what": "raised", "by": who, "note": ""})
        elif t is None:
            continue
        elif ev == "status" and v.get("to"):
            t["status"] = v["to"]
            last_status = {"to": v["to"], "note": str(v.get("note") or ""), "at": at, "by": who}
            history.append({"at": at, "what": v["to"], "by": who, "note": str(v.get("note") or "")})
        elif ev == "assign" and isinstance(v.get("assignees"), list):
            t["assignees"] = list(v["assignees"])
            history.append({"at": at, "what": "assigned", "by": who, "note": ", ".join(v["assignees"])})
        elif ev == "edit" and isinstance(v.get("field"), str):
            if v["field"] != "alias" or not t.get("alias"):
                t[v["field"]] = v.get("value")
            if v["field"] == "priority":                # DQ-8 (act panel): the act panel's history shows Urgent moves
                history.append({"at": at, "what": "urgent" if str(v.get("value") or "").strip().lower() ==
                                PRIORITY_URGENT else "not urgent", "by": who, "note": ""})
        elif ev == "comment" and v.get("text"):
            comments.append({"at": at, "by": who, "text": str(v["text"])})
        elif ev == "link" and isinstance(v.get("add"), dict) and v["add"].get("ref"):
            link_events.append({"at": at, "by": who, "add": v["add"]})
    tags = t.get("tags") if t and isinstance(t.get("tags"), list) else []
    if t is None or DEV_TAG not in tags:
        return None
    kind = next((k for k in ITEM_KINDS if k in tags), "issue")
    status = t.get("status") if isinstance(t.get("status"), str) else "proposed"
    body_cards = [card_of_ref(x.get("ref")) for x in (t.get("links") or [])
                  if isinstance(x, dict) and x.get("type") == "card"]
    linked = [card_of_ref(x["add"].get("ref")) for x in link_events if x["add"].get("type") == "card"]
    on_card = next((c for c in body_cards if c), None)
    carded_as = next((c for c in reversed(linked) if c), None)
    fixed = (FIXED_NOTE_RE.match(last_status["note"]) if status == "done" and last_status and
             last_status["to"] == "done" else None)
    if kind == "issue":
        state = ISSUE_STATES.get(status) or ("carded" if status == "done" and carded_as else
                                             "fixed" if status == "done" and fixed else "closed")
    elif kind == "follow-up":
        state = FOLLOW_UP_STATES.get(status, "raised")
    else:
        state = "fact"
    detail, quote, said_by, session = split_body(t.get("body"))
    fixes = [dict(c, text=c["text"][len(FIX_PREFIX):]) for c in comments if c["text"].startswith(FIX_PREFIX)]
    context = [dict(c, text=c["text"][len(CONTEXT_PREFIX):]) for c in comments if c["text"].startswith(CONTEXT_PREFIX)]
    notes = [c for c in comments if not c["text"].startswith((FIX_PREFIX, CONTEXT_PREFIX, FIXED_COMMENT))]
    fixed_at = None
    if state == "fixed":
        full = [c["text"][len(FIXED_COMMENT):].strip() for c in comments if c["text"].startswith(FIXED_COMMENT)]
        fixed_at = {"sha": full[-1] if full and full[-1].startswith(fixed.group(1)) else fixed.group(1),
                    "subject": cut(fixed.group(2), 300), "at": None}      # dev_items fills these from git
    parent = str(t.get("parent") or "").strip()
    return {"id": item, "alias": t.get("alias") or None, "kind": kind, "status": status, "state": state,
            "title": cut(t.get("title"), 300), "detail": cut(detail, 900), "quote": quote, "said_by": said_by,
            "session": session, "by": t.get("by") or t.get("requested_by"), "created": utc(t.get("created")),
            "assignees": [a for a in (t.get("assignees") or []) if isinstance(a, str)],
            "parent": parent or None, "on_card": on_card, "carded_as": carded_as if state == "carded" else None,
            "reason": last_status["note"] if state == "wont-do" and last_status else None, "fixed_at": fixed_at,
            "fixes": fixes, "context": context, "notes": notes, "history": history[-20:], "follow_ups": [],
            "urgent": kind == "follow-up" and str(t.get("priority") or "").strip().lower() == PRIORITY_URGENT}


def fixed_commits(root, fixes):
    """PF-18l (fixed move): fill each fixed issue's {sha, subject, at} from ONE git log (--ignore-missing: a sha that
    is not a commit prints nothing and keeps what the note said); `at` is the commit's committer time."""
    want = sorted(set(f["sha"] for f in fixes))
    if not want:
        return
    try:
        text = git(root, "log", "--no-walk", "--ignore-missing", "--format=%H" + SEP + "%cI" + SEP + "%s",
                   *(want + ["--"]))
    except (RuntimeError, OSError, subprocess.SubprocessError):
        return
    commits = [line.split(SEP) for line in text.splitlines() if line.count(SEP) == 2]
    for f in fixes:
        hits = [x for x in commits if x[0].startswith(f["sha"])]
        if len(hits) == 1:
            f.update(sha=hits[0][0], at=utc(hits[0][1]), subject=cut(hits[0][2], 300))


def dev_items(root):
    """([every dev-tagged task, folded], task files read); follow-ups listed on their parent issue."""
    by_item, n = read_task_records(root)
    out = [e for e in (fold_dev(item, rows) for item, rows in sorted(by_item.items())) if e]
    fixed_commits(root, [e["fixed_at"] for e in out if e["fixed_at"]])
    ids = dict((e["id"], e) for e in out)
    for e in out:
        p = ids.get(e["parent"] or "")
        if e["kind"] == "follow-up" and p is not None and p["kind"] == "issue":
            p["follow_ups"].append(e["id"])
    out.sort(key=lambda e: (e["created"] or "", e["id"]))
    return out, n


def attach_issues(cards, items, tags):
    """Each card gets from_issues (issues carded into it: "from issue …"), issues (open issues raised on it),
    follow_ups and context (the dev items riding on it); each item's cards get their tags."""
    by_id = dict((c["id"], c) for c in cards)
    for c in cards:
        c["from_issues"], c["issues"], c["follow_ups"], c["context"] = [], [], [], []
    for e in items:
        for key in ("on_card", "carded_as"):
            cid = e[key]
            e[key + "_tag"] = (tags.get(cid) or (by_id[cid]["tag"] if cid in by_id else None)) if cid else None
        short = {"id": e["id"], "alias": e["alias"], "title": e["title"], "state": e["state"]}
        if e["carded_as"] in by_id:
            by_id[e["carded_as"]]["from_issues"].append(short)
        home = by_id.get(e["on_card"] or "")
        if home is None:
            continue
        if e["kind"] == "issue" and e["state"] in ("raised", "discussing"):
            home["issues"].append(short)
        elif e["kind"] == "follow-up":
            home["follow_ups"].append(dict(short, assignees=e["assignees"]))
        elif e["kind"] == "context":
            home["context"].append(dict(short, by=e["by"], created=e["created"]))


def human_acts(items):
    """DQ-5 (human acts): every open follow-up, one entry each, urgent first, then newest first. Run after
    attach_issues (it reads each item's on_card_tag). `on` is the parent card or issue, or None."""
    by_id = dict((e["id"], e) for e in items)
    out = []
    for e in items:
        if e["kind"] != "follow-up" or e["state"] != "raised":
            continue
        p = by_id.get(e["parent"] or "")
        if e["on_card"]:
            on = {"type": "card", "id": e["on_card"], "tag": e.get("on_card_tag")}
        elif e["parent"]:
            on = {"type": "issue", "id": e["parent"], "alias": p["alias"] if p else None,
                  "title": p["title"] if p else None, "state": p["state"] if p else None}
        else:
            on = None
        out.append({"id": e["id"], "alias": e["alias"], "title": e["title"], "assignees": list(e["assignees"]),
                    "urgent": e["urgent"], "created": e["created"], "by": e["by"], "said_by": e["said_by"],
                    "session": e["session"], "quote": e["quote"], "on": on})
    out.sort(key=lambda a: a["created"] or "", reverse=True)
    out.sort(key=lambda a: not a["urgent"])
    return out


# --- marks (PF-18b (review marks)) --------------------------------------------------------------------------------

_REVIEW = []


def review_module():
    """RV-2 (review request module), loaded by path once; ImportError or OSError when it is not beside this folder."""
    if not _REVIEW:
        spec = importlib.util.spec_from_file_location("review_request", REVIEW_MODULE)
        if spec is None or spec.loader is None:
            raise ImportError("no review module at %s" % REVIEW_MODULE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _REVIEW.append(mod)
    return _REVIEW[0]


def mark_word(rec):
    """understood · question · issue · resolve · note for one mark record: its first reason, else its grammar words
    (a judgment's only: a `seen` names a note by its first reason or nothing, so an assignment is never a note)."""
    v = rec.get("verdict") if isinstance(rec, dict) else None
    if not isinstance(v, dict):
        return None
    reasons = v.get("reasons") if isinstance(v.get("reasons"), list) else []
    if reasons and reasons[0] in MARKS and (reasons[0] == NOTE) == (v.get("event") == MARKS[NOTE]["event"]):
        return reasons[0]
    for word, shape in MARKS.items():
        if word != NOTE and all(v.get(k) == want for k, want in shape.items()):
            return word
    return None


def resolves(rec):
    """The person a Resolve record names ("of:<person>"), or None."""
    v = rec.get("verdict") or {}
    for r in v.get("reasons") or []:
        if isinstance(r, str) and r.startswith(OF):
            return r[len(OF):]
    return None


def read_marks(rv, root):
    """{card id: [record, …]} of every RQ-dev-queue-<card id> item on the review plane in `root`."""
    out = {}
    for r in rv.read_records(root=root):
        item = str(r.get("item") or "")
        if item.startswith(MARK_ITEM):
            out.setdefault(item[len(MARK_ITEM):], []).append(r)
    return out


def marks_of(rv, recs):
    """[{person, mark, at, note, open?, resolved_by?, resolved_at?}] by person: each person's mark is their latest
    verdict (the review fold's latest-per-reviewer); a Question or Issue is open until a Resolve naming its raiser is
    filed after it, in a later second (the fold's latest close over that person's mark and the Resolves naming them)."""
    out = []
    for who, r in sorted(rv.fold(recs)["verdicts"].items()):
        word = mark_word(r)
        if word not in MARKS or word == "resolve":
            continue
        row = {"person": who, "mark": word, "at": utc(r.get("created")),
               "note": cut((r.get("verdict") or {}).get("note"), 300)}
        if word in FLAGS:
            closes = [x for x in recs if mark_word(x) == "resolve" and resolves(x) == who]
            close = rv.fold([r] + closes)["close"]
            # strictly later: a new flag in the same second as a Resolve stays open rather than vanish
            done = close is not None and str(close.get("created") or "") > str(r.get("created") or "")
            row["open"] = not done
            if done:
                row["resolved_by"], row["resolved_at"] = close.get("reviewer"), utc(close.get("created"))
        out.append(row)
    return out


def notes_of(recs):
    """DQ-3 (note mark): ([{person, note, at}] each person's latest note, newest first; every note, oldest first).
    Latest is the latest `created`; records sharing a second keep the order they were read in (the fold's rule)."""
    rows = sorted([r for r in recs if mark_word(r) == NOTE], key=lambda r: str(r.get("created") or ""))
    every = [{"person": r.get("reviewer"), "note": cut((r.get("verdict") or {}).get("note"), 300),
              "at": utc(r.get("created"))} for r in rows]
    latest = dict((n["person"], n) for n in every)
    return sorted(latest.values(), key=lambda n: n["at"] or "", reverse=True), every


def is_assign(rec):
    """True for a PF-18j (people data) assignment record: event seen, first reason "assign"."""
    v = rec.get("verdict") if isinstance(rec, dict) else None
    return (isinstance(v, dict) and v.get("event") == ASSIGN["event"] and isinstance(v.get("reasons"), list)
            and v["reasons"][:1] == ASSIGN["reasons"])


def newest_assign(recs):
    """The newest assignment record, or None. Newest is the latest `created`; records sharing a second keep the order
    they were read in (the review fold's rule)."""
    rows = sorted([r for r in recs if is_assign(r)], key=lambda r: str(r.get("created") or ""))
    return rows[-1] if rows else None


def assignee_of(recs):
    """PF-18j (people data): the person the newest assignment record names, or None (none, or never assigned)."""
    rec = newest_assign(recs)
    who = str(((rec or {}).get("verdict") or {}).get("note") or "").strip().lower()
    return who if who and who != NONE else None


def urgent_of(recs):
    """DQ-4 (prompts and urgent): True when the newest assignment record names an assignee and carries the reason
    word "urgent"; a later plain assign clears it, and an unassigned card is never urgent."""
    if not assignee_of(recs):
        return False
    reasons = (newest_assign(recs).get("verdict") or {}).get("reasons") or []
    return URGENT in reasons[1:]


def assigner_of(recs):
    """PF-18m (open issues only), the assigner rule: who filed the newest assignment record (its `--by`), only while
    it names an assignee; None for an unassigned card."""
    if not assignee_of(recs):
        return None
    who = str(newest_assign(recs).get("reviewer") or "").strip().lower()
    return who or None


def reviewers_of(developer, assigner=None):
    """PF-18j (people data): the two of REVIEW_TEAM who are not the developer; REVIEWERS for anyone else, or none.
    PF-18m (open issues only): the card's assigner is not one of them either (a self-assignment changes nothing)."""
    if developer in REVIEW_TEAM:
        return [p for p in REVIEW_TEAM if p != developer and p != assigner]
    return list(REVIEWERS)


def review_line(marks, reviewers=REVIEWERS):
    """Shipped's line: one entry per reviewer of the card, {person, understood} (None when unmarked), plus the mark
    when made."""
    mine = dict((m["person"], m) for m in marks)
    line = []
    for p in reviewers:
        m = mine.get(p)
        if not m:
            line.append({"person": p, "understood": None})
            continue
        e = {"person": p, "understood": m["mark"] == "understood", "mark": m["mark"], "at": m["at"]}
        if "open" in m:
            e["open"] = m["open"]
        line.append(e)
    return line


# --- the board ----------------------------------------------------------------------------------------------------

def build(root, cutoff=CUTOFF, decks=None, now=None):
    t0 = time.time()
    cutoff = utc(cutoff) or CUTOFF
    root = os.path.abspath(root)
    names = people_of(root)
    tags = read_json(os.path.join(root, ID_TAGS)) or {}
    tags = {k: v for k, v in tags.items() if isinstance(v, str) and not k.startswith("_")}
    deck_list = deck_paths(root, decks)
    cards = read_cards(root, deck_list, tags, names)
    ids = set(cards)
    req_by_card, req_by_item, n_requests = read_requests(root)
    rv, marks, marks_error = None, {}, None
    try:
        rv = review_module()
        marks = read_marks(rv, root)
    except (ImportError, OSError, ValueError, AttributeError) as exc:   # the board still reads, and says why
        rv, marks_error = None, "%s: %s" % (type(exc).__name__, str(exc)[:200])

    base_dates = [c["carded_on"] for c in cards.values() if c["family"] in BASELINE_FAMILIES and c["carded_on"]]
    first = min([cutoff[:10]] + base_dates)
    since = (datetime.date.fromisoformat(first) - datetime.timedelta(days=1)).isoformat() + "T00:00:00Z"
    log = read_log(root, since)
    authors = Authors(root)
    merged, direct, direct_by, touched = {}, {}, {}, {}
    for c in log:                                    # newest first: the first one seen is the newest
        s = c["subject"]
        for cid in merge_ids(s):
            if cid in ids:
                merged.setdefault(cid, {"sha": c["sha"][:10], "at": c["at"], "subject": cut(s, 240),
                                        "via": "merge commit"})
        m = DIRECT_RE.match(s)
        if m and m.group(1) in ids and len(c["parents"]) < 2 and m.group(1) not in direct:
            direct[m.group(1)] = {"sha": c["sha"][:10], "at": c["at"], "subject": cut(s, 240), "via": "direct commit"}
            direct_by[m.group(1)] = (c["email"], c["name"])
        m = IMPL_SUBJECT_RE.match(s)
        if m and m.group(1) in ids:
            touched.setdefault(m.group(1), c["at"])
    heading, warnings = heading_ships(root, cards)  # PF-18i (landed counts): the third ship signal

    out_cards, hidden, closed_no_build = [], set(), []
    for cid in sorted(cards, key=lambda k: (family_of(k), k)):
        c = dict(cards[cid])
        c.pop("landed", None)
        closed = c.pop("closed_no_build", False)
        history, times = [], []
        if c["carded_on"]:
            history.append({"at": utc(c["carded_on"]), "what": "carded", "by": None})
            times.append(utc(c["carded_on"]))
        reqs = req_by_card.get(cid, [])
        for r in reqs:
            history.append({"at": r["at"], "what": "dispatched", "by": r["by"], "item": r["item"]})
            times.append(r["at"])
            for w in req_by_item.get(r["item"], []):
                history.append({"at": w["at"], "what": w["status"], "by": w["by"], "item": r["item"]})
                times.append(w["at"])
        progress = None
        if reqs:
            latest = reqs[0]
            rows = req_by_item.get(latest["item"], [])
            status = rows[0]["status"] if rows else "queued"
            if status in CHIPS:
                progress = {"chip": CHIPS[status], "status": status, "item": latest["item"],
                            "at": rows[0]["at"] if rows else latest["at"], "detail": rows[0]["detail"] if rows else ""}
        m = merged.get(cid)
        # a merge commit wins over a direct commit, a direct commit over the heading's sha (PF-18i (landed counts))
        d = direct.get(cid) or (heading[cid][0] if cid in heading else None)
        if m:
            history.append({"at": m["at"], "what": "merged", "by": None, "sha": m["sha"]})
            times.append(m["at"])
        elif d:
            history.append({"at": d["at"], "what": "committed on main", "by": None, "sha": d["sha"]})
            times.append(d["at"])
        if cid in touched:
            times.append(touched[cid])
        times = [t for t in times if t]
        c["last_activity"] = max(times) if times else None
        if m:
            c["merged"], c["state"] = m, "shipped"
        elif progress and not (d and d["at"] and d["at"] > (progress["at"] or "")):
            c["merged"], c["state"] = None, "in-progress"   # a request newer than the commit, either kind
        elif d:
            c["merged"], c["state"] = d, "shipped"
        else:
            c["merged"], c["state"] = None, "up-next"
        c["progress"] = progress if c["state"] == "in-progress" else None
        if c["state"] != "up-next":
            c["pending"] = None
        if not c["built_by"]:                        # PF-18g (built by): rules (b), (c), (d)
            filed = next((r["filer"] for r in reqs if r["filer"] and r["filer"] != "mini-worker"), None)
            if filed:
                c["built_by"], c["built_by_from"] = filed, "request"
            elif not reqs and c["state"] == "shipped" and c["merged"]["via"] in ("direct commit", "heading"):
                who = direct_by[cid] if c["merged"]["via"] == "direct commit" else heading[cid][1]
                c["built_by"], c["built_by_from"] = authors(*who), "commit"
        early = c["state"] == "shipped" and (c["merged"]["at"] or "") < cutoff
        if early and c["family"] not in EARLY_REVIEW_FAMILIES:
            continue                                 # PF-18f (earlier PF review): another family's earlier card
        # PF-18j (people data): the assignee (newest assign record), the developer (assignee, else built by) and the
        # card's own two reviewers
        recs = marks.get(cid, [])
        c["assignee"] = assignee_of(recs)
        c["urgent"] = urgent_of(recs)                # DQ-4 (prompts and urgent): rides the assign record
        c["developer"] = c["assignee"] or c["built_by"]
        # PF-18k (people views page): a private card asks no one for a mark
        # PF-18m (open issues only), the assigner rule: whoever assigned the card does not review it
        c["reviewers"] = [] if c["private"] else reviewers_of(c["developer"], assigner_of(recs))
        # PF-18j (people data): marks on every column; a Question or Issue on an Up next, In progress or Shipped card
        c["marks"] = marks_of(rv, recs) if rv is not None else []
        if c["state"] != "shipped" and not c["marks"]:
            c["marks"] = None                        # as before: today's page shows mark buttons where marks is a list
        for m in c["marks"] or []:
            history.append({"at": m["at"], "what": "marked " + m["mark"], "by": m["person"]})
            if m.get("resolved_at"):
                history.append({"at": m["resolved_at"], "what": "resolved", "by": m["resolved_by"]})
        # DQ-3 (note mark): each person's latest note on the tile; every note in the history. A note moves nothing:
        # not the column, the review line, Flagged or anyone's review
        c["notes"], every = notes_of(recs) if rv is not None else ([], [])
        for n in every:
            history.append({"at": n["at"], "what": "noted", "by": n["person"], "note": n["note"]})
        c["column"], c["review"] = c["state"], None
        if c["state"] == "shipped":
            # PF-18f (earlier PF review): a card shipped before the cutoff gets the same rules as any shipped card;
            # PF-18b (review marks): both of the card's reviewers Understood → Reviewed
            c["review"] = review_line(c["marks"], c["reviewers"])
            if rv is not None and all(r["understood"] for r in c["review"]):
                c["column"] = "reviewed"
        if any(m.get("open") for m in c["marks"] or []):
            # an open Question or Issue → Flagged, at its stage; a Resolve returns the card to its column. Nothing
            # waits on a mark: the card's state, chips and dispatch are untouched
            c["column"], c["flag_stage"] = "flagged", FLAG_STAGES[c["state"]]
        history.sort(key=lambda h: h["at"] or "", reverse=True)
        c["history"] = history[:20]
        if c["family"] in BASELINE_FAMILIES or (c["last_activity"] or "") >= cutoff:
            if cid in HIDDEN_CARDS:
                hidden.add(cid)                      # PF-18h (hidden cards): off the board by the setting
                continue
            if closed:
                closed_no_build.append(cid)          # PF-18m (open issues only): off the board by its heading
                continue
            out_cards.append(c)

    files = read_files(root, cutoff)         # cutoff is a full UTC time: git reads a bare date at today's clock
    direct_work = []
    for c in log:
        if (c["at"] or "") < cutoff or len(c["parents"]) > 1:
            continue
        s = c["subject"]
        if MACHINE_RE.match(s) or s.startswith("Merge ") or names_a_card(s, ids):
            continue
        areas = []
        for f in files.get(c["sha"], []):
            a = area_of(f)
            if a not in areas:
                areas.append(a)
        direct_work.append({"sha": c["sha"][:10], "person": authors(c["email"], c["name"]), "at": c["at"],
                            "what": cut(s, 240), "areas": areas[:4]})

    issues, n_tasks = dev_items(root)
    attach_issues(out_cards, issues, tags)
    acts = human_acts(issues)                        # DQ-5 (human acts): drawn in each assignee's Up next group

    # PF-18h (hidden cards): a hidden card's decisions still show; so do a closed-no-build card's (PF-18m (open issues
    # only))
    shown = set(c["id"] for c in out_cards) | hidden | set(closed_no_build)
    decisions = []
    for d in read_decisions(root, names, tags, ids):
        d["in_stream"] = d["date"] >= cutoff[:10]
        if d["in_stream"] or any(x["id"] in shown for x in d["cards"]):
            decisions.append(d)

    head = ""
    try:
        head = git(root, "rev-parse", "--short=10", "HEAD").strip()
    except (RuntimeError, OSError, subprocess.SubprocessError):
        pass
    return {
        "schema": 1, "kind": "dev-queue", "card": "PF-18 (dev-queue view)",
        "now": utc(now) if now else datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cutoff": cutoff, "baseline_families": list(BASELINE_FAMILIES),
        "early_review_families": list(EARLY_REVIEW_FAMILIES), "head": head,
        "hidden_cards": len(hidden),                 # PF-18h (hidden cards): the count only, never the list
        "closed_no_build": closed_no_build,          # PF-18m (open issues only): the list, by id
        "people": names, "reviewers": list(REVIEWERS),
        # PF-18j (people data): each card's own `reviewers` come from this team; `reviewers` above is the fallback pair
        "review_team": list(REVIEW_TEAM), "flag_stages": dict(FLAG_STAGES),
        # the card each of these columns came with; with PF-18b (review marks) in, neither waits any more
        "columns_after": {"issue-queue": "PF-18c (issue queue)", "flagged": "PF-18b (review marks)"},
        "marks": {"card": "PF-18b (review marks)", "words": list(MARKS), "flags": list(FLAGS),
                  "resolvers": list(RESOLVERS), "item": MARK_ITEM + "<card id>", "note_max": NOTE_MAX,
                  "error": marks_error},
        "cards": out_cards, "issues": issues, "acts": acts, "direct_work": direct_work, "decisions": decisions,
        "sources": {"decks": deck_list, "cards_read": len(cards), "request_files": n_requests,
                    "task_files": n_tasks, "tasks_dir": TASKS, "dev_tag": DEV_TAG,
                    "commits_read": len(log), "log_since": since, "decision_log": DECISION_LOG,
                    "review_items": len(marks), "machine_prefixes": list(MACHINE_PREFIXES),
                    "warnings": warnings},
        "elapsed_s": round(time.time() - t0, 2),
    }


def board_card(rv, root, card, cutoff, now):
    """The card as the board shows it; Refused (nothing filed) for a bad id, a hidden card or a card off the board."""
    card = str(card or "").strip()
    if not re.fullmatch(ID, card):
        raise rv.Refused("%r is not a card id. Nothing was filed." % card[:40])
    if card in HIDDEN_CARDS:
        raise rv.Refused("%s is hidden by setting (HIDDEN_CARDS, PF-18h (hidden cards)): not on the board, so it takes "
                         "no mark. Nothing was filed." % card)
    doc = build(root, cutoff, now=now)
    if card in doc["closed_no_build"]:
        raise rv.Refused("%s is closed with no build (its heading says %s, PF-18m (open issues only)): not on the "
                         "board, so it takes no mark. Nothing was filed." % (card, CLOSED_NO_BUILD))
    return card, dict((x["id"], x) for x in doc["cards"]).get(card)


def assign(root, card, person, by, cutoff=CUTOFF, env=None, now=None, commit=True, urgent=False):
    """PF-18j (people data): ONE review record naming a card's assignee (one of REVIEW_TEAM, or none), item
    RQ-dev-queue-<card>, filed by the review module's file_record like a mark; the newest one wins. developer assigns in
    Claude; no page button. DQ-4 (prompts and urgent): `urgent` adds the reason word "urgent" to the same record; an
    unassigned card has no priority, so none with urgent is refused. The review module's Refused names why, before
    anything is written."""
    rv = review_module()
    by = rv.people(by, "--by")[0]
    who = str(person or "").strip().lower()
    if who not in REVIEW_TEAM + (NONE,):
        raise rv.Refused("%r is not an assignee (%s, or %s). Nothing was filed."
                         % (who[:40], " | ".join(REVIEW_TEAM), NONE))
    if urgent and who == NONE:
        raise rv.Refused("an unassigned card has no priority: --urgent needs an assignee (%s). Nothing was filed."
                         % " | ".join(REVIEW_TEAM))
    card, c = board_card(rv, root, card, cutoff, now)
    if not c:
        raise rv.Refused("%s is not a card on the board: an assignee is for a card on the board. Nothing was filed."
                         % card)
    verdict = dict(ASSIGN, reasons=list(ASSIGN["reasons"]) + ([URGENT] if urgent else []), note=who)
    return rv.file_record(MARK_ITEM + card, verdict, by, root=root, env=env, now=now, commit=commit)


def mark(root, card, word, by, note="", of=None, cutoff=CUTOFF, env=None, now=None, commit=True):
    """PF-18b (review marks): ONE review record for one person's mark on one card on the board, filed by the review
    module's file_record; returns what it returned. Understood only on a shipped card (shipped since the cutoff, or
    an EARLY_REVIEW_FAMILIES card shipped before it: PF-18f (earlier PF review)); Question, Issue and Resolve on an Up
    next, In progress or Shipped card too (PF-18j (people data)); Note on any card, its one line required (DQ-3 (note
    mark)). The review module's Refused names why, before anything is written."""
    rv = review_module()
    word = str(word or "").strip().lower()
    if word not in MARKS:
        raise rv.Refused("%r is not a mark (%s). Nothing was filed." % (word[:40], " | ".join(MARKS)))
    by = rv.people(by, "--by")[0]
    if word == NOTE and re.search(r"[\r\n]", str(note or "")):
        raise rv.Refused("a note is one line. Nothing was filed.")
    note =" ".join(str(note or "").split())
    if len(note) > NOTE_MAX:
        raise rv.Refused("the note is %d characters; at most %d. Nothing was filed." % (len(note), NOTE_MAX))
    if word == NOTE and not note:
        raise rv.Refused("a note needs its words (--note, one line, at most %d characters). Nothing was filed."
                         % NOTE_MAX)
    card, c = board_card(rv, root, card, cutoff, now)
    if not c:
        raise rv.Refused("%s is not a card shipped since %s, nor a %s card shipped before it, nor an Up next or In "
                         "progress card: marks are for cards on the board. Nothing was filed."
                         % (card, utc(cutoff) or cutoff, "/".join(EARLY_REVIEW_FAMILIES) or "reviewed-family"))
    if word == "understood" and c["state"] != "shipped":
        raise rv.Refused("%s is not a card shipped since %s, nor a %s card shipped before it: Understood is for "
                         "shipped cards on the board (a Question or Issue fits any card). Nothing was filed."
                         % (card, utc(cutoff) or cutoff, "/".join(EARLY_REVIEW_FAMILIES) or "reviewed-family"))
    verdict = dict(MARKS[word], reasons=[word])
    if word == "resolve":
        flags = [m["person"] for m in c["marks"] or [] if m.get("open")]
        who = rv.people(of, "--of")[0] if of else (by if by in flags or by not in RESOLVERS or len(flags) != 1
                                                  else flags[0])
        if who not in flags:
            # DQ-3 (note mark): a note is never open, so a Resolve of one lands here too
            raise rv.Refused("%s has no open question or issue from %s to resolve (open: %s): nothing to resolve "
                             "(a note is never open). Nothing was filed." % (card, who, ", ".join(flags) or "none"))
        if by != who and by not in RESOLVERS:
            raise rv.Refused("Resolve belongs to whoever raised the mark (%s) and %s, not %s. Nothing was filed."
                             % (who, " and ".join(RESOLVERS), by))
        verdict["reasons"].append(OF + who)
    elif of:
        raise rv.Refused("--of names whose mark a Resolve resolves; %s takes none. Nothing was filed." % word)
    if note:
        verdict["note"] = note
    return rv.file_record(MARK_ITEM + card, verdict, by, root=root, env=env, now=now, commit=commit)


def done(root, task, by, note="", now=None, commit=True):
    """DQ-8 (act panel): tick one human act (an open dev follow-up) done through dev_issues.py's own `done` — the
    who-may rule (an assignee of the follow-up, or developer) lives there — then commit the records it wrote, by path.
    (code, the line said, the refusal or None)."""
    import dev_issues                                   # it imports this file: loaded here, never at the top
    out, err = io.StringIO(), io.StringIO()
    argv = ["done", str(task or ""), "--by", str(by or ""), "--root", root, "--json"] + (
        ["--note", note] if note else []) + (["--now", now] if now else [])
    code = dev_issues.main(argv, out=out, err=err)
    if code != 0:
        why = err.getvalue().strip()
        return code, "", why.split("refused — ", 1)[-1] if "refused — " in why else why
    got = json.loads(out.getvalue())
    line = (got.get("lines") or [""])[0]
    if commit and got.get("paths"):
        msg = "review: %s ticked done by %s on the dev-queue page" % (task, by)
        try:
            git(root, "add", "--", *got["paths"])
            git(root, "commit", "-q", "-m", msg, "--", *got["paths"])
            line += " (committed)"
        except (RuntimeError, OSError, subprocess.SubprocessError):
            line += " (not committed)"
    return 0, line, None


def mark_main(argv):
    ap = argparse.ArgumentParser(prog="dev_queue.py mark", description="PF-18b (review marks): one mark, one record")
    ap.add_argument("card")
    ap.add_argument("word", help=" | ".join(tuple(MARKS) + ACT_WORDS))
    ap.add_argument("--by", required=True, help="the person marking (the page server passes its own)")
    ap.add_argument("--note", default="", help="one line, at most %d characters (required for note)" % NOTE_MAX)
    ap.add_argument("--of", default=None, help="Resolve only: whose question or issue (default: your own)")
    ap.add_argument("--root", default=None, help="the repo (default: the repo this file is in)")
    ap.add_argument("--cutoff", default=CUTOFF)
    ap.add_argument("--no-commit", action="store_true", help="write the record; no git commit")
    x = ap.parse_args(argv)
    root = x.root or str(paths.repo(HERE))
    if x.word.strip().lower() in ACT_WORDS:             # DQ-8 (act panel): Done on a human act, never a review record
        if x.of:
            sys.stderr.write("REFUSED: --of names whose mark a Resolve resolves; done takes none. Nothing was filed.\n")
            return 2
        code, line, why = done(root, x.card, x.by, note=x.note, commit=not x.no_commit)
        if code != 0:
            sys.stderr.write("REFUSED: %s. Nothing was filed.\n" % why.rstrip(".") if code == 2 else
                             "dev_queue done: %s\n" % why)
            return code
        sys.stdout.write("%s ticked done by %s · %s\n" % (x.card, x.by, line))
        return 0
    try:
        rv = review_module()
    except (ImportError, OSError) as exc:
        sys.stderr.write("dev_queue mark: the review module cannot load: %s\n" % exc)
        return 2
    try:
        out = mark(root, x.card, x.word, x.by, note=x.note, of=x.of, cutoff=x.cutoff, commit=not x.no_commit)
    except rv.Refused as exc:
        sys.stderr.write("REFUSED: %s\n" % exc)
        return 2
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        sys.stderr.write("dev_queue mark: %s\n" % exc)
        return 1
    v = out["record"]["verdict"]
    what = x.word.lower() + (" of " + resolves(out["record"]) if v.get("event") == "close" else "")
    sys.stdout.write("%s marked %s by %s · %s via %s%s\n" % (
        x.card, what, out["record"]["reviewer"], out["item"], out["route"],
        "" if out["route"] == "api" else (" (committed)" if out["committed"] else " (not committed)")))
    return 0


def assign_main(argv):
    ap = argparse.ArgumentParser(prog="dev_queue.py assign", description="PF-18j (people data): one assignee, one "
                                 "record; the newest wins")
    ap.add_argument("card")
    ap.add_argument("person", help=" | ".join(REVIEW_TEAM + (NONE,)))
    ap.add_argument("--urgent", action="store_true", help="DQ-4 (prompts and urgent): someone is blocked now, or "
                    "money or a customer is at risk; a later assign without it clears it")
    ap.add_argument("--by", required=True, help="the person assigning")
    ap.add_argument("--root", default=None, help="the repo (default: the repo this file is in)")
    ap.add_argument("--cutoff", default=CUTOFF)
    ap.add_argument("--no-commit", action="store_true", help="write the record; no git commit")
    x = ap.parse_args(argv)
    root = x.root or str(paths.repo(HERE))
    try:
        rv = review_module()
    except (ImportError, OSError) as exc:
        sys.stderr.write("dev_queue assign: the review module cannot load: %s\n" % exc)
        return 2
    try:
        out = assign(root, x.card, x.person, x.by, cutoff=x.cutoff, commit=not x.no_commit, urgent=x.urgent)
    except rv.Refused as exc:
        sys.stderr.write("REFUSED: %s\n" % exc)
        return 2
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        sys.stderr.write("dev_queue assign: %s\n" % exc)
        return 1
    sys.stdout.write("%s assigned to %s%s by %s · %s via %s%s\n" % (
        x.card, out["record"]["verdict"]["note"], " (urgent)" if x.urgent else "", out["record"]["reviewer"],
        out["item"], out["route"],
        "" if out["route"] == "api" else (" (committed)" if out["committed"] else " (not committed)")))
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ["mark"]:
        return mark_main(argv[1:])
    if argv[:1] == ["assign"]:
        return assign_main(argv[1:])
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=None, help="the repo to read (default: the repo this file is in)")
    ap.add_argument("--cutoff", default=CUTOFF)
    ap.add_argument("--deck", action="append", default=None, help="a deck glob under the root (repeatable); "
                    "replaces the registry and the default globs")
    ap.add_argument("--now", default=None, help="the time to stamp (default: now)")
    x = ap.parse_args(argv)
    root = x.root or str(paths.repo(HERE))
    try:
        doc = build(root, x.cutoff, x.deck, x.now)
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        sys.stderr.write("dev_queue: %s\n" % exc)
        return 2
    sys.stdout.write(json.dumps(doc, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
