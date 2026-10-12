"""The merge, on fixtures — no network, no spend.  python3 -m unittest tests/test_lines.py"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lines as L  # noqa: E402


def w(t, a, b, sp, typ="word"):
    return {"text": t, "start": a, "end": b, "speaker": sp, "type": typ}


# The Korean-mother case: Scribe (English) hears the daughter, and where the mother
# speaks Korean it has one stray English word and a [laughs].
SCRIBE = [w("So", 0.3, 0.5, "s0"), w("my", 0.5, 0.7, "s0"), w("mom", 0.7, 1.0, "s0"), w("uses", 1.0, 1.4, "s0"),
          w("[laughs]", 5.0, 5.2, "s1", "audio_event"), w("Lotion", 5.3, 5.8, "s1"),
          w("She", 9.0, 9.2, "s0"), w("loves", 9.2, 9.6, "s0"), w("it", 9.6, 9.8, "s0")]
GEM = [{"speaker": "Speaker 1", "start": 0.0, "end": 1.5, "text": "So my mom uses", "language": "en"},
       {"speaker": "Speaker 2", "start": 4.5, "end": 8.5, "text": "lotion만큼 괜찮아. 진짜 좋아.", "language": "ko"},
       {"speaker": "Speaker 1", "start": 8.8, "end": 10.0, "text": "She loves it", "language": "en"}]


class Merge(unittest.TestCase):
    def setUp(self):
        self.out = L.merge(GEM, SCRIBE, "eng", 11.0)

    def test_every_word_kept_in_its_language(self):
        self.assertEqual(self.out[1]["text"], "lotion만큼 괜찮아. 진짜 좋아.")
        self.assertEqual(self.out[1]["language"], "ko")

    def test_scribe_times_used_where_it_heard(self):
        self.assertAlmostEqual(self.out[0]["start"], 0.3)
        self.assertAlmostEqual(self.out[2]["start"], 9.0)

    def test_mother_is_not_the_daughter(self):
        self.assertNotEqual(self.out[1]["speaker"], self.out[0]["speaker"])
        self.assertIn("speaker-from-words-model", self.out[1]["flags"])

    def test_language_split(self):
        self.assertEqual(set(L.languages(self.out)), {"en", "ko"})

    def test_three_letter_codes(self):
        self.assertEqual(L.two("spa"), "es")
        self.assertEqual(L.two("kor"), "ko")

    def test_chinese_matched_by_character(self):
        self.assertEqual(L.norm("你看看"), ["你", "看", "看"])


if __name__ == "__main__":
    unittest.main()
