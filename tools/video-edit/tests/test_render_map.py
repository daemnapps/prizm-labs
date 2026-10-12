"""render_map: what is on screen at every moment — B-roll wins its window, the picture fills the rest, no gaps."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "machine"))
try:
    import PIL  # noqa: F401  the edit-map line needs Pillow (tools/video-edit/CLAUDE.md)
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False
if HAVE_PIL:
    import render_map as RM  # noqa: E402


@unittest.skipUnless(HAVE_PIL, "Pillow is not installed here — the edit-map line needs it; see tools/video-edit/CLAUDE.md")
class Flatten(unittest.TestCase):
    def test_broll_wins_its_window_and_nothing_is_left_uncovered(self):
        m = {"picture": [{"a": 0, "b": 5, "kind": "clip", "clip": "A", "in": 1.0},
                         {"a": 5, "b": 9, "kind": "clip", "clip": "B", "in": 0.0, "speed": 0.8}],
             "broll": [{"a": 3, "b": 6, "file": "broll/x.mp4", "name": "x"}]}
        segs = RM.flatten(m)
        self.assertEqual([(s["a"], s["b"], s.get("clip") or s.get("file")) for s in segs],
                         [(0, 3, "A"), (3, 6, "broll/x.mp4"), (6, 9, "B")])
        self.assertAlmostEqual(segs[2]["in"], 0.8)          # B resumes where it would be, at its own speed

    def test_overlapping_pieces_never_play_twice(self):
        """4 Oct 2026: a line's lead-in pad overlapped the shot before; both were rendered whole and the picture slid
        ~0.4 s behind the voice by the pitch. Now each piece starts where the last ends, its source moved on with it."""
        m = {"total": 6.0, "picture": [{"a": 0, "b": 3.0, "kind": "clip", "clip": "A", "in": 0.5},
                                       {"a": 2.94, "b": 6.0, "kind": "clip", "clip": "B", "in": 0.48}]}
        segs = RM.flatten(m)
        self.assertEqual([(s["a"], s["b"]) for s in segs], [(0, 3.0), (3.0, 6.0)])
        self.assertAlmostEqual(segs[1]["in"], 0.54)           # B's frame at 3.0 s is the one the map put there
        frames = sum(round(s["b"] * RM.FPS) - round(s["a"] * RM.FPS) for s in segs)
        self.assertEqual(frames, 6 * RM.FPS)

    def test_no_flash_a_sliver_joins_the_broll_beside_it(self):
        m = {"total": 9.0, "picture": [{"a": 0, "b": 9, "kind": "clip", "clip": "A", "in": 0.0}],
             "broll": [{"a": 3, "b": 4.8, "file": "broll/x.mp4"}, {"a": 4.9, "b": 7, "file": "broll/y.mp4"}]}
        segs = RM.flatten(m)
        self.assertTrue(all(s["b"] - s["a"] >= RM.MIN_SHOT for s in segs))
        self.assertEqual([(s["a"], s["b"]) for s in segs], [(0, 3), (3, 4.9), (4.9, 7), (7, 9)])
        self.assertAlmostEqual(sum(s["b"] - s["a"] for s in segs), 9.0)

    def test_captions_split_a_line_into_short_pieces(self):
        caps = RM.caption_chunks({"voice": [{"a": 0, "b": 4, "text": "one two three four five six seven", "cap_y": 0.8}]})
        self.assertEqual([c["text"] for c in caps], ["one two three four", "five six seven"])

    def test_captions_change_on_the_spoken_words(self):
        line = {"scene": "S1", "a": 10.0, "b": 14.0, "text": "I tried it. Then I tried the other one twice", "cap_y": 0.8}
        heard = [{"start": 10.0 + x} for x in (0.1, 0.3, 0.5, 1.8, 2.0, 2.2, 2.4, 2.6, 2.9, 3.2)]
        caps = RM.caption_chunks({"voice": [line]}, timed=RM.line_words({"voice": [line]}, heard))
        self.assertEqual([c["text"] for c in caps], ["I tried it.", "Then I tried the", "other one twice"])
        self.assertEqual([round(c["a"], 2) for c in caps], [10.0, 11.8, 12.6])   # up when she says its first word
        self.assertEqual(caps[-1]["b"], 14.0)

    def test_a_lip_synced_sliver_stays_on_its_own_take(self):
        """4 Oct: a 0.47 s lip-synced shot was handed to the shot before (another angle) — her voice on the wrong
        mouth. A sliver joins its own clip's next piece first."""
        m = {"total": 6.0, "picture": [{"a": 0, "b": 2.0, "kind": "clip", "clip": "A", "in": 0.0},
                                       {"a": 2.0, "b": 2.4, "kind": "clip", "clip": "B", "in": 1.0, "scale": 1.07, "lip": True},
                                       {"a": 2.4, "b": 6.0, "kind": "clip", "clip": "B", "in": 1.4, "lip": True}]}
        segs = RM.flatten(m)
        self.assertEqual([(s["a"], s["b"], s["clip"]) for s in segs], [(0, 2.0, "A"), (2.0, 6.0, "B")])
        self.assertAlmostEqual(segs[1]["in"], 1.0)


if __name__ == "__main__":
    unittest.main()
