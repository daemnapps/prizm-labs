#!/usr/bin/env python3
"""DQ-7 (folded columns): Dev-queue columns fold when empty, Reviewed folds by default, a hand-set fold wins (the PM
board's idiom), and a folded column still shows what waits on you — in a real browser.

    python3 components/page-features/test_dq7_folded_columns.py

    The template platform/views/viewers/_templates/dev-queue.html, as it is on disk, in headless Chrome (CHROME_BIN, else
    /Applications/Google Chrome.app), served by test_pf18k_people_views.py's stub with its fixture board plus one Urgent
    card (PF-5, assigned to developer), kept in this file:
    (1) unset state: the empty Issue queue renders folded, a non-empty Up next open, Reviewed folded with a card in it;
        the header is a button with aria-expanded, a title "Expand <label>" / "Collapse <label>" and ▸ / ▾
    (2) a click on the header writes dq_col_<id> and flips it; a hand-opened empty column stays open on reload
    (3) a hand-folded column stays folded when cards arrive (a filter cleared)
    (4) a filter that empties a column folds it and clearing the filter reopens it
    (5) a folded Up next with an Urgent card assigned to the viewer shows "1 urgent", a folded Shipped shows "N to
        review" for the viewer's Your review group; open, neither badge is drawn; a badge never unfolds the column
    (6) the fold is the viewer's: a view-as lens keeps it, and the only keys written are dq_col_<id>
    (7) with localStorage throwing, the page renders with the default rule and a header click throws nothing
    (8) the grid gives folded columns the strip width (42px), the open ones share the rest
    Chrome is driven over the DevTools protocol by test_pf18e_panel_opens.py's stdlib client. No Chrome → prints
    SKIPPED with the reason; exits 0 only when CI_NO_CHROME=1 is set, else 1.

Stdlib only, Python 3.9. Writes only in temp folders; no network beyond 127.0.0.1.
"""
import copy
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_pf18e_panel_opens as pf18e  # noqa: E402  the Chrome driver
import test_pf18k_people_views as pf18k  # noqa: E402  the fixture board and its stub

COLS = ("issue-queue", "up-next", "in-progress", "shipped", "flagged", "reviewed")
# Each column's fold as drawn: folded class, the header button's words, the badge, the drawn count, its width
STATE = """(() => {
  const out = {};
  document.querySelectorAll('section.column').forEach(sec => {
    const b = sec.querySelector('button.column-toggle'), badge = sec.querySelector('.fold-badge');
    out[sec.id.slice(4)] = {folded: sec.classList.contains('folded'), expanded: b.getAttribute('aria-expanded'),
      title: b.getAttribute('title'), chev: b.querySelector('.chev').textContent,
      badge: badge ? badge.textContent : null,
      badge_shown: badge ? getComputedStyle(badge).display !== 'none' : false,
      body_shown: getComputedStyle(sec.querySelector('.column-body')).display !== 'none',
      n: +sec.querySelector('.column-count').textContent, width: sec.getBoundingClientRect().width};
  });
  return out;
})()"""
KEYS = ("(() => { try { const k = []; for (let i = 0; i < localStorage.length; i++) k.push(localStorage.key(i));"
        " return k.sort(); } catch (e) { return 'threw'; } })()")
THROWING = ("Object.defineProperty(window, 'localStorage', {configurable: true,"
            " get() { throw new DOMException('storage denied', 'SecurityError'); }});")


def board():
    """pf18k's board plus one Urgent card assigned to developer (DQ-4 (prompts and urgent)'s flag, cards[].urgent), and
    PF-3 reviewed by email_lead and designer instead of developer, so exactly one card (PF-31) sits in developer's Your review."""
    doc = copy.deepcopy(pf18k.Data.doc if hasattr(pf18k.Data, "doc") else pf18k.board())
    for c in doc["cards"]:
        if c["id"] == "PF-5":
            assert c["assignee"] == "developer" and c["column"] == "up-next", c
            c["urgent"] = True
        if c["id"] == "PF-3":
            assert c["column"] == "shipped" and "developer" in c["reviewers"], c
            c["reviewers"] = ["email_lead", "designer"]
    return doc


def to_review(doc, who):
    """The viewer's Your review group: shipped, not private, they review it and have not marked it Understood."""
    mine = lambda c: any(r["person"] == who and r["understood"] for r in c["review"] or [])
    return len([c for c in doc["cards"] if c["column"] == "shipped" and not c["private"] and not mine(c)
                and who in c["reviewers"]])


