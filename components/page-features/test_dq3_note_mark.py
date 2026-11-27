#!/usr/bin/env python3
"""DQ-3 (note mark): a fifth Dev-queue mark, Note: one line on any card, shown on its tile, never a flag or a review.

    python3 components/page-features/test_dq3_note_mark.py

    (d) data, through kit/serve.py's Act (run table entry 24) and the real dev_queue.py mark, in one fixture workspace:
        - a note on an Up next card is ONE review record, a no-judgment `seen` with reasons ["note"] and its line as
          the note; the card stays in Up next and carries the note in `notes`
        - a second note from the same person replaces the first in `notes`; both stay in the history ("noted")
        - a note never changes column, state, the review line or Flagged, on Up next, In progress and Shipped (a
          Reviewed card stays Reviewed); it is never in `marks`, and an assignment is never read as a note (nor a
          note as an assignment)
        - Resolve of a note is refused ("nothing to resolve") and writes nothing; a note with no words, two lines,
          over 200 characters or with --of is refused before the write
    (v) the template platform/views/viewers/_templates/dev-queue.html, as it is on disk, in headless Chrome (CHROME_BIN,
        else /Applications/Google Chrome.app) from test_pf18k_people_views.py's stub server, on the board (d) built:
        - each person's latest note is on the tile face ("✎ developer: …"), the older one only in the panel's history
        - the Note button sits beside the marks in the panel (its own class: the marks' buttons are unchanged); a
          click with words posts /act n 24 with the card and the words, a click with none posts nothing
        - the noted Reviewed card is in email_lead's "You reviewed", never in her "Your review"; with the lens on there is
          no Note button
    No Chrome → prints SKIPPED with the reason; exits 0 only when CI_NO_CHROME=1 is set, else 1.

The fixture workspace is test_pf18b_review_marks.py's (a test file; no .md fixtures under components/). Stdlib only,
Python 3.9. Writes only in temp folders; no network beyond 127.0.0.1: the review key is removed from every environment.
"""
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "kit"))
import dev_queue  # noqa: E402
import features  # noqa: E402
import serve  # noqa: E402
import test_pf18_dev_queue as pf18  # noqa: E402  the fixture repo
import test_pf18b_review_marks as pf18b  # noqa: E402  the fixture workspace, Act's runner, next_second
import test_pf18e_panel_opens as pf18e  # noqa: E402  the Chrome driver
import test_pf18k_people_views as pf18k  # noqa: E402  the stub server, the board reader

REAL = features.ROOT
PAGE = os.path.join(REAL, "platform/views/viewers/_templates/dev-queue.html")
ENV = dict((k, v) for k, v in os.environ.items() if k not in pf18b.NO_KEY)
FIRST, SECOND = "check the mock before building", "the mock is fine, go"


def keyed(c):
    """What a note must never move."""
    return (c["column"], c["state"], c.get("flag_stage"), json.dumps(c.get("review"), sort_keys=True),
            json.dumps(c.get("marks"), sort_keys=True), json.dumps(c.get("reviewers")))


