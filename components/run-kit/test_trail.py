"""The decision trail: rows are kept, repeats are not, the block reads in stage order, a brief gathers every run."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_kit import trail as T  # noqa: E402


class Trail(unittest.TestCase):
    def test_empty_is_none(self):
        self.assertEqual(T.block([]), "NONE")
        self.assertEqual(T.block(None), "NONE")

    def test_add_keeps_reason_and_skips_a_repeat(self):
        st = {}
        T.add(st, "teardown", "format", "talking head", "one person carries the message")
        T.add(st, "teardown", "format", "talking head", "one person carries the message")
        self.assertEqual(len(st["trail"]), 1)
        T.add(st, "teardown", "format", "skit", "a scene carries it")
        self.assertEqual(len(st["trail"]), 2)

    def test_block_orders_by_stage(self):
        st = {}
        T.add(st, "writing", "idea", "X", "scored highest")
        T.add(st, "pick", "post", "url", "shared most per thousand views")
        b = T.block(T.rows(st))
        self.assertLess(b.index("PICK:"), b.index("WRITING:"))
        self.assertIn("because scored highest", b)

    def test_note_writes_run_json_and_never_raises(self):
        with tempfile.TemporaryDirectory() as t:
            r = T.note(t, "production", "lane", "ai", "the format needs pictures no camera can take")
            self.assertEqual(r["choice"], "ai")
            self.assertEqual(len(T.rows(t)), 1)
            self.assertIsNone(T.note("/dev/null/nope", "x", "y", "z", "w"))

    def test_for_brief_gathers_teardown_writing_production_edit(self):
        with tempfile.TemporaryDirectory() as t:
            R = Path(t)
            (R / "components").mkdir()
            runs = R / "runs"
            T.note(runs / "video-teardown" / "_work" / "s1", "teardown", "format", "f", "why f")
            T.note(runs / "video-writing" / "acme" / "s1", "writing", "idea", "i", "why i")
            p = runs / "video-production" / "acme" / "p1"
            T.note(p, "production", "lane", "ai", "why ai")
            st = json.loads((p / "run.json").read_text())
            st["brief_from"] = "runs/video-writing/acme/s1/deliverable/5-brief.md"
            (p / "run.json").write_text(json.dumps(st))
            k = runs / "video-edit" / "acme" / "e1" / "kit"
            k.mkdir(parents=True)
            (k / "edit-kit.json").write_text(json.dumps({"from_run": "runs/video-production/acme/p1"}))
            T.note(k.parent, "edit", "pace", "tight", "why tight")
            got = [r["stage"] for r in T.for_brief("acme/s1", repo=R)]
            self.assertEqual(sorted(got), sorted(["teardown", "writing", "production", "edit"]))


if __name__ == "__main__":
    unittest.main()
