#!/usr/bin/env python3
"""The emotional map is wired end to end (the owner, 2026-10-13: "let's install
a full map proper fundamentally in the system similar to the marketing
doctrine"). No model, no network.

    python3 test_emotional_map.py
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import chain as C               # noqa: E402
import elements_check as EC     # noqa: E402
import run as R                 # noqa: E402

SLICE = "components/marketing-doctrine/slices/emotion.md"


class Wired(unittest.TestCase):
    def test_slice_exists_and_is_bound_to_1c_3_and_5(self):
        self.assertTrue((C.workspace() / SLICE).is_file())
        sv = json.loads((HERE / "extra-stages.json").read_text())["stage_vars"]
        for k in ("stage1c", "stage3", "stage5"):
            self.assertEqual(sv[k].get("emotion"), SLICE, k)

    def test_the_current_prompts_ask_for_it(self):
        for k in ("stage1c", "stage3"):
            path, _, _ = C.newest(k)
            self.assertIn("{emotion}", path.read_text(), path.name)
        self.assertIn("EMOTIONAL MAP", C.newest("stage1c")[0].read_text())
        self.assertIn("THE FEELING HOLDS", C.newest("stage3")[0].read_text())

    def test_doctrine_json_keeps_the_map(self):
        self.assertIn("emotional_map", R.DOCTRINE_KEYS)


class Visual(unittest.TestCase):
    VSLICE = "components/marketing-doctrine/slices/visual.md"

    def test_visual_slice_bound_to_1c_and_5(self):
        sv = json.loads((HERE / "extra-stages.json").read_text())["stage_vars"]
        for k in ("stage1c", "stage5"):
            self.assertEqual(sv[k].get("visual"), self.VSLICE, k)

    def test_1c_reads_the_swipes_look_and_files_it(self):
        txt = C.newest("stage1c")[0].read_text()
        self.assertIn("{visual}", txt)
        self.assertIn("THE VISUAL READ", txt)
        self.assertIn("visual", R.DOCTRINE_KEYS)

    def test_visual_values_are_labelled_and_unknowns_recorded(self):
        out = EC.label({"visual": {"shot": ["close", "dutch"], "capture": "phone"}})
        self.assertEqual([(e["value"], e["known"]) for e in out["visual/shot"]],
                         [("close", True), ("dutch", False)])
        self.assertTrue(out["visual/capture"][0]["known"])


class Labelled(unittest.TestCase):
    def test_feelings_and_arc_are_looked_up_and_unknowns_recorded(self):
        doc = {"emotional_map": {"arc": "dip-and-rise", "beats": [
            {"feeling": "recognition"}, {"feeling": "frustration"},
            {"feeling": "recognition"}, {"feeling": "glee"}]}}
        out = EC.label(doc)
        self.assertTrue(out["emotion/arc"]["known"])
        got = {e["value"]: e["known"] for e in out["emotion/feeling"]}
        self.assertEqual(got, {"recognition": True, "frustration": True, "glee": False})

    def test_a_run_read_before_the_map_is_unchanged(self):
        out = EC.label({"framework": "x"})
        self.assertNotIn("emotion/arc", out)
        self.assertNotIn("emotion/feeling", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
