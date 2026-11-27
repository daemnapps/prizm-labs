"""A styled print's look picture goes on a reference board even when it is the only reference (set_queue, 2026-11-20).

An empty set in the ad's style has no product, cast or identity picture: its one reference is the style swatch. The plan's
words call it "the reference board" and `picture_sets.py put` keeps only a casting sheet or a board as a kept print's
reference, so the plan must name the board, or `file_it` is refused on any reprint."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from image_production import set_queue as Q  # noqa: E402


def request(**extra):
    r = {"id": "set-room-style", "brand": "b", "state": "open", "what": "a room, empty", "scene": "a room, empty",
         "products": [], "cast": [], "style": "family-3d", "style_formula": "big-studio 3D animated feature",
         "element": {"kind": "set", "id": "room", "new": True}}
    r.update(extra)
    return r


class StyleBoard(unittest.TestCase):
    def plan(self, r):
        with mock.patch.object(Q, "read", lambda b, rid: r), mock.patch.object(Q, "worlds", lambda b, s: []):
            return Q.plan("b", r["id"])

    def test_lone_style_swatch_goes_on_a_board(self):
        out = self.plan(request(look_reference="components/video-production/styles/swatches/family-3d.jpg"))
        board = "runs/image-production/b/set-requests/set-room-style-reference.png"
        self.assertEqual(out["reference_board"]["board"], board)
        self.assertEqual(out["reference_board"]["from"], ["components/video-production/styles/swatches/family-3d.jpg"])
        self.assertIn("cast_board.py refs", out["reference_board"]["command"])
        self.assertEqual(out["print"]["references"], [board])
        self.assertIn("--reference " + board, out["file_it"])
        self.assertRegex(board, r"-reference\.png$")   # the name `put` accepts as a board

    def test_unstyled_single_reference_stays_bare(self):
        out = self.plan(request(style=None, style_formula=None, identity_reference="runs/x/swipe.jpg"))
        self.assertIsNone(out["reference_board"])
        self.assertEqual(out["print"]["references"], ["runs/x/swipe.jpg"])

    def test_style_with_identity_still_one_board(self):
        out = self.plan(request(identity_reference="runs/x/swipe.jpg",
                                look_reference="components/video-production/styles/swatches/family-3d.jpg"))
        self.assertEqual(out["reference_board"]["from"],
                         ["runs/x/swipe.jpg", "components/video-production/styles/swatches/family-3d.jpg"])


if __name__ == "__main__":
    unittest.main()
