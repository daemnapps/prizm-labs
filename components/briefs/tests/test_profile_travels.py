"""The full profile a piece was written from travels with the hand-off, and nothing is made up when it has none."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runsheet  # noqa: E402


class Travels(unittest.TestCase):
    def test_copied_from_the_run_beside_the_brief(self):
        with tempfile.TemporaryDirectory() as t:
            repo, root = Path(t), Path(t) / "handoff"
            root.mkdir()
            run = repo / "runs" / "x"
            run.mkdir(parents=True)
            self.assertFalse(runsheet.profile_into(root, {"run": "runs/x"}, repo))
            (run / "profile.json").write_text("{}")
            (run / "profile.md").write_text("# Who this is for")
            self.assertTrue(runsheet.profile_into(root, {"run": "runs/x"}, repo))
            self.assertTrue((root / "PROFILE.md").is_file() and (root / "profile.json").is_file())


if __name__ == "__main__":
    unittest.main()
