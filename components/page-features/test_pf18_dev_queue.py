#!/usr/bin/env python3
"""PF-18 (dev-queue view): the dev-queue family and its data command, components/page-features/dev_queue.py.

    python3 components/page-features/test_pf18_dev_queue.py

    (a) each column and chip from its own source, on a fixture repo built here (decks, request records, a git log,
        a decision log): Up next chips from heading words, In progress chips from the newest worker record, Shipped
        from merge commits (a seat's "lead: merge …" too) or a card's own commit on main, a PF card shipped before
        the cutoff in Shipped like any other (PF-18f (earlier PF review), tested in test_pf18f_earlier_pf.py); Issue
        queue and Flagged name the card each came with (Flagged's marks are PF-18b (review marks)'s, tested in
        test_pf18b_review_marks.py)
    (b) PF-4b is never PF-4: a merge, a request record and a decision naming PF-4b leave PF-4 untouched
    (c) the data command never calls cards_status: every process it starts is git, a cards_status.py planted in the
        fixture never runs, a cards-status record claiming a merge is not read
    (d) the cutoff is honoured, and it is one setting: the baseline, the no-card stream and the decision stream all
        move with --cutoff (a PF card stays in Shipped on either side of it: PF-18f (earlier PF review))
    (e) the deck list is a parameter: --deck reads only the decks it names (a .fixture.txt deck here)
    (f) served: the family's sources.json runs it through the kit's Sources from the repo root (cache, watch, stamp)
    (p) the page: the template's own script, in node with a minimal DOM, draws each column, chip, stream and panel
        from the fixture's data, asks only /data and /stamp, and has no button on the board but Copy for Claude and
        opening a card (the marks sit in the card panel and on open marks: PF-18b (review marks))
    (g) at HEAD: the template reads only /data/dev-queue and /stamp/dev-queue on its own (the marks go through the
        act.js block), has the mock's anchors and the six columns in order, Copy for Claude, and a run table of the
        four marks only; going live (check_live on a /page-draft of it) and the share check pass; pages.list_pages
        lists dev-queue, owner developer; one real run on this repo

The fixture decks live in this file, never as .md files under components/ (CLI-13 (id-tag lint) reads those).
Stdlib only, Python 3.9. Writes only in temp folders; no network.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "kit"))
import dev_queue  # noqa: E402
import draft  # noqa: E402
import features  # noqa: E402
import live  # noqa: E402
import pages  # noqa: E402
import serve  # noqa: E402
import share  # noqa: E402

REAL = features.ROOT
TPL = "platform/views/viewers/_templates/"
REQ = "platform/data/records/workflow-requests/"
NOW = "2026-10-29T05:00:00Z"

DECK = """# page-features cards (fixture)

### PF-3 — feature check: one command proves every wired feature (carded 2026-10-21 by the lead; owner email_lead (page-features))
### PF-4 — page starter kit: a tiny local server (carded 2026-10-21 by the lead; owner developer (assumption))
### PF-4b — kit hardening: the kit answers only its own Mac (carded 2026-10-22 by the lead; owner email_lead (page-features); DISPATCHED)
### PF-5 — mock carries features: the mock stamps its table (carded 2026-10-21 by the lead; APPROVED)
### PF-6 — page families: versions of one page (carded 2026-10-21 by the lead; owner developer (assumption); NOT DISPATCHED)
### PF-7 — working versions: demo or working (carded 2026-10-21; APPROVED; DISPATCH WAITS for PF-6 (page families))
### PF-8 — go button: the Go from the page (carded 2026-10-21; APPROVED, then HELD for a ruling)
### PF-9 — no words: a heading with no status words (carded 2026-10-21; owner designer (engine))
### PF-11 — part codes: S<n> (carded 2026-10-22; owner email_lead (emails family); DISPATCHED)
### PF-12 — code chips: the code sits on the picture (carded 2026-10-22; DISPATCHED)
### PF-13 — direct buttons: five buttons run at once (carded 2026-10-28; DISPATCHED)
### PF-14 — page server: one server per person (carded 2026-10-28; DISPATCHED)
### PF-15 — direct default: every button runs direct (carded 2026-10-28; DISPATCHED)
### PF-16 — fixed port: one port per person (carded 2026-10-28; DISPATCHED)
"""
DECK_LD = """# system-path cards (fixture)

### LD-1 — old card: merged long ago (carded 2026-10-01; owner developer)
### LD-2 — busy card: carded long ago, requested after the cutoff (carded 2026-10-01; owner designer)
### LD-3 — new card: carded after the cutoff (carded 2026-10-28; owner email_lead; NOT DISPATCHED)
### LD-4 — quiet card: nothing since (carded 2026-10-01; owner developer)
"""
DECK_ONLY = """### PF-20 — fixture-only card: read through --deck (carded 2026-10-28; APPROVED)
"""
DECISIONS = """# The org — decision log

- 2026-10-28 — STANDING RULE: EVERY BUTTON RUNS DIRECT. PF-15 (direct default) carries it. developer, typed to the lead 2026-10-28: "Go".
  KILL: a double spend → money buttons back to Claude.

- 2026-10-27 — KIT HARDENING HOLDS: PF-4b (kit hardening) keeps its Host check; I-241 (drive timeout FYI) told. email_lead, relayed by PLAN: "keep it".
  KILL: a page breaks → revisit.

- 2026-10-22 — OLD RULING ON PF-4b (kit hardening), BEFORE THE CUTOFF. developer, typed to the lead.
  KILL: none.