class Data(unittest.TestCase):
    """(d)"""

    @classmethod
    def setUpClass(cls):
        cls.root = pf18b.workspace()
        cls.rv = dev_queue.review_module()
        cls.steps = {}
        b = Data.Steps(cls.root, cls.rv)
        try:
            cls.steps = b.run()
        finally:
            cls.doc = dev_queue.build(cls.root, now=pf18.NOW)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, True)

    class Steps(object):
        """The sequence, run once; each step keeps the board before and after it."""

        def __init__(self, root, rv):
            self.root, self.rv = root, rv

        def run_cmd(self, argv):
            p = subprocess.run(argv, cwd=self.root, capture_output=True, text=True, env=pf18b.env_for(self.root),
                               timeout=120, stdin=subprocess.DEVNULL)
            return p.returncode, (p.stdout or "") + (p.stderr or "")

        def press(self, person, n, card, value=""):
            pf18b.next_second()
            act = serve.Act("dev-queue", self.root, person, None, runner=self.run_cmd)
            return act.run({"family": "dev-queue", "n": n, "item": card, "value": value})

        def board(self):
            return pf18.by_id(dev_queue.build(self.root, now=pf18.NOW))

        def n(self):
            return len(self.rv.read_records(root=self.root))

        def run(self):
            s = {}
            # PF-15 reviewed by both before any note; PF-5 assigned to developer (a `seen` too)
            for who in ("email_lead", "designer"):
                assert self.press(who, 20, "PF-15")["ok"]
            assert self.press("developer", 21, "PF-7", "which mock?")["ok"]
            dev_queue.assign(self.root, "PF-5", "designer", "developer", env=ENV, commit=False)
            s["before"] = self.board()
            s["n0"] = self.n()
            s["first"] = self.press("developer", 24, "PF-5", FIRST)
            s["n1"] = self.n()
            s["after_first"] = self.board()
            s["first_rec"] = self.rv.read_records(root=self.root)[-1]
            s["second"] = self.press("developer", 24, "PF-5", SECOND)
            s["after_second"] = self.board()
            for who, card, words in (("email_lead", "PF-5", "designer owns this one"), ("designer", "PF-11", "halfway"),
                                     ("email_lead", "PF-15", "read it twice, still fine"),
                                     ("designer", "PF-7", "a note beside the question")):
                s[(who, card)] = self.press(who, 24, card, words)
            s["after_all"] = self.board()
            n = self.n()
            s["resolve"] = self.press("developer", 23, "PF-5", "developer")
            s["resolve_email_lead"] = self.press("developer", 23, "PF-15", "email_lead")
            s["empty"] = self.press("developer", 24, "PF-5", "")
            s["n_refused"] = (n, self.n())
            s["after_refused"] = self.board()
            return s

    def test_d1_a_note_on_up_next_stays_in_up_next_on_the_tile(self):
        s = self.steps
        self.assertTrue(s["first"]["ok"], s["first"])
        self.assertEqual(s["n1"], s["n0"] + 1, "one click, one record")
        rec = s["first_rec"]
        self.assertEqual((rec["reviewer"], rec["item"]), ("developer", "RQ-dev-queue-PF-5"))
        self.assertEqual(rec["verdict"], {"event": "seen", "reasons": ["note"], "note": FIRST})
        c = s["after_first"]["PF-5"]
        self.assertEqual((c["column"], c["state"]), ("up-next", "up-next"))
        self.assertEqual([(n["person"], n["note"]) for n in c["notes"]], [("developer", FIRST)])
        self.assertEqual(keyed(c), keyed(s["before"]["PF-5"]), "nothing else on the card moved")

    def test_d2_a_second_note_replaces_the_first_on_the_tile_both_in_history(self):
        s = self.steps
        self.assertTrue(s["second"]["ok"], s["second"])
        c = s["after_second"]["PF-5"]
        self.assertEqual([(n["person"], n["note"]) for n in c["notes"]], [("developer", SECOND)], "the latest only")
        noted = [(x["by"], x["note"]) for x in c["history"] if x["what"] == "noted"]
        self.assertEqual(sorted(noted), sorted([("developer", FIRST), ("developer", SECOND)]), "both stay in the history")
        c = s["after_all"]["PF-5"]
        self.assertEqual([n["person"] for n in c["notes"]], ["email_lead", "developer"], "one per person, newest first")

    def test_d3_a_note_never_moves_a_card_flags_or_reviews(self):
        s = self.steps
        before, after = s["before"], s["after_all"]
        for card, column in (("PF-5", "up-next"), ("PF-11", "in-progress"), ("PF-15", "reviewed"), ("PF-7", "flagged")):
            self.assertEqual(after[card]["column"], column, card)
            self.assertEqual(keyed(after[card]), keyed(before[card]), "%s: column, state, review, marks unchanged" % card)
            self.assertTrue(after[card]["notes"], card)
            self.assertNotIn("note", [m["mark"] for m in after[card]["marks"] or []], "%s: a note is never a mark" % card)
        self.assertEqual([(r["person"], r["understood"]) for r in after["PF-15"]["review"]],
                         [("email_lead", True), ("designer", True)], "a note is no review and undoes none")
        # PF-18m (open issues only)'s assigner rule: developer assigned PF-5, so he is not its reviewer; email_lead alone remains
        self.assertEqual((after["PF-5"]["assignee"], after["PF-5"]["reviewers"]), ("designer", ["email_lead"]),
                         "an assignment still reads as one; a note is never an assignment")
        rv = self.rv
        recs = [r for r in rv.read_records(root=self.root) if r.get("item") == "RQ-dev-queue-PF-5"]
        self.assertEqual(rv.fold(recs)["verdicts"], {}, "no note is a verdict in the review fold")
        self.assertEqual(len(dev_queue.notes_of(recs)[1]), 3, "two of developer's and email_lead's; the assignment is no note")
        for r in recs:
            if dev_queue.is_assign(r):
                self.assertIsNone(dev_queue.mark_word(r), "an assignment is never read as a note")
        self.assertEqual(self.doc["marks"]["words"], ["understood", "question", "issue", "resolve", "note"])
        self.assertEqual(self.doc["marks"]["flags"], ["question", "issue"])

    def test_d4_resolve_of_a_note_is_refused(self):
        s = self.steps
        for key in ("resolve", "resolve_email_lead"):
            self.assertFalse(s[key]["ok"], key)
            self.assertIn("REFUSED", s[key]["said"])
            self.assertIn("nothing to resolve", s[key]["said"])
        self.assertFalse(s["empty"]["ok"])
        self.assertIn("a note needs its words", s["empty"]["said"])
        n, after = s["n_refused"]
        self.assertEqual(after, n, "refusals write nothing")
        for card in ("PF-5", "PF-15"):
            self.assertEqual(keyed(s["after_refused"][card]), keyed(s["after_all"][card]), card)

    def test_d5_the_data_command_refuses_a_bad_note_before_the_write(self):
        root = pf18b.workspace()
        self.addCleanup(shutil.rmtree, root, True)
        rv = self.rv
        for note, of, why in (("", None, "needs its words"), ("   ", None, "needs its words"),
                              ("two\nlines", None, "one line"), ("x" * 201, None, "at most 200"),
                              ("words", "developer", "--of")):
            with self.assertRaises(rv.Refused, msg=repr(note)) as cm:
                dev_queue.mark(root, "PF-5", "note", "developer", note=note, of=of, env=ENV, commit=False)
            self.assertIn(why, str(cm.exception))
        with self.assertRaises(rv.Refused) as cm:
            dev_queue.mark(root, "PF-5", "resolve", "developer", of="developer", env=ENV, commit=False)
        self.assertIn("nothing to resolve", str(cm.exception))
        self.assertEqual(rv.read_records(root=root), [], "every refusal before the write")
        out = dev_queue.mark(root, "PF-16", "note", "editor", note="x" * 200, env=ENV, commit=False)
        self.assertEqual(out["record"]["verdict"]["reasons"], ["note"], "anyone, on a shipped card, 200 characters")
        self.assertEqual(pf18.by_id(dev_queue.build(root, now=pf18.NOW))["PF-16"]["column"], "shipped")


