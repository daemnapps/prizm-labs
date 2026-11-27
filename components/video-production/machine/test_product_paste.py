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


    def test_a_find_on_skin_is_refused_for_a_product_that_is_not_skin_coloured(self):
        pp = load()
        (self.d / "kit" / "kit.json").write_text('{"tube_rgb": [0.05, 0.18, 0.36]}')     # a blue tube
        im = Image.open(self.pic).convert("RGB")
        ImageDraw.Draw(im).ellipse((150, 200, 250, 400), fill=(214, 160, 130))             # a shin, not a tube
        leg = self.d / "leg.png"; im.save(leg)
        r = pp.paste(leg, self.d / "kit", self.d / "out3.png", found={"box": [0, 0, 1, 1]}, mask=self.mask)
        self.assertFalse(r["ok"], r)
        self.assertIn("skin", r["why"][0])
        self.assertFalse((self.d / "out3.png").exists())

    def test_a_skin_coloured_product_is_never_refused_on_skin(self):
        pp = load()
        (self.d / "kit" / "kit.json").write_text('{"tube_rgb": [0.36, 0.30, 0.27]}')     # a brown tube
        self.assertTrue(pp.skin_like(self.d / "kit"))

class WhatToFind(unittest.TestCase):
    def test_each_kit_is_looked_for_by_its_own_words(self):
        pp = load()
        k = Path(tempfile.mkdtemp()); (k / "kit.json").write_text('{"what": "the blue tube"}')
        self.assertEqual(pp.kit_what(k), "the blue tube")           # two tubes in one picture: never "the product" twice
        self.assertEqual(pp.kit_what(k, "the cap"), "the cap")      # the caller's words win
        self.assertEqual(pp.kit_what(Path(tempfile.mkdtemp())), "the product")


if __name__ == "__main__":
    unittest.main()
