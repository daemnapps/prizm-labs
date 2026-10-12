"""The swipe's structure is locked (the owner, 2026-09-24): the rewrite may not
move a place, drop a role or change the story unless he approves it by number."""
import importlib.util, json, os, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
_s = importlib.util.spec_from_file_location("td_run", HERE / "run.py")
R = importlib.util.module_from_spec(_s); _s.loader.exec_module(R)

BODY = """# Injection

**1. THE INJECTED SCRIPT**

| # | Timestamp | Speaker | Source line | Our line |
|---|---|---|---|---|
| T1 | 0:00 | Creator | I'm at the place. | I'm at our place. |
| T2 | 0:03 | Expert | Mm-hmm. | unchanged |

**2. DOMINANT TRAIT**

x

## ELEMENT LEDGER

| # | Element | Status | How |
|---|---|---|---|
| 1 | The hook | Kept | same words, our product |
| 2 | Three expert offices | Adapted | moved to a home setting |
| 3 | The street opener | Dropped | cut |

## STRUCTURE QUESTIONS FOR DAMON

| # | The swipe has | The position suggests | Why it might matter |
|---|---|---|---|
| 1 | two experts | one founder | trust |

## NEXT
"""


class StructureLock(unittest.TestCase):
    def setUp(self):
        os.environ.pop("DAEMN_STRUCTURE_APPROVALS", None)
        self.d = Path(tempfile.mkdtemp())
        self.st = {"stages": {"stage3": {"status": "done", "out": "3.md"}}}
        (self.d / "transcript.json").write_text(json.dumps([{"id": "T1"}, {"id": "T2"}]))
        R.save = lambda d, st: None

    def test_changes_are_found(self):
        self.assertEqual([c["n"] for c in R.structure_changes(BODY)], ["2", "3", "Q1"])

    def test_unapproved_change_holds(self):
        with self.assertRaises(RuntimeError):
            R.structure_gate(self.d, self.st, "stage3", BODY)
        self.assertEqual(self.st["stages"]["stage3"]["status"], "held")
        self.assertIn("Three expert offices", (self.d / "STRUCTURE-CHECK.md").read_text())

    def test_partial_approval_still_holds(self):
        os.environ["DAEMN_STRUCTURE_APPROVALS"] = "2,3"
        with self.assertRaises(RuntimeError):
            R.structure_gate(self.d, self.st, "stage3", BODY)

    def test_full_approval_passes(self):
        os.environ["DAEMN_STRUCTURE_APPROVALS"] = "2,3,Q1"
        R.structure_gate(self.d, self.st, "stage3", BODY)
        self.assertEqual(self.st["stages"]["stage3"]["status"], "done")

    def test_faithful_rewrite_passes(self):
        R.structure_gate(self.d, self.st, "stage3", BODY.split("| 2 |")[0])
        self.assertEqual(self.st["stages"]["stage3"]["status"], "done")

    def test_a_swipe_line_missing_from_the_script_holds(self):
        (self.d / "transcript.json").write_text(json.dumps([{"id": "T1"}, {"id": "T2"}, {"id": "T3"}]))
        with self.assertRaises(RuntimeError):
            R.structure_gate(self.d, self.st, "stage3", BODY.split("| 2 |")[0])
        self.assertIn("T3", (self.d / "STRUCTURE-CHECK.md").read_text())

    def tearDown(self):
        os.environ.pop("DAEMN_STRUCTURE_APPROVALS", None)


if __name__ == "__main__":
    unittest.main()
