#!/usr/bin/env python3
"""PF-18g (built by): card faces say who asked for the build ("Built by"), not the card's owner; the owner moves to
the panel.

    python3 components/page-features/test_pf18g_built_by.py

    (a) built_by and built_by_from, rule by rule, on a fixture repo: the approver in the heading ("developer typed to the
        lead", "developer, relayed verbatim by ◆ PLAN" → developer; "email_lead typed" → email_lead) leads; else the filer of the card's
        newest implement request (email_lead, never the mini-worker's newer status record); else a direct commit's author
        through run_kit.people (designer); else none. The heading rule is the decision log's own pattern, one copy.
    (p) the page in node: every shipped tile says "Built by <person>", never "Owner ·" (narrowed by DQ-6 (built by
        label): an Up next or In progress tile says "Unassigned" or "Assigned · <person>"); the panel lists Asked by
        with its rule in small text and Build owner; the name filter finds a card by its builder and by its owner;
        the hint reads "Name: built by, asked by, owner, assignee, change author or decider"

The fixture lives in this file (no .md fixtures under components/); the repo helpers are test_pf18_dev_queue's.
Stdlib only, Python 3.9. Writes only in temp folders; no network.
"""
import inspect
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "kit"))
import dev_queue  # noqa: E402
import test_pf18_dev_queue as pf18  # noqa: E402  Repo, write, request, the page harness

REAL = pf18.REAL
TPL = pf18.TPL
NOW = "2026-10-29T05:00:00Z"

DECK = """# page-features cards (fixture)

### PF-40 — typed card: the approver typed it (carded 2026-10-28 by the lead; APPROVED + DISPATCH: developer typed to the lead: "go"; owner email_lead (page-features), told after)
### PF-41 — relayed card: the approver's words came through PLAN (carded 2026-10-28 by the lead; from an issue (developer, relayed verbatim by ◆ PLAN [e318fe]: "do it"); owner email_lead (page-features))
### PF-42 — email_lead card: email_lead approved it (carded 2026-10-28 by the lead; APPROVED: email_lead typed to the lead: "yes"; owner designer (engine))
### PF-43 — requested card: no approver named (carded 2026-10-28 by the lead; owner developer (assumption))
### PF-44 — direct card: built straight on main (carded 2026-10-28 by the lead; owner email_lead (page-features))
### PF-45 — quiet card: nothing names a builder (carded 2026-10-28 by the lead; APPROVED)
"""


def fixture():
    root = os.path.realpath(tempfile.mkdtemp(prefix="pf18g-"))
    os.makedirs(os.path.join(root, "brands"))
    for pid, email in pf18.EMAILS.items():
        pf18.write(root, "team/people/%s/identity.json" % pid,
                   json.dumps({"person": pid, "emails": [{"address": email}]}))
    pf18.write(root, "team/id-tags.json", json.dumps({"_readme": "fixture"}))
    pf18.write(root, "new-workflow-design/builds/page-features/task-cards.md", DECK)
    # PF-43: an older request filed by developer, the newest by email_lead, then the worker's status record (never a filer)
    pf18.request(root, "2026-10-28T01:00:00Z", "developer", "impl-pf43-first", {"action": "implement", "cards": ["PF-43"]})
    pf18.request(root, "2026-10-28T02:00:00Z", "email_lead", "impl-pf43-again", {"action": "implement", "cards": ["PF-43"]})
    pf18.request(root, "2026-10-28T03:00:00Z", "mini-worker", "impl-pf43-again", {"status": "running", "detail": "go"})
    # PF-40: a request filed by email_lead loses to the heading's approver
    pf18.request(root, "2026-10-28T01:30:00Z", "email_lead", "impl-pf40-typed", {"action": "implement", "cards": ["PF-40"]})
    git = pf18.Repo(root)
    git.commit("lead: card the deck", "2026-10-28T00:00:00Z")
    git.merge("merge PF-40 (typed card) — record done", "2026-10-28T04:00:00Z")
    git.merge("merge PF-41 (relayed card) — record done", "2026-10-28T04:10:00Z")
    git.merge("merge PF-42 (email_lead card) — record done", "2026-10-28T04:20:00Z")
    git.commit("PF-44 (direct card), built on main", "2026-10-28T04:30:00Z", "designer")
    return root


