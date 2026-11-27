"""The prop purpose: an object alone, never handed the brand's people footage, delivered as a cut-out."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from PIL import Image, ImageDraw  # noqa: E402

from image_production import context as CX, engine as EN  # noqa: E402


def purposes():
    d = json.loads((HERE / "purposes.json").read_text())
    rows = d.get("purposes", d)
    return rows if isinstance(rows, dict) else {r["id"]: r for r in rows}


class PropPurpose(unittest.TestCase):
    def test_the_prop_purpose_is_people_free_asset_free_and_cut_out(self):
        p = purposes()["prop"]
        self.assertIs(p["people"], False)
        self.assertIs(p["assets"], False)
        self.assertIs(p["cutout"], True)
        self.assertIs(p["reference_required"], False)      # a parody prop has no real photo to start from
        self.assertNotEqual(p["words"], "never")            # a parody label is spelled on the object

    def test_a_prop_is_never_handed_the_brands_footage(self):
        self.assertFalse(CX.wants_assets({"direction": "a tub"}, purposes()["prop"]))
        self.assertTrue(CX.wants_assets({"direction": "a man"}, purposes()["ad"]))
        self.assertFalse(CX.wants_assets({"from_image": "x.png"}, purposes()["ad"]))   # an edit, as before

    def test_the_cutout_clears_the_ground_and_keeps_white_inside_the_object(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "prop-01.png"
            im = Image.new("RGB", (200, 200), (255, 255, 255))
            dr = ImageDraw.Draw(im)
            dr.rectangle((60, 40, 140, 160), fill=(200, 60, 90))         # the object
            dr.rectangle((85, 80, 115, 120), fill=(255, 255, 255))       # its white label, inside it
            im.save(f)
            out = Image.open(EN.cutout(f))
            self.assertEqual(out.mode, "RGBA")
            self.assertLessEqual(out.size[0], 90)                          # cropped to the object (and its soft edge)
            a = out.split()[3]
            self.assertEqual(a.getpixel((out.size[0] // 2, out.size[1] // 2)), 255)   # the white label stays
            self.assertTrue((Path(d) / "prop-01-cut.png").is_file())


if __name__ == "__main__":
    unittest.main()
