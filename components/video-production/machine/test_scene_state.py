"""A person's time-bound marks resolve to the scene being printed (the beard shaved in S19 is gone at S24).
Run: python3 -m unittest test_scene_state"""
import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
sys.argv = sys.argv[:1]
_sp = importlib.util.spec_from_file_location("vm_run_scene_state", HERE / "run.py")
R = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(R)

WORDS = ("Load-bearing: acne and dark spots across his cheeks, at full strength in every shot until S20. They fade "
         "across S20-S22 and are clear from S23. The beard is on through S18 and shaved in S19.")


class SceneState(unittest.TestCase):
    def test_after_the_shave(self):
        out = R.scene_state(WORDS, 24)
        held, gone = out.split("These no longer")
        self.assertIn("shaved in S19", held)
        self.assertIn("clear from S23", held)
        self.assertIn("on through S18", gone)

    def test_before_the_shave(self):
        held = R.scene_state(WORDS, 3).split("These no longer")[0]
        self.assertIn("on through S18", held)
        self.assertNotIn("shaved", held)

    def test_no_timed_words(self):
        self.assertEqual(R.scene_state("short black hair", 5), "")


if __name__ == "__main__":
    unittest.main()
