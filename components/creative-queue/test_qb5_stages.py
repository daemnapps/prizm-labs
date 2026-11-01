"""QB-5 (production contract): ONE stage list. The queue reads the naming standard's stages
(components/naming/stages.json), its own copy is gone, and QB-1 (queue core)'s tests stay green.
Stdlib only, no network. Run from the repo root:
    python3 components/creative-queue/test_qb5_stages.py
"""
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
import qcore  # noqa: E402

NAMING = HERE.parent / "naming"


def naming_stages():
    spec = importlib.util.spec_from_file_location("naming_stages_qb5", str(NAMING / "stages.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class OneStageList(unittest.TestCase):
    def test_order_is_namings_stage_ids(self):
        ids = [s["id"] for s in json.loads((NAMING / "stages.json").read_text())["stages"]]
        self.assertEqual(len(ids), 8)
        self.assertEqual(qcore.ORDER, ids)
        self.assertEqual(qcore._order(), ids)

    def test_order_is_naming_stages_py_order(self):
        self.assertEqual(qcore.ORDER, naming_stages().ORDER)

    def test_own_copy_is_gone(self):
        self.assertFalse((HERE / "stages.json").exists())

    def test_requested_stage_still_checked_against_the_list(self):
        with self.assertRaises(ValueError):
            qcore.append_decision("/nonexistent-root-never-written", "steph",
                                  {"id": "x", "op": "set", "field": "requested_stage", "value": "nowhere"})


class QB1StaysGreen(unittest.TestCase):
    def run_file(self, name):
        p = subprocess.run([sys.executable, str(HERE / name)], cwd=str(HERE.parent.parent), capture_output=True,
                           text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 0, (p.stdout + p.stderr)[-2000:])

    def test_qb1_reduce(self):
        self.run_file("test_qb1_reduce.py")

    def test_qb1_cli(self):
        self.run_file("test_qb1_cli.py")


if __name__ == "__main__":
    unittest.main()
