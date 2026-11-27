#!/usr/bin/env python3
"""PF-18k (people views page): each viewer's Dev-queue board, PRIVATE cards and the view-as lens, in a real browser.

    python3 components/page-features/test_pf18k_people_views.py

    (d) data: the word PRIVATE in a card's heading (exact, upper case, its own word) gives `private: true` and
        `reviewers: []`; lower-case "private" inside a sentence does not; at this tree LD-100 (chain model explicit)
        is private in a real run
    (v) the template platform/views/viewers/_templates/dev-queue.html, as it is on disk, in headless Chrome (CHROME_BIN,
        else /Applications/Google Chrome.app) from a stub server on 127.0.0.1 answering /data/dev-queue with ONE fixture
        board and a different `viewer` per page:
        - developer's view puts a email_lead card in Your review and his own in Waiting on others; his Up next opens on his
          cards and ends on Unassigned; In progress tiles carry the assignee chip; Flagged is grouped by stage
        - email_lead's Reviewed lists a card she marked Understood while designer has not; designer's does not
        - a PRIVATE card built by developer is absent from email_lead's and designer's boards, counts and stats, present in
          developer's with the Private chip, and shipped sits in his Reviewed under "Your work, private (no review)" and
          in nobody's Your review
        - the lens: developer's page looking as email_lead shows her private card (read-only); with the lens on no mark button
          is drawn, a mark button kept from before is REFUSED (no POST at all, while the same button posted before
          the lens: the positive control), and no request the page makes carries the viewed name
        - an editor page renders today's team board: no switch, no stats, no groups, every non-private card in its
          data column
    Chrome is driven over the DevTools protocol by test_pf18e_panel_opens.py's stdlib client. No Chrome → prints
    SKIPPED with the reason; exits 0 only when CI_NO_CHROME=1 is set, else 1.

The fixture board is built by the real data command (dev_queue.build) on test_pf18b_review_marks.py's fixture
workspace plus the cards below, kept in this file (no .md fixtures under components/). Stdlib only, Python 3.9. Writes
only in temp folders; no network beyond 127.0.0.1.
"""
import http.server
import json
import os
import re
import shutil
import sys
import threading
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "kit"))
import dev_queue  # noqa: E402
import features  # noqa: E402
import test_pf18_dev_queue as pf18  # noqa: E402  the fixture repo
import test_pf18b_review_marks as pf18b  # noqa: E402  the fixture workspace with the review module
import test_pf18e_panel_opens as pf18e  # noqa: E402  the Chrome driver

REAL = features.ROOT
PAGE = os.path.join(REAL, "platform/views/viewers/_templates/dev-queue.html")
BUILD_AT = "2026-10-29T09:00:00Z"
DECK_MORE = (
    "### PF-30 — fixture: developer's own shipped work (carded 2026-10-28; developer typed to the lead: \"go\"; DISPATCHED)\n"
    "### PF-31 — fixture: email_lead's shipped work (carded 2026-10-28; email_lead typed to the lead: \"go\"; DISPATCHED)\n"
    "### PF-32 — fixture: a build of developer's nobody needs to see (carded 2026-10-28; PRIVATE; developer typed to the "
    "lead: \"go\"; DISPATCHED)\n"
    "### PF-33 — fixture: email_lead's own experiment (carded 2026-10-28; PRIVATE; email_lead typed to the lead: \"card it\"; "
    "APPROVED)\n"
    "### PF-34 — fixture: the dashboard's private notes get a filter (carded 2026-10-28; developer typed to the lead: "
    "\"keep it private for now\"; APPROVED)\n"
    "### PF-35 — fixture: an Up next card for designer (carded 2026-10-28; APPROVED)\n"
    "### PF-36 — fixture: developer's private Up next card (carded 2026-10-28; PRIVATE; developer typed to the lead: \"card "
    "it\"; APPROVED)\n")
ENV = dict((k, v) for k, v in os.environ.items() if k not in pf18b.NO_KEY)
TEAM = ("developer", "email_lead", "designer")


