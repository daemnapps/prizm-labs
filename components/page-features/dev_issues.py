#!/usr/bin/env python3
"""PF-18c (issue queue): file and move the dev-queue's issues. An issue is a PM task tagged `dev` (developer, 2026-10-29:
"issues as PM tasks"), written as the tasks kind's own event records into platform/data/records/tasks/ (envelope and
names as that folder's README and the kind manifest platform/data/kinds/tasks.json say); never a new kind.

    python3 components/page-features/dev_issues.py file <items.json | -> --by <person>
    python3 components/page-features/dev_issues.py discussing <task> --by <person> [--with <person> …] [--note <why>]
    python3 components/page-features/dev_issues.py card <task> <card id> --by <person> [--note <why>]
    python3 components/page-features/dev_issues.py wont <task> --reason <why> --by <person>
    python3 components/page-features/dev_issues.py done <follow-up task> --by <person> [--note <why>]
    python3 components/page-features/dev_issues.py fixed <issue task> <sha> --by <person> [--note <why>]
    python3 components/page-features/dev_issues.py fix <issue task> <text> --by <person>
    python3 components/page-features/dev_issues.py priority <follow-up task> --urgent|--not-urgent --by <person>
    python3 components/page-features/dev_issues.py show
  every command: [--root <repo>] [--now <ISO time>] [--json]; every writing command: [--dry-run] (writes nothing)

`file` is the main way in: a Claude step hands it a session's pending list, ALREADY SORTED (one item per thing: the
29 Oct list split item 11 into an issue, 11a, and a follow-up, 11b). A JSON list; each item:
    kind      issue | follow-up | context
    title     one line (a context note's title is the fact itself)
    quote     the person's own words, kept verbatim
    session   the source session (e.g. 545f20)
    parent    a bare card id (PF-14 for PF-14 (page server)), a dev task id (TSK-…, or its T-<n>), another item's `ref`
              in this list, or none
    person    follow-up: who does it (required), one id or a list of ids (DQ-5 (human acts): the act shows in
              each one's Up next group); issue: who it is handed to (optional, one id)
    said_by   who the quote is from (default: --by)
    ref       a label other items' `parent` may name (11a)
    detail    optional longer text
    fixes     issue only: proposed fixes, a list of lines
    urgent    follow-up only: true files it Urgent (its `priority` "urgent"; DQ-5 (human acts))
Any bad item refuses the whole list (exit 2, every problem named, nothing written). Issues are filed first, so a
follow-up or note can name an issue of the same list.

What each word writes (one record per event, one second apart, names `<stamp>--<by>--<task>[--<event>].json`):
    issue      create, tags dev + issue, status proposed (Raised); each fix a comment "Proposed fix: …"
    follow-up  create, tags dev + follow-up, status todo with its person (Raised); on an issue `parent` = the issue,
               on a card a card link
    context    on an issue: a comment "Context: …"; on a card: a create tagged dev + context, status done, with a
               card link (a card is not a task, so the fact needs a record of its own); never parentless
    discussing status in_progress (+ assign with --with)                 Raised → Discussing
    card       link {type: card, ref: <deck>#<id>}, then status done     → Carded; the card shows "from issue …"
    wont       status dropped, the reason in its note                    → Won't do (reason kept)
    done       a follow-up's status done                                 ticked done (a follow-up is never carded);
               only by an assignee of the follow-up or developer (DQ-8 (act panel), Resolve's rule), anyone else refused
    fixed      a comment "Fixed at commit <full sha>", then status done   → Fixed (PF-18l (fixed move)): an issue
               with the note "fixed at <short sha>: <subject>"           fixed by a commit on HEAD with no card; the
               (the tasks kind allows no commit link type)               sha must resolve to a commit on HEAD
    fix        a comment "Proposed fix: …" on an open issue
    priority   DQ-5 (human acts): an edit of the follow-up's `priority` field, "urgent" (--urgent) or "" (--not-urgent);
               the newest edit wins; an open follow-up only (a card's Urgent rides its assign, DQ-4 (prompts and
               urgent))
A move starts at the later of --now and one second after the newest record of the task it moves (PF-18d (stamp
order)): the fold reads a task's rows in created order and skips all before the create, so a move stamped before a
batch's later creates would vanish. A start more than 60 s past --now is refused ("this task has records from the
future"), nothing written.
It never commits or pushes: the caller commits the paths it prints. The mini's task-index tick (WM-120 (machine tasks
indexed)) indexes each new task for the PM board; components/page-features/dev_queue.py reads them for the page.
Exit 0 filed (or would file), 2 refused, 3 unreadable input. Stdlib only, Python 3.9.
"""
import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dev_queue  # noqa: E402  the reader: the fold, the decks, the people (it puts run-kit on the path)
from run_kit import paths  # noqa: E402  the one workspace locator (builder card rule 3)

