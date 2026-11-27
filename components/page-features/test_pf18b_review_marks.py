#!/usr/bin/env python3
"""PF-18b (review marks): Understood, Question, Issue and Resolve on the dev-queue board, each one review record.

    python3 components/page-features/test_pf18b_review_marks.py

    (a) the four marks fit the FROZEN review kind (RV-1 (review kind manifest)): each body passes the review module's
        own validate against platform/data/kinds/review.json, which this card never edits
    (b) each button through the page server: kit/serve.py's Act runs the dev-queue run table's entry (SCRIPTS
        "review") as the server's own person, the real dev_queue.py mark files exactly ONE record by the review
        module's file_record (committed, its own commit subject), and the board moves the card: Shipped → Flagged on
        a Question or Issue, back on a Resolve, Reviewed on both reviewers' Understood; one latest mark per person
    (c) Resolve is refused for anyone but the raiser or developer, and nothing is written; a card not shipped, or another
        family's card shipped before the cutoff, takes no mark (narrowed by PF-18f (earlier PF review))
    (d) the kit's checks: the argv is built by the kit (mark, card, word, --by the kit's person, --note= or --of=),
        never --root; a non-card item, a Resolve without a person, a field, a bad note, an entry with a mark not in
        the list are refused before anything runs
    (e) the real family at HEAD: the run table holds the four quick marks, each wired action has its entry, the page
        carries kit/act.js whole and passes the share check's run-entry rule
    (p) the page in node on a board with marks: Flagged shows the flag with its Resolve, Shipped's line reads each
        reviewer's mark, Understood · Question · Issue sit in the shipped card's panel (the board's only mark button
        is an open mark's Resolve, so PF-18c (issue queue)'s "no new kind of button" on the board holds), and a click
        calls pfAct with the mark's number and the card

The fixture repo is test_pf18_dev_queue.py's (a test file). Stdlib only, Python 3.9. Writes only in temp folders;
no network: the review key is removed from every environment here, so the module's git door is the one used.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "kit"))
import dev_queue  # noqa: E402
import features  # noqa: E402
import live  # noqa: E402
import serve  # noqa: E402
import share  # noqa: E402
import test_pf18_dev_queue as pf18  # noqa: E402  the fixture repo, kept in its test file

REAL = features.ROOT
TPL = "platform/views/viewers/_templates/"
MANIFEST = "platform/data/kinds/review.json"
RECORDS = "platform/data/records/review"
NO_KEY = ("REVIEWER_KEY_TEAM", "AI_WORKSPACE")
# what a fixture workspace needs to run the real data command and the real review module from its own root
COPY = ("components/page-features/dev_queue.py", "components/review/review_request.py",
        "platform/workers/mini-worker/plane_caps.py", MANIFEST, TPL + "dev-queue.actions.json")


def env_for(root):
    env = dict((k, v) for k, v in os.environ.items() if k not in NO_KEY)
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "HOME": root, "GIT_AUTHOR_NAME": "Page Server",
                "GIT_AUTHOR_EMAIL": "server@example.com", "GIT_COMMITTER_NAME": "Page Server",
                "GIT_COMMITTER_EMAIL": "server@example.com"})
    return env


def workspace():
    """test_pf18's fixture repo plus the real data command, review module, its cap and its manifest, and the
    family's run table, so the page server's argv runs exactly as it would on a person's copy."""
    root = pf18.fixture()
    for rel in COPY:
        os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True)
        shutil.copy(os.path.join(REAL, rel), os.path.join(root, rel))
    shutil.copytree(os.path.join(REAL, "components/run-kit/run_kit"), os.path.join(root, "components/run-kit/run_kit"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    return root


def next_second():
    """Marks are stamped to the second; each step waits for a new one so no two records share a stamp."""
    t = time.time()
    time.sleep(1.02 - (t - int(t)))


class Grammar(unittest.TestCase):
    """(a)"""

    def test_a_every_mark_is_frozen_grammar(self):
        rv = dev_queue.review_module()
        with open(os.path.join(REAL, MANIFEST), encoding="utf-8") as fh:
            fields = dict((f["key"], f) for f in json.load(fh)["verdict_fields"])
        for word, shape in dev_queue.MARKS.items():
            body = dict(shape, reasons=[word], note="one line")
            if word == "resolve":
                body["reasons"].append(dev_queue.OF + "email_lead")
            rv.validate(body)                              # the module's own door, the manifest's own words
            self.assertIn(body["event"], fields["event"]["values"])
            if body["event"] == "verdict":
                self.assertIn(body["verdict"], fields["verdict"]["values"])
            elif body["event"] == "seen":                  # DQ-3 (note mark): no judgment, no disposition
                self.assertEqual(word, "note")
                self.assertNotIn("verdict", body)
                self.assertNotIn("decision", body)
            else:
                self.assertIn(body["decision"], fields["decision"]["values"])
            self.assertEqual(set(body) - set(fields), set(), "%s: no key the manifest does not declare" % word)
        # narrowed for DQ-8 (act panel): the kit's word list is the marks plus Done, which writes no review record
        self.assertEqual(sorted(tuple(dev_queue.MARKS) + dev_queue.ACT_WORDS), sorted(serve.REVIEW_MARKS))
        self.assertTrue(rv.ITEM_RE.match(dev_queue.MARK_ITEM + "PF-18b"))

    def test_a_the_manifest_is_untouched(self):
        p = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", MANIFEST], cwd=REAL)
        self.assertEqual(p.returncode, 0, "RV-1 (review kind manifest) is frozen: this card never edits it")


class Buttons(unittest.TestCase):
    """(b) (c) through kit/serve.py's Act and the real data command, in one fixture workspace."""

    @classmethod
    def setUpClass(cls):
        cls.root = workspace()
        cls.rv = dev_queue.review_module()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, True)

    def run_cmd(self, argv):
        p = subprocess.run(argv, cwd=self.root, capture_output=True, text=True, env=env_for(self.root), timeout=120,
                           stdin=subprocess.DEVNULL)
        return p.returncode, (p.stdout or "") + (p.stderr or "")

    def press(self, person, n, card, value=""):
        """One click: the page server's Act for this person, exactly the body pfAct posts."""
        next_second()
        act = serve.Act("dev-queue", self.root, person, None, runner=self.run_cmd)
        return act.run({"family": "dev-queue", "n": n, "item": card, "value": value})

    def records(self):
        return self.rv.read_records(root=self.root)

    def board(self):
        return pf18.by_id(dev_queue.build(self.root, now=pf18.NOW))

    def pressed(self, person, n, card, value=""):
        """A click that must save: one more record, from this person, by the module; the board after it."""
        before = len(self.records())
        got = self.press(person, n, card, value)
        self.assertTrue(got["ok"], got)
        recs = self.records()
        self.assertEqual(len(recs), before + 1, "one click, one record")
        rec = recs[-1]
        self.assertEqual((rec["reviewer"], rec["item"], rec["via"], rec["kind"]),
                         (person, "RQ-dev-queue-" + card, self.rv.VERSION, "review"))
        log = subprocess.run(["git", "log", "-1", "--format=%s", "--name-only"], cwd=self.root, capture_output=True,
                             text=True, env=env_for(self.root)).stdout.split("\n")
        self.assertTrue(log[0].startswith("review: %s RQ-dev-queue-%s" % (rec["verdict"]["event"], card)), log)
        self.assertEqual([x for x in log[1:] if x.strip()], [RECORDS + "/" + self.rv.filename(rec)],
                         "the module's commit carries the one record and nothing else")
        return rec, self.board()

    def test_b_c_each_button_writes_one_record_and_moves_the_card(self):
        c = self.board()
        self.assertEqual((c["PF-15"]["column"], c["PF-15"]["marks"]), ("shipped", []))

        rec, c = self.pressed("email_lead", 20, "PF-15")
        self.assertEqual(rec["verdict"], {"event": "verdict", "verdict": "approve", "reasons": ["understood"]})
        self.assertEqual(c["PF-15"]["column"], "shipped", "one reviewer's Understood is not Reviewed")
        self.assertEqual([(r["person"], r["understood"]) for r in c["PF-15"]["review"]],
                         [("email_lead", True), ("designer", None)])

        rec, c = self.pressed("designer", 21, "PF-15", "what does quick mean here?")
        self.assertEqual(rec["verdict"], {"event": "verdict", "verdict": "fix", "reasons": ["question"],
                                          "note": "what does quick mean here?"})
        self.assertEqual(c["PF-15"]["column"], "flagged", "an open Question moves the card to Flagged")
        self.assertEqual([(m["person"], m["mark"], m.get("open")) for m in c["PF-15"]["marks"]],
                         [("email_lead", "understood", None), ("designer", "question", True)])

        n = len(self.records())
        got = self.press("email_lead", 23, "PF-15", "designer")
        self.assertFalse(got["ok"], "email_lead did not raise it and is not developer")
        self.assertIn("REFUSED: Resolve belongs to whoever raised the mark (designer)", got["said"])
        self.assertEqual(len(self.records()), n, "a refused Resolve writes nothing")
        self.assertEqual(self.board()["PF-15"]["column"], "flagged")

        rec, c = self.pressed("developer", 23, "PF-15", "designer")
        self.assertEqual(rec["verdict"], {"event": "close", "decision": "accepted",
                                          "reasons": ["resolve", "of:designer"]})
        self.assertEqual(c["PF-15"]["column"], "shipped", "resolved: back to Shipped, designer has not understood")
        v = [m for m in c["PF-15"]["marks"] if m["person"] == "designer"][0]
        self.assertEqual((v["open"], v["resolved_by"]), (False, "developer"))

        rec, c = self.pressed("designer", 22, "PF-15", "the copy fallback is gone")
        self.assertEqual(rec["verdict"]["verdict"], "reject")
        self.assertEqual(c["PF-15"]["column"], "flagged", "a new Issue after the Resolve is open again")
        self.assertEqual(len([m for m in c["PF-15"]["marks"] if m["person"] == "designer"]), 1,
                         "one latest mark per person per card")

        rec, c = self.pressed("designer", 23, "PF-15", "designer")
        self.assertEqual(c["PF-15"]["column"], "shipped", "the raiser resolves her own")

        rec, c = self.pressed("designer", 20, "PF-15")
        self.assertEqual(c["PF-15"]["column"], "reviewed", "both reviewers Understood → Reviewed")
        self.assertEqual([r["understood"] for r in c["PF-15"]["review"]], [True, True])
        self.assertIn("marked understood", [h["what"] for h in c["PF-15"]["history"]])

        rec, c = self.pressed("editor", 21, "PF-15")
        self.assertEqual(c["PF-15"]["column"], "flagged", "a Question from anyone flags it")
        self.assertNotIn("editor", [r["person"] for r in c["PF-15"]["review"]], "the review line is the two reviewers")
        got = self.press("designer", 23, "PF-15", "editor")
        self.assertFalse(got["ok"])
        self.assertIn("REFUSED", got["said"])
        rec, c = self.pressed("editor", 23, "PF-15", "editor")
        self.assertEqual(c["PF-15"]["column"], "reviewed")

        # scope: shipped cards on the board only. Narrowed by PF-18f (earlier PF review): PF-4b, a PF card shipped
        # before the cutoff, now takes marks (test_pf18f_earlier_pf.py); LD-1, another family's, is still refused
        for card in ("PF-5", "LD-1"):                    # up next; another family's card shipped before the cutoff
            n = len(self.records())
            got = self.press("email_lead", 20, card)
            self.assertFalse(got["ok"], card)
            self.assertIn("is not a card shipped since 2026-10-27T00:00:00Z", got["said"])
            self.assertEqual(len(self.records()), n)
        self.assertEqual(self.board()["PF-16"]["column"], "shipped", "marks on PF-15 never touch PF-16")

    def test_c_resolve_rules_in_the_data_command(self):
        root = workspace()
        self.addCleanup(shutil.rmtree, root, True)
        rv = self.rv
        env = dict((k, v) for k, v in os.environ.items() if k not in NO_KEY)
        dev_queue.mark(root, "PF-16", "issue", "email_lead", note="broken", env=env, commit=False, now="2026-10-29T01:00:00Z")
        dev_queue.mark(root, "PF-16", "question", "designer", env=env, commit=False, now="2026-10-29T01:00:01Z")
        for by, of in (("designer", "email_lead"), ("editor", "email_lead"), ("editor", None)):
            with self.assertRaises(rv.Refused, msg=(by, of)):
                dev_queue.mark(root, "PF-16", "resolve", by, of=of, env=env, commit=False, now="2026-10-29T01:00:02Z")
        with self.assertRaises(rv.Refused):
            dev_queue.mark(root, "PF-16", "resolve", "developer", env=env, commit=False, now="2026-10-29T01:00:02Z")
        with self.assertRaises(rv.Refused):
            dev_queue.mark(root, "PF-16", "understood", "email_lead", of="email_lead", env=env, commit=False)
        with self.assertRaises(rv.Refused):
            dev_queue.mark(root, "PF-16", "approve", "email_lead", env=env, commit=False)
        with self.assertRaises(rv.Refused):
            dev_queue.mark(root, "PF-16", "question", "email_lead", note="x" * 201, env=env, commit=False)
        self.assertEqual(len(rv.read_records(root=root)), 2, "every refusal before the write")
        out = dev_queue.mark(root, "PF-16", "resolve", "email_lead", env=env, commit=False, now="2026-10-29T01:00:03Z")
        self.assertEqual(out["record"]["verdict"]["reasons"], ["resolve", "of:email_lead"], "your own by default")
        out = dev_queue.mark(root, "PF-16", "resolve", "developer", env=env, commit=False, now="2026-10-29T01:00:04Z")
        self.assertEqual(out["record"]["verdict"]["reasons"], ["resolve", "of:designer"],
                         "developer with one open mark resolves it")
        self.assertEqual(pf18.by_id(dev_queue.build(root, now=pf18.NOW))["PF-16"]["column"], "shipped")


class KitChecks(unittest.TestCase):
    """(d) Act.build only: nothing runs."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pf18b-kit-")
        self.addCleanup(shutil.rmtree, self.root, True)
        with open(os.path.join(REAL, TPL, "dev-queue.actions.json"), encoding="utf-8") as fh:
            self.table(json.load(fh))
        self.act = serve.Act("dev-queue", self.root, "email_lead", None, runner=lambda argv: (0, "ran"))

    def table(self, doc):
        p = os.path.join(self.root, TPL, "dev-queue.actions.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)

    def build(self, n, item, value="", **more):
        body = dict({"family": "dev-queue", "n": n, "item": item, "value": value}, **more)
        return self.act.build(body)

    def refused(self, code, n, item, value="", **more):
        with self.assertRaises(serve.Refused) as cm:
            self.build(n, item, value, **more)
        self.assertEqual(cm.exception.code, code, cm.exception.said)
        return cm.exception.said

    def test_d_the_kit_builds_the_argv(self):
        script = os.path.join(self.root, "components/page-features/dev_queue.py")
        self.assertEqual(serve.SCRIPTS["review"], "components/page-features/dev_queue.py")
        self.assertEqual(self.build(20, "PF-18b"),
                         ([sys.executable, script, "mark", "PF-18b", "understood", "--by", "email_lead"], None))
        self.assertEqual(self.build(21, "PF-15", "why quick?")[0][-1], "--note=why quick?")
        self.assertEqual(self.build(22, "MET-C43", "it broke")[0][3:5], ["MET-C43", "issue"])
        self.assertEqual(self.build(23, "PF-15", "designer")[0][-2:], ["email_lead", "--of=designer"])
        for n in (20, 21, 22, 23):
            argv = self.build(n, "PF-15", "designer")[0]
            self.assertFalse([a for a in argv if a == "--root" or a.startswith("--root=")])
            self.assertEqual(argv[5:7], ["--by", "email_lead"], "the kit's own person, never the body's")

    def test_d_refused_before_anything_runs(self):
        self.assertIn("card id", self.refused(400, 20, "brand__label"))
        self.assertIn("card id", self.refused(400, 20, "pf-15"))
        self.assertIn("whose mark", self.refused(400, 23, "PF-15", ""))
        self.assertIn("whose mark", self.refused(400, 23, "PF-15", "email_lead Smith"))
        self.refused(400, 21, "PF-15", "two\nlines")
        self.refused(400, 21, "PF-15", "-x")
        self.refused(400, 21, "PF-15", "x" * 201)
        self.refused(400, 21, "PF-15", "tab\there")
        self.refused(400, 21, "PF-15", "words", field="who")
        self.refused(403, 99, "PF-15")                         # not in the run table (24 is Note: DQ-3 (note mark))
        self.table({"direct": {"20": {"kind": "quick", "run": "review", "mark": "approve"},
                               "21": {"kind": "quick", "run": "review", "mark": "question", "fields": ["x"]}}})
        self.assertEqual(self.refused(403, 20, "PF-15"), serve.NOT_DIRECT, "a mark not in the fixed list")
        self.refused(403, 21, "PF-15", field="x")
        nobody = serve.Act("dev-queue", self.root, None, "no person for this clone")
        with self.assertRaises(serve.Refused) as cm:
            nobody.build({"family": "dev-queue", "n": 20, "item": "PF-15"})
        self.assertEqual(cm.exception.code, 403)


class RealFamily(unittest.TestCase):
    """(e) at HEAD, read-only."""

    def test_e_run_table_and_act_block(self):
        table = live.run_table("dev-queue", REAL)
        self.assertEqual(dict((n, (e[0][0], e[0][1])) for n, e in table.items()), {
            "20": ("direct", {"kind": "quick", "run": "review", "mark": "understood"}),
            "21": ("direct", {"kind": "quick", "run": "review", "mark": "question"}),
            "22": ("direct", {"kind": "quick", "run": "review", "mark": "issue"}),
            "23": ("direct", {"kind": "quick", "run": "review", "mark": "resolve"}),
            "24": ("direct", {"kind": "quick", "run": "review", "mark": "note"}),   # DQ-3 (note mark)
            "26": ("direct", {"kind": "quick", "run": "review", "mark": "done"})})   # DQ-8 (act panel): Done
        doc = features.load(os.path.join(REAL, TPL, "dev-queue.features.json"))
        self.assertEqual(live.run_entry_findings(doc, "dev-queue", table), [])
        text = pf18.read(os.path.join(REAL, TPL, "dev-queue.html"))
        span = live._act_span(text)
        self.assertEqual(text[span[0]:span[1]], "%s\n<script id=\"pf-act\">\n%s</script>\n%s" % (
            live.ACT_START, pf18.read(os.path.join(HERE, "kit", "act.js")), live.ACT_END))
        self.assertIn("window.pfAct(MARK[word].n, {item: c.id, value: value || \"\"}, {family: SOURCE", text)
        r = share.share_check(TPL + "dev-queue.html", root=REAL, runner=lambda argv, cwd: (0, "listed\n", ""),
                              scan=lambda t: [])
        self.assertIsNone(r["refused"], r)
        self.assertFalse([b for b in r["blockers"] if b["hard"]], r["blockers"])

    def test_e_sources_watch_the_marks(self):
        self.assertIn("platform/data/records/review/*.json", serve.sources("dev-queue", REAL)["dev-queue"]["watch"])


PAGE_TAIL = r"""
(async () => {
  for (let i = 0; i < 5; i++) await tick();
  const out = {asked: asked, errors: errors, columns: {}, words: {}};
  ["shipped", "flagged", "reviewed"].forEach(c => {
    out.columns[c] = tiles(c);
    out.words[c] = g("col-" + c).textContent.replace(/\s+/g, " ").trim();
  });
  const board = every().filter(e => e.tagName === "BUTTON");
  out.board_marks = board.filter(b => b.className === "mark-button").map(b => b.getAttribute("aria-label"));
  // Understood, Question and Issue sit in the card panel: open PF-16's
  board.find(b => b.className === "tile-open" && b.getAttribute("aria-label").indexOf("Open PF-16 (") === 0).fire("click");
  out.panel = g("panel-content").textContent.replace(/\s+/g, " ").trim();
  const marks = every().filter(e => e.tagName === "BUTTON" && e.className === "mark-button");
  out.marks = marks.map(b => b.getAttribute("aria-label"));
  const calls = [];
  window.pfAct = (n, body, opts) => { calls.push([n, body, opts.family, typeof opts.ask]); return Promise.resolve({ok: false}); };
  window.prompt = () => "  why   this? ";
  const click = label => marks.find(b => b.getAttribute("aria-label") === label).fire("click");
  click("Understood on PF-16 (fixed port)");
  click("Question on PF-16 (fixed port)");
  click("Resolve designer's question on PF-15 (direct default)");
  await tick();
  out.calls = calls;
  console.log(JSON.stringify(out));
})().catch(e => console.log(JSON.stringify({errors: [String(e.stack || e)].concat(errors)})));
"""


class Page(unittest.TestCase):
    """(p) the template's own script on a board with marks, in node (skipped where there is no node)."""

    def test_p_the_page_shows_and_sends_the_marks(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("no node on this machine")
        root = workspace()
        self.addCleanup(shutil.rmtree, root, True)
        env = dict((k, v) for k, v in os.environ.items() if k not in NO_KEY)
        dev_queue.mark(root, "PF-15", "understood", "email_lead", env=env, commit=False, now="2026-10-29T01:00:00Z")
        dev_queue.mark(root, "PF-15", "question", "designer", note="why quick?", env=env, commit=False,
                       now="2026-10-29T01:00:01Z")
        doc = dev_queue.build(root, now=pf18.NOW)
        pf18.write(root, "data.json", json.dumps(doc))
        harness = pf18.PAGE_HARNESS[:pf18.PAGE_HARNESS.index("(async () => {")] + PAGE_TAIL
        pf18.write(root, "harness.js", harness)
        p = subprocess.run([node, os.path.join(root, "harness.js"), os.path.join(REAL, TPL, "dev-queue.html"),
                            os.path.join(root, "data.json")], capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        got = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(got["errors"], [])
        self.assertEqual(got["asked"], [["/data/dev-queue", "GET"], ["/stamp/dev-queue", "GET"]], "no write on load")
        # narrowed by PF-18f (earlier PF review): the PF cards shipped before the cutoff sit in Shipped before PF-16
        # (narrowed again by DQ-6 (built by label)'s order rule: Shipped is a queue, oldest merge first)
        self.assertEqual((got["columns"]["flagged"], got["columns"]["shipped"]), (["PF-15"], ["PF-3", "PF-4b", "PF-16"]))
        self.assertIn("email_lead ✓ · designer ?", got["words"]["flagged"])
        self.assertIn("? designer · Question : why quick?", got["words"]["flagged"])
        self.assertIn("email_lead – · designer –", got["words"]["shipped"])
        self.assertEqual(got["board_marks"], ["Resolve designer's question on PF-15 (direct default)"],
                         "on the board only an open mark's Resolve; the other three are in the card panel")
        self.assertIn("Resolve designer's question on PF-15 (direct default)", got["marks"])
        self.assertIn("Issue on PF-16 (fixed port)", got["marks"])
        self.assertIn("Marks · 0", got["panel"])
        self.assertEqual(got["calls"], [[20, {"item": "PF-16", "value": ""}, "dev-queue", "string"],
                                        [21, {"item": "PF-16", "value": "why this?"}, "dev-queue", "string"],
                                        [23, {"item": "PF-15", "value": "designer"}, "dev-queue", "string"]])


if __name__ == "__main__":
    unittest.main()
