#!/usr/bin/env python3
"""python3 machine/test_slotfill.py — holes are always filled; no network (fake researcher)."""
import importlib.util, json, tempfile, unittest
from pathlib import Path
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("t_slot", HERE / "slotfill.py"); sl = importlib.util.module_from_spec(spec); spec.loader.exec_module(sl)
DOC = {"scenes": [
    {"id": "S1", "section": "hook", "voice": "I'm at the counter."},
    {"id": "S3", "section": "failed-solutions", "kind": "screen", "voice": "", "screen": {"lines": ["WHAT IT COST", "[UNFILLED]"], "lands_on": "a little kojic acid soap", "surface": "order"}},
    {"id": "S5", "section": "objections", "voice": "You use less than you think. [SLOT: how much per use] That's why twice a week lasts."}]}

def brief():
    f = Path(tempfile.mkdtemp()) / "5-brief.md"
    f.write_text("# brief\n\n```json\n" + json.dumps(DOC) + "\n```\n")
    return f

class Fill(unittest.TestCase):
    def setUp(self):
        # tests never write into a real brand folder
        self._doc = sl.document
        sl.document = lambda *a, **k: None

    def tearDown(self):
        sl.document = self._doc

    def test_every_hole_is_filled_and_nothing_is_dropped(self):
        f = brief()
        def fake(prompt):
            self.assertIn("kojic acid soap", prompt)      # the hole comes with its scene's context
            return json.dumps({"holes": [
                {"id": "H1", "fill": "$12 FOR KOJIC ACID SOAP", "line": "$12 FOR KOJIC ACID SOAP", "source": "web", "receipt": "https://example.com"},
                {"id": "H2", "fill": "A little goes further than you'd guess.", "line": "You use less than you think. A little goes further than you'd guess. That's why twice a week lasts.", "source": "inferred", "receipt": "inferred from: context"}]})
        res = sl.fill(f, "brand-a", "body-scrub", call=fake)
        self.assertEqual(len(res["changes"]), 2)
        d = sl._block(f.read_text())[1]
        s3 = next(s for s in d["scenes"] if s["id"] == "S3")
        self.assertEqual(s3["screen"]["lines"], ["WHAT IT COST", "$12 FOR KOJIC ACID SOAP"])
        s5 = next(s for s in d["scenes"] if s["id"] == "S5")
        self.assertNotIn("[SLOT", s5["voice"])
        self.assertIn("That's why twice a week lasts.", s5["voice"])
        self.assertNotIn("[UNFILLED", f.read_text().split("## Holes filled")[0])

    def test_no_holes_no_call(self):
        f = Path(tempfile.mkdtemp()) / "b.md"
        f.write_text("```json\n" + json.dumps({"scenes": [{"id": "S1", "voice": "fine"}]}) + "\n```\n")
        res = sl.fill(f, "brand-a", call=lambda p: (_ for _ in ()).throw(AssertionError("called")))
        self.assertEqual(res.get("note"), "no holes")

if __name__ == "__main__":
    unittest.main()