class Base(unittest.TestCase):
    throwing = False

    @classmethod
    def setUpClass(cls):
        binary, _why = pf18e.chrome_bin()
        cls.doc = board()
        with open(pf18k.PAGE, "rb") as fh:
            cls.stub = pf18k.Stub(fh.read(), cls.doc)
        cls.stub.viewer = "developer"
        cls.chrome = pf18e.Chrome(binary)
        if cls.throwing:
            cls.chrome.call("Page.addScriptToEvaluateOnNewDocument", source=THROWING)

    @classmethod
    def tearDownClass(cls):
        cls.chrome.quit()
        cls.stub.stop()

    def load(self, clear=False):
        c = self.chrome
        if clear:
            c.call("Page.navigate", url=self.stub.url)
            c.wait("document.readyState === 'complete'")
            c.js("try { localStorage.clear(); } catch (e) {}")
        c.call("Page.navigate", url=self.stub.url)
        self.assertTrue(c.wait("document.readyState === 'complete' && "
                               "document.getElementById('snapshot').textContent.indexOf('Read') === 0 && "
                               "document.querySelectorAll('button.column-toggle').length === 6"),
                        "the board never drew: %s" % c.exceptions)
        self.assertEqual(c.exceptions, [], "no page exception")
        return c.js(STATE)

    def toggle(self, col):
        before = len(self.chrome.exceptions)
        self.chrome.js("document.querySelector('#col-%s button.column-toggle').click()" % col)
        self.assertEqual(self.chrome.exceptions[before:], [], "%s: the click threw" % col)
        return self.chrome.js(STATE)

    def stored(self, col):
        return self.chrome.js("localStorage.getItem('dq_col_%s')" % col)

    def family(self, fam):
        """Tick (or untick) one card family in the filter bar, as a person would."""
        self.chrome.js("(() => { const i = document.querySelector('#family-options input[value=\"%s\"]');"
                       " i.click(); })()" % fam)
        return self.chrome.js(STATE)


