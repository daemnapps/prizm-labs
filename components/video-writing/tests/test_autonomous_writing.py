"""run.py --autonomous: this run's holds go to the decision layer (video-teardown decide.py) and the run continues;
the house settings file is never changed. A hook matrix still failing after its one remake is passed and filed."""
import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

MACHINE = Path(__file__).resolve().parents[1] / "machine"
TD = Path(__file__).resolve().parents[2] / "video-teardown" / "machine"
sys.path.insert(0, str(MACHINE))


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, str(MACHINE / file))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Autonomous(unittest.TestCase):
    def test_switch_turns_the_layer_on_for_this_run_only(self):
        run = load("vw_run_auto", "run.py")
        house = Path(run.HERE.parents[2] / "runs" / "settings" / "settings.json")
        before = house.read_bytes() if house.is_file() else None
        with tempfile.TemporaryDirectory() as t, patch.dict(os.environ, {}, clear=False):
            mine = run.autonomous(Path(t))
            cfg = json.loads(mine.read_text())
            self.assertEqual(os.environ["VT_CHAIN"], "v2")
            self.assertEqual(os.environ["OUTLIER_SETTINGS"], str(mine))
            self.assertFalse(cfg["automation"]["paused"])
            self.assertEqual(cfg["automation"]["writing"], "auto")
            sys.path.insert(0, str(TD))
            spec = importlib.util.spec_from_file_location("vt_decide_fixture", str(TD / "decide.py"))
            decide = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(decide)                  # reads OUTLIER_SETTINGS at import, as the chain does
            self.assertTrue(decide.on("hook") and decide.on("audit") and decide.on("swipe"))
        self.assertEqual(house.read_bytes() if house.is_file() else None, before)

    def test_without_the_switch_nothing_changes(self):
        with patch.dict(os.environ, {"VT_CHAIN": ""}):
            spec = importlib.util.spec_from_file_location("vt_decide_off", str(TD / "decide.py"))
            decide = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(decide)
            self.assertFalse(decide.on("hook"))


class DecidedHooks(unittest.TestCase):
    def setUp(self):
        self.wv2 = load("vw_wv2_auto", "writing_v2.py")
        self.calls = []
        fake = types.SimpleNamespace(on=lambda gate: True,
                                     auto=lambda d, st, gate, items: self.calls.append((gate, items)) or [])
        self.p = patch.dict(sys.modules, {"decide": fake})
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_passed_after_the_one_remake(self):
        with tempfile.TemporaryDirectory() as t:
            matrix = {"openings": []}
            ok = self.wv2.decided_hooks(Path(t), {"_v2_hook_remade": True}, matrix, ["V3: missing scroll"])
            self.assertTrue(ok)
            self.assertEqual(self.calls[0][0], "hook")
            self.assertEqual(matrix["decided"][0]["finding"], "V3: missing scroll")
            self.assertTrue((Path(t) / "HOOK-FORMAT-decided.md").is_file())

    def test_not_before_the_remake_and_not_without_a_matrix(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(self.wv2.decided_hooks(Path(t), {}, {"openings": []}, ["x"]))
            self.assertFalse(self.wv2.decided_hooks(Path(t), {"_v2_hook_remade": True}, None, ["x"]))
            self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
