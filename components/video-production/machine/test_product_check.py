import json, tempfile, unittest
from pathlib import Path
from PIL import Image, ImageDraw
import product_check as pc
import product_fix as pf


class ProductShape(unittest.TestCase):
    """The product is measured, not guessed (2026-10-02)."""

    def test_axis_ratio_ignores_lean(self):
        for angle in (0, 25, 45):
            m = Image.new("L", (800, 800), 0)
            ImageDraw.Draw(m).rectangle([300, 200, 480, 560], fill=255)   # 180 × 360 = 2.0
            r = pc.axis_ratio(m.rotate(angle, expand=False))
            self.assertAlmostEqual(r, 2.0, delta=0.12)

    def test_fix_words_come_from_image_edit_and_the_kit(self):
        kit = {"outline": {"axis_ratio": 1.79, "height_over_width": 1.68}, "size_cm": {"height": 10.5, "width": 6.3}}
        w = pf.words(kit)
        self.assertIn("1.79 times as tall", w); self.assertIn("whole product", w)


if __name__ == "__main__":
    unittest.main()
