#!/usr/bin/env python3
"""PF-18c (issue queue): issues as PM tasks tagged dev — components/page-features/dev_issues.py (the filing step and
the moves) and what dev_queue.py and the dev-queue template make of them.

    python3 components/page-features/test_pf18c_issue_queue.py

    (a) file: a session's sorted list becomes one tasks record per issue and follow-up (tags dev + its kind, Raised),
        context notes and proposed fixes become comments on their parent issue, a note on a card its own done task;
        each keeps its quote verbatim and its source session; issues are filed before the items that name them
    (b) --dry-run writes nothing and prints what it would file
    (c) a bad item refuses the whole list, every problem named, nothing written
    (d) moves: Raised → Discussing (with people), Carded (a card link, then done; the card shows "from issue …"),
        Won't do (its reason kept, none refused), a follow-up ticked done; moves that make no sense are refused
    (e) the records are the tasks kind's own: events, statuses and link types from platform/data/kinds/tasks.json,
        names carrying the item id (the records-plane name check), and the PM board's own fold (mytasks) reads the
        same status and card link
    (f) dev_queue.py: the `issues` list and each card's from_issues, issues, follow_ups and context; non-dev tasks are
        not read in; the page server watches the task records
    (p) the page: the template's own script, in node with a minimal DOM, draws the queue groups (Won't do not
        drawn since PF-18m (open issues only), its record kept), the quote, the "from issue …" line and the card
        panel's follow-ups and context
    (g) at HEAD: show and a dry run on this repo write nothing; the catalog marks the Issue queue wired

Fixtures are built in temp folders from test_pf18_dev_queue's fixture repo; no .md fixtures under components/.
Stdlib only, Python 3.9. No network; no real task record is written.
"""
import importlib.util
import io
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
import dev_issues  # noqa: E402
import dev_queue  # noqa: E402
import features  # noqa: E402
import serve  # noqa: E402
import test_pf18_dev_queue as pf18  # noqa: E402  the PF-18 fixture repo and page harness, reused

REAL = features.ROOT
TASKS = "platform/data/records/tasks/"
TPL = "platform/views/viewers/_templates/"
TASK_ID_RE = re.compile(r"^TSK-\d{14}-[a-z0-9]+(?:-[a-z0-9]+)*$")
QUOTE_1 = "what i meant by do it next is to discuss with email_lead or designer\nand have them take it over"

# A session's pending list, already sorted (11 split into an issue and a follow-up), in a mixed order on purpose.
ITEMS = [
    {"kind": "follow-up", "ref": "11b", "title": "Correct I-241 (drive timeout FYI): the trigger was not a download",
     "quote": "tell designer the trigger is unknown", "session": "545f20", "parent": "11a", "person": "designer"},
    {"kind": "issue", "ref": "1", "title": "A fresh copy has no email pictures", "quote": QUOTE_1, "session": "545f20",
     "fixes": ["No shot while a picture is missing", "A fresh checkout pulls the pictures in the background"],
     "detail": "Shots are taken with broken images."},
    {"kind": "context", "ref": "4", "title": "12 old emails miss pictures on Drive itself", "quote": "past sends",
     "session": "545f20", "parent": "1"},
    {"kind": "issue", "ref": "11a", "title": "The email list hung for 9 minutes", "quote": "it hung again",
     "session": "545f20"},
    {"kind": "follow-up", "ref": "14", "title": "Restore the picture cache set aside in the test", "quote": "put it back",
     "session": "545f20", "person": "developer"},
    {"kind": "issue", "ref": "5", "title": "A page can press another page type's buttons", "quote": "it should not",
     "session": "545f20", "parent": "PF-14", "said_by": "email_lead"},
    {"kind": "follow-up", "ref": "9", "title": "Test a paid email button", "quote": "not tested yet",
     "session": "545f20", "parent": "PF-14", "person": "email_lead"},
    {"kind": "context", "ref": "pass", "title": "Passed on, off and restart", "quote": "all green",
     "session": "545f20", "parent": "PF-16"},
    {"kind": "issue", "ref": "13", "title": "The confirmation lands under the pill", "quote": "leave it",
     "session": "545f20"},
    {"kind": "issue", "ref": "12", "title": "Email shots come out 100 px short", "quote": "the footer is cut",
     "session": "a1b2c3", "person": "designer"},
]
NOT_DEV = {"schema": 1, "kind": "tasks", "reviewer": "email_lead", "item": "TSK-20261028183000-settle-a-claim",
           "verdict": {"event": "create", "item": {"id": "TSK-20261028183000-settle-a-claim", "title": "Settle a claim",
                                                   "status": "todo", "tags": ["ops"], "links": [], "parent": ""}},
           "notes": "", "created": "2026-10-28T18:30:00Z", "via": "test"}