def board():
    """One shared board: developer's and email_lead's shipped work, private cards, assignees, an Up next question."""
    root = pf18b.workspace()
    try:
        deck = os.path.join(root, "new-workflow-design/builds/page-features/task-cards.md")
        with open(deck, "a", encoding="utf-8") as fh:
            fh.write(DECK_MORE)
        git = pf18.Repo(root)
        git.commit("lead: card PF-30 to PF-36 (fixture cards)", "2026-10-28T16:30:00Z")
        for i, cid in enumerate(("PF-30", "PF-31", "PF-32")):
            git.merge("merge %s (fixture card) — developer typed to the lead: \"merge %s\"" % (cid, cid),
                      "2026-10-28T17:%02d:00Z" % i)
        n = [0]

        def now():
            n[0] += 1
            return "2026-10-29T08:00:%02dZ" % n[0]
        dev_queue.mark(root, "PF-30", "understood", "email_lead", env=ENV, commit=False, now=now())
        dev_queue.mark(root, "PF-7", "question", "designer", note="which mock?", env=ENV, commit=False, now=now())
        for card, who in (("PF-5", "developer"), ("PF-35", "designer"), ("PF-11", "email_lead")):
            dev_queue.assign(root, card, who, "developer", env=ENV, commit=False, now=now())
        return dev_queue.build(root, now=BUILD_AT)
    finally:
        shutil.rmtree(root, True)


class Stub(object):
    """127.0.0.1: / is the template on disk with a kit-token meta (so pfAct really posts), /data answers the board
    with the viewer set for this page, POST /act is recorded and answered ok. Every request is kept, body too."""

    def __init__(self, page, doc):
        self.asked, self.viewer = [], None
        page = page.replace(b'<meta charset="utf-8">', b'<meta charset="utf-8">\n<meta name="kit-token" content="t">', 1)
        stub = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                path = self.path.split("?")[0]
                stub.asked.append(("GET", self.path, ""))
                if path in ("/", "/dev-queue.html"):
                    self.answer(200, "text/html; charset=utf-8", page)
                elif path == "/data/dev-queue":
                    self.answer(200, "application/json", json.dumps(dict(doc, viewer=stub.viewer)).encode("utf-8"))
                elif path == "/stamp/dev-queue":
                    self.answer(200, "application/json", b'{"name": "dev-queue", "stamp": [1, 1]}')
                else:
                    self.answer(404, "text/plain", b"no")

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(n).decode("utf-8")
                stub.asked.append(("POST", self.path, body + " " + json.dumps(dict(self.headers))))
                self.answer(200, "application/json", b'{"ok": true, "said": "filed"}')

            def answer(self, code, kind, body):
                self.send_response(code)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:%d/" % self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


# Each column's tiles by group: the h4 above the tile's list, "rest" for the closed fold, "" for an ungrouped column
VIEW = """(() => {
  const out = {};
  document.querySelectorAll('section.column').forEach(sec => {
    const col = sec.id.slice(4); out[col] = {};
    sec.querySelectorAll('[data-tile]').forEach(t => {
      const ul = t.closest('ul'); let g = '';
      if (ul.parentElement.tagName === 'DETAILS') g = 'rest';
      else { let e = ul.previousElementSibling; while (e && e.tagName !== 'H4') e = e.previousElementSibling;
             g = e ? e.textContent.split(' · ')[0] : ''; }
      (out[col][g] = out[col][g] || []).push(t.getAttribute('data-tile'));
    });
  });
  const chips = {};
  document.querySelectorAll('[data-tile]').forEach(t => {
    chips[t.getAttribute('data-tile')] = Array.from(t.querySelectorAll('.chip')).map(c => c.textContent); });
  const box = id => document.getElementById(id);
  return {cols: out, chips: chips, tiles: Array.from(document.querySelectorAll('[data-tile]')).map(t => t.getAttribute('data-tile')),
    groups: Array.from(document.querySelectorAll('section.column:not(#col-issue-queue) h4.queue-group')).map(e => e.textContent),
    stats: box('stats').hidden ? null : Array.from(box('stats').children).map(e => e.textContent).join(' '), viewas: !box('viewas').hidden,
    lens: box('lens').hidden ? null : box('lens').textContent, summary: box('summary').textContent,
    count: box('card-count').textContent, toast: box('toast').textContent,
    views: Array.from(document.querySelectorAll('button.view-as')).map(b => [b.getAttribute('data-view'), b.getAttribute('aria-pressed')])};
})()"""
PANEL_MARKS = "Array.from(document.querySelectorAll('#panel-content button.mark-button')).map(b => b.getAttribute('data-mark'))"


