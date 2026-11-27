"""listen.py: the music checked by ear twice; the people's non-word sounds labelled second by second."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import listen as L  # noqa: E402


class Listen(unittest.TestCase):
    def test_families(self):
        self.assertEqual(L.family(["R&B / Hip-Hop", "Trapsoul"]), "hip-hop")
        self.assertEqual(L.family("Synth-Pop"), "pop")

    def test_two_agreeing_reads_check_the_music_and_dispute_a_wrong_name(self):
        ask = lambda q, f: {"genre": "Hip-Hop", "subgenre": "Trap", "bpm": 80, "felt_tempo": "half-time"}
        got = L.music_check("m.mp3", "Pop Synth-Pop", ask)
        self.assertTrue(got["agreed"])
        self.assertTrue(got["name_disputed"])
        reads = iter([{"genre": "Hip-Hop"}, {"genre": "Pop"}])
        got = L.music_check("m.mp3", None, lambda q, f: next(reads))
        self.assertFalse(got["agreed"])
        self.assertNotIn("genre", got)

    def test_seconds_in_a_row_with_one_sound_are_one(self):
        d = Path(tempfile.mkdtemp())
        a = d / "v.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "6", str(a)],
                       check=True)
        answers = iter([{"sound": "ew", "feeling": "disgust"}, {"sound": "word"}, {"sound": "mmm", "feeling": "delighted"},
                        {"sound": "mmm", "feeling": "delighted"}])
        rows = L.label_seconds(a, [(1.2, 5.0)], lambda q, f: next(answers))
        self.assertEqual([(r["sound"], r["at"], r["until"]) for r in rows], [("ew", 1.0, 2), ("mmm", 3.0, 5)])


if __name__ == "__main__":
    unittest.main()