def run(root, *argv):
    out, err = io.StringIO(), io.StringIO()
    code = dev_issues.main(list(argv) + ["--root", root], out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def listing(root):
    d = os.path.join(root, TASKS)
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


def records(root):
    return [(f, json.loads(pf18.read(os.path.join(root, TASKS, f)))) for f in listing(root) if f.endswith(".json")]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REAL, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def file_items(root, items=None, now="2026-10-29T07:00:00Z"):
    path = os.path.join(root, "items.json")
    pf18.write(root, "items.json", json.dumps(items or ITEMS))
    return run(root, "file", path, "--by", "developer", "--now", now)


def ids_by_title(root):
    items, _n = dev_queue.dev_items(root)
    return dict((e["title"], e["id"]) for e in items)


class Filing(unittest.TestCase):
    """(a)(b)(c)"""

    def setUp(self):
        self.root = pf18.fixture()
        self.addCleanup(shutil.rmtree, self.root, True)
        pf18.write(self.root, TASKS + "20261028T183000Z--email_lead--TSK-20261028183000-settle-a-claim.json",
                   json.dumps(NOT_DEV))

    def test_a_one_record_per_item_sorted(self):
        code, out, err = file_items(self.root)
        self.assertEqual(code, 0, err)
        recs = [r for f, r in records(self.root) if r["reviewer"] == "developer"]
        creates = [r for r in recs if r["verdict"]["event"] == "create"]
        comments = [r for r in recs if r["verdict"]["event"] == "comment"]
        self.assertEqual(len(creates), 9, "5 issues + 3 follow-ups + 1 context note on a card")
        self.assertEqual(len(comments), 3, "2 proposed fixes + 1 context note on an issue")
        kinds = [r["verdict"]["item"]["tags"] for r in sorted(creates, key=lambda r: r["created"])]
        self.assertEqual([t[1] for t in kinds], ["issue"] * 5 + ["follow-up"] * 3 + ["context"],
                         "issues filed first, so a follow-up can name an issue of the same list")
        self.assertTrue(all(t[0] == "dev" for t in kinds))
        stamps = [r["created"] for r in recs]
        self.assertEqual(len(set(stamps)), len(stamps), "one second apart: no two records share a name stamp")
        by = dict((r["verdict"]["item"]["title"], r["verdict"]["item"]) for r in creates)
        one = by["A fresh copy has no email pictures"]
        self.assertRegex(one["id"], TASK_ID_RE)
        self.assertEqual((one["status"], one["assignees"], one["parent"], one["links"]), ("proposed", [], "", []))
        self.assertEqual((one["source"], one["requested_by"], one["by"]), ("ai-triage", "developer", "developer"))
        self.assertTrue(one["body"].endswith("Source session: 545f20\nQuote (developer):\n" + QUOTE_1), "quote verbatim")
        self.assertTrue(one["body"].startswith("Shots are taken with broken images.\n\n"))
        follow = by["Correct I-241 (drive timeout FYI): the trigger was not a download"]
        self.assertEqual((follow["status"], follow["assignees"]), ("todo", ["designer"]))
        self.assertEqual(follow["parent"], by["The email list hung for 9 minutes"]["id"], "11b rides on 11a")
        on_card = by["A page can press another page type's buttons"]
        self.assertEqual(on_card["links"], [{"type": "card",
                                             "ref": "new-workflow-design/builds/page-features/task-cards.md#PF-14"}])
        self.assertIn("Quote (email_lead):", on_card["body"])
        note = by["Passed on, off and restart"]
        self.assertEqual((note["status"], note["tags"]), ("done", ["dev", "context"]), "a fact on a card: its own task")
        texts = sorted(r["verdict"]["text"] for r in comments)
        self.assertEqual(texts, ["Context: 12 old emails miss pictures on Drive itself",
                                 "Proposed fix: A fresh checkout pulls the pictures in the background",
                                 "Proposed fix: No shot while a picture is missing"])
        self.assertTrue(all(r["item"] == one["id"] for r in comments))
        self.assertIn("Filed 12 records", out)
        self.assertIn("follow-up  11b", out)
        self.assertEqual(out.count("  wrote " + TASKS), 12, "it prints every path it wrote")

    def test_b_dry_run_writes_nothing(self):
        before = listing(self.root)
        pf18.write(self.root, "items.json", json.dumps(ITEMS))
        code, out, err = run(self.root, "file", os.path.join(self.root, "items.json"), "--by", "developer", "--dry-run",
                             "--now", "2026-10-29T07:00:00Z")
        self.assertEqual(code, 0, err)
        self.assertEqual(listing(self.root), before)
        self.assertIn("Would file 12 records", out)
        self.assertIn("dry run, nothing written", out)
        self.assertEqual(out.count("  would write " + TASKS), 12)
        code, out, err = run(self.root, "file", os.path.join(self.root, "items.json"), "--by", "developer", "--dry-run",
                             "--json")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(json.loads(out)["records"]), 12)
        self.assertEqual(listing(self.root), before)

    def test_c_one_bad_item_refuses_the_list(self):
        before = listing(self.root)
        bad = [dict(ITEMS[1]),
               {"kind": "bug", "title": "x", "quote": "q", "session": "s"},
               {"kind": "issue", "title": "no quote", "session": "s"},
               {"kind": "issue", "title": "no session", "quote": "q"},
               {"kind": "follow-up", "title": "nobody", "quote": "q", "session": "s"},
               {"kind": "context", "title": "floating fact", "quote": "q", "session": "s"},
               {"kind": "issue", "title": "unknown card", "quote": "q", "session": "s", "parent": "PF-99"},
               {"kind": "follow-up", "title": "outsider", "quote": "q", "session": "s", "person": "vendor"},
               {"kind": "issue", "title": "typo", "quote": "q", "session": "s", "parnet": "PF-14"},
               {"kind": "issue", "title": "issue on issue", "quote": "q", "session": "s", "parent": "1"},
               {"kind": "follow-up", "title": "fixes", "quote": "q", "session": "s", "person": "developer", "fixes": ["x"]}]
        code, out, err = file_items(self.root, bad)
        self.assertEqual(code, 2)
        self.assertEqual(listing(self.root), before, "nothing written")
        for words in ("item 2: kind 'bug'", "item 3: no quote", "item 4: no source session",
                      "item 5: a follow-up needs its person", "item 6: a context note rides on its issue or card",
                      "item 7: card PF-99 is in no deck", "item 8: person 'vendor'", "item 9: unknown key parnet",
                      "item 10: an issue on an issue", "item 11: only an issue holds proposed fixes"):
            self.assertIn(words, err)
        code, out, err = run(self.root, "file", os.path.join(self.root, "missing.json"), "--by", "developer")
        self.assertEqual(code, 3)
        code, out, err = file_items(self.root, [ITEMS[1]])
        self.assertEqual(code, 0, err)
        code, out, err = run(self.root, "file", os.path.join(self.root, "items.json"), "--by", "nobody")
        self.assertEqual(code, 2)
        self.assertIn("--by 'nobody'", err)


