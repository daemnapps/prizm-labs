#!/usr/bin/env python3
"""SI-129 (briefs register honest): the brief register's `status` holds only
rule 6's three words, and where a brief sits on the track lives in `state` —
in the file and in every program that reads it (components rule 6, triage
page 15, Option A).

    /usr/bin/python3 tools/image-teardown/tests/test_register_state.py

No network, no model. The real briefs.json is only ever READ.
"""
import json, re, sys, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tools"))
import briefs as B  # noqa: E402

REAL = HERE / "briefs.json"
STATUSES = {"draft", "approved", "deprecated"}
TRACK = ["for-review", "approved", "in-production", "shipped"]


def rows():
    reg = json.loads(REAL.read_text(encoding="utf-8"))
    for sec in ("briefs", "retired"):
        for k, r in reg.get(sec, {}).items():
            yield sec, k, r


class RegisterFile(unittest.TestCase):

    def test_every_status_is_a_rule6_word(self):
        seen = 0
        for sec, k, r in rows():
            self.assertIn(r.get("status"), STATUSES, f"{sec}/{k}")
            seen += 1
        self.assertGreater(seen, 0)

    def test_the_lifecycle_words_live_in_state(self):
        for sec, k, r in rows():
            self.assertIn(r.get("state"), TRACK, f"{sec}/{k}")

    def test_status_follows_state(self):
        for sec, k, r in rows():
            self.assertEqual(r["status"], B.STATUS_OF[r["state"]], f"{sec}/{k}")

    def test_the_moved_words_are_all_there(self):
        states = [r["state"] for _, _, r in rows()]
        self.assertIn("for-review", states)
        self.assertIn("in-production", states)


class Readers(unittest.TestCase):

    def test_track_and_mapping(self):
        self.assertEqual(B.TRACK, TRACK)
        self.assertEqual(B.STATUS_OF, {"for-review": "draft", "approved": "approved",
                                       "in-production": "approved", "shipped": "approved"})

    def test_lifecycle_reads_state_and_an_old_row_still_reads(self):
        self.assertEqual(B.lifecycle({"status": "approved", "state": "in-production"}),
                         "in-production")
        self.assertEqual(B.lifecycle({"status": "for-review"}), "for-review")

    def test_set_lifecycle_writes_state_and_its_status(self):
        rec = {"status": "draft", "state": "for-review"}
        B.set_lifecycle(rec, "in-production")
        self.assertEqual(rec, {"status": "approved", "state": "in-production"})
        B.set_lifecycle(rec, "for-review")
        self.assertEqual(rec, {"status": "draft", "state": "for-review"})

    def test_new_briefs_are_written_draft_and_for_review(self):
        src = (HERE / "tools" / "briefs.py").read_text(encoding="utf-8")
        self.assertNotRegex(src, r'"status":\s*"(for-review|in-production|shipped)"')
        drafts = re.findall(r'"status":\s*"draft",[^\n]*\n\s*"state":\s*"for-review"', src)
        self.assertEqual(len(drafts), 5)

    def test_serve_reads_state(self):
        src = (HERE / "serve.py").read_text(encoding="utf-8")
        self.assertIn("B.lifecycle(rec)", src)
        self.assertIn("B.set_lifecycle(rec, s)", src)
        self.assertNotRegex(src, r'rec\["status"\]\s*=')
        self.assertNotRegex(src, r'TRACK\.index\(rec\["status"\]\)')


if __name__ == "__main__":
    unittest.main()