VIA = "page-features/dev_issues"
SOURCE = "ai-triage"                 # a tasks `source` word: a session's list, sorted by Claude
STREAM = "page-features"
ITEM_KEYS = ("kind", "title", "quote", "session", "source_session", "parent", "person", "said_by", "ref", "detail",
             "fixes", "urgent")
OPEN = ("raised", "discussing")
KIND_REFUSALS = {"discussing": "it goes Raised → Done, never Discussing", "card": "a follow-up is never carded",
                 "fix": "only an issue holds proposed fixes", "fixed": "`done` is its move, never Fixed"}
SHORT_SHA = 10
SLUG_MAX = 40
AHEAD_MAX = datetime.timedelta(seconds=60)   # PF-18d (stamp order): a move never stamped further past now than this


def now_utc(now=None):
    stamp = dev_queue.utc(now) if now else None
    if now and not stamp:
        raise ValueError("--now %r is not an ISO time" % now)
    t = (datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc) if stamp
         else datetime.datetime.now(datetime.timezone.utc))
    return t.replace(microsecond=0)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def slug(title):
    s = re.sub(r"[^a-z0-9]+", "-", str(title).lower()).strip("-")[:SLUG_MAX].strip("-")
    return s or "item"


def body_of(detail, quote, said_by, session):
    """The task body: the detail, then the source session and the quote verbatim (dev_queue.split_body reads it)."""
    tail = "Source session: %s\nQuote (%s):\n%s" % (session, said_by, quote)
    return (detail.strip() + "\n\n" + tail) if detail and detail.strip() else tail


def record(by, item, verdict):
    return {"schema": 1, "kind": "tasks", "reviewer": by, "item": item, "verdict": verdict, "notes": "",
            "created": None, "via": VIA}


def record_name(r):
    event = r["verdict"]["event"]
    return "%s--%s--%s%s.json" % (r["created"].replace("-", "").replace(":", ""), r["reviewer"], r["item"],
                                  "" if event == "create" else "--" + event)


class Board(object):
    """What is on disk: the people, the cards and the dev tasks."""

    def __init__(self, root):
        self.root = root
        self.people = dev_queue.people_of(root)
        tags = dev_queue.read_json(os.path.join(root, dev_queue.ID_TAGS)) or {}
        self.tags = dict((k, v) for k, v in tags.items() if isinstance(v, str) and not k.startswith("_"))
        self.cards = dev_queue.read_cards(root, dev_queue.deck_paths(root), self.tags, self.people)
        items, _n = dev_queue.dev_items(root)
        self.items = dict((e["id"], e) for e in items)
        self.aliases = dict((e["alias"], e["id"]) for e in items if e["alias"])

    def task(self, ref):
        tid = self.aliases.get(ref, ref)
        return self.items.get(tid)

    def card_ref(self, cid):
        c = self.cards.get(cid)
        return "%s#%s" % (c["deck"], cid) if c else None

    def card_words(self, cid):
        tag = self.tags.get(cid) or (self.cards.get(cid) or {}).get("tag")
        return "%s (%s)" % (cid, tag) if tag else cid


# --- file: a session's sorted list ----------------------------------------------------------------------------------

