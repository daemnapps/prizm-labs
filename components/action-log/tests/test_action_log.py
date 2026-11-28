import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class ActionLogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["ACTION_LOG_WS"] = str(self.tmp)
        os.environ["ACTION_LOG_FILE"] = str(self.tmp / "runs/action-log/log.jsonl")
        os.environ["ACTION_LOG_VIEWS"] = str(self.tmp / "runs/action-log/views.json")
        os.environ["ACTION_LOG_CONF"] = str(self.tmp / "none.json")
        sys.path.insert(0, str(HERE.parent))
        import importlib
        import action_log
        self.A = importlib.reload(action_log)

    def entry(self, **k):
        e = {"brand": "acme", "kind": "budget", "by": "owner", "why": "test",
             "object": {"type": "campaign", "id": "1"}, "before": "1000", "after": "950"}
        e.update(k)
        return e

    def test_append_chains_and_verifies(self):
        a = self.A.append(self.entry())
        b = self.A.append(self.entry(after="900"))
        self.assertEqual((a["seq"], b["seq"]), (1, 2))
        self.assertEqual(b["prev"], a["hash"])
        self.assertTrue(self.A.verify()["ok"])

    def test_an_edit_breaks_the_chain(self):
        self.A.append(self.entry())
        self.A.append(self.entry(after="900"))
        p = Path(os.environ["ACTION_LOG_FILE"])
        lines = p.read_text().splitlines()
        e = json.loads(lines[0]); e["after"] = "5000"; lines[0] = json.dumps(e)
        p.write_text("\n".join(lines) + "\n")
        self.assertFalse(self.A.verify()["ok"])

    def test_the_door_refuses_a_bad_entry(self):
        with self.assertRaises(ValueError):
            self.A.append({"brand": "acme", "kind": "budget"})
        with self.assertRaises(ValueError):
            self.A.append(self.entry(kind="whatever"))
        with self.assertRaises(ValueError):
            self.A.append(self.entry(brand="Not A Brand"))

    def test_ingest_is_idempotent(self):
        d = self.tmp / "runs/media-buying/acme"
        d.mkdir(parents=True)
        (self.tmp / "brands/acme").mkdir(parents=True)
        (d / "actions.jsonl").write_text(json.dumps({"at": "2026-11-28T13:46:55", "id": "9", "did": "main budget $1,000 -> $950",
                                                     "why": 'owner (typed: "Yes, $950")', "meta": {"success": True}}) + "\n")
        r1 = self.A.ingest()
        r2 = self.A.ingest()
        self.assertEqual((r1["added"], r2["added"]), (1, 0))
        e = self.A.read()[0]
        self.assertEqual((e["kind"], e["before"], e["after"], e["said"]), ("budget", "1000", "950", "Yes, $950"))

    def test_views(self):
        v = self.A.save_view({"name": "new briefs", "kind": "live", "days": 14, "window": 7, "reads": ["cpa_change"]})
        self.assertEqual(v["reads"], ["cpa_change"])
        self.A.save_view({"name": "new briefs", "window": 3})
        self.assertEqual(len(self.A.views()["views"]), 1)


if __name__ == "__main__":
    unittest.main()