class Views(unittest.TestCase):
    """(v)"""

    @classmethod
    def setUpClass(cls):
        binary, _why = pf18e.chrome_bin()
        if not hasattr(Data, "doc"):
            Data.setUpClass()
        cls.doc = Data.doc
        with open(PAGE, "rb") as fh:
            cls.stub = pf18k.Stub(fh.read(), cls.doc)
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
        got = self.chrome.js(pf18k.VIEW)
        self.assertEqual(self.chrome.exceptions, [], "no page exception")
        return got

    def tile_notes(self, card):
        return self.chrome.js("Array.from(document.querySelectorAll('[data-tile=\"%s\"] .tile-note'))"
                              ".map(e => e.textContent)" % card)

    def test_v1_the_tile_face_and_the_history(self):
        v = self.page("developer")
        self.assertIn("PF-5", v["cols"]["up-next"]["designer"], "a noted card stays in Up next")
        self.assertEqual(self.tile_notes("PF-5"), ["✎ email_lead: designer owns this one", "✎ developer: " + SECOND])
        self.assertEqual(self.tile_notes("PF-11"), ["✎ designer: halfway"])
        self.assertIn("PF-7", sum(v["cols"]["flagged"].values(), []), "the question flags, the note does not unflag")
        c = self.chrome
        self.assertTrue(c.js(pf18k.open_panel("PF-5")))
        hist = c.js("Array.from(document.querySelectorAll('#panel-content ol.history li')).map(e => e.textContent)")
        self.assertTrue([x for x in hist if x.startswith("Left a note: " + FIRST)], hist)
        self.assertTrue([x for x in hist if x.startswith("Left a note: " + SECOND)], hist)
        self.assertNotIn(FIRST, " ".join(self.tile_notes("PF-5")), "the older note is not on the face")

    def test_v2_the_note_button_beside_the_marks(self):
        c = self.chrome
        self.page("developer")
        self.assertTrue(c.js(pf18k.open_panel("PF-15")))
        self.assertEqual(c.js(pf18k.PANEL_MARKS), ["understood", "question", "issue"], "the marks are unchanged")
        group = c.js("Array.from(document.querySelectorAll('#panel-content .marks button'))"
                     ".map(b => b.className + ':' + b.getAttribute('data-mark'))")
        self.assertEqual(group[-1], "note-button:note", group)
        self.assertEqual(c.js("document.querySelector('#panel-content button.note-button').textContent"), "✎ Note")
        before = len(self.stub.asked)
        c.js("window.prompt = () => '  a line  for  later ';"
             " document.querySelector('#panel-content button.note-button').click()")
        self.assertTrue(c.wait("document.getElementById('toast').textContent.indexOf('Note saved on PF-15') >= 0"))
        posts = [a for a in self.stub.asked[before:] if a[0] == "POST"]
        self.assertEqual([a[1] for a in posts], ["/act"])
        self.assertEqual(json.loads(posts[0][2].split(" {")[0]),
                         {"item": "PF-15", "value": "a line for later", "family": "dev-queue", "n": 24})
        self.assertTrue(c.wait("document.querySelectorAll('[data-tile]').length > 0"))
        self.assertTrue(c.js(pf18k.open_panel("PF-5")))
        before = len(self.stub.asked)
        c.js("window.prompt = () => '   '; document.querySelector('#panel-content button.note-button').click()")
        c.wait("false", 1)
        self.assertEqual([a for a in self.stub.asked[before:] if a[0] == "POST"], [], "no words, nothing posted")
        self.assertIn("a note needs its words", c.js("document.getElementById('panel-content').textContent"))
        for card in ("PF-11", "PF-7"):
            self.assertTrue(c.js(pf18k.open_panel(card)), card)
            self.assertEqual(c.js("document.querySelectorAll('#panel-content button.note-button').length"), 1, card)
        self.assertEqual(c.exceptions, [])

    def test_v3_never_in_your_review_and_no_button_through_the_lens(self):
        s = self.page("email_lead")
        self.assertIn("PF-15", s["cols"]["reviewed"]["You reviewed"])
        self.assertNotIn("PF-15", s["cols"]["shipped"].get("Your review", []), "a note asks no one for a review")
        c = self.chrome
        self.page("developer")
        c.js("document.querySelector('button.view-as[data-view=email_lead]').click()")
        self.assertTrue(c.js(pf18k.open_panel("PF-5")))
        self.assertEqual(c.js("document.querySelectorAll('button.note-button').length"), 0, "read-only lens")
        self.assertEqual(c.exceptions, [])


def main():
    binary, why = pf18e.chrome_bin()
    if not binary:
        print("SKIPPED: %s; set CHROME_BIN to a Chrome or Chromium binary" % why)
        sys.exit(0 if os.environ.get("CI_NO_CHROME") == "1" else 1)
    unittest.main()


if __name__ == "__main__":
    main()