def check_items(items, board, by):
    """[problem, …] for the whole list; empty means every item can be filed."""
    out = []
    if not isinstance(items, list) or not items:
        return ["the input is not a non-empty JSON list of items"]
    refs = {}
    for i, it in enumerate(items, 1):
        if isinstance(it, dict) and isinstance(it.get("ref"), str) and it["ref"].strip():
            if it["ref"] in refs:
                out.append("item %d: ref %r is used twice" % (i, it["ref"]))
            refs[it["ref"]] = it
    for i, it in enumerate(items, 1):
        name = "item %d" % i
        if not isinstance(it, dict):
            out.append("%s: not an object" % name)
            continue
        if it.get("ref"):
            name += " (%s)" % it["ref"]
        extra = sorted(set(it) - set(ITEM_KEYS))
        if extra:
            out.append("%s: unknown key%s %s" % (name, "s" if len(extra) > 1 else "", ", ".join(extra)))
        kind = it.get("kind")
        if kind not in dev_queue.ITEM_KINDS:
            out.append("%s: kind %r is not one of %s" % (name, kind, " | ".join(dev_queue.ITEM_KINDS)))
            continue
        for key in ("title", "quote"):
            if not (isinstance(it.get(key), str) and it[key].strip()):
                out.append("%s: no %s" % (name, key))
        session = it.get("session", it.get("source_session"))
        if not (isinstance(session, str) and session.strip()):
            out.append("%s: no source session" % name)
        person = it.get("person")
        if isinstance(person, list) and kind != "follow-up":
            out.append("%s: only a follow-up takes a list of people" % name)
        elif isinstance(person, list) and not all(isinstance(p, str) and p for p in person):
            out.append("%s: person is not a list of person ids" % name)
        elif isinstance(person, list) and len(set(person)) != len(person):
            out.append("%s: person names someone twice" % name)
        for key in ("person", "said_by"):
            for who in (it.get(key) if key == "person" and isinstance(person, list) else [it.get(key)]):
                if who not in (None, "") and (not isinstance(who, str) or who not in board.people):
                    out.append("%s: %s %r has no team/people/<name>/identity.json" % (name, key, who))
        if kind == "follow-up" and not person:
            out.append("%s: a follow-up needs its person" % name)
        if it.get("urgent") not in (None, False):
            if kind != "follow-up":
                out.append("%s: only a follow-up is filed urgent here (a card's Urgent rides its assign)" % name)
            elif it["urgent"] is not True:
                out.append("%s: urgent is true or false" % name)
        if it.get("fixes") not in (None, []):
            if kind != "issue":
                out.append("%s: only an issue holds proposed fixes" % name)
            elif not (isinstance(it["fixes"], list) and all(isinstance(f, str) and f.strip() for f in it["fixes"])):
                out.append("%s: fixes is not a list of lines" % name)
        if it.get("detail") not in (None, "") and not isinstance(it["detail"], str):
            out.append("%s: detail is not text" % name)
        parent = it.get("parent")
        if parent in (None, "", "none"):
            if kind == "context":
                out.append("%s: a context note rides on its issue or card; it has no parent" % name)
            continue
        if not isinstance(parent, str):
            out.append("%s: parent is not text" % name)
            continue
        if parent in refs:
            other = refs[parent]
            if other is it or other.get("kind") != "issue":
                out.append("%s: parent %r is not an issue of this list" % (name, parent))
            elif kind == "issue":
                out.append("%s: an issue on an issue is a proposed fix or a context note" % name)
        elif dev_queue.ID_RE.fullmatch(parent) and not parent.startswith("T-"):
            if parent not in board.cards:
                out.append("%s: card %s is in no deck" % (name, parent))
        else:
            t = board.task(parent)
            if t is None:
                out.append("%s: parent %r is no card, no dev task and no ref of this list" % (name, parent))
            elif t["kind"] != "issue":
                out.append("%s: parent %s is a %s, not an issue" % (name, t["id"], t["kind"]))
            elif kind == "issue":
                out.append("%s: an issue on an issue is a proposed fix or a context note" % name)
    if by not in board.people:
        out.append("--by %r has no team/people/<name>/identity.json" % by)
    return out