def open_panel(card):
    return ("(() => { const p = document.getElementById('panel'); if (p.open) p.close();"
            " document.querySelector('[data-tile=\"%s\"] button.tile-open').click(); return p.open; })()" % card)


class Data(unittest.TestCase):
    """(d)"""

    @classmethod
    def setUpClass(cls):
        cls.doc = board()
        cls.cards = pf18.by_id(cls.doc)

    def test_d_the_heading_word(self):
        c = self.cards
        for cid in ("PF-32", "PF-33", "PF-36"):
            self.assertIs(c[cid]["private"], True, cid)
            self.assertEqual(c[cid]["reviewers"], [], "%s asks no one for a mark" % cid)
        self.assertEqual((c["PF-32"]["developer"], c["PF-32"]["review"]), ("developer", []))
        self.assertEqual(c["PF-33"]["developer"], "email_lead")
        self.assertIs(c["PF-34"]["private"], False, "lower-case private inside a sentence is not the word")
        self.assertEqual(c["PF-34"]["reviewers"], ["email_lead", "designer"])
        for cid in ("PF-30", "PF-31", "PF-5"):
            self.assertIs(c[cid]["private"], False, cid)
        self.assertEqual((c["PF-30"]["developer"], c["PF-31"]["developer"]), ("developer", "email_lead"))
        rx = dev_queue.PRIVATE_RE
        for heading, want in (("(PRIVATE; developer typed)", True), ("(private build)", False), ("(Private)", False),
                              ("(PRIVATELY)", False), ("(UNPRIVATE)", False)):
            self.assertEqual(bool(rx.search(heading)), want, heading)

    def test_d_a_real_run_shows_ld100_private(self):
        c = pf18.by_id(dev_queue.build(REAL))
        self.assertIn("LD-100", c)
        self.assertIs(c["LD-100"]["private"], True, "LD-100 (chain model explicit)'s heading carries PRIVATE")
        self.assertEqual(c["LD-100"]["reviewers"], [])