class Folds(Base):

    def test_1_unset_state_the_default_rule(self):
        s = self.load(clear=True)
        self.assertEqual(s["issue-queue"]["n"], 0, "fixture: nothing in the Issue queue")
        self.assertTrue(s["issue-queue"]["folded"], "an empty column folds by default")
        self.assertFalse(s["issue-queue"]["body_shown"], "a folded column's body is hidden with CSS")
        self.assertGreater(s["up-next"]["n"], 0)
        self.assertFalse(s["up-next"]["folded"], "a non-empty column opens by default")
        self.assertTrue(s["up-next"]["body_shown"])
        self.assertGreater(s["reviewed"]["n"], 0, "fixture: developer's private shipped card sits in his Reviewed")
        self.assertTrue(s["reviewed"]["folded"], "Reviewed folds by default, cards and all")
        for col in COLS:
            want = s[col]["folded"]
            self.assertEqual(s[col]["expanded"], "false" if want else "true", col)
            label = {"issue-queue": "Issue queue", "up-next": "Up next", "in-progress": "In progress",
                     "shipped": "Shipped", "flagged": "Flagged", "reviewed": "Reviewed"}[col]
            self.assertEqual(s[col]["title"], ("Expand " if want else "Collapse ") + label, col)
            self.assertEqual(s[col]["chev"], "▸" if want else "▾", col)
        self.assertEqual(self.chrome.js(KEYS), [], "nothing is stored until a person clicks")

    def test_2_a_click_writes_and_flips_and_is_remembered(self):
        self.load(clear=True)
        s = self.toggle("issue-queue")
        self.assertEqual(self.stored("issue-queue"), "1", "the click writes dq_col_<id>: open")
        self.assertFalse(s["issue-queue"]["folded"], "flipped open")
        self.assertTrue(s["issue-queue"]["body_shown"])
        s = self.load()
        self.assertFalse(s["issue-queue"]["folded"], "a hand-opened empty column stays open on re-render")
        s = self.toggle("reviewed")
        self.assertEqual(self.stored("reviewed"), "1")
        self.assertFalse(s["reviewed"]["folded"], "Reviewed opens once someone opens it")
        self.assertFalse(self.load()["reviewed"]["folded"], "and stays open")
        s = self.toggle("up-next")
        self.assertEqual(self.stored("up-next"), "0", "a hand fold on an open column writes 0")
        self.assertTrue(s["up-next"]["folded"])
        self.assertTrue(self.load()["up-next"]["folded"], "a hand-folded column stays folded with cards in it")

    def test_3_a_hand_folded_column_stays_folded_when_cards_arrive(self):
        self.load(clear=True)
        s = self.family("LD")
        self.assertEqual(s["flagged"]["n"], 0, "fixture: no LD card is flagged")
        self.assertTrue(s["flagged"]["folded"])
        self.toggle("flagged")                       # open by hand ...
        s = self.toggle("flagged")                   # ... and fold by hand: dq_col_flagged = 0
        self.assertEqual(self.stored("flagged"), "0")
        s = self.family("LD")                        # the filter cleared: PF-7 arrives
        self.assertGreater(s["flagged"]["n"], 0)
        self.assertTrue(s["flagged"]["folded"], "the hand-set fold wins over the cards arriving")

    def test_4_a_filter_that_empties_a_column_folds_it(self):
        s = self.load(clear=True)
        self.assertFalse(s["shipped"]["folded"])
        s = self.family("LD")
        self.assertEqual(s["shipped"]["n"], 0, "fixture: no LD card shipped")
        self.assertTrue(s["shipped"]["folded"], "a filter that empties a column folds it")
        self.assertFalse(s["up-next"]["folded"], "LD-3 keeps Up next open")
        s = self.family("LD")
        self.assertGreater(s["shipped"]["n"], 0)
        self.assertFalse(s["shipped"]["folded"], "clearing the filter opens it again")
        self.assertIsNone(self.stored("shipped"), "a filter writes nothing")

    def test_5_what_waits_on_you_shows_on_a_folded_strip(self):
        s = self.load(clear=True)
        self.assertIsNone(s["up-next"]["badge"], "open: no badge, the cards are in view")
        self.assertIsNone(s["shipped"]["badge"])
        s = self.toggle("up-next")
        self.assertEqual(s["up-next"]["badge"], "1 urgent", "PF-5, Urgent, assigned to developer")
        self.assertTrue(s["up-next"]["badge_shown"])
        self.assertTrue(s["up-next"]["folded"], "the badge never unfolds the column")
        self.assertEqual(to_review(self.doc, "developer"), 1, "fixture: one card, PF-31, waits on developer's review")
        s = self.toggle("shipped")
        self.assertEqual(s["shipped"]["badge"], "1 to review", "the viewer's Your review group")
        self.assertTrue(s["shipped"]["badge_shown"])
        self.assertTrue(s["shipped"]["folded"], "the badge never unfolds the column")
        for col in ("issue-queue", "in-progress", "flagged", "reviewed"):
            self.assertIsNone(s[col]["badge"], "%s carries no badge" % col)
        s = self.load()
        self.assertEqual((s["up-next"]["badge"], s["shipped"]["badge"]), ("1 urgent", "1 to review"), "on reload too")
        # designer's page: PF-5 is not hers, so her folded Up next carries no badge; PF-31 waits on her too
        self.stub.viewer = "designer"
        try:
            s = self.load()
        finally:
            self.stub.viewer = "developer"
        self.assertTrue(s["up-next"]["folded"], "the fold is this browser's, whoever the page serves")
        self.assertIsNone(s["up-next"]["badge"], "nothing urgent is assigned to designer")
        self.assertEqual(s["shipped"]["badge"], "%d to review" % to_review(self.doc, "designer"))

    def test_6_the_fold_is_the_viewers_own(self):
        self.load(clear=True)
        self.toggle("in-progress")
        self.chrome.js("document.querySelector('button.view-as[data-view=email_lead]').click()")
        s = self.chrome.js(STATE)
        self.assertTrue(self.chrome.js("!document.getElementById('lens').hidden"), "the lens is on")
        self.assertTrue(s["in-progress"]["folded"], "looking as email_lead keeps developer's own fold")
        self.assertTrue(s["issue-queue"]["folded"] and s["reviewed"]["folded"])
        self.assertEqual(self.chrome.js(KEYS), ["dq_col_in-progress"], "one key per hand-set column, no name in it")
        self.chrome.js("Array.from(document.querySelectorAll('#lens button')).find(b => b.textContent === 'Back to my view').click()")
        self.assertTrue(self.chrome.js(STATE)["in-progress"]["folded"])
        self.assertFalse([a for a in self.stub.asked if a[0] == "POST"], "a fold posts nothing")
        self.assertFalse([a for a in self.stub.asked if "dq_col" in a[1]], "nor rides any URL")

    def test_8_the_grid_gives_a_folded_column_the_strip_width(self):
        s = self.load(clear=True)
        for col in COLS:
            if s[col]["folded"]:
                self.assertAlmostEqual(s[col]["width"], 42, delta=1, msg="%s: the strip width" % col)
            else:
                self.assertGreater(s[col]["width"], 150, "%s: an open column shares the rest" % col)
        cols = self.chrome.js("getComputedStyle(document.getElementById('board')).gridTemplateColumns").split()
        self.assertEqual(len(cols), 6)
        self.assertEqual([abs(float(w[:-2]) - 42) < 1 for w in cols], [s[c]["folded"] for c in COLS])


class NoStorage(Base):
    """(7) localStorage that throws on every touch."""
    throwing = True

    def test_7_the_page_renders_with_the_default_rule(self):
        c = self.chrome
        s = self.load()
        self.assertEqual(c.js(KEYS), "threw", "the stub really throws")
        self.assertTrue(s["issue-queue"]["folded"])
        self.assertFalse(s["up-next"]["folded"])
        self.assertTrue(s["reviewed"]["folded"])
        self.assertTrue(c.js("document.querySelectorAll('[data-tile]').length > 0"), "the board drew")
        s = self.toggle("issue-queue")
        self.assertTrue(s["issue-queue"]["folded"], "nothing could be stored: the default rule still draws")
        self.assertEqual(c.exceptions, [], "no page exception without storage")


def main():
    binary, why = pf18e.chrome_bin()
    if not binary:
        print("SKIPPED: %s; set CHROME_BIN to a Chrome or Chromium binary" % why)
        sys.exit(0 if os.environ.get("CI_NO_CHROME") == "1" else 1)
    unittest.main()


if __name__ == "__main__":
    main()