def plan_file(items, board, by, start):
    """(records, [line, …]) for a checked list, stamped from `start` one second apart. Pure."""
    clock = [start]
    recs, lines = [], []

    def add(r):
        r["created"] = iso(clock[0])
        clock[0] += datetime.timedelta(seconds=1)
        recs.append(r)
        return r

    order = sorted(range(len(items)), key=lambda i: (dev_queue.ITEM_KINDS.index(items[i]["kind"]), i))
    made = {}                                                           # ref → new task id

    def resolve(parent):
        if parent in (None, "", "none"):
            return None, None
        if parent in made:
            return "issue", made[parent]
        if parent in board.cards:
            return "card", parent
        return "issue", board.task(parent)["id"]

    for i in order:
        it = items[i]
        kind, title = it["kind"], " ".join(it["title"].split())
        session = (it.get("session") or it.get("source_session")).strip()
        said_by = it.get("said_by") or by
        ptype, pid = resolve(it.get("parent"))
        label = it.get("ref") or str(i + 1)
        on = (" on " + (board.card_words(pid) if ptype == "card" else pid)) if pid else ""
        if kind == "context" and ptype == "issue":
            add(record(by, pid, {"event": "comment", "text": dev_queue.CONTEXT_PREFIX + title}))
            lines.append("context    %-5s comment on %s: %s" % (label, pid, title))
            continue
        tid = "TSK-%s-%s" % (clock[0].strftime("%Y%m%d%H%M%S"), slug(title))
        tags = [dev_queue.DEV_TAG, kind]
        status = {"issue": "proposed", "follow-up": "todo", "context": "done"}[kind]
        person = it.get("person") or ""
        assignees = list(person) if isinstance(person, list) else [person] if person else []
        person = ", ".join(assignees)
        item = {"id": tid, "title": title, "body": body_of(it.get("detail") or "", it["quote"], said_by, session),
                "status": status, "assignees": assignees, "requested_by": by, "source": SOURCE, "stream": STREAM,
                "priority": dev_queue.PRIORITY_URGENT if it.get("urgent") is True else "", "due": "",
                "links": [{"type": "card", "ref": board.card_ref(pid)}] if ptype == "card" else [],
                "parent": pid if ptype == "issue" else "", "tags": tags, "created": None, "by": by}
        r = add(record(by, tid, {"event": "create", "item": item}))
        item["created"] = r["created"]
        if it.get("ref"):
            made[it["ref"]] = tid
        word = {"issue": "Raised", "follow-up": "Urgent" if it.get("urgent") is True else "Raised",
                "context": "fact"}[kind]
        lines.append("%-10s %-5s %s  %s%s%s: %s" % (kind, label, tid, word, " with " + person if person else "", on,
                                                   title))
        for fix in it.get("fixes") or []:
            add(record(by, tid, {"event": "comment", "text": dev_queue.FIX_PREFIX + " ".join(fix.split())}))
            lines.append("  fix      %-5s comment on %s: %s" % (label, tid, " ".join(fix.split())))
    return recs, lines


# --- moves ----------------------------------------------------------------------------------------------------------

def commit_on_head(root, sha):
    """(full sha, subject) of `sha` when it resolves to a commit reachable from HEAD (PF-18l (fixed move)), else raises
    ValueError naming why."""
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", sha or ""):
        raise ValueError("%r is not a commit sha (7 to 40 hex characters)" % sha)
    try:
        full = dev_queue.git(root, "rev-parse", "--verify", "--quiet", sha + "^{commit}").strip()
    except (RuntimeError, OSError, dev_queue.subprocess.SubprocessError):
        raise ValueError("%s is no commit in %s" % (sha, root))
    try:
        dev_queue.git(root, "merge-base", "--is-ancestor", full, "HEAD")
    except (RuntimeError, OSError, dev_queue.subprocess.SubprocessError):
        raise ValueError("commit %s is not on HEAD: only a commit on main fixes an issue" % full[:SHORT_SHA])
    subject = " ".join(dev_queue.git(root, "log", "-1", "--format=%s", full).split())
    return full, subject


