"""picture_standard: the brand's product picture rules reach the print words, and a picture is measured against them."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import picture_standard as PS  # noqa: E402


class Standard(unittest.TestCase):
    def test_brand_b_has_the_three_kinds(self):
        self.assertEqual(set(PS.standard("brand_b")["kinds"]), {"shop-card", "gallery", "offer-icon"})

    def test_lines_carry_ground_and_bundle_rules(self):
        ls = " ".join(PS.lines("brand_b", "shop-card", bundle=True))
        self.assertIn("255 255 255", ls)
        self.assertIn("open pouch", ls)
        self.assertNotIn("open pouch", " ".join(PS.lines("brand_b", "shop-card")))

    def test_unknown_kind_is_refused(self):
        with self.assertRaises(SystemExit):
            PS.lines("brand_b", "poster")

    def test_brand_without_standard_gives_nothing(self):
        self.assertEqual(PS.lines("no-such-brand", "shop-card"), [])

    def test_check_measures_ground_and_fill(self):
        from PIL import Image, ImageDraw
        with tempfile.TemporaryDirectory() as d:
            good, grey = Path(d) / "good.png", Path(d) / "grey.png"
            for f, bg in ((good, (255, 255, 255)), (grey, (245, 245, 245))):
                im = Image.new("RGB", (1220, 1220), bg)
                ImageDraw.Draw(im).rectangle((300, 250, 920, 1000), fill=(110, 96, 88))
                im.save(f)
            self.assertTrue(PS.check("brand_b", "shop-card", good)["ok"])
            r = PS.check("brand_b", "shop-card", grey)
            self.assertFalse(r["ok"])
            self.assertIn("ground", r["fails"][0])


if __name__ == "__main__":
    unittest.main()