class Views(unittest.TestCase):
    """(v)"""

    @classmethod
    def setUpClass(cls):
        binary, _why = pf18e.chrome_bin()
        cls.doc = Data.doc if hasattr(Data, "doc") else board()
        cls.cards = pf18.by_id(cls.doc)
        with open(PAGE, "rb") as fh:
            cls.stub = Stub(fh.read(), cls.doc)
        cls.chrome = pf18e.Chrome(binary)

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
        got = self.chrome.js(VIEW)
        self.assertEqual(self.chrome.exceptions, [], "no page exception")
        return got

    def expected_stats(self, who):
        sees = [c for c in self.doc["cards"] if not c["private"] or c["developer"] == who]
        mine = lambda c, p: any(r["person"] == p and r["understood"] for r in c["review"] or [])
        ship = [c for c in sees if c["column"] == "shipped" and not c["private"] and not mine(c, who)]
        return ("%d wait on your review %d of yours wait on others %d assigned to you %d unassigned" % (
            len([c for c in ship if who in c["reviewers"]]),
            len([c for c in ship if c["developer"] == who and who not in c["reviewers"]]),
            len([c for c in sees if c["assignee"] == who and c["state"] != "shipped"]),
            len([c for c in sees if c["column"] == "up-next" and not c["assignee"]])), len(sees))

    def test_v1_dayus_view(self):
        v = self.page("developer")
        cols = v["cols"]
        self.assertIn("PF-31", cols["shipped"]["Your review"], "a email_lead card waits on developer's review")
        self.assertIn("PF-30", cols["shipped"]["Waiting on others"], "his own card waits on others")
        self.assertNotIn("PF-30", cols["shipped"]["Your review"])
        groups = [g for g in cols["up-next"]]
        self.assertEqual(groups[0], "You", "his Up next opens on his cards")
        self.assertEqual(cols["up-next"]["You"], ["PF-5"])
        self.assertEqual(groups[-1], "Unassigned", "unassigned at the bottom")
        self.assertEqual(cols["up-next"]["designer"], ["PF-35"])
        self.assertIn("Assigned · email_lead", v["chips"]["PF-11"], "the assignee chip on an In progress tile")
        self.assertIn("PF-11", cols["in-progress"][""])
        self.assertEqual(cols["flagged"]["Before build"], ["PF-7"], "Flagged grouped by stage")
        for g in ("Before build", "While building", "After ship"):
            self.assertIn(g + " · ", " ".join(v["groups"]))
        # PRIVATE: present in his own view with the chip; shipped, in his private group and in no Your review
        self.assertEqual(cols["reviewed"]["Your work, private (no review)"], ["PF-32"])
        self.assertIn("Private", v["chips"]["PF-32"])
        self.assertIn("PF-36", v["tiles"])
        self.assertIn("Private", v["chips"]["PF-36"])
        self.assertNotIn("PF-33", v["tiles"], "email_lead's private card is off his own board")
        stats, n = self.expected_stats("developer")
        self.assertEqual(re.sub(r"\s+", " ", v["stats"]).strip(), stats)
        self.assertTrue(v["count"].endswith(" of %d cards" % n), v["count"])
        self.assertTrue(v["viewas"])
        self.assertEqual(v["views"], [["developer", "true"], ["email_lead", "false"], ["designer", "false"]])
        self.assertIsNone(v["lens"], "his own view: no lens")

    def test_v2_email_lead_and_designer(self):
        s = self.page("email_lead")
        self.assertIn("PF-30", s["cols"]["reviewed"]["You reviewed"], "she marked it; designer has not")
        self.assertEqual(self.cards["PF-30"]["column"], "shipped", "not fully reviewed in the shared data")
        self.assertIn("PF-33", s["cols"]["up-next"]["Unassigned"], "her private card, in its normal column, in her view")
        self.assertIn("Private", s["chips"]["PF-33"])
        val = self.page("designer")
        self.assertNotIn("PF-30", (val["cols"]["reviewed"].get("You reviewed") or []))
        self.assertIn("PF-30", val["cols"]["shipped"]["Your review"])
        self.assertEqual(val["cols"]["up-next"]["You"], ["PF-35"])
        for who, v in (("email_lead", s), ("designer", val)):
            for cid in ("PF-32", "PF-36"):
                self.assertNotIn(cid, v["tiles"], "%s: developer's private %s is off the board" % (who, cid))
            stats, n = self.expected_stats(who)
            self.assertEqual(re.sub(r"\s+", " ", v["stats"]).strip(), stats, who)
            self.assertTrue(v["count"].endswith(" of %d cards" % n), (who, v["count"]))
            self.assertNotIn("PF-32", " ".join(sum(v["cols"]["shipped"].values(), [])), who)
        self.assertNotIn("PF-33", val["tiles"], "email_lead's private card is off designer's board")
        # the summary counts what each board draws: developer's private shipped card is in no one else's shipped count
        shipped = lambda v: int(re.search(r"(\d+) shipped", v["summary"]).group(1))
        developer = self.page("developer")
        self.assertEqual(shipped(developer) - shipped(val), 1, (developer["summary"], val["summary"]))

    def test_v3_the_lens(self):
        c = self.chrome
        start = len(self.stub.asked)
        self.page("developer")
        self.assertTrue(c.js(open_panel("PF-31")))
        self.assertEqual(c.js(PANEL_MARKS), ["understood", "question", "issue"])
        before = len(self.stub.asked)
        c.js("document.querySelector('#panel-content button.mark-button[data-mark=understood]').click()")
        self.assertTrue(c.wait("document.getElementById('toast').textContent.indexOf('saved on PF-31') >= 0"),
                        "the positive control: the same button posts when no lens is on")
        posts = [a for a in self.stub.asked[before:] if a[0] == "POST"]
        self.assertEqual([a[1] for a in posts], ["/act"])
        self.assertEqual(json.loads(posts[0][2].split(" {")[0]), {"item": "PF-31", "value": "", "family": "dev-queue", "n": 20})
        self.assertTrue(c.wait("document.querySelectorAll('[data-tile]').length > 0"))
        self.assertTrue(c.js(open_panel("PF-31")))
        c.js("window.__kept = Array.from(document.querySelectorAll('#panel-content button.mark-button'))")

        lens_from = len(self.stub.asked)
        c.js("document.querySelector('button.view-as[data-view=email_lead]').click()")
        v = c.js(VIEW)
        self.assertTrue(v["lens"] and "Looking as email_lead." in v["lens"] and "Read-only" in v["lens"], v["lens"])
        self.assertEqual(v["views"], [["developer", "false"], ["email_lead", "true"], ["designer", "false"]])
        self.assertIn("PF-33", v["tiles"], "email_lead's private card, seen through developer's lens")
        self.assertIn("Private", v["chips"]["PF-33"])
        self.assertNotIn("PF-32", v["tiles"], "developer's own private card is not on email_lead's board")
        self.assertIn("PF-30", v["cols"]["reviewed"]["You reviewed"], "her layout")
        self.assertEqual(c.js("document.getElementById('panel').open && "
                              "document.getElementById('panel-content').querySelectorAll('button.mark-button').length"), 0,
                         "the open panel, recomposed: marks hidden")
        for cid in ("PF-30", "PF-15", "PF-7", "PF-33"):
            self.assertTrue(c.js(open_panel(cid)), cid)
            self.assertEqual(c.js(PANEL_MARKS), [], "%s: no mark button while the lens is on" % cid)
        self.assertEqual(c.js("document.querySelectorAll('button.mark-button').length"), 0, "none on the board either")
        self.assertIn("Read-only", c.js("document.getElementById('panel-content').textContent"))
        # refused: every button kept from before the lens stops at its top, nothing is posted, the page says why
        kinds = c.js("window.__kept.map(b => b.getAttribute('data-mark'))")
        self.assertEqual(kinds, ["understood", "question", "issue"])
        for i in range(len(kinds)):
            c.js("document.getElementById('toast').textContent = ''; window.__kept[%d].click()" % i)
            self.assertIn("Not saved: you are looking as email_lead, read-only", c.js("document.getElementById('toast').textContent"))
        c.wait("false", 1)
        lensed = self.stub.asked[lens_from:]
        self.assertEqual([a for a in lensed if a[0] == "POST"], [], "with the lens on, a mark is refused")
        self.assertFalse([a for a in self.stub.asked[start:] if "email_lead" in (a[1] + a[2]).lower()],
                         "no request the page made carries the viewed name: %s" % lensed)
        self.assertEqual(c.exceptions, [])
        c.js("Array.from(document.querySelectorAll('#lens button')).find(b => b.textContent === 'Back to my view').click()")
        v = c.js(VIEW)
        self.assertIsNone(v["lens"])
        self.assertNotIn("PF-33", v["tiles"])
        self.assertIn("PF-32", v["tiles"])

    def test_v4_an_editor_page_renders_todays_board(self):
        for viewer in ("editor", None):
            v = self.page(viewer)
            self.assertFalse(v["viewas"], viewer)
            self.assertIsNone(v["stats"], viewer)
            self.assertIsNone(v["lens"], viewer)
            self.assertEqual(v["groups"], [], "%s: no per-person groups" % viewer)
            for col in ("up-next", "in-progress", "shipped", "flagged", "reviewed"):
                want = sorted(c["id"] for c in self.doc["cards"] if c["column"] == col and not c["private"])
                got = sorted(sum(v["cols"].get(col, {}).values(), []))
                self.assertEqual(got, want, "%s: %s holds its data column" % (viewer, col))
            for cid in ("PF-32", "PF-33", "PF-36"):
                self.assertNotIn(cid, v["tiles"], "%s: a private card is drawn only in its developer's view" % viewer)
            for chip in sum(v["chips"].values(), []):
                self.assertFalse(chip.startswith("Assigned · ") or chip == "Private", (viewer, chip))


def main():
    binary, why = pf18e.chrome_bin()
    if not binary:
        print("SKIPPED: %s; set CHROME_BIN to a Chrome or Chromium binary" % why)
        sys.exit(0 if os.environ.get("CI_NO_CHROME") == "1" else 1)
    unittest.main()


if __name__ == "__main__":
    main()