def plan_move(board, word, ref, by, note="", card=None, with_people=None, text=None, commit=None, urgent=None):
    """(records, line) for one move, or raises ValueError naming why it is refused. `fixed` takes `commit`, the
    (full sha, subject) commit_on_head resolved; `priority` takes `urgent`, True or False (DQ-5 (human acts))."""
    if by not in board.people:
        raise ValueError("--by %r has no team/people/<name>/identity.json" % by)
    t = board.task(ref)
    if t is None:
        raise ValueError("%s is no dev task (tasks tagged %s under %s)" % (ref, dev_queue.DEV_TAG, dev_queue.TASKS))
    tid, kind, state = t["id"], t["kind"], t["state"]
    if kind == "context":
        raise ValueError("%s is a context note: a fact, nothing moves it" % tid)
    if kind != "issue" and word in KIND_REFUSALS:
        raise ValueError("%s is a follow-up: %s" % (tid, KIND_REFUSALS[word]))
    if kind != "follow-up" and word == "done":
        raise ValueError("%s is an issue: it is carded, Fixed or Won't do, never ticked done" % tid)
    if kind != "follow-up" and word == "priority":
        raise ValueError("%s is an issue: only a follow-up takes --urgent here (a card's Urgent rides its assign, "
                         "DQ-4 (prompts and urgent))" % tid)
    if state not in OPEN:
        raise ValueError("%s is %s already: only a Raised or Discussing %s moves" % (tid, state, kind))
    note = " ".join((note or "").split())
    if word == "discussing":
        recs = []
        if with_people:
            bad = [p for p in with_people if p not in board.people]
            if bad:
                raise ValueError("--with %s: no team/people/<name>/identity.json" % ", ".join(bad))
            recs.append(record(by, tid, {"event": "assign", "assignees": list(with_people)}))
        recs.append(record(by, tid, {"event": "status", "to": "in_progress", "note": note or "Discussing"}))
        return recs, "%s  Raised → Discussing%s" % (tid, " with " + ", ".join(with_people) if with_people else "")
    if word == "card":
        if card not in board.cards:
            raise ValueError("card %s is in no deck: card it first, then link the issue" % card)
        say = "carded as " + board.card_words(card)
        return ([record(by, tid, {"event": "link", "add": {"type": "card", "ref": board.card_ref(card)}}),
                 record(by, tid, {"event": "status", "to": "done", "note": say + (" — " + note if note else "")})],
                "%s  → Carded: %s shows \"from issue %s\"" % (tid, board.card_words(card), t["title"]))
    if word == "wont":
        if not note:
            raise ValueError("Won't do keeps its reason: give --reason")
        return ([record(by, tid, {"event": "status", "to": "dropped", "note": note})],
                "%s  → Won't do: %s" % (tid, note))
    if word == "done":
        # DQ-8 (act panel): Resolve's pattern (feature 23): an assignee of the follow-up, or developer, and no one else
        if by not in t["assignees"] and by not in dev_queue.RESOLVERS:
            raise ValueError("only an assignee of %s (%s) or %s may tick it done, not %s"
                             % (tid, ", ".join(t["assignees"]) or "no one assigned", " or ".join(dev_queue.RESOLVERS),
                                by))
        return ([record(by, tid, {"event": "status", "to": "done", "note": note or "ticked done"})],
                "%s  Raised → Done" % tid)
    if word == "fixed":
        full, subject = commit
        say = "fixed at %s: %s" % (full[:SHORT_SHA], subject)
        return ([record(by, tid, {"event": "comment", "text": dev_queue.FIXED_COMMENT + full}),
                 record(by, tid, {"event": "status", "to": "done", "note": say + (" — " + note if note else "")})],
                "%s  → Fixed at %s · %s" % (tid, full[:SHORT_SHA], subject))
    if word == "priority":
        if urgent not in (True, False):
            raise ValueError("say --urgent or --not-urgent")
        if bool(t.get("urgent")) == urgent:
            raise ValueError("%s is %s already" % (tid, "urgent" if urgent else "not urgent"))
        value = dev_queue.PRIORITY_URGENT if urgent else ""
        return ([record(by, tid, {"event": "edit", "field": "priority", "value": value})],
                "%s  → %s" % (tid, "Urgent" if urgent else "not urgent"))
    if word == "fix":
        text = " ".join((text or "").split())
        if not text:
            raise ValueError("no fix text")
        return [record(by, tid, {"event": "comment", "text": dev_queue.FIX_PREFIX + text})], \
            "%s  proposed fix: %s" % (tid, text)
    raise ValueError("unknown move %r" % word)


