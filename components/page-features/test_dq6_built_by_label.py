#!/usr/bin/env python3
"""DQ-6 (built by label): tiles say who is assigned before a build and who built it after; "Built by" never names the
asker on an Up next card; the queues read oldest first.

    python3 components/page-features/test_dq6_built_by_label.py

    (d) data: PF-24 (full-height shots), approved by developer in its heading and assigned to email_lead, carries built_by developer
        (from the heading) and developer email_lead; once shipped its reviewers leave email_lead out; an unassigned shipped card's
        developer is its built_by
    (v) the template platform/views/viewers/_templates/dev-queue.html, as it is on disk, in headless Chrome
        (CHROME_BIN, else /Applications/Google Chrome.app) from test_pf18k_people_views.py's stub server:
        - PF-24 in Up next reads "Assigned · email_lead", no "Built by" on any Up next or In progress tile; once shipped it
          reads "Built by email_lead"; its panel says "Asked by developer" both times
        - an unassigned shipped card reads "Built by <its built_by>"
        - the Name filter finds PF-24 by email_lead (the developer and assignee) and by developer (who asked)
        - the shipped PF-24 waits on others in email_lead's view, never in her Your review
        - order: three Up next cards carded 10-21, 10-27 and 10-30 (the 10-30 one urgent) read 10-30, 10-21, 10-27;
          Shipped Your review oldest merge first; Reviewed newest first by the mark that completed it
    No Chrome → prints SKIPPED with the reason; exits 0 only when CI_NO_CHROME=1 is set, else 1.

Fixture cards are kept in this file (no .md fixtures under components/). Stdlib only, Python 3.9. Writes only in temp
folders; no network beyond 127.0.0.1.
"""
import os
import shutil
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
import test_pf18k_people_views as pf18k  # noqa: E402  the stub server and the view reader

REAL = features.ROOT
PAGE = os.path.join(REAL, "platform/views/viewers/_templates/dev-queue.html")
DECK = "new-workflow-design/builds/page-features/task-cards.md"
BUILD_AT = "2026-10-30T09:00:00Z"
# Ids run against the dates on purpose, so an id order or a newest-first order cannot pass.
DECK_MORE = (
    "### PF-24 — fixture: full-height shots (carded 2026-10-29; APPROVED: developer typed to the lead: \"go\")\n"
    "### PF-50 — fixture: carded last, urgent (carded 2026-10-30; APPROVED)\n"
    "### PF-51 — fixture: carded in the middle (carded 2026-10-27; APPROVED)\n"
    "### PF-52 — fixture: carded first (carded 2026-10-21; APPROVED)\n"
    "### PF-53 — fixture: email_lead's later merge (carded 2026-10-28; email_lead typed to the lead: \"go\"; DISPATCHED)\n"
    "### PF-54 — fixture: email_lead's earlier merge (carded 2026-10-28; email_lead typed to the lead: \"go\"; DISPATCHED)\n"
    "### PF-55 — fixture: reviewed first, merged later (carded 2026-10-28; designer typed to the lead: \"go\"; "
    "DISPATCHED)\n"
    "### PF-56 — fixture: reviewed last, merged earlier (carded 2026-10-28; designer typed to the lead: \"go\"; "
    "DISPATCHED)\n")
ENV = dict((k, v) for k, v in os.environ.items() if k not in pf18b.NO_KEY)


def boards():
    """(before, after): one workspace read twice, before and after PF-24 (full-height shots) merges."""
    root = pf18b.workspace()
    try:
        with open(os.path.join(root, DECK), "a", encoding="utf-8") as fh:
            fh.write(DECK_MORE)
        git = pf18.Repo(root)
        git.commit("lead: card PF-24 and PF-50 to PF-56 (fixture cards)", "2026-10-28T16:30:00Z")
        for cid, at in (("PF-54", "17:10"), ("PF-53", "17:20"), ("PF-56", "17:30"), ("PF-55", "17:40")):
            git.merge("merge %s (fixture card) — record done" % cid, "2026-10-28T%s:00Z" % at)
        n = [0]

        def now():
            n[0] += 1
            return "2026-10-29T08:00:%02dZ" % n[0]
        for card, who, urgent in (("PF-24", "email_lead", False), ("PF-50", "designer", True),
                                  ("PF-51", "designer", False), ("PF-52", "designer", False)):
            dev_queue.assign(root, card, who, "developer", env=ENV, commit=False, now=now(), urgent=urgent)
        # PF-55 completes first (both reviewers Understood), PF-56 after it
        for card in ("PF-55", "PF-56"):
            for who in ("developer", "email_lead"):
                dev_queue.mark(root, card, "understood", who, env=ENV, commit=False, now=now())
        before = dev_queue.build(root, now=BUILD_AT)
        git.merge("merge PF-24 (full-height shots) — record done", "2026-10-29T12:00:00Z")
        return before, dev_queue.build(root, now=BUILD_AT)
    finally:
        shutil.rmtree(root, True)


