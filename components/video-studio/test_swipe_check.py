"""swipe_check.no_repeat: a clip section is never used twice in one cut."""
import unittest

import swipe_check as SC


class NoRepeat(unittest.TestCase):
    def test_overlap_of_one_file_repeats(self):
        r = SC.repeats([("S2.1", "/a/clip.mp4", 0.3, 1.6), ("S5.2", "/a/clip.mp4", 1.0, 2.0)])
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0][:2], ("S2.1", "S5.2"))

    def test_one_footage_clip_plays_once_per_ad(self):
        # rule 2026-11-21: a footage clip file plays once per ad, even at different moments
        r = SC.repeats([("S3.K07", "/real/k.mp4", 120.4, 121.0), ("S3.K08", "/real/k.mp4", 123.7, 124.0)])
        self.assertEqual(r, [("S3.K07", "S3.K08", "the same clip")])

    def test_a_made_clip_used_twice_repeats_even_without_overlap(self):
        segs = [("S2.1", "/src/generated/hug.mp4", 0.3, 1.6), ("S5.K18", "/src/generated/hug.mp4", 2.4, 4.9)]
        self.assertEqual(SC.repeats(segs), [("S2.1", "S5.K18", "the same clip")])
        r = SC.repeats(segs, made=["/src/generated"])
        self.assertEqual(r, [("S2.1", "S5.K18", "the same made clip")])

    def test_touching_ends_of_a_made_clip_in_one_scene_are_one_take(self):
        self.assertEqual(SC.repeats([("S1.1", "/g/f.mp4", 0.0, 1.0), ("S1.2", "/g/f.mp4", 1.0, 2.0)], made=["/g"]), [])

    def test_one_take_cut_into_one_scenes_shots_is_not_a_repeat(self):
        # a continuous take (take.py) covering S1.1-S1.3, each shot playing its own seconds of the one made clip
        segs = [("S1.1", "/src/generated/hook.mp4", 0.0, 2.67), ("S1.2", "/src/generated/hook.mp4", 2.67, 3.84),
                ("S1.3", "/src/generated/hook.mp4", 3.84, 6.84)]
        self.assertEqual(SC.repeats(segs, made=["/src/generated"]), [])

    def test_one_take_with_overlapping_seconds_still_repeats(self):
        segs = [("S12.1", "/src/generated/couple.mp4", 0.0, 1.67), ("S12.3", "/src/generated/couple.mp4", 1.4, 1.96)]
        self.assertEqual(len(SC.repeats(segs, made=["/src/generated"])), 1)

    def test_a_made_take_reused_in_another_scene_repeats(self):
        segs = [("S1.1", "/src/generated/hook.mp4", 0.0, 2.0), ("S9.4", "/src/generated/hook.mp4", 6.0, 7.0)]
        self.assertEqual(SC.repeats(segs, made=["/src/generated"]), [("S1.1", "S9.4", "the same made clip")])

    def test_different_files_never_repeat(self):
        self.assertEqual(SC.repeats([("A", "/f.mp4", 0, 2), ("B", "/g.mp4", 0, 2)], made=["/"]), [])


if __name__ == "__main__":
    unittest.main()