def move_start(root, board, ref, now):
    """(start, newest) for a move on `ref`: the later of `now` and one second after the newest `created` among the
    task's records on disk (dev_queue's own reader), and that newest stamp (None when the task has none). Raises
    ValueError when the start is more than AHEAD_MAX past `now` (PF-18d (stamp order))."""
    t = board.task(ref)
    if t is None:
        return now, None                                                # plan_move names the refusal
    rows = dev_queue.read_task_records(root)[0].get(t["id"]) or []
    stamps = [s for s in (dev_queue.utc(r.get("created")) for _n, r in rows) if s]
    if not stamps:
        return now, None
    newest = max(stamps)
    after = now_utc(newest) + datetime.timedelta(seconds=1)
    start = max(now, after)
    if start - now > AHEAD_MAX:
        raise ValueError("this task has records from the future (%s)" % newest)
    return start, newest


# --- writing --------------------------------------------------------------------------------------------------------

def stamp_free(root, build, start, tries=120):
    """(records, lines) from build(start), moved on a second at a time until no record's file already exists."""
    folder = os.path.join(root, dev_queue.TASKS)
    for _ in range(tries):
        recs, lines = build(start)
        if not any(os.path.exists(os.path.join(folder, record_name(r))) for r in recs):
            return recs, lines
        start += datetime.timedelta(seconds=1)
    raise ValueError("no free record names within %d seconds of %s" % (tries, iso(start)))


def write_records(root, recs):
    """Write each record as its own new file; never overwrites. [repo-relative path, …]."""
    folder = os.path.join(root, dev_queue.TASKS)
    os.makedirs(folder, exist_ok=True)
    out = []
    for r in recs:
        rel = "%s/%s" % (dev_queue.TASKS, record_name(r))
        with open(os.path.join(root, rel), "x", encoding="utf-8") as fh:
            fh.write(json.dumps(r, indent=1, ensure_ascii=False) + "\n")
        out.append(rel)
    return out


def report(recs, lines, written, dry, as_json, out):
    rels = written or ["%s/%s" % (dev_queue.TASKS, record_name(r)) for r in recs]
    if as_json:
        out.write(json.dumps({"dry_run": dry, "records": recs, "paths": rels, "lines": lines},
                             ensure_ascii=False, indent=1) + "\n")
        return
    head = "Would file" if dry else "Filed"
    out.write("%s %d record%s (dev-tagged PM tasks, PF-18c (issue queue))%s\n"
              % (head, len(recs), "" if len(recs) == 1 else "s", " — dry run, nothing written" if dry else ""))
    for line in lines:
        out.write("  " + line + "\n")
    for rel in rels:
        out.write(("  would write " if dry else "  wrote ") + rel + "\n")
    if not dry:
        out.write("Commit these paths; the mini's task index lists the new tasks on the PM board.\n")


def show(board, as_json, out):
    items = sorted(board.items.values(), key=lambda e: (e["created"] or "", e["id"]))
    if as_json:
        out.write(json.dumps(items, ensure_ascii=False, indent=1) + "\n")
        return
    if not items:
        out.write("No dev-tagged tasks under %s.\n" % dev_queue.TASKS)
    for e in items:
        where = (" on " + e["on_card"]) if e["on_card"] else (" on " + e["parent"]) if e["parent"] else ""
        out.write("%-10s %-11s %s%s: %s\n" % (e["kind"], e["state"], e["alias"] or e["id"], where, e["title"]))


