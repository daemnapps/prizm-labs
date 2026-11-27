#!/usr/bin/env python3
"""DQ-4 (prompts and urgent): the Dev-queue's Copy-for-Claude prompts ask why, who it affects and how important; a
card's Importance line is data; an assignment can be Urgent.

    python3 components/page-features/test_dq4_prompts_urgent.py

    (d) data: a card's first "- Importance:" line under its heading is its `importance`, a card without one has None,
        a line under a non-card heading belongs to no card; at this tree DQ-4 (prompts and urgent), DQ-5 (human acts)
        and PF-26b (emails catalog regenerate) carry one. `assign … --urgent` rides the same assign record (a second
        reason word, frozen grammar), `urgent` true; a later plain assign clears it; an unassigned card is never
        urgent and `none --urgent` is refused, nothing filed; the command line says so too
    (v) the template platform/views/viewers/_templates/dev-queue.html, as it is on disk, in headless Chrome
        (CHROME_BIN, else /Applications/Google Chrome.app) from test_pf18k_people_views.py's stub server: each prompt's
        text per column, state and viewer (the assignee gets 1a, a reviewer who has not marked Understood 3a, everyone
        else 1 and 3; a lensed view follows the looked-at person); the issue, follow-up, change and decision prompts;
        every importance clause says (with the evidence, or "not stated"); the red Urgent chip on an urgent card only,
        first in its person's Up next group
    No Chrome → prints SKIPPED with the reason; exits 0 only when CI_NO_CHROME=1 is set, else 1.

Fixture cards and issues are kept in this file (no .md fixtures under components/). Stdlib only, Python 3.9. Writes only
in temp folders; no network beyond 127.0.0.1.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "kit"))
import dev_queue  # noqa: E402
import features  # noqa: E402
import test_pf18_dev_queue as pf18  # noqa: E402  the fixture repo
import test_pf18b_review_marks as pf18b  # noqa: E402  the fixture workspace with the review module
import test_pf18e_panel_opens as pf18e  # noqa: E402  the Chrome driver
import test_pf18k_people_views as pf18k  # noqa: E402  the stub server

REAL = features.ROOT
PAGE = os.path.join(REAL, "platform/views/viewers/_templates/dev-queue.html")
DECK = "new-workflow-design/builds/page-features/task-cards.md"
BUILD_AT = "2026-10-29T09:00:00Z"
DECK_MORE = (
    "### PF-40 — fixture: the email page will not load (carded 2026-10-28; APPROVED)\n"
    "- Importance: email_lead is blocked now: the email page will not load for her.\n"
    "- Change: fix it.\n"
    "- Importance: a second line is never read.\n"
    "### PF-41 — fixture: a plain card, carded later (carded 2026-10-29; APPROVED)\n"
    "- Importance: nothing blocked.\n"
    "### PF-42 — fixture: an old card with no Importance line (carded 2026-10-28; APPROVED)\n"
    "- Change: something small.\n"
    "## a section that is not a card\n"
    "- Importance: under no card, never read.\n"
    "### PF-43 — fixture: email_lead's shipped work for review (carded 2026-10-28; email_lead typed to the lead: \"go\"; "
    "DISPATCHED)\n")
ISSUES = [
    {"id": "T-901", "alias": "I-901", "kind": "issue", "state": "raised", "status": "proposed",
     "title": "The list hangs", "said_by": "email_lead", "by": "email_lead", "session": "abc123", "assignees": []},
    {"id": "T-902", "alias": "I-902", "kind": "issue", "state": "discussing", "status": "todo",
     "title": "Pictures are missing", "said_by": "developer", "by": "developer", "session": None, "assignees": ["developer"]},
    {"id": "T-903", "alias": "I-903", "kind": "follow-up", "state": "raised", "status": "proposed",
     "title": "Send the how-to note", "said_by": "developer", "by": "developer", "session": None, "assignees": ["designer"]},
]
IMPORTANT = "how important it is (with the evidence, or \"not stated\")"


def plain(text):
    return " ".join(str(text or "").replace("`", "").split())


def ref(c):
    return c["id"] + (" (%s)" % c["tag"] if c["tag"] else "")


def imp(c):
    return " Read how important it is first from its Importance line: \"%s\"." % plain(c["importance"]) \
        if c["importance"] else ""


def p1(c):
    return ("Explain %s to me in plain words: what it will change, why it's needed, who or what it affects, %s, what "
            "it waits on, and who decides.%s" % (ref(c), IMPORTANT, imp(c)))


def p1a(c):
    return ("%s is assigned to me. Tell me in plain words why it matters, who or what it affects and %s; then show me "
            "how to reproduce the problem myself, and help me decide: dispatch, close with a reason, or ask developer.%s"
            % (ref(c), IMPORTANT, imp(c)))


def p2(c):
    return ("Explain %s to me in plain words: what it changes, why it's being built and who or what it will affect, "
            "where its build stands (%s, item %s), and what happens next."
            % (ref(c), c["progress"]["chip"], c["progress"]["item"]))


def p3(c):
    return ("Explain %s to me in plain words: what changed for me, why it was built, who or what else it affects, how "
            "to try it, what to watch." % ref(c))


def p3a(c):
    return p3(c) + " Then: what should I try before I mark it Understood, and what would make it a Question or an Issue?"


ENV = dict((k, v) for k, v in os.environ.items() if k not in pf18b.NO_KEY)


def workspace():
    root = pf18b.workspace()
    with open(os.path.join(root, DECK), "a", encoding="utf-8") as fh:
        fh.write(DECK_MORE)
    git = pf18.Repo(root)
    git.commit("lead: card PF-40 to PF-43 (fixture cards)", "2026-10-28T16:30:00Z")
    git.merge("merge PF-43 (fixture) — email_lead typed to the lead: \"merge PF-43\"", "2026-10-28T17:00:00Z")
    return root


def board():
    """One shared board: PF-40 urgent for developer, PF-41 plain for developer, PF-42 urgent then plain, PF-5 urgent then
    unassigned, PF-43 shipped and marked Understood by designer only. Returns (doc, refusal words)."""
    root = workspace()
    try:
        n = [0]

        def now():
            n[0] += 1
            return "2026-10-29T08:00:%02dZ" % n[0]
        for card, who, urgent in (("PF-40", "developer", True), ("PF-41", "developer", False), ("PF-42", "developer", True),
                                  ("PF-42", "developer", False), ("PF-5", "designer", True), ("PF-5", "none", False)):
            dev_queue.assign(root, card, who, "developer", env=ENV, commit=False, now=now(), urgent=urgent)
        rv = dev_queue.review_module()
        refused = None
        try:
            dev_queue.assign(root, "PF-41", "none", "developer", env=ENV, commit=False, now=now(), urgent=True)
        except rv.Refused as exc:
            refused = str(exc)
        dev_queue.mark(root, "PF-43", "understood", "designer", env=ENV, commit=False, now=now())
        return dev_queue.build(root, now=BUILD_AT), refused
    finally:
        shutil.rmtree(root, True)


_BOARD = []


def shared():
    if not _BOARD:
        _BOARD.append(board())
    return _BOARD[0]


class Data(unittest.TestCase):
    """(d)"""

    @classmethod
    def setUpClass(cls):
        cls.doc, cls.refused = shared()
        cls.cards = pf18.by_id(cls.doc)

    def test_d1_the_importance_line(self):
        c = self.cards
        self.assertEqual(c["PF-40"]["importance"], "email_lead is blocked now: the email page will not load for her.",
                         "the first line under the heading; a second one is never read")
        self.assertEqual(c["PF-41"]["importance"], "nothing blocked.")
        self.assertIsNone(c["PF-42"]["importance"], "no line: None, and the section's line after it is no card's")
        self.assertIsNone(c["PF-43"]["importance"])
        for cid in ("PF-4", "PF-5", "PF-12"):
            self.assertIsNone(c[cid]["importance"], "old cards are not backfilled: %s" % cid)

    def test_d2_real_cards_carry_it(self):
        c = pf18.by_id(dev_queue.build(REAL))
        for cid in ("DQ-4", "DQ-5", "PF-26b"):
            self.assertIn(cid, c)
            self.assertTrue(c[cid]["importance"], "%s carries an Importance line at this tree" % cid)
        self.assertIsNone(c["DQ-3"]["importance"], "DQ-3 (note mark) was carded before the practice")
        for card in c.values():
            self.assertIn(card["urgent"], (True, False), card["id"])

    def test_d3_urgent_rides_the_assignment(self):
        c = self.cards
        self.assertEqual((c["PF-40"]["assignee"], c["PF-40"]["urgent"]), ("developer", True))
        self.assertEqual((c["PF-41"]["assignee"], c["PF-41"]["urgent"]), ("developer", False))
        self.assertEqual((c["PF-42"]["assignee"], c["PF-42"]["urgent"]), ("developer", False),
                         "a later plain assign clears it")
        self.assertEqual((c["PF-5"]["assignee"], c["PF-5"]["urgent"]), (None, False), "unassigned is never urgent")
        for card in self.doc["cards"]:
            if not card["assignee"]:
                self.assertIs(card["urgent"], False, card["id"])
        self.assertIn("no priority", self.refused or "", "none --urgent is refused")
        self.assertIn("Nothing was filed", self.refused)

    def test_d4_frozen_grammar(self):
        rv = dev_queue.review_module()
        body = dict(dev_queue.ASSIGN, reasons=["assign", dev_queue.URGENT], note="developer")
        rv.validate(body)
        rec = {"verdict": body, "created": "2026-10-29T08:00:00Z", "reviewer": "developer"}
        self.assertTrue(dev_queue.is_assign(rec))
        self.assertIsNone(dev_queue.mark_word(rec), "an urgent assignment is never a mark or a note")
        self.assertIs(dev_queue.urgent_of([rec]), True)

    def test_d5_the_command_line(self):
        root = workspace()
        try:
            def run(*args):
                p = subprocess.run([sys.executable, os.path.join(root, "components/page-features/dev_queue.py"),
                                    "assign"] + list(args) + ["--root", root, "--no-commit"],
                                   capture_output=True, text=True, env=ENV, cwd=root, timeout=300)
                return p.returncode, p.stdout, p.stderr
            code, out, err = run("PF-41", "none", "--urgent", "--by", "developer")
            self.assertEqual(code, 2, (out, err))
            self.assertIn("REFUSED: an unassigned card has no priority", err)
            code, out, err = run("PF-41", "email_lead", "--urgent", "--by", "developer")
            self.assertEqual(code, 0, err)
            self.assertIn("PF-41 assigned to email_lead (urgent) by developer", out)
            self.assertIs(pf18.by_id(dev_queue.build(root))["PF-41"]["urgent"], True)
            pf18b.next_second()
            code, out, err = run("PF-41", "email_lead", "--by", "developer")
            self.assertEqual(code, 0, err)
            self.assertNotIn("(urgent)", out)
            c = pf18.by_id(dev_queue.build(root))["PF-41"]
            self.assertEqual((c["assignee"], c["urgent"]), ("email_lead", False), "the plain assign wins and clears it")
        finally:
            shutil.rmtree(root, True)


HOOK = ("Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText: t => {"
        " window.__copied.push(t); return Promise.resolve(); }}}); window.__copied = []; true")


def copy_of(selector):
    return ("(() => { window.__copied = []; const b = document.querySelector(%s);"
            " if (!b) return null; b.click(); return window.__copied[0] || null; })()" % json.dumps(selector))


class Views(unittest.TestCase):
    """(v)"""

    @classmethod
    def setUpClass(cls):
        binary, _why = pf18e.chrome_bin()
        doc = dict(shared()[0])
        stamp = "2026-10-29T07:00:00Z"
        extra = [dict({"created": stamp, "on_card": None, "parent": None, "carded_as": None, "reason": None,
                       "fixed_at": None, "fixes": [], "context": [], "notes": [], "history": [], "follow_ups": [],
                       "quote": None, "detail": "", "urgent": False}, **e) for e in ISSUES]
        doc["issues"] = list(doc.get("issues") or []) + extra
        doc["acts"] = dev_queue.human_acts(doc["issues"])   # DQ-5 (human acts): an open follow-up is drawn as an act in Up next
        cls.doc = doc
        cls.cards = pf18.by_id(doc)
        with open(PAGE, "rb") as fh:
            cls.stub = pf18k.Stub(fh.read(), doc)
        cls.chrome = pf18e.Chrome(binary)
        cls.copied = []

    @classmethod
    def tearDownClass(cls):
        cls.chrome.quit()
        cls.stub.stop()

    def page(self, viewer):
        self.stub.viewer = viewer
        self.chrome.call("Page.navigate", url=self.stub.url)
        self.assertTrue(self.chrome.wait("document.readyState === 'complete' && "
                                         "document.getElementById('snapshot').textContent.indexOf('Read') === 0 && "
                                         "document.querySelectorAll('[data-tile]').length > 0"),
                        "the board never drew for %s: %s" % (viewer, self.chrome.exceptions))
        self.assertTrue(self.chrome.js(HOOK))
        got = self.chrome.js(pf18k.VIEW)
        self.assertEqual(self.chrome.exceptions, [], "no page exception")
        return got

    def copy(self, selector):
        text = self.chrome.js(copy_of(selector))
        self.assertTrue(text, "nothing copied from %s" % selector)
        type(self).copied.append(text)
        return text

    def tile(self, cid):
        return self.copy("[data-tile=\"%s\"] .copy-button" % cid)

    def test_v1_the_assignees_view(self):
        c = self.cards
        v = self.page("developer")
        # narrowed by DQ-6 (built by label)'s order rule: after Urgent, oldest filing first (PF-42 is older than PF-41)
        self.assertEqual(v["cols"]["up-next"]["You"], ["PF-40", "PF-42", "PF-41"],
                         "the urgent card first in his group, then the carded order, oldest first")
        self.assertIn("Urgent", v["chips"]["PF-40"])
        for cid in ("PF-41", "PF-42", "PF-5", "PF-43"):
            self.assertNotIn("Urgent", v["chips"].get(cid, []), cid)
        self.assertEqual(self.chrome.js("getComputedStyle(document.querySelector('[data-tile=\"PF-40\"] .chip.urgent'))"
                                        ".backgroundColor") not in ("", "rgba(0, 0, 0, 0)"), True, "a filled chip")
        self.assertEqual(self.tile("PF-40"), p1a(c["PF-40"]), "1a, with the card's Importance line")
        self.assertEqual(self.tile("PF-42"), p1a(c["PF-42"]), "1a, no Importance line to read")
        self.assertNotIn("Importance line", self.copied[-1])
        self.assertEqual(self.tile("PF-12"), p2(c["PF-12"]), "2: In progress")
        self.assertEqual(self.tile("PF-43"), p3a(c["PF-43"]), "3a: a reviewer who has not marked Understood")
        # the panel's copy is the same request
        self.assertTrue(self.chrome.js(pf18k.open_panel("PF-40")))
        self.assertEqual(self.copy("#panel-content .copy-button"), p1a(c["PF-40"]))

    def test_v2_other_viewers(self):
        c = self.cards
        s = self.page("email_lead")
        self.assertEqual(s["cols"]["up-next"]["developer"][0], "PF-40", "first in developer's group in email_lead's view too")
        self.assertIn("Urgent", s["chips"]["PF-40"])
        self.assertEqual(self.tile("PF-40"), p1(c["PF-40"]), "1: not her card")
        self.assertEqual(self.tile("PF-43"), p3(c["PF-43"]), "3: her own work, she is no reviewer of it")
        self.page("designer")
        self.assertEqual(self.tile("PF-43"), p3(c["PF-43"]), "3: she already marked it Understood")
        for viewer in ("editor", None):
            e = self.page(viewer)
            self.assertIn("Urgent", e["chips"]["PF-40"], "the chip on the team board too")
            self.assertEqual(self.tile("PF-40"), p1(c["PF-40"]), viewer)
            self.assertEqual(self.tile("PF-43"), p3(c["PF-43"]), viewer)

    def test_v3_the_lens_follows_the_looked_at_person(self):
        c = self.cards
        self.page("developer")
        self.chrome.js("document.querySelector('button.view-as[data-view=email_lead]').click()")
        self.assertIn("Looking as email_lead.", self.chrome.js("document.getElementById('lens').textContent"))
        self.assertEqual(self.tile("PF-40"), p1(c["PF-40"]), "as email_lead: 1")
        self.assertEqual(self.tile("PF-43"), p3(c["PF-43"]), "as email_lead: 3")
        self.page("email_lead")
        self.chrome.js("document.querySelector('button.view-as[data-view=developer]').click()")
        self.assertEqual(self.tile("PF-40"), p1a(c["PF-40"]), "email_lead looking as developer: his 1a")
        self.assertEqual(self.tile("PF-43"), p3a(c["PF-43"]), "email_lead looking as developer: his 3a")

    def test_v4_issues_changes_decisions(self):
        # T-903 is a follow-up: since DQ-5 (human acts) it is an act tile in Up next, so its prompt is read there
        self.page("developer")
        self.assertEqual(self.copy("[data-issue=\"T-901\"] .copy-button"),
                         "Look at dev issue \"The list hangs\" (I-901) (raised by email_lead, session abc123) and help me "
                         "decide: discuss it, card it, or mark it Won't do with its reason. Tell me why it matters, who "
                         "or what it affects, and %s, through components/page-features/dev_issues.py." % IMPORTANT)
        self.assertEqual(self.copy("[data-issue=\"T-902\"] .copy-button"),
                         "Summarize dev issue \"Pictures are missing\" (I-902), with developer: the problem, who or what it "
                         "affects and %s, its proposed fixes and context, and whether it is ready to card." % IMPORTANT)
        self.assertEqual(self.copy("[data-act=\"T-903\"] .copy-button"),
                         "Tell me what is left on follow-up \"Send the how-to note\" (I-903) for designer, why it "
                         "matters and whether anything waits on it, and when it is finished tick it done with "
                         "components/page-features/dev_issues.py done.")
        change = self.copy(".change .copy-button")
        self.assertTrue(re.match(r"^Explain change [0-9a-f]{7,40} \(", change), change)
        self.assertTrue(change.endswith("\" — what it does, why, who or what it affects, and what it touched."), change)
        decision = self.copy(".decision .copy-button")
        self.assertTrue(decision.startswith("Tell me about the decision \""), decision)
        self.assertTrue(re.search(r"\" \([^()]+\): why it was made, who it affects, and what it changes for me\.$",
                                  decision), decision)

    def test_v5_the_wont_do_prompt_on_disk(self):
        """7 is drawn nowhere on the board since PF-18m (open issues only) hides Won't do; its text is in the page."""
        with open(PAGE, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("\" and why it was marked Won't do: \" + plain(e.reason) +", text)
        self.assertIn("\", and who or what is still affected by leaving it.\"", text)

    def test_v9_every_importance_clause(self):
        """Run last (by name): every copied text above asks for the evidence, or "not stated"."""
        self.assertGreaterEqual(len(self.copied), 15, "the copies above ran first")
        n = 0
        for text in self.copied:
            for m in re.finditer(r"how important", text):
                n += 1
                tail = text[m.start():]
                self.assertTrue(tail.startswith(IMPORTANT) or tail.startswith("how important it is first from its "
                                                                              "Importance line"), text)
        self.assertGreaterEqual(n, 8)


def main():
    binary, why = pf18e.chrome_bin()
    if not binary:
        print("SKIPPED: %s; set CHROME_BIN to a Chrome or Chromium binary" % why)
        sys.exit(0 if os.environ.get("CI_NO_CHROME") == "1" else 1)
    unittest.main()


if __name__ == "__main__":
    main()
