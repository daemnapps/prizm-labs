"""The 3D product path — the parts that need no Blender and no model.

    python3 tools/image-production/tests/test_product3d.py

Every test builds a throwaway kit bank under tempfile; nothing reaches runs/,
brands/, Blender or a network.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from image_production import product3d as D            # noqa: E402


def kit_bank(root, decl=True, blend=True, alias="thing"):
    kit = Path(root) / "brandx" / "products" / "the-thing"
    (kit / "model").mkdir(parents=True)
    (kit / "kit.json").write_text(json.dumps({"aliases": [alias], "what": "the object",
                                              "behaviour": {"rests": [{"on": "its stand"}]}}))
    if blend:
        (kit / "model" / "m.blend").write_bytes(b"x")
    if decl:
        (kit / "model" / "render3d.json").write_text(json.dumps({
            "status": "draft", "model": {"blend": "model/m.blend", "root": "product"},
            "default_pose": "rest", "poses": {"rest": {"rest": 0}}}))
    return kit


class Kits(unittest.TestCase):
    def test_found_by_folder_and_alias(self):
        with tempfile.TemporaryDirectory() as t:
            kit = kit_bank(t)
            self.assertEqual(D.find_kit("brandx", "the-thing", root=t), kit)
            self.assertEqual(D.find_kit("brandx", "THING", root=t), kit)
            self.assertIsNone(D.find_kit("brandx", "other", root=t))
            self.assertIsNone(D.find_kit("brandy", "thing", root=t))

    def test_no_declaration_or_no_model_file_means_no_3d(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(D.has_model(kit_bank(t, decl=False)))
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(D.has_model(kit_bank(t, blend=False)))
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(D.has_model(kit_bank(t)))


class Request(unittest.TestCase):
    def test_on_by_default_off_when_asked_and_never_for_an_edit(self):
        with tempfile.TemporaryDirectory() as t:
            kit_bank(t)
            orig = D.bank
            D.bank = lambda: Path(t)
            try:
                self.assertIsNotNone(D.wanted({"product": "thing"}, "brandx")[0])
                self.assertIsNone(D.wanted({"product": "thing", "product_3d": False}, "brandx")[0])
                self.assertIsNone(D.wanted({"product": "thing", "from_image": "a.png"}, "brandx")[0])
                self.assertIsNone(D.wanted({}, "brandx")[0])
                with self.assertRaises(FileNotFoundError):
                    D.wanted({"product": "nope", "product_3d": True}, "brandx")
            finally:
                D.bank = orig

    def test_plan_defaults_and_spot_words(self):
        pl = D.plan({"product_place": {"x": 0.2}}, {"default_pose": "rest"})
        self.assertEqual((pl["pose"], pl["x"], pl["y"]), ("rest", 0.2, 0.72))
        self.assertIn("lower left", D.spot_words(pl))


class Place(unittest.TestCase):
    def test_composite_lands_on_the_anchor_and_leaves_no_box(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            Image.new("RGB", (400, 300), (150, 120, 90)).save(t / "scene.png")
            mask = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
            for x in range(30, 70):
                for y in range(20, 90):
                    mask.putpixel((x, y), (20, 20, 20, 255))
            full = mask.copy()
            for x in range(0, 100):                          # a faint catcher veil over the frame
                for y in range(0, 100):
                    if full.getpixel((x, y))[3] == 0:
                        full.putpixel((x, y), (0, 0, 0, 6))
            mask.save(t / "r-mask.png")
            full.save(t / "r.png")
            rec = {"file": str(t / "r.png"), "mask": str(t / "r-mask.png"),
                   "contact_px": [50, 90], "px_per_cm": 10.0}
            out = D.place_product(t / "scene.png", rec, t / "out.png", anchor=(200, 250),
                                  px_per_cm=20.0, grain=False)
            self.assertEqual(out["box"], [100, 70, 300, 270])
            im = Image.open(t / "out.png")
            self.assertLess(sum(im.getpixel((200, 200))), 150)          # the product is there
            self.assertEqual(im.getpixel((105, 75)), (150, 120, 90))     # the veil is not


if __name__ == "__main__":
    unittest.main(verbosity=1)
