"""to_studio.sound_layers: music cue stretches and every sound effect on their own rows."""
import tempfile
import unittest
from pathlib import Path

import to_studio as TS


class SoundLayers(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.fx = Path(self.d.name) / "click.mp3"
        self.fx.write_bytes(b"x")

    def tearDown(self):
        self.d.cleanup()

    def test_effects_each_get_their_own_row_on_the_ads_clock(self):
        plan = {"effects": [{"at": 2.26, "sound": "typewriter", "what": "pops in", "file": str(self.fx)},
                            {"at": 20.0, "sound": "buzzer", "what": "the X", "file": str(self.fx), "volume_db": -4}]}
        marks, sfx = TS.sound_layers(plan, m0=1.0, md=40.0, end=48.0, who="Suno")
        self.assertEqual([s["at"] for s in sfx], [3.26, 21.0])
        self.assertEqual(sfx[0]["label"], "Effect · typewriter · pops in")
        self.assertEqual(sfx[1]["volume_db"], -4.0)

    def test_an_effect_with_no_file_or_past_the_end_is_left_out(self):
        plan = {"effects": [{"at": 1.0, "sound": "x", "file": "/no/such.mp3"},
                            {"at": 60.0, "sound": "late", "file": str(self.fx)}]}
        self.assertEqual(TS.sound_layers(plan, 0.0, 40.0, 48.0, "Suno")[1], [])

    def test_the_cue_sheet_names_the_song_rows_stretches(self):
        plan = {"lane": "phonk", "cue_sheet": [{"at": 0.0, "until": 24.0, "what": "the build"},
                                               {"at": 24.0, "until": 49.0, "what": "the hit"}]}
        marks, _ = TS.sound_layers(plan, 0.0, 48.0, 48.0, "Suno")
        self.assertEqual([m["label"] for m in marks], ["Music · Suno · phonk · the build", "Music · Suno · phonk · the hit"])
        self.assertEqual(marks[1]["duration"], 24.0)                 # clipped at the bed's own length

    def test_no_cue_sheet_keeps_the_one_bed_mark(self):
        marks, sfx = TS.sound_layers({"lane": "bed"}, 0.0, 30.0, 48.0, "ElevenLabs Music")
        self.assertEqual(len(marks), 1)
        self.assertTrue(marks[0]["label"].startswith("Music bed"))
        self.assertEqual(sfx, [])


if __name__ == "__main__":
    unittest.main()
