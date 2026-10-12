"""Music, effects and the mix — the parts that need no network.  python3 -m unittest tests/test_sound.py"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import effects as EF  # noqa: E402
import mix as MX  # noqa: E402
import music as MU  # noqa: E402


class Filing(unittest.TestCase):
    def test_machine_sounds_filed_under_ucs(self):
        self.assertEqual(EF.ucs_of("Whoosh, swoosh, swish"), "SWOOSHES")
        self.assertEqual(EF.ucs_of("Typewriter"), "OBJECTS")          # no rule: filed OBJECTS for the ear to name
        self.assertEqual(EF.ucs_of("Beep, bleep"), "BEEPS")
        self.assertEqual(EF.ucs_of("Spray"), "AIR")

    def test_every_rule_points_at_a_real_category(self):
        cats = set(EF.LISTS["ucs_category"])
        self.assertEqual(len(cats), len(EF.LISTS["ucs_category"]))   # no duplicates
        self.assertIn("SWOOSHES", cats)
        for _, cat in EF.RULES:
            self.assertIn(cat, cats)


class Labels(unittest.TestCase):
    def test_off_list_music_label_is_kept_and_named(self):
        self.assertEqual(MU.check({"energy": "medium", "shape": "wobbly"}), ["shape: wobbly"])


class Render(unittest.TestCase):
    def test_no_music_says_so(self):
        self.assertIn("No music", MU.render({"present": False, "why": "silent"}))

    def test_effects_table(self):
        md = EF.render({"effects": [{"at": 0.83, "name": "whoosh", "sure": "high", "ucs_category": "SWOOSHES",
                                     "job": "transition", "added": True}], "room": "silence",
                        "moments_found": 3, "moments_confirmed": 1})
        self.assertIn("| 0.83s | whoosh | high | SWOOSHES | transition | yes |", md)

    def test_mix_ducking_wording(self):
        md = MX.render({"loudness": {"lufs": -14.1}, "voice_over_music_db": 19.1, "music_ducks_by_db": -1.7,
                        "form": {"spoken_percent": 70, "music_percent": 90}, "silences": []})
        self.assertIn("music does not drop under the voice", md)
        self.assertIn("none — sound all the way through", md)


if __name__ == "__main__":
    unittest.main()