class BuiltBy(unittest.TestCase):
    """(a)"""

    @classmethod
    def setUpClass(cls):
        cls.root = fixture()
        cls.doc = dev_queue.build(cls.root, now=NOW)
        cls.cards = pf18.by_id(cls.doc)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, True)

    def test_a_each_rule_in_order(self):
        got = dict((k, (c["built_by"], c["built_by_from"])) for k, c in self.cards.items())
        self.assertEqual(got, {"PF-40": ("developer", "heading"), "PF-41": ("developer", "heading"),
                               "PF-42": ("email_lead", "heading"), "PF-43": ("email_lead", "request"),
                               "PF-44": ("designer", "commit"), "PF-45": (None, None)})
        owners = dict((k, c["owner"]) for k, c in self.cards.items())
        self.assertEqual(owners, {"PF-40": "email_lead", "PF-41": "email_lead", "PF-42": "designer", "PF-43": "developer",
                                  "PF-44": "email_lead", "PF-45": None}, "the build owner stays the heading's owner")
        self.assertEqual(self.cards["PF-43"]["column"], "in-progress")
        self.assertEqual(self.cards["PF-44"]["merged"]["via"], "direct commit")

    def test_a_the_heading_rule_is_the_decision_logs_own(self):
        src = inspect.getsource(dev_queue)
        self.assertEqual(src.count("typed|relayed"), 1, "one pattern, reused, never copied")
        self.assertIn("approver_res(names)", inspect.getsource(dev_queue.read_decisions))
        by_re = dev_queue.approver_res({"developer": "developer", "email_lead": "email_lead"})[0]
        self.assertEqual(by_re.search("developer typed to the lead: \"card it\"").group(1), "developer")
        self.assertEqual(by_re.search("(developer, relayed verbatim by ◆ PLAN [e318fe]: \"x\")").group(1), "developer")
        c = dev_queue.parse_heading("### PF-9 — t: x (carded 2026-10-28; APPROVED: email_lead typed: \"yes\"; owner developer)",
                                    {}, {"developer": "developer", "email_lead": "email_lead"})
        self.assertEqual((c["built_by"], c["built_by_from"], c["owner"]), ("email_lead", "heading", "developer"))


PAGE_TAIL = r"""
(async () => {
  for (let i = 0; i < 5; i++) await tick();
  const words = e => e.textContent.replace(/\s+/g, " ").trim();
  const out = {errors: errors, metas: {}, panels: {}, filtered: {}};
  for (const art of every().filter(e => e.getAttribute("data-tile"))) {
    const m = find(art, e => e.classList.contains("card-meta"))[0];
    out.metas[art.getAttribute("data-tile")] = m ? words(m) : null;
  }
  out.board = ["up-next", "in-progress", "shipped", "flagged", "reviewed"].map(c => words(g("col-" + c))).join(" ");
  const open = id => every().filter(e => e.tagName === "BUTTON").find(b => b.className === "tile-open" &&
    b.getAttribute("aria-label").indexOf("Open " + id + " (") === 0);
  for (const id of ["PF-42", "PF-44", "PF-45"]) {
    open(id).fire("click");
    const body = g("panel-content");
    out.panels[id] = {text: words(body), small: find(body, e => e.classList.contains("built-from")).map(words)};
    g("panel").close();
  }
  const shown = () => every().filter(e => e.getAttribute("data-tile")).map(e => e.getAttribute("data-tile")).sort();
  const pick = (who, on) => {
    const box = find(g("name-options"), e => e.tagName === "INPUT" && e.getAttribute("value") === who)[0];
    box.checked = on;
    box.fire("change");
  };
  out.options = find(g("name-options"), e => e.tagName === "INPUT").map(e => e.getAttribute("value")).sort();
  out.hint = words(find(g("name-options"), e => e.tagName === "P")[0]);
  for (const who of ["designer", "email_lead", "developer"]) { pick(who, true); out.filtered[who] = shown(); pick(who, false); }
  console.log(JSON.stringify(out));
})().catch(e => console.log(JSON.stringify({errors: [String(e.stack || e)].concat(errors)})));
"""