class Moves(unittest.TestCase):
    """(d)(e)(f)"""

    @classmethod
    def setUpClass(cls):
        cls.root = pf18.fixture()
        pf18.write(cls.root, TASKS + "20261028T183000Z--email_lead--TSK-20261028183000-settle-a-claim.json",
                   json.dumps(NOT_DEV))
        code, out, err = file_items(cls.root)
        assert code == 0, err
        cls.ids = ids = ids_by_title(cls.root)
        cls.one, cls.hang = ids["A fresh copy has no email pictures"], ids["The email list hung for 9 minutes"]
        cls.pill, cls.crop = ids["The confirmation lands under the pill"], ids["Email shots come out 100 px short"]
        cls.follow = ids["Correct I-241 (drive timeout FYI): the trigger was not a download"]
        cls.cache = ids["Restore the picture cache set aside in the test"]
        r = cls.root
        cls.codes = [
            run(r, "discussing", cls.one, "--by", "developer", "--with", "email_lead", "--with", "designer", "--now",
                "2026-10-29T08:00:00Z"),
            run(r, "discussing", cls.hang, "--by", "developer", "--note", "cause unknown", "--now", "2026-10-29T08:00:00Z"),
            run(r, "wont", cls.pill, "--by", "developer", "--reason", "developer: \"leave it\"", "--now", "2026-10-29T08:01:00Z"),
            run(r, "card", cls.crop, "PF-5", "--by", "developer", "--now", "2026-10-29T08:02:00Z"),
            run(r, "done", cls.follow, "--by", "designer", "--now", "2026-10-29T08:03:00Z"),
            run(r, "fix", cls.hang, "A 60-second timeout guards the call", "--by", "developer", "--now",
                "2026-10-29T08:04:00Z")]
        cls.doc = dev_queue.build(cls.root, now="2026-10-29T09:00:00Z")
        cls.items = dict((e["id"], e) for e in cls.doc["issues"])
        cls.cards = pf18.by_id(cls.doc)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, True)

    def test_d_moves(self):
        for code, out, err in self.codes:
            self.assertEqual(code, 0, err)
        e = self.items
        self.assertEqual((e[self.one]["state"], e[self.one]["status"], e[self.one]["assignees"]),
                         ("discussing", "in_progress", ["email_lead", "designer"]))
        self.assertEqual(e[self.hang]["state"], "discussing")
        self.assertEqual((e[self.pill]["state"], e[self.pill]["reason"]), ("wont-do", "developer: \"leave it\""),
                         "Won't do keeps its reason")
        self.assertEqual((e[self.crop]["state"], e[self.crop]["carded_as"], e[self.crop]["carded_as_tag"]),
                         ("carded", "PF-5", "mock carries features"))
        self.assertEqual(e[self.follow]["state"], "done", "a follow-up ticked done")
        self.assertEqual(e[self.cache]["state"], "raised")
        self.assertEqual([f["text"] for f in e[self.hang]["fixes"]], ["A 60-second timeout guards the call"])
        self.assertIn("shows \"from issue Email shots come out 100 px short\"", self.codes[3][1])

    def test_d_refused_moves(self):
        r, before = self.root, listing(self.root)
        for argv, words in (
                (["card", self.follow, "PF-5"], "a follow-up is never carded"),
                (["done", self.one], "never ticked done"),
                (["card", self.crop, "PF-6"], "is carded already"),
                (["discussing", self.pill], "is wont-do already"),
                (["card", self.hang, "PF-99"], "card PF-99 is in no deck"),
                (["wont", self.hang], "Won't do keeps its reason"),
                (["discussing", self.cache], "never Discussing"),
                (["fix", self.cache, "x"], "only an issue holds proposed fixes"),
                (["discussing", "TSK-20261028183000-settle-a-claim"], "is no dev task"),
                (["discussing", self.hang, "--with", "vendor"], "--with vendor")):
            code, out, err = run(r, *(argv + ["--by", "developer"]))
            self.assertEqual(code, 2, (argv, out))
            self.assertIn(words, err, argv)
        code, out, err = run(r, "card", self.one, "PF-5", "--by", "developer", "--dry-run", "--now", "2026-10-29T11:00:00Z")
        self.assertEqual(code, 0, err)
        self.assertIn("Would file 2 records", out)
        self.assertEqual(listing(r), before, "refusals and a dry run write nothing")

    def test_e_the_tasks_kinds_own_records(self):
        kind = json.loads(pf18.read(os.path.join(REAL, "platform/data/kinds/tasks.json")))
        fields = dict((f["key"], f) for f in kind["verdict_fields"])
        link_types = re.search(r"\{type: ([a-z|]+), ref\}", fields["add"]["note"]).group(1).split("|")
        check = load("check_record_names", "new-workflow-design/builds/records-plane/check_record_names.py")
        mine = [(f, r) for f, r in records(self.root) if r.get("via") == dev_issues.VIA]
        self.assertTrue(mine)
        for f, r in mine:
            self.assertEqual(sorted(r), ["created", "item", "kind", "notes", "reviewer", "schema", "verdict", "via"])
            self.assertEqual((r["schema"], r["kind"]), (1, "tasks"))
            v = r["verdict"]
            self.assertIn(v["event"], fields["event"]["values"])
            for key, spec in fields.items():
                if spec.get("required_when") == "event=" + v["event"]:
                    self.assertIn(key, v, (f, key))
            if v["event"] == "status":
                self.assertIn(v["to"], fields["to"]["values"])
            if v["event"] == "link":
                self.assertIn(v["add"]["type"], link_types)
            nid = check.name_id(f)
            self.assertTrue(nid == r["item"] or nid.startswith(r["item"] + "--"), f)
            self.assertTrue(f.startswith(r["created"].replace("-", "").replace(":", "") + "--" + r["reviewer"] + "--"))
        mytasks = load("mytasks_for_pf18c", "new-workflow-design/builds/pm-tool/mytasks.py")
        by_item = {}
        for f, r in records(self.root):
            by_item.setdefault(r["item"], []).append(r)
        crop = mytasks.fold_task(self.crop, None, by_item[self.crop])
        self.assertEqual(crop["status"], "done")
        self.assertIn({"type": "card", "ref": "new-workflow-design/builds/page-features/task-cards.md#PF-5"},
                      crop["links"])
        one = mytasks.fold_task(self.one, None, by_item[self.one])
        self.assertEqual((one["status"], one["assignees"], "dev" in one["tags"]),
                         ("in_progress", ["email_lead", "designer"], True), "the PM board folds the same task")

    def test_f_dev_queue_reads_them(self):
        e = self.items
        self.assertNotIn("TSK-20261028183000-settle-a-claim", e, "a task with no dev tag is not an issue")
        self.assertEqual(self.doc["sources"]["tasks_dir"], "platform/data/records/tasks")
        self.assertEqual(self.doc["columns_after"]["issue-queue"], "PF-18c (issue queue)")
        one = e[self.one]
        self.assertEqual((one["quote"], one["session"], one["said_by"], one["detail"]),
                         (QUOTE_1, "545f20", "developer", "Shots are taken with broken images."))
        self.assertEqual([c["text"] for c in one["context"]], ["12 old emails miss pictures on Drive itself"])
        self.assertEqual(len(one["fixes"]), 2)
        self.assertEqual(e[self.hang]["follow_ups"], [self.follow], "11b rides on 11a")
        pf5, pf14, pf16 = self.cards["PF-5"], self.cards["PF-14"], self.cards["PF-16"]
        self.assertEqual([i["id"] for i in pf5["from_issues"]], [self.crop], "the card shows from issue …")
        self.assertEqual([i["title"] for i in pf14["issues"]], ["A page can press another page type's buttons"])
        self.assertEqual([(f["title"], f["assignees"]) for f in pf14["follow_ups"]],
                         [("Test a paid email button", ["email_lead"])])
        self.assertEqual([c["title"] for c in pf16["context"]], ["Passed on, off and restart"])
        self.assertEqual(self.cards["PF-4"]["from_issues"], [])
        decl = serve.sources("dev-queue", REAL)
        self.assertIn("platform/data/records/tasks/*.json", decl["dev-queue"]["watch"])
        src = serve.Sources(decl, root=self.root)
        before = src.stamp("dev-queue")
        code, out, err = run(self.root, "fix", self.one, "Another idea", "--by", "email_lead", "--now", "2026-10-29T10:00:00Z")
        self.assertEqual(code, 0, err)
        self.assertNotEqual(src.stamp("dev-queue"), before, "a new task record moves the page's stamp")


