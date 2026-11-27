"""clip_join.py: short shots are one take, repeats are one clip, and what stands alone is left alone."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import clip_join as J  # noqa: E402


def clip(n, secs, recipe=None, refs=("a",), **kw):
    return dict({"id": "S1-shot-%d" % n, "scene": "S1", "brief_scene": "S1", "tool": "gen.shot", "recipe": recipe or "shot %d" % n, "copies": ["K%d" % n],
                 "swipe": [], "refs": ["refs/S1-shot-%d/a.jpg" % n], "named_refs": list(refs), "lips": None, "route": "shot", "secs": secs,
                 "return": "returned/x_asset-10-shot-%d.mp4" % n, "same_people_as": None if n == 1 else "S1-shot-1", "continues": None}, **kw)


class Join(unittest.TestCase):
    def test_fourteen_short_shots_are_three_clips(self):
        was = [clip(i, 1.5) for i in range(1, 15)]
        got = J.join(was)
        self.assertEqual(len(got), 3)
        self.assertEqual([n for c in got for n in c["shot_nos"]], list(range(1, 15)))      # every shot, once, in order
        self.assertAlmostEqual(sum(c["secs"] for c in got), 21)
        self.assertLess(J.bought(got), J.bought(was) / 2)
        self.assertEqual(len({c["id"] for c in got} | {c["return"] for c in got}), 6)      # no two share a name
        for i in range(1, 15):
            self.assertTrue(any("shot %d" % i in c["recipe"] for c in got))
        self.assertTrue(all(c["same_people_as"] in (None, got[0]["id"]) for c in got))

    def test_the_same_words_are_one_clip(self):
        got = J.join([clip(1, 5, "pours salt"), clip(2, 5, "pours salt")])
        self.assertEqual((len(got), got[0]["recipe"], got[0]["secs"], got[0]["return"]), (1, "pours salt", 10, "returned/x_asset-10.mp4"))

    def test_what_stands_alone_is_left_alone(self):
        was = [clip(1, 8), clip(2, 8)]
        self.assertEqual([c["id"] for c in J.join(was)], ["S1-shot-1", "S1-shot-2"])
        for other in (clip(2, 1.5, refs=("b",)), clip(2, 1.5, song_at=[0, 2]), clip(2, 1.5, tool="edit"), clip(2, 1.5, route="screen"),
                      clip(2, 1.5, lips="on")):
            self.assertEqual(len(J.join([clip(1, 1.5), other])), 2)

    def test_a_short_tail_goes_with_the_clip_before(self):
        got = J.join([clip(i, 3) for i in range(1, 6)])
        self.assertTrue(all(c["secs"] >= 4 for c in got))
        self.assertTrue(all(c["secs"] <= 15 for c in got))

    def test_a_long_talking_shot_is_parts_between_sentences(self):
        words = " ".join("Sentence number %d has eight words in it." % i for i in range(1, 22))
        got = J.split(clip(1, 61.6), words)
        self.assertEqual(" ".join(c["says"] for c in got), words)                          # every word, once, in order
        self.assertTrue(all(c["secs"] <= 15.5 for c in got))
        self.assertAlmostEqual(sum(c["secs"] for c in got), 61.6, places=1)
        self.assertEqual([c["continues"] for c in got], [None] + [c["id"] for c in got[:-1]])
        self.assertEqual(len({c["return"] for c in got}), len(got))
        self.assertEqual(J.split(clip(1, 12), words), [clip(1, 12)])
        self.assertTrue(all(c["secs"] <= 15.5 for c in J.split(clip(1, 40), "")))          # nobody speaks


if __name__ == "__main__":
    unittest.main()