class Page(unittest.TestCase):
    """(p) the template's own script on the fixture's data, in node (skipped where there is no node)."""

    def test_p_faces_panel_and_filter(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("no node on this machine")
        root = fixture()
        self.addCleanup(shutil.rmtree, root, True)
        pf18.write(root, "data.json", json.dumps(dev_queue.build(root, now=NOW)))
        pf18.write(root, "harness.js", pf18.PAGE_HARNESS[:pf18.PAGE_HARNESS.index("(async () => {")] + PAGE_TAIL)
        p = subprocess.run([node, os.path.join(root, "harness.js"), os.path.join(REAL, TPL, "dev-queue.html"),
                            os.path.join(root, "data.json")], capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        got = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(got["errors"], [])
        m = got["metas"]
        self.assertEqual(sorted(m), ["PF-40", "PF-41", "PF-42", "PF-43", "PF-44", "PF-45"])
        # narrowed by DQ-6 (built by label): a shipped face says "Built by <developer>" (no assignee here, so built_by);
        # an In progress or Up next face says who is assigned, never "Built by"
        for cid, who in (("PF-40", "developer"), ("PF-41", "developer"), ("PF-42", "email_lead"), ("PF-44", "designer")):
            self.assertTrue(m[cid].startswith("Built by " + who + " · "), (cid, m[cid]))
        self.assertTrue(m["PF-43"].startswith("Unassigned · "), m["PF-43"])
        self.assertTrue(m["PF-45"].startswith("Unassigned · "), m["PF-45"])
        self.assertNotIn("Owner ·", got["board"], "the face never shows the owner")
        self.assertNotIn("designer ·", m["PF-42"], "PF-42's owner is not on its face")

        email_lead = got["panels"]["PF-42"]
        self.assertIn("Built by email_lead", email_lead["text"])
        self.assertIn("Asked by email_lead", email_lead["text"], "DQ-6 (built by label): the approver-derived field, renamed")
        self.assertIn("Build owner designer", email_lead["text"])
        self.assertEqual(email_lead["small"], ["(the approver in the card's heading)"])
        self.assertNotIn("Owner ·", email_lead["text"])
        self.assertEqual(got["panels"]["PF-44"]["small"], ["(author of the card's commit on main)"])
        self.assertIn("Build owner email_lead", got["panels"]["PF-44"]["text"])
        self.assertEqual(got["panels"]["PF-45"]["small"], ["(no rule found a builder)"])

        self.assertEqual(got["options"], ["developer", "email_lead", "designer"])
        self.assertEqual(got["filtered"]["designer"], ["PF-42", "PF-44"],
                         "PF-44 by its builder, PF-42 by its owner")
        self.assertEqual(got["filtered"]["email_lead"], ["PF-40", "PF-41", "PF-42", "PF-43", "PF-44"],
                         "PF-42 and PF-43 by their builder; PF-40, PF-41 and PF-44 by their owner")
        self.assertEqual(got["filtered"]["developer"], ["PF-40", "PF-41", "PF-43"],
                         "PF-40 and PF-41 by their builder, PF-43 by its owner")
        # narrowed by DQ-6 (built by label): the filter also matches who asked for it and the assignee
        self.assertIn("A card matches by who builds or built it, who asked for it, its owner or its assignee", got["hint"])

    def test_p_the_filter_hint(self):
        text = pf18.read(os.path.join(REAL, TPL, "dev-queue.html"))
        self.assertIn('<p class="filter-hint">Name: built by, asked by, owner, assignee, change author or decider</p>', text)
        self.assertNotIn("Name: card owner", text)


if __name__ == "__main__":
    unittest.main()
