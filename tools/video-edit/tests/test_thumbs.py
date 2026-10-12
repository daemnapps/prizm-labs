"""Cover words go where the picture is free: never on lips, a face or a hand (the owner, 4 Oct 2026)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
try:
    import PIL  # noqa: F401  the edit-map line needs Pillow (tools/video-edit/CLAUDE.md)
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False
if HAVE_PIL:
    import thumbs as T  # noqa: E402


@unittest.skipUnless(HAVE_PIL, "Pillow is not installed here — the edit-map line needs it; see tools/video-edit/CLAUDE.md")
class Placement(unittest.TestCase):
    def test_clears_the_face_and_lips(self):
        sc = {"faces": [{"x": .3, "y": .40, "w": .5, "h": .31}], "lips": [{"x": .5, "y": .58, "w": .15, "h": .06}],
              "hands": [], "salient": []}
        y, covers = T.place(sc, 700, 200, prefer=.64)
        self.assertGreaterEqual(y, .71)
        self.assertEqual(covers, {})

    def test_clears_a_hand_below_the_face(self):
        sc = {"faces": [{"x": .2, "y": .18, "w": .4, "h": .23}], "lips": [],
              "hands": [{"x": .6, "y": .55, "w": .35, "h": .18}], "salient": []}
        y, covers = T.place(sc, 860, 200, prefer=.64)
        self.assertGreaterEqual(y, .73)
        self.assertNotIn("hands", covers)

    def test_stays_on_the_looks_spot_when_free(self):
        y, _ = T.place({"faces": [], "lips": [], "hands": [], "salient": []}, 700, 200, prefer=.64)
        self.assertAlmostEqual(y, .64, places=2)


if __name__ == "__main__":
    unittest.main()