_BOARDS = []


def shared():
    if not _BOARDS:
        _BOARDS.append(boards())
    return _BOARDS[0]


class Data(unittest.TestCase):
    """(d)"""

    @classmethod
    def setUpClass(cls):
        before, after = shared()
        cls.before, cls.after = pf18.by_id(before), pf18.by_id(after)

    def test_d1_pf24_asked_by_developer_built_by_email_lead(self):
        for c in (self.before["PF-24"], self.after["PF-24"]):
            self.assertEqual((c["built_by"], c["built_by_from"], c["assignee"], c["developer"]),
                             ("developer", "heading", "email_lead", "email_lead"))
        self.assertEqual(self.before["PF-24"]["column"], "up-next")
        self.assertEqual(self.after["PF-24"]["column"], "shipped")

    def test_d2_the_shipped_pf24s_reviewers_exclude_email_lead(self):
        self.assertNotIn("email_lead", self.after["PF-24"]["reviewers"])
        self.assertTrue(self.after["PF-24"]["reviewers"], "someone is asked")

    def test_d3_an_unassigned_shipped_card_is_built_by_its_built_by(self):
        for cid, who in (("PF-53", "email_lead"), ("PF-55", "designer")):
            c = self.after[cid]
            self.assertEqual((c["column"] in ("shipped", "reviewed"), c["assignee"], c["developer"], c["built_by"]),
                             (True, None, who, who), cid)
        self.assertEqual((self.after["PF-55"]["column"], self.after["PF-56"]["column"]), ("reviewed", "reviewed"))


META = ("(() => { const o = {}; document.querySelectorAll('[data-tile]').forEach(t => {"
        " const m = t.querySelector('.card-meta'); o[t.getAttribute('data-tile')] = m ? m.textContent : null; });"
        " return o; })()")
PANEL_TEXT = "document.getElementById('panel-content').textContent.replace(/\\s+/g, ' ')"


def filtered(who):
    # the filter redraws its own boxes on every change: find the box again to clear it
    box = "document.querySelector('#name-options input[value=\"%s\"]')" % who
    return ("(() => { %s.click();"
            " const t = Array.from(document.querySelectorAll('[data-tile]')).map(e => e.getAttribute('data-tile'));"
            " %s.click(); return t; })()" % (box, box))


