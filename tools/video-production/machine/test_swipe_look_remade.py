"""The swipe look follows the picture's bytes (2026-10-24): a picture remade after its look is looked again from its own
bytes, and the old "before" copy is set aside, never put back. No network."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sp = importlib.util.spec_from_file_location("t_swipe_look", HERE / "swipe_look.py")
SL = importlib.util.module_from_spec(sp)
sp.loader.exec_module(SL)


class RemadePicture(unittest.TestCase):
    def test_a_remade_picture_gets_its_own_look(self):
        with tempfile.TemporaryDirectory() as d:
            run = Path(d)
            (run / "media").mkdir()
            sw = run / "K39.jpg"
            Image.new("RGB", (64, 96), (120, 110, 90)).save(sw)
            (run / "element-refs.json").write_text(json.dumps({"S1-F1": [{"what": "swipe frame K39", "file": str(sw)}]}))
            pic = run / "media" / "S1-F1.png"
            Image.new("RGB", (64, 96), (200, 30, 30)).save(pic)
            self.assertEqual(SL.run(run), ["S1-F1 ← K39.jpg"])
            self.assertEqual(SL.run(run), [], "a picture already looked is left alone")
            Image.new("RGB", (64, 96), (30, 30, 200)).save(pic)            # remade
            self.assertEqual(SL.run(run), ["S1-F1 ← K39.jpg"])
            before = Image.open(run / "media/versions/S1-F1-before-swipe-look.png").getpixel((5, 5))
            self.assertEqual(before, (30, 30, 200), "the look starts from the remade picture, not the old one")
            self.assertTrue((run / "media/versions/S1-F1-before-swipe-look-2.png").is_file())


if __name__ == "__main__":
    unittest.main()
