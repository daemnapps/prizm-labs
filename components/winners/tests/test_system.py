"""winners.py system: every step from ad results to a brief, for any brand, from files only; the bar stays the
owner's and teardowns are marked as spend."""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import system as SY  # noqa: E402


class System(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.home = self.root / "runs" / "winners" / "acme"
        (self.home / "score" / "2026-11-20").mkdir(parents=True)
        (self.home / "score" / "2026-11-20" / "score.json").write_text(json.dumps({"results_from": "the warehouse"}))
        (self.home / "bank.json").write_text(json.dumps({"brand": "acme", "bar": {"min_spend": None}, "rows": [
            {"id": "acme-1", "name": "A", "core": True, "format": "Video", "snapshots": [{"purchases": 5}]},
            {"id": "acme-2", "name": "B", "core": True, "format": "Video", "snapshots": [{"purchases": 3}]},
            {"id": "acme-3", "name": "C", "core": True, "format": "Image", "snapshots": [{"purchases": 2}]}]}))

    def by(self, d):
        return {s["step"]: s for s in d["steps"]}

    def test_a_brand_with_a_bank_and_no_index(self):
        d = SY.build(self.root, "acme", today=dt.date(2026, 11, 26))
        s = self.by(d)
        self.assertEqual(list(s), ["results", "audit", "bank", "bar", "teardowns", "proof", "index", "messages",
                                   "shapes", "profiles", "brief"])
        self.assertEqual(s["results"]["state"], "ready")
        self.assertEqual(s["bar"]["state"], "owner")                 # never set here
        self.assertEqual(s["index"]["state"], "todo")
        self.assertIn("winner_index.py build --brand acme", s["index"]["next"])
        self.assertEqual(s["brief"]["state"], "blocked")
        self.assertEqual([x["step"] for x in d["waiting_on_owner"]], ["bar"])

    def test_teardowns_count_core_videos_and_mark_spend(self):
        (self.home / "winner-index.json").write_text(json.dumps({"built": "2099-01-01", "winners": [
            {"run": "acme-core8-01", "bank_id": "acme-1", "copy_of": None, "teardown": {"complete": True},
             "retire": {"call": "keep"}, "proof": {"purchases": 5}, "label": "Winner #1 · a", "message_read": {}}]}))
        s = self.by(SY.build(self.root, "acme", today=dt.date(2026, 11, 26)))
        self.assertEqual(s["teardowns"]["state"], "spend")
        self.assertTrue(s["teardowns"]["has"].startswith("1 of 2 Core videos torn down (1 Core image ads"))
        self.assertEqual(s["proof"]["state"], "ready")
        self.assertEqual(s["messages"]["state"], "todo")             # its message read is empty

    def test_a_parked_winner_is_a_decision_not_a_gap(self):
        (self.home / "winner-index.json").write_text(json.dumps({"built": "2099-01-01", "winners": [
            {"run": "acme-core8-01", "bank_id": "acme-1", "copy_of": None, "teardown": {"complete": True, "missing": []},
             "retire": {"call": "keep"}, "proof": {"purchases": 5}, "label": "Winner #1 · a",
             "message_read": {"core": "c", "beliefs": ["b"], "delivery": "d", "angle": ["a"], "load_bearing": ["l"]}}]}))
        (self.home / "messages").mkdir()
        (self.home / "messages" / "messages.json").write_text(json.dumps(
            {"messages": [], "parked": [{"run": "acme-core8-01", "why": "its message is not ours to say"}]}))
        s = self.by(SY.build(self.root, "acme", today=dt.date(2026, 11, 26)))
        self.assertEqual(s["messages"]["state"], "ready")
        self.assertIn("1 parked on purpose", s["messages"]["has"])

    def test_a_stale_score_says_so(self):
        s = self.by(SY.build(self.root, "acme", today=dt.date(2026, 12, 30)))
        self.assertEqual(s["results"]["state"], "stale")
        self.assertIn("score --brand acme", s["results"]["next"])

    def test_write_files_both_copies(self):
        p, _ = SY.write(self.root, "acme")
        self.assertTrue(p.is_file() and (self.home / "system.json").is_file())


if __name__ == "__main__":
    unittest.main()
