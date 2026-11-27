"""One print at a time and any Higgsfield account (set_queue, 2026-11-11)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from image_production import set_queue as Q  # noqa: E402


class Printing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.p = mock.patch.object(Q, "home", lambda brand: self.home / brand)
        self.p.start()
        (self.home / "b").mkdir()
        (self.home / "b" / "r1.json").write_text(json.dumps({"id": "r1", "brand": "b", "state": "open", "what": "x"}))

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def test_sent_print_blocks_a_second_print_and_plan(self):
        Q.printing("b", "r1", "proj", "gen", "editor@x", 671.82)
        with self.assertRaises(SystemExit):
            Q.printing("b", "r1", "proj", "gen2")
        with mock.patch.object(Q, "read", lambda b, r: json.loads((self.home / "b" / "r1.json").read_text())):
            out = Q.plan("b", "r1")
        self.assertIsNone(out["print"])
        self.assertIn("Do not print it again", out["stop"])

    def test_clear_needs_a_reason_and_frees_the_request(self):
        Q.printing("b", "r1", "proj", "gen")
        with self.assertRaises(SystemExit):
            Q.printing("b", "r1", clear="  ")
        r = Q.printing("b", "r1", clear="not taken: no charge")
        self.assertNotIn("printing", r)
        self.assertEqual(r["print_log"][0]["generation"], "gen")
        Q.printing("b", "r1", "proj", "gen3")

    def test_sending_needs_both_ids(self):
        with self.assertRaises(SystemExit):
            Q.printing("b", "r1", "proj", None)


class AnyAccount(unittest.TestCase):
    def test_note_says_never_carry_ids(self):
        self.assertIn("Never pass an id", Q.ANY_ACCOUNT)


if __name__ == "__main__":
    unittest.main()
