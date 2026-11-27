"""The owner's locked script door and the new-piece fork (2026-10-23). No model is called."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
M = HERE.parent / "machine"
sys.path.insert(0, str(M))
sys.path.insert(0, str(HERE.parents[1] / "video-teardown" / "machine"))

import writing_v2 as W  # noqa: E402
import importlib.util  # noqa: E402

_sp = importlib.util.spec_from_file_location("vw_launcher", M / "run.py")   # video-writing's launcher (its fork),
WR = importlib.util.module_from_spec(_sp)                                     # not the teardown's run.py on the path
_sp.loader.exec_module(WR)

SCRIPT = """# A piece

## THE CONCEPT

Something.

## LINES

| scene | speaker | line |
|---|---|---|
| S1 | THE PASTOR | Church! Brother Marcus… stand UP! |
| S4 | BROTHER MARCUS | …It grows in slow. |

## THE CAST

- people
"""


class OwnerScript(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "run.json").write_text(json.dumps({"brand": "b", "stages": {}}))
        src = self.d / "in.md"
        src.write_text(SCRIPT)
        self.st = W.lock_owner_script(self.d, src)

    def test_lines_read_from_the_table(self):
        lines = W.owner_lines(SCRIPT)
        self.assertEqual([l["scene"] for l in lines], ["S1", "S4"])
        self.assertEqual(self.st["owner_script"]["lines"], 2)

    def test_every_pass_is_handed_the_words(self):
        block = W.owner_block(self.d, self.st)
        self.assertIn("VERBATIM", block)
        self.assertIn("stand UP!", block)
        self.assertEqual(W.owner_block(self.d, {"stages": {}}), "")     # no locked script, nothing added

    def test_a_brief_carrying_every_line_passes(self):
        (self.d / "stages").mkdir()
        (self.d / "stages" / "5-brief.md").write_text('"voice": "Church! Brother Marcus... stand up!" and "It grows in slow."')
        self.st["stages"]["stage5"] = {"out": "stages/5-brief.md"}
        self.assertEqual(W.owner_words_check(self.d, self.st), [])

    def test_a_changed_line_is_named(self):
        (self.d / "stages").mkdir()
        (self.d / "stages" / "5-brief.md").write_text("Church! Brother Marcus, get up! It grows in slow.")
        self.st["stages"]["stage5"] = {"out": "stages/5-brief.md"}
        self.assertEqual([m["scene"] for m in W.owner_words_check(self.d, self.st)], ["S1"])

    def test_a_script_with_no_lines_is_refused(self):
        src = self.d / "bad.md"
        src.write_text("# nothing listed")
        with self.assertRaises(SystemExit):
            W.lock_owner_script(self.d, src)


class Fork(unittest.TestCase):
    def test_new_piece_keeps_the_teardown_and_starts_the_writing_empty(self):
        root = Path(tempfile.mkdtemp())
        src = root / "swipe"
        (src / "stages").mkdir(parents=True)
        (src / "framemap").mkdir()
        (src / "stages" / "1-teardown.md").write_text("record")
        (src / "stages" / "3-injection.md").write_text("old writing")
        (src / "run.json").write_text(json.dumps({"label": "swipe", "brand": "b", "role": "reference", "stages": {
            "stage1": {"status": "done", "out": "stages/1-teardown.md"},
            "stage3": {"status": "done", "out": "stages/3-injection.md"}}}))
        dst = WR.fork(src, "new-piece")
        st = json.loads((dst / "run.json").read_text())
        self.assertEqual(st["label"], "new-piece")
        self.assertEqual(list(st["stages"]), ["stage1"])
        self.assertTrue((dst / "stages" / "1-teardown.md").is_file())
        self.assertFalse((dst / "stages" / "3-injection.md").exists())
        self.assertTrue((dst / "framemap").is_symlink())
        self.assertNotIn("role", st)
        self.assertEqual(WR.fork(src, "new-piece"), dst)                 # a second call resumes, never overwrites


if __name__ == "__main__":
    unittest.main()