PAGE_RUN = r"""
(async () => {
  for (let i = 0; i < 5; i++) await tick();
  const col = g("col-issue-queue"), words = e => e.textContent.replace(/\s+/g, " ").trim();
  const out = {asked: asked, errors: errors};
  out.tiles = find(col, e => e.getAttribute("data-issue")).map(e => e.getAttribute("data-issue"));
  out.groups = find(col, e => e.classList.contains("queue-group")).map(words);
  out.closed = find(col, e => e.tagName === "DETAILS").map(d => ({summary: words(d.children[0]),
    open: d.open, tiles: find(d, e => e.getAttribute("data-issue")).map(e => e.getAttribute("data-issue"))}));
  out.words = words(col);
  out.count = words(find(col, e => e.classList.contains("column-count"))[0]);
  out.summary = words(g("summary"));
  out.up_next = words(g("col-up-next"));
  const buttons = every().filter(e => e.tagName === "BUTTON");
  out.button_kinds = [...new Set(buttons.map(b => b.className))].sort();
  out.copies_in_queue = find(col, e => e.className === "copy-button").length;
  find(col, e => e.className === "copy-button")[0].fire("click");
  await tick();
  out.copied = copied.slice();
  const openOf = id => buttons.find(b => b.className === "tile-open" && b.getAttribute("aria-label").indexOf("Open " + id + " (") === 0);
  out.panels = {};
  for (const id of ["PF-5", "PF-14", "PF-16"]) { openOf(id).fire("click"); out.panels[id] = words(g("panel-content")); g("panel").close(); }
  const email_lead = find(g("name-options"), e => e.tagName === "INPUT" && e.getAttribute("value") === "email_lead")[0];
  email_lead.checked = true;
  email_lead.fire("change");
  out.email_lead = find(g("col-issue-queue"), e => e.getAttribute("data-issue")).map(e => e.getAttribute("data-issue"));
  console.log(JSON.stringify(out));
})().catch(e => console.log(JSON.stringify({errors: [String(e.stack || e)].concat(errors)})));
"""

