"""checks_board: the Checks panel never breaks on a production that is part-way made."""
import json
import tempfile
import unittest
from pathlib import Path

import checks_board as CB


class PartWay(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.B = Path(self.d.name)
        (self.B / "scenes" / "S1" / "hook").mkdir(parents=True)

    def tearDown(self):
        self.d.cleanup()

    def take(self, **kw):
        json.dump(dict({"model": "seedance@higgsfield", "seconds": 5, "script": [{"do": "she leans in"}]}, **kw),
                  open(self.B / "scenes" / "S1" / "hook" / "take.json", "w"))

    def rows(self, group):
        return [c for c in CB.checks("p", self.B)["checks"] if c["group"] == group]

    def test_a_take_with_no_out_yet_is_not_made(self):
        self.take()                                       # written, never run: no "out"
        r = self.rows("AI takes")
        self.assertEqual(len(r), 1)
        self.assertFalse(r[0]["ok"])
        self.assertEqual(r[0]["short"], "not made")
        self.assertIsNone(r[0]["video"])

    def test_a_take_whose_out_file_is_missing_is_not_made(self):
        self.take(out=str(self.B / "scenes" / "S1" / "hook" / "take.mp4"))
        self.assertFalse(self.rows("AI takes")[0]["ok"])

    def test_a_made_take_links_its_clip(self):
        f = self.B / "scenes" / "S1" / "hook" / "take.mp4"
        f.write_bytes(b"x")
        self.take(out=str(f))
        r = self.rows("AI takes")[0]
        self.assertTrue(r["ok"])
        self.assertEqual(r["video"], "/files/p/scenes/S1/hook/take.mp4")

    def test_half_written_records_do_not_empty_the_panel(self):
        self.take()
        json.dump({"checks": [{"detail": "no name, no pass"}]}, open(self.B / "SWIPE-CHECK.json", "w"))
        json.dump({"stage": "render", "steps": [{"said": "no name, no state"}]}, open(self.B / "next-job.json", "w"))
        json.dump([{"note": "no what"}], open(self.B / "checks-eye.json", "w"))
        (self.B / "voice" / "continuous").mkdir(parents=True)
        json.dump({"text": "no match yet"}, open(self.B / "voice" / "continuous" / "body.json", "w"))
        out = CB.checks("p", self.B)
        self.assertTrue(out["checks"])
        self.assertIn("Voice", {c["group"] for c in out["checks"]})

    def test_an_empty_production_answers(self):
        out = CB.checks("p", self.B)
        self.assertIsInstance(out["checks"], list)


if __name__ == "__main__":
    unittest.main()