def main(argv=None, out=None, err=None):
    out, err = out or sys.stdout, err or sys.stderr
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("word", choices=("file", "discussing", "card", "wont", "done", "fixed", "fix", "priority", "show"))
    ap.add_argument("args", nargs="*")
    ap.add_argument("--by", default=None, help="the person filing or moving (team/people/<name>)")
    ap.add_argument("--with", dest="with_people", action="append", default=None, help="discussing: who has it")
    ap.add_argument("--note", default="")
    ap.add_argument("--reason", default="")
    ap.add_argument("--root", default=None, help="the repo (default: the repo this file is in)")
    ap.add_argument("--now", default=None, help="the time to stamp (default: now)")
    ap.add_argument("--urgent", dest="urgent", action="store_const", const=True, default=None,
                    help="priority: the follow-up is Urgent (DQ-5 (human acts)); the newest edit wins")
    ap.add_argument("--not-urgent", dest="urgent", action="store_const", const=False,
                    help="priority: the follow-up is plain again")
    ap.add_argument("--dry-run", action="store_true", help="print what would be filed; write nothing")
    ap.add_argument("--json", action="store_true")
    x = ap.parse_args(argv)
    root = os.path.abspath(x.root or str(paths.repo(HERE)))
    board = Board(root)
    if x.word == "show":
        show(board, x.json, out)
        return 0
    need = {"file": 1, "discussing": 1, "card": 2, "wont": 1, "done": 1, "fixed": 2, "fix": 2, "priority": 1}[x.word]
    if len(x.args) != need:
        err.write("dev_issues %s: takes %d argument%s, got %d\n" % (x.word, need, "" if need == 1 else "s",
                                                                    len(x.args)))
        return 2
    if not x.by:
        err.write("dev_issues %s: --by <person> is required\n" % x.word)
        return 2
    try:
        start = now_utc(x.now)
    except ValueError as exc:
        err.write("dev_issues: %s\n" % exc)
        return 2
    try:
        if x.word == "file":
            try:
                if x.args[0] == "-":
                    src = sys.stdin.read()
                else:
                    with open(x.args[0], encoding="utf-8") as handle:
                        src = handle.read()
                items = json.loads(src)
            except (OSError, ValueError, UnicodeDecodeError) as exc:
                err.write("dev_issues file: cannot read %s: %s\n" % (x.args[0], exc))
                return 3
            problems = check_items(items, board, x.by)
            if problems:
                err.write("dev_issues file: refused, nothing written —\n" + "".join("  %s\n" % p for p in problems))
                return 2
            recs, lines = stamp_free(root, lambda s: plan_file(items, board, x.by, s), start)
        else:
            card = x.args[1] if x.word == "card" else None
            text = x.args[1] if x.word == "fix" else None
            note = x.reason if x.word == "wont" else x.note
            commit = None
            if x.word == "fixed":
                plan_move(board, x.word, x.args[0], x.by, note=note, commit=("0" * 40, ""))  # its own refusals first
                commit = commit_on_head(root, x.args[1])

            def build(s):
                recs, line = plan_move(board, x.word, x.args[0], x.by, note=note, card=card,
                                       with_people=x.with_people, text=text, commit=commit, urgent=x.urgent)
                for i, r in enumerate(recs):
                    r["created"] = iso(s + datetime.timedelta(seconds=i))
                return recs, [line]
            build(start)                                                # the move's own refusals come first
            first, newest = move_start(root, board, x.args[0], start)
            recs, lines = stamp_free(root, build, first)
            if recs and now_utc(recs[0]["created"]) - start > AHEAD_MAX:
                raise ValueError("this task has records from the future (%s): no free record name within 60 s"
                                 % (newest or recs[0]["created"]))
    except ValueError as exc:
        err.write("dev_issues %s: refused — %s\n" % (x.word, exc))
        return 2
    written = None if x.dry_run else write_records(root, recs)
    report(recs, lines, written, x.dry_run, x.json, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