PAGE_EMPTY = r"""
(async () => {
  for (let i = 0; i < 5; i++) await tick();
  const col = g("col-issue-queue");
  console.log(JSON.stringify({errors: errors, words: col.textContent.replace(/\s+/g, " ").trim(),
    tiles: find(col, e => e.getAttribute("data-issue")).map(e => e.getAttribute("data-issue"))}));
})().catch(e => console.log(JSON.stringify({errors: [String(e.stack || e)].concat(errors)})));
"""


class Page(unittest.TestCase):
    """(p) the template's own script on the moved fixture's data (skipped where there is no node)."""

    setUpClass = classmethod(Moves.setUpClass.__func__)
    tearDownClass = classmethod(Moves.tearDownClass.__func__)

    def test_p_the_page_draws_the_queue(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("no node on this machine")
        harness = pf18.PAGE_HARNESS.split("(async () => {")[0] + PAGE_RUN
        pf18.write(self.root, "data.json", json.dumps(self.doc))
        pf18.write(self.root, "harness.js", harness)
        p = subprocess.run([node, os.path.join(self.root, "harness.js"), os.path.join(REAL, TPL, "dev-queue.html"),
                            os.path.join(self.root, "data.json")], capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        got = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(got["errors"], [])
        self.assertEqual(got["asked"], [["/data/dev-queue", "GET"], ["/stamp/dev-queue", "GET"]], "reads, never writes")
        # narrowed by DQ-5 (human acts): the queue holds issues only; open follow-ups are acts in Up next
        self.assertEqual(got["groups"], ["Discussing · 2", "Raised · 1"])
        self.assertEqual(got["count"], "3", "open issues only")
        # narrowed by PF-18m (open issues only): Won't do was a collapsed group; now it is not drawn, record kept
        self.assertEqual(got["closed"], [], "no closed group in the queue")
        self.assertNotIn(self.pill, got["tiles"], "a Won't do issue leaves the queue")
        self.assertEqual(dict((e["id"], e) for e in self.doc["issues"])[self.pill]["state"], "wont-do",
                         "its record is kept in the data")
        self.assertNotIn(self.crop, got["tiles"], "a carded issue leaves the queue")
        self.assertNotIn(self.follow, got["tiles"], "a follow-up on an issue rides inside it")
        self.assertNotIn(self.cache, got["tiles"], "DQ-5 (human acts): a parentless follow-up is an act, not a queue tile")
        self.assertIn("✋ Human act", got["up_next"], "DQ-5 (human acts): it is drawn in Up next")
        for words in ("“what i meant by do it next", "session 545f20", "With email_lead & designer",
                      "Proposed No shot while a picture is missing", "Context 12 old emails miss pictures",
                      "Follow-up designer: Correct I-241 (drive timeout FYI)", "on PF-14 (page server)"):
            self.assertIn(words, got["words"])
        self.assertNotIn("Won't do developer: \"leave it\"", got["words"], "PF-18m (open issues only): not drawn")
        self.assertTrue(got["summary"].startswith("3 open in the issue queue"), got["summary"])
        self.assertIn("from issue %s · Email shots come out 100 px short" % self.crop, got["up_next"])
        # narrowed for DQ-7 (folded columns): each column's header is its fold button, a view toggle that writes nothing
        # narrowed for DQ-8 (act panel): a human act's tile opens its act panel (act-open), a view that writes nothing
        self.assertEqual(got["button_kinds"], ["act-open", "card-chip", "column-toggle", "copy-button", "tile-open"],
                         "no new kind of button but the folds and the act tile's open button")
        self.assertEqual(got["copies_in_queue"], len(got["tiles"]), "every issue tile has Copy for Claude")
        # narrowed by DQ-6 (built by label)'s order rule: the Issue queue is a queue, oldest raised first
        self.assertIn("Summarize dev issue \"A fresh copy has no email pictures\"", got["copied"][0], "oldest Discussing first")
        self.assertIn("From issue · 1", got["panels"]["PF-5"])
        self.assertIn("Open issues on this card · 1", got["panels"]["PF-14"])
        self.assertIn("Follow-ups · 1 email_lead: Test a paid email button · open", got["panels"]["PF-14"])
        self.assertIn("Context · 1 Passed on, off and restart", got["panels"]["PF-16"])
        self.assertEqual(sorted(got["email_lead"]), sorted([self.one, ids_by_title(self.root)[
            "A page can press another page type's buttons"]]), "the name filter: raised by or with email_lead")

    def test_p_an_empty_queue_says_where_issues_come_from(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("no node on this machine")
        doc = dict(self.doc, issues=[])
        pf18.write(self.root, "empty.json", json.dumps(doc))
        pf18.write(self.root, "harness.js", pf18.PAGE_HARNESS.split("(async () => {")[0] + PAGE_EMPTY)
        p = subprocess.run([node, os.path.join(self.root, "harness.js"), os.path.join(REAL, TPL, "dev-queue.html"),
                            os.path.join(self.root, "empty.json")], capture_output=True, text=True, timeout=60)
        got = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(got["errors"], [])
        self.assertEqual(got["tiles"], [])
        self.assertIn("Nothing raised yet", got["words"])
        self.assertIn("filing step files a session's list", got["words"])


class AtHead(unittest.TestCase):
    """(g) this repo, read-only."""

    def test_g_show_and_a_dry_run_write_nothing(self):
        before = listing(REAL)
        code, out, err = run(REAL, "show")
        self.assertEqual(code, 0, err)
        item = {"kind": "issue", "title": "A dry-run probe", "quote": "probe", "session": "test", "parent": "PF-18"}
        tmp = tempfile.mkdtemp(prefix="pf18c-probe-")
        self.addCleanup(shutil.rmtree, tmp, True)
        path = os.path.join(tmp, "items.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([item], fh)
        code, out, err = run(REAL, "file", path, "--by", "developer", "--dry-run")
        self.assertEqual(code, 0, err)
        self.assertIn("Would file 1 record", out)
        self.assertIn("on PF-18 (", out)
        self.assertEqual(listing(REAL), before, "no real task record written")

    def test_g_the_catalog(self):
        doc = features.load(os.path.join(REAL, TPL, "dev-queue.features.json"))
        self.assertEqual(features.validate(doc), [])
        seven = [e for e in doc["features"] if e["n"] == 7][0]
        self.assertEqual((seven["kind"], seven["state"], seven["source"]["field"]), ("data", "wired", "issues"))
        text = pf18.read(os.path.join(REAL, TPL, "dev-queue.html"))
        self.assertEqual(features.sync_text(text, doc), text, "the embedded catalog is the family list")


if __name__ == "__main__":
    unittest.main()
