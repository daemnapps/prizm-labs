"""run.py --piece <label> --fork-only: the new piece's folder is made and nothing is written, so a continuation's
creative matrix row can be pinned before its writing runs (micro-drama series layer)."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MACHINE = Path(__file__).resolve().parents[1] / "machine"
sys.path.insert(0, str(MACHINE))


def load():
    spec = importlib.util.spec_from_file_location("vw_run_fork_only", str(MACHINE / "run.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ForkOnly(unittest.TestCase):
    def test_forks_and_writes_nothing(self):
        run = load()
        with tempfile.TemporaryDirectory() as t:
            src = Path(t) / "swipe-run"
            src.mkdir()
            (src / "run.json").write_text(json.dumps({"stages": {"stage2": {"status": "done"}}}))
            with patch.dict(sys.modules, {"writing_v2": None}):
                code = run.main([str(src), "--piece", "part-2", "--fork-only"])
            self.assertEqual(code, 0)
            piece = Path(t) / "part-2"
            self.assertTrue((piece / "run.json").is_file())
            self.assertEqual(json.loads((piece / "run.json").read_text())["forked_from"], "swipe-run")
            self.assertFalse((piece / "matrix-cell.json").exists())

    def test_fork_only_needs_a_piece(self):
        run = load()
        with tempfile.TemporaryDirectory() as t:
            src = Path(t) / "swipe-run"
            src.mkdir()
            (src / "run.json").write_text("{}")
            with self.assertRaises(SystemExit):
                run.main([str(src), "--fork-only"])


if __name__ == "__main__":
    unittest.main()
