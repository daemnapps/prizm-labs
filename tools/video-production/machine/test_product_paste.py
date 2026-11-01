#!/usr/bin/env python3
"""python3 machine/test_product_paste.py — no network. Runs where numpy is (local-studio's .venv), and
skips cleanly elsewhere. THE PRODUCT PASTE (2026-10-09): the drawn product is replaced by the kit's real
cut-out at the matching angle; a drawn thing that matches no angle is held, never pasted."""
import importlib.util, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
try:
    import numpy as np
    from PIL import Image, ImageDraw
except ImportError:                                    # the mini's stdlib Python
    np = None


def load():
    sp = importlib.util.spec_from_file_location("pp", HERE / "product_paste.py")
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


@unittest.skipIf(np is None, "numpy lives in local-studio's .venv")
class Paste(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "kit" / "sources").mkdir(parents=True)
        for a, w in ((0, 60), (90, 30)):               # a front (wide) and a side (slim) real angle
            c = Image.new("RGBA", (w + 20, 140), (0, 0, 0, 0))
            ImageDraw.Draw(c).ellipse((10, 10, 10 + w, 130), fill=(200, 30, 30, 255))
            c.save(self.d / "kit" / "sources" / f"turntable-{a:03d}.png")
        self.pic = self.d / "pic.png"
        im = Image.new("RGB", (400, 600), (240, 240, 240))
        ImageDraw.Draw(im).ellipse((150, 200, 250, 400), fill=(20, 20, 200))   # the drawn product, front-wide
        im.save(self.pic)
        self.mask = Image.new("L", (400, 600), 0)
        ImageDraw.Draw(self.mask).ellipse((150, 200, 250, 400), fill=255)

    def test_the_drawn_product_becomes_the_real_one(self):
        pp = load()
        r = pp.paste(self.pic, self.d / "kit", self.d / "out.png", found={"box": [0, 0, 1, 1], "facing": "side"},
                     mask=self.mask)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["angle"], 0)                # the wide outline is the front, not the side
        px = Image.open(self.d / "out.png").convert("RGB").getpixel((200, 300))
        self.assertGreater(px[0], px[2])               # the real (red) product, not the drawn (blue) one

    def test_a_thing_no_angle_fits_is_held(self):
        pp = load()
        m = Image.new("L", (400, 600), 0)
        ImageDraw.Draw(m).rectangle((20, 280, 380, 320), fill=255)   # a long flat bar: not the product
        r = pp.paste(self.pic, self.d / "kit", self.d / "out2.png", found={"box": [0, 0, 1, 1], "facing": "side"}, mask=m)
        self.assertFalse(r["ok"], r)
        self.assertFalse((self.d / "out2.png").exists())

    def test_a_kit_with_no_cutouts_is_passed_over(self):
        pp = load()
        empty = self.d / "empty"; (empty / "sources").mkdir(parents=True)
        self.assertEqual(pp.paste(self.pic, empty, found={"box": [0, 0, 1, 1]}).get("skipped"), "no turntable cut-outs in the kit")


if __name__ == "__main__":
    unittest.main()