class Views(unittest.TestCase):
    """(v)"""

    @classmethod
    def setUpClass(cls):
        binary, _why = pf18e.chrome_bin()
        cls.before, cls.after = shared()
        with open(PAGE, "rb") as fh:
            page = fh.read()
        cls.stubs = {"before": pf18k.Stub(page, cls.before), "after": pf18k.Stub(page, cls.after)}
        cls.chrome = pf18e.Chrome(binary)

    @classmethod
    def tearDownClass(cls):
        cls.chrome.quit()
        for s in cls.stubs.values():
            s.stop()

    def page(self, which, viewer):
        stub = self.stubs[which]
        stub.viewer = viewer
        self.chrome.call("Page.navigate", url=stub.url)
        self.assertTrue(self.chrome.wait("document.readyState === 'complete' && "
                                         "document.getElementById('snapshot').textContent.indexOf('Read') === 0 && "
                                         "document.querySelectorAll('[data-tile]').length > 0"),
                        "the board never drew for %s: %s" % (viewer, self.chrome.exceptions))
        got = self.chrome.js(pf18k.VIEW)
        got["meta"] = self.chrome.js(META)
        self.assertEqual(self.chrome.exceptions, [], "no page exception")
        return got

    def panel(self, cid):
        self.assertTrue(self.chrome.js(pf18k.open_panel(cid)), cid)
        return self.chrome.js(PANEL_TEXT)

    def test_v1_pf24_assigned_in_up_next_asked_by_in_the_panel(self):
        cards = pf18.by_id(self.before)
        for viewer in (None, "developer", "email_lead"):
            v = self.page("before", viewer)
            self.assertTrue(v["meta"]["PF-24"].startswith("Assigned · email_lead · Filed "), (viewer, v["meta"]["PF-24"]))
            for cid, words in v["meta"].items():
                if cards[cid]["column"] in ("up-next", "in-progress"):
                    self.assertNotIn("Built by", words, (viewer, cid))
                    self.assertTrue(words.startswith("Assigned · " if cards[cid]["assignee"] else "Unassigned · "),
                                    (viewer, cid, words))
            text = self.panel("PF-24")
            self.assertIn("Asked by developer", text, viewer)
            self.assertIn("(the approver in the card's heading)", text)
            self.assertIn("Build owner", text)
            self.assertNotIn("Built by", text, "%s: nothing is built yet" % viewer)

    def test_v2_pf24_built_by_email_lead_once_shipped(self):
        v = self.page("after", None)
        self.assertTrue(v["meta"]["PF-24"].startswith("Built by email_lead · Shipped "), v["meta"]["PF-24"])
        text = self.panel("PF-24")
        self.assertIn("Built by email_lead", text)
        self.assertIn("Asked by developer", text)
        # an unassigned shipped card shows today's built_by
        self.assertTrue(v["meta"]["PF-53"].startswith("Built by email_lead · Shipped "), v["meta"]["PF-53"])
        self.assertTrue(v["meta"]["PF-55"].startswith("Built by designer · Shipped "), v["meta"]["PF-55"])

    def test_v3_the_name_filter(self):
        for which in ("before", "after"):
            self.page(which, None)
            self.assertIn("PF-24", self.chrome.js(filtered("email_lead")), "%s: by the developer and assignee" % which)
            self.assertIn("PF-24", self.chrome.js(filtered("developer")), "%s: by who asked" % which)
            self.assertNotIn("PF-24", self.chrome.js(filtered("designer")), which)

    def test_v4_the_shipped_pf24_is_not_in_stephs_review(self):
        v = self.page("after", "email_lead")
        self.assertIn("PF-24", v["cols"]["shipped"]["Waiting on others"])
        self.assertNotIn("PF-24", v["cols"]["shipped"].get("Your review", []))

    def test_v5_queues_oldest_first_histories_newest_first(self):
        v = self.page("before", "designer")
        self.assertEqual(v["cols"]["up-next"]["You"], ["PF-50", "PF-52", "PF-51"],
                         "10-30 (urgent), then 10-21, then 10-27")
        self.assertIn("Urgent", v["chips"]["PF-50"])
        team = self.page("before", None)["cols"]["up-next"][""]
        self.assertEqual([c for c in team if c in ("PF-50", "PF-51", "PF-52")], ["PF-50", "PF-52", "PF-51"],
                         "the team board too")
        merged = dict((c["id"], (c["merged"] or {}).get("at")) for c in self.after["cards"])
        d = self.page("after", "developer")["cols"]["shipped"]["Your review"]
        self.assertEqual([c for c in d if c in ("PF-53", "PF-54")], ["PF-54", "PF-53"], "oldest merge first")
        self.assertEqual([merged[c] for c in d], sorted(merged[c] for c in d), "the whole group, oldest merge first")
        reviewed = self.page("after", None)["cols"]["reviewed"][""]
        self.assertEqual(reviewed, ["PF-56", "PF-55"], "newest completing mark first (merge order would be PF-55 first)")


def main():
    binary, why = pf18e.chrome_bin()
    if not binary:
        print("SKIPPED: %s; set CHROME_BIN to a Chrome or Chromium binary" % why)
        sys.exit(0 if os.environ.get("CI_NO_CHROME") == "1" else 1)
    unittest.main()


if __name__ == "__main__":
    main()