- 2026-10-20 — AN OLD UNRELATED ONE: LD-4 (quiet card) waits. developer, typed to the lead.
"""
PLANTED = ("import os\nopen(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RAN'), 'w').write('ran')\n"
           "print('{}')\n")
EMAILS = {"developer": "developer@example.com", "email_lead": "email_lead@example.com", "designer": "val@example.com"}


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)


class Repo(object):
    """A temp git repo whose commits carry the dates and authors a test names (never pushed)."""

    def __init__(self, root):
        self.root = root
        self.git("init", "-q")

    def git(self, *args, **env):
        e = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", HOME=self.root)
        e.update(env)
        p = subprocess.run(["git"] + list(args), cwd=self.root, capture_output=True, text=True, env=e)
        if p.returncode:
            raise AssertionError("git %s: %s" % (args, p.stderr))
        return p.stdout.strip()

    def _env(self, at, who):
        return {"GIT_AUTHOR_DATE": at, "GIT_COMMITTER_DATE": at, "GIT_AUTHOR_NAME": who.title(),
                "GIT_COMMITTER_NAME": who.title(), "GIT_AUTHOR_EMAIL": EMAILS.get(who, who + "@example.com"),
                "GIT_COMMITTER_EMAIL": EMAILS.get(who, who + "@example.com")}

    def commit(self, subject, at, who="developer", files=None):
        for rel, text in (files or {"log/%s.txt" % at.replace(":", ""): subject}).items():
            write(self.root, rel, text)
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", subject, **self._env(at, who))
        return self.git("rev-parse", "HEAD")

    def merge(self, subject, at, side="impl(page-features): the maker's commit", who="developer"):
        """A two-parent merge commit on HEAD: a side commit (the branch's maker commit) plus the merge itself."""
        tree = self.git("rev-parse", "HEAD^{tree}")
        head = self.git("rev-parse", "HEAD")
        env = self._env(at, who)
        branch = self.git("commit-tree", tree, "-p", head, "-m", side, **env)
        merged = self.git("commit-tree", tree, "-p", head, "-p", branch, "-m", subject, **env)
        self.git("update-ref", "HEAD", merged)
        return merged


def request(root, at, who, item, verdict, encode=False):
    stamp = re.sub(r"[-:]", "", at)
    doc = {"schema": 1, "kind": "workflow-requests", "reviewer": who, "item": item,
           "verdict": json.dumps(verdict) if encode else verdict, "notes": "", "created": at, "via": "test"}
    write(root, REQ + "%s--%s--%s.json" % (stamp, who, item), json.dumps(doc))


def fixture():
    """A temp workspace with two decks, request records, a dated git history and a decision log."""
    root = os.path.realpath(tempfile.mkdtemp(prefix="pf18-"))
    os.makedirs(os.path.join(root, "brands"))
    for pid, email in EMAILS.items():
        write(root, "team/people/%s/identity.json" % pid, json.dumps({"person": pid, "emails": [{"address": email}]}))
    write(root, "team/id-tags.json", json.dumps({"_readme": "fixture", "PF-4": "page starter kit",
                                                  "PF-4b": "kit hardening", "I-241": "drive timeout FYI"}))
    write(root, "new-workflow-design/workflows.json", json.dumps(
        {"workflows": [{"name": "page-features", "cards_file": "new-workflow-design/builds/page-features/task-cards.md"}]}))
    write(root, "new-workflow-design/builds/page-features/task-cards.md", DECK)
    write(root, "new-workflow-design/builds/system-path/task-cards.md", DECK_LD)
    write(root, "decks/task-cards.fixture.txt", DECK_ONLY)
    write(root, "the-org/decision-log.md", DECISIONS)
    write(root, "platform/workers/mini-worker/cards_status.py", PLANTED)
    write(root, "platform/data/records/cards-status/20261029T000000Z--mini-worker--PF.json", json.dumps(
        {"schema": 1, "kind": "cards-status", "item": "PF", "verdict": {"cards": [{"id": "PF-5", "state": "merged"}]}}))
    # request records: one card per chip, a cancelled one, PF-4b's (merged anyway), LD-2's after the cutoff
    request(root, "2026-10-22T01:00:00Z", "developer", "impl-pf4b-kit", {"action": "implement", "cards": ["PF-4b"]})
    request(root, "2026-10-22T01:30:00Z", "mini-worker", "impl-pf4b-kit", {"status": "done", "detail": "awaiting merge"})
    request(root, "2026-10-28T01:00:00Z", "developer", "impl-pf11-parts", {"action": "implement", "cards": ["PF-11"]})
    request(root, "2026-10-28T01:01:00Z", "mini-worker", "impl-pf11-parts", {"status": "running", "detail": "started"})
    request(root, "2026-10-28T02:00:00Z", "developer", "impl-pf12-chips", {"action": "implement", "cards": ["PF-12"]},
            encode=True)
    request(root, "2026-10-28T02:01:00Z", "mini-worker", "impl-pf12-chips", {"status": "running", "detail": "started"})
    request(root, "2026-10-28T02:30:00Z", "mini-worker", "impl-pf12-chips", {"status": "done", "detail": "awaiting"},
            encode=True)
    request(root, "2026-10-28T03:00:00Z", "developer", "impl-pf13-direct", {"action": "implement", "cards": ["PF-13"]})
    request(root, "2026-10-28T03:30:00Z", "mini-worker", "impl-pf13-direct",
            {"status": "done-unverified", "detail": "checks 0/1 passed"})
    request(root, "2026-10-28T04:00:00Z", "developer", "impl-pf14-server", {"action": "implement", "cards": ["PF-14"]})
    request(root, "2026-10-28T04:30:00Z", "mini-worker", "impl-pf14-server", {"status": "failed", "detail": "worker error"})
    request(root, "2026-10-28T05:00:00Z", "developer", "impl-pf6-families", {"action": "implement", "cards": ["PF-6"]})
    request(root, "2026-10-28T05:10:00Z", "developer", "impl-pf6-families", {"action": "cancel"})
    request(root, "2026-10-27T05:00:00Z", "designer", "impl-ld2-busy", {"action": "implement", "cards": ["LD-2"]})
    git = Repo(root)
    git.commit("lead: card the decks", "2026-10-01T00:00:00Z")
    git.merge("merge LD-1 (old card) — developer typed to the lead: \"merge LD-1\"", "2026-10-02T00:00:00Z")
    git.commit("PF-3 (feature check), built directly on main", "2026-10-21T10:00:00Z", "email_lead")
    git.merge("merge PF-4b (kit hardening) — developer typed to the lead: \"merge PF-4b\"; after PF-4 (page starter kit)",
              "2026-10-22T02:00:00Z")
    git.commit("gdrive-creator: an old retry, before the cutoff", "2026-10-26T23:00:00Z", "developer",
               {"components/gdrive-creator/a.txt": "1"})
    git.commit("gdrive-creator: every Drive call gives up after 60 s", "2026-10-27T00:30:00Z", "developer",
               {"components/gdrive-creator/a.txt": "2"})
    git.merge("merge PF-15 (direct default) — record done 5/5", "2026-10-28T10:00:00Z")
    git.merge("lead: merge PF-16 (fixed port) under duty 5", "2026-10-28T11:00:00Z")
    git.commit("emails: brand_b nov-19 written and laid out", "2026-10-28T12:00:00Z", "email_lead",
               {"components/email-production/x.txt": "x", "platform/views/viewers/email_lead/emails.html": "<p>"})
    git.commit("atlas: recompiled at abc", "2026-10-28T13:00:00Z", "developer")
    git.commit("fix the PF-9 heading words", "2026-10-28T14:00:00Z", "designer")
    git.commit("developer: I-241 (drive timeout FYI) to designer", "2026-10-28T15:00:00Z", "developer")
    git.commit("pm: a payment request sent", "2026-10-28T16:00:00Z", "designer")
    return root


def by_id(doc):
    return dict((c["id"], c) for c in doc["cards"])


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = fixture()
        cls.doc = dev_queue.build(cls.root, now=NOW)
        cls.cards = by_id(cls.doc)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, True)

    # (a)
    def test_a_up_next_chips_from_heading_words(self):
        c = self.cards
        self.assertEqual(c["PF-5"]["column"], "up-next")
        self.assertEqual(c["PF-5"]["pending"], "approved", "APPROVED")
        self.assertEqual(c["PF-6"]["pending"], "waiting", "NOT DISPATCHED; its cancelled request leaves it up next")
        self.assertEqual(c["PF-6"]["column"], "up-next")
        self.assertEqual(c["PF-7"]["pending"], "waiting", "DISPATCH WAITS outranks APPROVED")
        self.assertEqual(c["PF-8"]["pending"], "held", "HELD outranks APPROVED")
        self.assertIsNone(c["PF-9"]["pending"], "no status words, no chip")
        self.assertEqual(c["LD-3"]["pending"], "waiting")
        self.assertEqual((c["PF-6"]["owner"], c["PF-9"]["owner"], c["PF-5"]["owner"]), ("developer", "designer", None))
        self.assertEqual(c["PF-5"]["carded_on"], "2026-10-21")
        self.assertEqual(c["PF-4"]["tag"], "page starter kit")
        self.assertEqual(c["PF-5"]["tag"], "mock carries features", "no stored tag: the title's lead words")
        self.assertEqual(c["PF-5"]["title"], "the mock stamps its table")

    def test_a_in_progress_chips_from_the_newest_worker_record(self):
        c = self.cards
        got = dict((k, (c[k]["column"], c[k]["progress"]["chip"])) for k in ("PF-11", "PF-12", "PF-13", "PF-14", "LD-2"))
        self.assertEqual(got, {"PF-11": ("in-progress", "Building"), "PF-12": ("in-progress", "Ready to merge"),
                               "PF-13": ("in-progress", "Check first"), "PF-14": ("in-progress", "Failed"),
                               "LD-2": ("in-progress", "Building")})
        self.assertEqual(c["PF-12"]["progress"]["item"], "impl-pf12-chips")
        self.assertEqual(c["LD-2"]["progress"]["status"], "queued", "a request with no worker record yet")
        self.assertIsNone(c["PF-11"]["pending"], "chips of Up next never ride on another column")

    def test_a_shipped_and_reviewed_from_git(self):
        c = self.cards
        self.assertEqual((c["PF-15"]["column"], c["PF-15"]["merged"]["via"]), ("shipped", "merge commit"))
        self.assertEqual(c["PF-16"]["column"], "shipped", "a seat's 'lead: merge PF-16 (…)' is a merge commit")
        self.assertEqual(c["PF-15"]["review"], [{"person": "email_lead", "understood": None},
                                                {"person": "designer", "understood": None}])
        self.assertEqual(c["PF-15"]["merged"]["at"], "2026-10-28T10:00:00Z")
        # narrowed by PF-18f (earlier PF review): a PF card merged before the cutoff is Shipped, unmarked, like any other
        self.assertEqual((c["PF-4b"]["column"], c["PF-4b"]["state"]), ("shipped", "shipped"),
                         "merged before the cutoff: a PF card in Shipped; its done record loses to the merge")
        self.assertIsNone(c["PF-4b"]["progress"])
        self.assertEqual(c["PF-4b"]["review"], [{"person": "email_lead", "understood": None},
                                                {"person": "designer", "understood": None}])
        self.assertEqual((c["PF-3"]["column"], c["PF-3"]["merged"]["via"]), ("shipped", "direct commit"))
        self.assertEqual([h["what"] for h in c["PF-12"]["history"]], ["done", "running", "dispatched", "carded"])
        self.assertEqual(self.doc["columns_after"], {"issue-queue": "PF-18c (issue queue)",
                                                     "flagged": "PF-18b (review marks)"})
        self.assertFalse([x for x in self.doc["cards"] if x["column"] in ("issue-queue", "flagged")])

    def test_a_streams(self):
        work = self.doc["direct_work"]
        self.assertEqual([(w["person"], w["what"]) for w in work], [
            ("designer", "pm: a payment request sent"),
            ("email_lead", "emails: brand_b nov-19 written and laid out"),
            ("developer", "gdrive-creator: every Drive call gives up after 60 s")])
        self.assertEqual(work[1]["areas"], ["email-production", "page:emails.html"])
        dec = self.doc["decisions"]
        self.assertEqual([(d["date"], d["in_stream"]) for d in dec],
                         [("2026-10-28", True), ("2026-10-27", True), ("2026-10-22", False)])
        self.assertEqual((dec[0]["decided_by"], dec[0]["how"]), ("developer", "typed"))
        self.assertEqual((dec[1]["decided_by"], dec[1]["how"]), ("email_lead", "relayed"))
        self.assertEqual(dec[0]["headline"], "STANDING RULE: EVERY BUTTON RUNS DIRECT")
        self.assertEqual(dec[0]["kill"], "KILL: a double spend → money buttons back to Claude.")
        self.assertEqual([(x["id"], x["tag"], x["card"]) for x in dec[1]["cards"]],
                         [("PF-4b", "kit hardening", True), ("I-241", "drive timeout FYI", False)])

    # (b)
    def test_b_pf4b_is_never_pf4(self):
        c = self.cards
        self.assertEqual((c["PF-4"]["column"], c["PF-4"]["merged"], c["PF-4"]["progress"]), ("up-next", None, None),
                         "the PF-4b merge, whose subject also names PF-4 after its dash, ships only PF-4b")
        self.assertEqual([h["what"] for h in c["PF-4"]["history"]], ["carded"], "no PF-4b request on PF-4")
        self.assertIn("impl-pf4b-kit", [h.get("item") for h in c["PF-4b"]["history"]])
        named = [x["id"] for d in self.doc["decisions"] for x in d["cards"]]
        self.assertIn("PF-4b", named)
        self.assertNotIn("PF-4", named)
        self.assertEqual(dev_queue.merge_ids("merge PF-4b (kit hardening) — after PF-4 (page starter kit)"), ["PF-4b"])
        self.assertEqual(dev_queue.merge_ids("merge MET-C43 (a) + MET-C42 (b) — go"), ["MET-C43", "MET-C42"])
        self.assertEqual([m.group(1) for m in dev_queue.ID_RE.finditer("PF-4b, PF-4 and PF-40; xPF-4")],
                         ["PF-4b", "PF-4", "PF-40"])

    # (c)
    def test_c_never_calls_cards_status(self):
        started = []
        real = subprocess.run

        def spy(argv, *a, **k):
            started.append(list(argv))
            return real(argv, *a, **k)
        dev_queue.subprocess.run = spy
        try:
            doc = dev_queue.build(self.root, now=NOW)
        finally:
            dev_queue.subprocess.run = real
        self.assertTrue(started)
        self.assertEqual(sorted(set(a[0] for a in started)), ["git"], "every process it starts is git")
        self.assertFalse([a for a in started if any("cards_status" in str(x) for x in a)])
        self.assertFalse(os.path.exists(os.path.join(self.root, "platform/workers/mini-worker/RAN")))
        self.assertEqual(by_id(doc)["PF-5"]["column"], "up-next", "a cards-status record saying merged is not read")
        p = subprocess.run([sys.executable, os.path.join(HERE, "dev_queue.py"), "--root", self.root, "--now", NOW],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(by_id(json.loads(p.stdout))["PF-15"]["column"], "shipped")
        self.assertFalse(os.path.exists(os.path.join(self.root, "platform/workers/mini-worker/RAN")))

    # (d)
    def test_d_the_cutoff_is_honoured(self):
        c = self.cards
        self.assertEqual(self.doc["cutoff"], dev_queue.CUTOFF)
        self.assertEqual(dev_queue.CUTOFF, "2026-10-27T00:00:00Z")
        self.assertNotIn("LD-1", c, "not PF, merged before the cutoff")
        self.assertNotIn("LD-4", c, "not PF, nothing since the cutoff")
        self.assertIn("LD-2", c, "a request record after the cutoff")
        self.assertIn("LD-3", c, "carded after the cutoff")
        self.assertIn("PF-9", c, "every PF card, whatever its dates")
        self.assertNotIn("an old retry", " ".join(w["what"] for w in self.doc["direct_work"]))

    def test_d_the_cutoff_is_one_setting(self):
        later = dev_queue.build(self.root, cutoff="2026-10-28T12:30:00Z", now=NOW)
        c = by_id(later)
        self.assertEqual(later["cutoff"], "2026-10-28T12:30:00Z")
        self.assertEqual((c["PF-15"]["column"], c["PF-15"]["review"][0]["understood"]), ("shipped", None),
                         "merged before the new cutoff: a PF card stays in Shipped, unmarked (narrowed by PF-18f "
                         "(earlier PF review))")
        self.assertNotIn("LD-2", c, "its only activity is before the new cutoff")
        self.assertIn("LD-3", by_id(dev_queue.build(self.root, cutoff="2026-10-28T00:00:00Z", now=NOW)))
        self.assertEqual([w["person"] for w in later["direct_work"]], ["designer"])
        self.assertEqual([d["date"] for d in later["decisions"] if d["in_stream"]], ["2026-10-28"])

    # (e)
    def test_e_the_deck_list_is_a_parameter(self):
        doc = dev_queue.build(self.root, decks=["decks/*.fixture.txt"], now=NOW)
        self.assertEqual(doc["sources"]["decks"], ["decks/task-cards.fixture.txt"])
        self.assertEqual([(x["id"], x["pending"]) for x in doc["cards"]], [("PF-20", "approved")])
        self.assertEqual(sorted(self.doc["sources"]["decks"]), ["new-workflow-design/builds/page-features/task-cards.md",
                                                                 "new-workflow-design/builds/system-path/task-cards.md"])

    # (f)
    def test_f_served_through_the_kit(self):
        root = os.path.realpath(tempfile.mkdtemp(prefix="pf18-served-"))
        self.addCleanup(shutil.rmtree, root, True)
        shutil.rmtree(root)
        shutil.copytree(self.root, root, symlinks=True)
        os.makedirs(os.path.join(root, "components/page-features"))
        shutil.copy(os.path.join(HERE, "dev_queue.py"), os.path.join(root, "components/page-features/dev_queue.py"))
        shutil.copytree(os.path.join(REAL, "components/run-kit/run_kit"), os.path.join(root, "components/run-kit/run_kit"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        decl = serve.sources("dev-queue", REAL)
        d = decl["dev-queue"]
        self.assertEqual(d["argv"], ["components/page-features/dev_queue.py", "--root", "."])
        self.assertGreaterEqual(d["cache_s"], 120)
        self.assertEqual(serve.preflight(decl), [])
        self.assertEqual(serve.runs_prefixes(decl), [], "no /runs/ folders")
        watched = set()
        for pat in d["watch"]:
            watched.update(os.path.relpath(f, root) for f in glob.glob(os.path.join(root, pat)))
        for need in ("new-workflow-design/builds/page-features/task-cards.md", "the-org/decision-log.md",
                     "new-workflow-design/workflows.json", REQ + "20261028T010000Z--developer--impl-pf11-parts.json"):
            self.assertIn(need, watched)
        runs = []
        src = serve.Sources(decl, root=root)
        real = src.runner
        src.runner = lambda argv: runs.append(argv) or real(argv)
        doc = json.loads(src.get("dev-queue"))
        self.assertEqual(by_id(doc)["PF-12"]["progress"]["chip"], "Ready to merge")
        json.loads(src.get("dev-queue"))
        self.assertEqual(len(runs), 1, "kept for cache_s while nothing watched changes")
        before = src.stamp("dev-queue")
        request(root, "2026-10-29T01:00:00Z", "mini-worker", "impl-pf11-parts", {"status": "done", "detail": "x"})
        self.assertNotEqual(src.stamp("dev-queue"), before)
        self.assertEqual(by_id(json.loads(src.get("dev-queue")))["PF-11"]["progress"]["chip"], "Ready to merge")
        self.assertEqual(len(runs), 2, "a new request record runs it again")


PAGE_HARNESS = r"""
// The page's own script in a minimal DOM: /data/dev-queue answers the fixture's JSON, nothing else is reached.
const fs = require("fs");
const html = fs.readFileSync(process.argv[2], "utf8");
const data = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const code = /<script id="dev-queue-page">([\s\S]*?)<\/script>/.exec(html)[1];
const byId = new Map(), asked = [];
class El {
  constructor(tag) {
    this.tagName = tag.toUpperCase(); this.children = []; this.parentNode = null; this.attrs = {}; this.listeners = {};
    this.own = ""; this.hidden = false; this.open = false; this.value = ""; this.checked = false; this.scrollTop = 0;
    const set = new Set();
    this.classList = {set: set, add(c) { set.add(c); }, remove(c) { set.delete(c); }, contains(c) { return set.has(c); },
      toggle(c, on) { if (on === undefined) on = !set.has(c); if (on) set.add(c); else set.delete(c); }};
  }
  set className(v) { this.classList.set.clear(); String(v).split(/\s+/).filter(Boolean).forEach(c => this.classList.set.add(c)); }
  get className() { return [...this.classList.set].join(" "); }
  setAttribute(k, v) { this.attrs[k] = String(v); if (k === "id") byId.set(String(v), this); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  appendChild(c) { if (c.parentNode) c.parentNode.removeChild(c); this.children.push(c); c.parentNode = this; return c; }
  removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); c.parentNode = null; return c; }
  get firstChild() { return this.children[0] || null; }
  set textContent(v) { this.children = []; this.own = String(v); }
  get textContent() { return this.own + this.children.map(c => c.textContent).join(" "); }
  addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); }
  fire(t) { const ev = {target: this, currentTarget: this, stopPropagation() {}}; (this.listeners[t] || []).forEach(f => f(ev)); }
  showModal() { this.open = true; }
  close() { this.open = false; this.fire("close"); }
  focus() {}
  select() {}
  contains(x) { for (; x; x = x.parentNode) if (x === this) return true; return false; }
  get isConnected() { return true; }
  getBoundingClientRect() { return {left: 0, right: 10, top: 0, bottom: 10}; }
  all() { return [this].concat(...this.children.map(c => (c.all ? c.all() : []))); }
}
class Txt { constructor(t) { this.t = t; this.parentNode = null; } get textContent() { return this.t; } }
const top = new El("body");
const every = () => [...new Set([...byId.values()].flatMap(e => e.all()))];
global.document = {
  createElement: t => new El(t), createTextNode: t => new Txt(t), addEventListener() {},
  getElementById: id => { if (!byId.has(id)) { const e = new El("div"); e.attrs.id = id; byId.set(id, e); top.appendChild(e); } return byId.get(id); },
  querySelectorAll: sel => sel === "[data-tile]" ? every().filter(e => e.getAttribute("data-tile")) :
    sel === ".tile.selected" ? every().filter(e => e.classList.contains("tile") && e.classList.contains("selected")) : []
};
global.window = {isSecureContext: true};
const copied = [];
Object.defineProperty(globalThis, "navigator", {configurable: true,
  value: {clipboard: {writeText: t => { copied.push(t); return Promise.resolve(); }}}});
global.fetch = (u, o) => {
  asked.push([u, (o && o.method) || "GET"]);
  if (u === "/data/dev-queue") return Promise.resolve({ok: true, json: () => Promise.resolve(data)});
  if (u === "/stamp/dev-queue") return Promise.resolve({ok: true, json: () => Promise.resolve({name: "dev-queue", stamp: [1, 1]})});
  return Promise.resolve({ok: false, status: 404, text: () => Promise.resolve("no")});
};
global.setInterval = () => 0;
const errors = [];
process.on("uncaughtException", e => errors.push(String(e.stack || e)));
process.on("unhandledRejection", e => errors.push(String((e && e.stack) || e)));
new Function(code)();
const g = id => byId.get(id), find = (e, p) => e.all().filter(p);
const tiles = col => find(g("col-" + col), e => e.getAttribute("data-tile")).map(e => e.getAttribute("data-tile"));
const tick = () => new Promise(r => setTimeout(r, 0));
(async () => {
  for (let i = 0; i < 5; i++) await tick();
  const out = {asked: asked, errors: errors, columns: {}, words: {}};
  ["issue-queue", "up-next", "in-progress", "shipped", "flagged", "reviewed"].forEach(c => {
    out.columns[c] = tiles(c);
    out.words[c] = g("col-" + c).textContent.replace(/\s+/g, " ").trim();
  });
  out.summary = g("summary").textContent.replace(/\s+/g, " ").trim();
  out.load_hidden = g("load").hidden;
  const buttons = every().filter(e => e.tagName === "BUTTON");
  out.button_kinds = [...new Set(buttons.map(b => b.className))].sort();
  out.copy_buttons = buttons.filter(b => b.className === "copy-button").length;
  out.changes = find(g("groups"), e => e.classList.contains("change")).length;
  out.decisions = find(g("decisions"), e => e.classList.contains("decision")).length;
  const openOf = id => buttons.find(b => b.className === "tile-open" && b.getAttribute("aria-label").indexOf("Open " + id + " (") === 0);
  out.panels = {};
  for (const id of ["PF-4", "PF-4b", "PF-12"]) {
    openOf(id).fire("click");
    const body = g("panel-content");
    out.panels[id] = {open: g("panel").open, decisions: find(body, e => e.classList.contains("decision")).length,
      text: body.textContent.replace(/\s+/g, " ").slice(0, 600)};   // 600: DQ-3 (note mark)'s button sits above the history
    find(body, e => e.className === "copy-button")[0].fire("click");
    await tick();
    g("panel").close();
  }
  out.copied = copied.slice();
  const email_lead = find(g("name-options"), e => e.tagName === "INPUT" && e.getAttribute("value") === "email_lead")[0];
  email_lead.checked = true;
  email_lead.fire("change");
  out.filtered = {cards: g("card-count").textContent, direct: g("direct-count").textContent,
    shipped: tiles("shipped"), reviewed: tiles("reviewed")};
  console.log(JSON.stringify(out));
})().catch(e => console.log(JSON.stringify({errors: [String(e.stack || e)].concat(errors)})));
"""


class Page(unittest.TestCase):
    """(a)(b) the template's own script on the fixture's data, in node with a minimal DOM (skipped where there is no
    node; the static checks in AtHead still hold)."""

    def test_the_page_draws_the_board_from_the_data(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("no node on this machine")
        root = fixture()
        self.addCleanup(shutil.rmtree, root, True)
        doc = dev_queue.build(root, now=NOW)
        write(root, "data.json", json.dumps(doc))
        write(root, "harness.js", PAGE_HARNESS)
        p = subprocess.run([node, os.path.join(root, "harness.js"), os.path.join(REAL, TPL, "dev-queue.html"),
                            os.path.join(root, "data.json")], capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        got = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(got["errors"], [])
        self.assertEqual(got["asked"], [["/data/dev-queue", "GET"], ["/stamp/dev-queue", "GET"]], "reads, never writes")
        self.assertTrue(got["load_hidden"])
        cols = got["columns"]
        self.assertEqual((cols["issue-queue"], cols["flagged"]), ([], []))
        self.assertIn("after PF-18c (issue queue)", got["words"]["issue-queue"])
        self.assertIn("Nothing flagged", got["words"]["flagged"], "no marks in this fixture: Flagged is empty")
        # narrowed by DQ-6 (built by label)'s order rule: oldest filing first, then id; the Approved / Waiting / Held
        # chip stays on the tile (asserted below) and is no sort key
        self.assertEqual(cols["up-next"], ["PF-4", "PF-5", "PF-6", "PF-7", "PF-8", "PF-9", "LD-3"],
                         "oldest filing first, then id")
        self.assertEqual(sorted(cols["in-progress"]), ["LD-2", "PF-11", "PF-12", "PF-13", "PF-14"])
        # narrowed by PF-18f (earlier PF review): the PF cards shipped before the cutoff sit in Shipped, no fold
        # narrowed by DQ-6 (built by label)'s order rule: Shipped is a queue, oldest merge first
        self.assertEqual(cols["shipped"], ["PF-3", "PF-4b", "PF-15", "PF-16"], "oldest merge first")
        self.assertEqual(cols["reviewed"], [], "no card marked Understood by both")
        self.assertIn("Nothing reviewed yet", got["words"]["reviewed"])
        self.assertNotIn("shipped before", got["words"]["reviewed"], "no fold")
        self.assertIn("email_lead – · designer –", got["words"]["shipped"])
        for words in ("Approved", "Waiting for a go", "Held"):
            self.assertIn(words, got["words"]["up-next"])
        for words in ("Building", "Ready to merge", "Check first", "Failed"):
            self.assertIn(words, got["words"]["in-progress"])
        # narrowed for DQ-7 (folded columns): each column's header is its fold button, a view toggle that writes nothing
        self.assertEqual(got["button_kinds"], ["card-chip", "column-toggle", "copy-button", "tile-open"],
                         "no button but Copy for Claude, opening a card, the decision's card chips and the folds")
        n_tiles = sum(len(v) for v in cols.values())
        self.assertEqual(got["copy_buttons"], n_tiles + got["changes"] + got["decisions"],
                         "every tile and row has Copy for Claude")
        self.assertEqual((got["changes"], got["decisions"]), (3, 2))
        self.assertEqual(got["panels"]["PF-4"]["decisions"], 0, "decisions naming PF-4b never land on PF-4")
        self.assertEqual(got["panels"]["PF-4b"]["decisions"], 2, "the stream one and the older one")
        self.assertIn("Build finished · ready to merge", got["panels"]["PF-12"]["text"])
        self.assertTrue(got["panels"]["PF-12"]["open"])
        # narrowed by DQ-4 (prompts and urgent): the Up next prompt now also asks why, who and how important (its
        # full text is pinned in test_dq4_prompts_urgent.py); the card, the change, the wait and the decider stay
        self.assertTrue(got["copied"][0].startswith("Explain PF-4 (page starter kit) to me in plain words: what it will "
                                                    "change, "), got["copied"][0])
        self.assertIn("what it waits on, and who decides.", got["copied"][0])
        self.assertIn("impl-pf12-chips", got["copied"][2])
        # narrowed by PF-18f (earlier PF review): PF-3 and PF-4b now sit in Shipped; PF-15 and PF-16 stay out
        self.assertEqual(sorted(got["filtered"]["shipped"]), ["PF-3", "PF-4b"], "both owned by email_lead")
        self.assertEqual(got["filtered"]["reviewed"], [])
        self.assertEqual(got["filtered"]["direct"], "1 of 3")


class AtHead(unittest.TestCase):
    """(g) the real family at HEAD, read-only."""

    def test_g_the_template(self):
        text = read(os.path.join(REAL, TPL, "dev-queue.html"))
        outside = text.replace(text[slice(*live._overlay_span(text))], "")
        act = outside[slice(*live._act_span(outside))]
        self.assertEqual(act, "%s\n<script id=\"pf-act\">\n%s</script>\n%s" % (
            live.ACT_START, read(os.path.join(HERE, "kit", "act.js")), live.ACT_END), "kit/act.js, whole")
        outside = outside.replace(act, "")    # PF-18b (review marks): the marks write through act.js only
        self.assertEqual(re.findall(r"fetch\(\s*[\"']([^\"']+)", outside), ["/data/", "/stamp/"])
        self.assertIn('var SOURCE = "dev-queue";', outside)
        for anchor in ("board-section", "name-menu", "family-menu", "groups", "decisions", "panel"):
            self.assertRegex(outside, r'id="%s"' % anchor, "the mock's anchor %s" % anchor)
        cols = re.findall(r'<section class="column" id="col-([a-z-]+)"', outside)
        self.assertEqual(cols, ["issue-queue", "up-next", "in-progress", "shipped", "flagged", "reviewed"])
        self.assertIn('label: "Flagged"', outside)
        self.assertNotIn('label: "Issues"', outside)
        self.assertNotIn("innerHTML", outside, "the page builds its own elements from the data")
        # narrowed for DQ-7 (folded columns): the fold's own view state, key dq_col_<id>, is the one localStorage use
        # allowed (the viewer's fold on this browser, never a record); any other localStorage still fails
        self.assertEqual(re.findall(r"localStorage\.(\w+)\(\"([a-z_]+)", outside),
                         [("getItem", "dq_col_"), ("setItem", "dq_col_")], "the fold's two storage calls, nothing else")
        for write_word in ("method:", "/act", "/upload", "localStorage"):
            self.assertNotIn(write_word, outside.replace('localStorage.getItem("dq_col_"', "").replace(
                'localStorage.setItem("dq_col_"', ""), "no write of its own: the marks go through pfAct")
        # narrowed for DQ-8 (act panel): the act panel's Done (26) is the second pfAct call, on the same review route
        self.assertEqual(re.findall(r"pfAct\(([^,]+),", outside), ["MARK[word].n", "DONE_N"],
                         "two pfAct calls: the marks and Done")
        self.assertIn('"Copy for Claude")', outside)
        doc = features.load(os.path.join(REAL, TPL, "dev-queue.features.json"))
        self.assertEqual(features.validate(doc), [])
        self.assertEqual(doc["owner"], "developer")
        self.assertEqual(features.sync_text(text, doc), text, "the embedded catalog is the family list")
        table = live.run_table("dev-queue", REAL)
        # DQ-3 (note mark): 24 Note is the fifth mark
        # narrowed for DQ-8 (act panel): 26 Done rides the marks' review route, its word "done"
        self.assertEqual(sorted(table, key=int), ["20", "21", "22", "23", "24", "26"],
                         "the run table holds the marks and Done only")
        self.assertEqual([table[n][0][1]["mark"] for n in ("20", "21", "22", "23", "24", "26")],
                         ["understood", "question", "issue", "resolve", "note", "done"])
        self.assertEqual(set(table[n][0][1]["run"] for n in table), {"review"}, "every entry on the review route")
        self.assertEqual([e["n"] for e in doc["features"] if e["kind"] == "action"], [20, 21, 22, 23, 24, 26])
        self.assertEqual(live.run_entry_findings(doc, "dev-queue", table), [])
        self.assertEqual(sorted(re.findall(r'data-feature="(\d+)"', outside), key=int),
                         [str(e["n"]) for e in doc["features"]])

    def test_g_check_live_passes_on_a_draft_of_the_template(self):
        root = tempfile.mkdtemp(prefix="pf18-live-")
        self.addCleanup(shutil.rmtree, root, True)
        for ext in ("html", "features.json", "actions.json"):    # actions.json: the marks' run table (PF-18b)
            write(root, TPL + "dev-queue." + ext, read(os.path.join(REAL, TPL, "dev-queue." + ext)))

        def fake_git(argv, cwd):
            return 0, "", ""
        made = draft.make_draft("dev-queue", name="try", person="fixp", root=root, runner=fake_git, share=False)
        self.assertEqual(made["result"], "draft", made)
        r = live.check_live(made["written"][0], person="fixp", root=root, runner=fake_git)
        self.assertIsNone(r["refused"], r)
        self.assertEqual(r["failures"], [])
        self.assertTrue(r["ok"])

    def test_g_the_share_check_passes_on_the_template(self):
        sys.path.insert(0, os.path.join(REAL, "components", "system-integration"))
        import page_scan
        # The family's four files committed in a temp repo: the check asks git whether the data command is in git,
        # and this tree hands its files to the worker uncommitted.
        root = os.path.realpath(tempfile.mkdtemp(prefix="pf18-share-"))
        self.addCleanup(shutil.rmtree, root, True)
        for rel in (TPL + "dev-queue.html", TPL + "dev-queue.features.json", TPL + "dev-queue.sources.json",
                    TPL + "dev-queue.actions.json", "components/page-features/dev_queue.py"):
            write(root, rel, read(os.path.join(REAL, rel)))
        repo = Repo(root)
        repo.commit("page: the dev-queue family", "2026-10-29T05:00:00Z", files={})
        r = share.share_check(TPL + "dev-queue.html", root=root, scan=page_scan.scan)
        self.assertIsNone(r["refused"], r)
        self.assertEqual(r["blockers"], [])
        self.assertEqual((r["view"], r["use"]), ("pass", "pass"))

    def test_g_list_pages_lists_dev_queue(self):
        result = pages.list_pages(person="nobody-here", root=REAL, runner=lambda argv, cwd: (0, "", ""))
        fams = dict((f["family"], f) for f in result["families"])
        self.assertIn("dev-queue", fams)
        self.assertEqual((fams["dev-queue"]["owner"], fams["dev-queue"]["available"]), ("developer", True))

    def test_g_one_real_run_on_this_repo(self):
        p = subprocess.run([sys.executable, os.path.join(HERE, "dev_queue.py"), "--root", REAL],
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(p.returncode, 0, p.stderr[-400:])
        doc = json.loads(p.stdout)
        c = by_id(doc)
        self.assertIn("PF-18", c)
        self.assertEqual(c["PF-4b"]["merged"]["via"], "merge commit")
        self.assertNotEqual((c["PF-4"]["merged"] or {}).get("sha"), c["PF-4b"]["merged"]["sha"])
        self.assertEqual(doc["cutoff"], dev_queue.CUTOFF)


if __name__ == "__main__":
    unittest.main()
