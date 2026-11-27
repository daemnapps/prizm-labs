"""Story caption words: bubbles land where the winner's did, inside the frame, and words too long are refused."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from image_production import story_caption as SC  # noqa: E402

FONTS = Path(SC.TEXT_FONT).is_file() and Path(SC.HANDLE_FONT).is_file()


@unittest.skipUnless(FONTS, "the system fonts this tool uses are not on this machine")
class StoryCaption(unittest.TestCase):
    CAP = {"handle": "@brand_a", "emoji": "", "bubbles": [["Best Black Friday buy! king", "got the FLEX starting at $49!"],
                                                           ["the sale is still live!"]]}

    def test_bubbles_stack_inside_the_frame(self):
        b = SC.boxes((900, 1600), self.CAP)["bubbles"]
        self.assertEqual(len(b), 2)
        self.assertLess(b[0][3], b[1][1])                       # the second bubble sits under the first
        for l, t, r, bot in b:
            self.assertTrue(0 <= l < r <= 900 and 0 <= t < bot <= 1600)
        self.assertAlmostEqual(b[0][1] / 1600, SC.LAYOUT["bubble_top"], places=2)

    def test_render_writes_the_picture(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            plate, out = Path(d) / "p.png", Path(d) / "o.png"
            Image.new("RGB", (900, 1600), (10, 10, 10)).save(plate)
            r = SC.render(plate, out, self.CAP)
            self.assertTrue(r["ok"] and out.is_file())
            self.assertEqual(Image.open(out).getpixel((450, r["boxes"]["bubbles"][0][1] + 3)), (255, 255, 255))

    def test_words_too_wide_are_refused(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            plate = Path(d) / "p.png"
            Image.new("RGB", (900, 1600)).save(plate)
            with self.assertRaises(ValueError):
                SC.render(plate, Path(d) / "o.png", {"bubbles": [["x" * 80]]})


if __name__ == "__main__":
    unittest.main()
