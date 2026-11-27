"""The split slide lays every photo and word where the winner had them, at 1080 x 1920."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from image_production import split_slide as SS  # noqa: E402


@unittest.skipUnless(Path(SS.AVENIR).is_file(), "the system face this tool uses is not on this machine")
class SplitSlide(unittest.TestCase):
    def test_slide_and_cover(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            ph = {}
            for k, c in zip(("tl", "tr", "bl", "br"), ((200, 0, 0), (0, 200, 0), (0, 0, 200), (200, 200, 0))):
                ph[k] = str(Path(d) / f"{k}.png"); Image.new("RGB", (400, 400), c).save(ph[k])
            out = Path(d) / "s.png"
            SS.render(out, ph, {"title": "THE NECK", "label_l": "DRY SHAVING", "label_r": "brand_a FLEX™",
                                "cap_l": "( BACK IN A DAY OR TWO )", "cap_r": "( ONE / TWO LINES )"})
            im = Image.open(out)
            self.assertEqual(im.size, (1080, 1920))
            l, t, r, b = SS._box(SS.LAYOUT["tl"])
            self.assertEqual(im.getpixel(((l + r) // 2, (t + b) // 2)), (200, 0, 0))
            self.assertEqual(im.getpixel((540, 50)), SS.STYLE["bars"])
            SS.cover(Path(d) / "c.png", ph["tl"], ["5 THINGS", "THAT NEVER FIXED", "( one )"])
            self.assertEqual(Image.open(Path(d) / "c.png").size, (1080, 1920))


if __name__ == "__main__":
    unittest.main()
