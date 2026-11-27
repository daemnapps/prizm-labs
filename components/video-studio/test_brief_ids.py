"""The Studio's ledger lookup matches brand + product + number (2026-11-11: one product's 0324 showed "On Meta"
because another product's 0324 is live). Cases: components/naming/fixtures/brief-ids-0324.json."""
import json
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import video_studio as VS  # noqa: E402

FX = json.loads((HERE.parent / "naming" / "fixtures" / "brief-ids-0324.json").read_text())
A, B, C = (b["key"] for b in FX["briefs"])


class StudioBriefIds(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("BRIEF_IDS_OFF", None)

    def test_another_products_number_never_stands_in(self):
        self.assertIsNone(VS._same_brief_entry(A, {B: {"stage": "live"}, C: {"stage": "live"}}))

    def test_same_brief_under_another_product_spelling(self):
        sh = FX["store_handle"]
        self.assertEqual(VS._same_brief_entry(sh["catalog"], {sh["key"]: {"stage": "making"}, C: {"stage": "live"}}),
                         {"stage": "making"})

    def test_ledger_stages_keeps_each_0324_apart(self):
        old = VS._get
        VS._get = lambda *a, **k: {"items": [{"id": A, "stage": "launch"}],
                                   "removed": [{"id": B, "stage": "live", "note": "Completed: on Meta"},
                                               {"id": C, "stage": "live", "note": "Completed: sent to Meta"}]}
        try:
            got = VS.ledger_stages([{"key": A}, {"key": B}, {"key": C}])
        finally:
            VS._get = old
        self.assertEqual([got[k]["id"] for k in (A, B, C)], ["launch", "live", "live"])

    def test_labels(self):
        for b in FX["briefs"]:
            self.assertEqual(VS.brief_label(b["key"]), b["label"])
        self.assertEqual(VS.brief_label(None), "")


class PictureLane(unittest.TestCase):
    """Picture briefs sit beside video ones in the Studio (2026-11-11): an item is its lane + its full key."""
    def reg(self):
        a, b = FX["briefs"][0], FX["briefs"][1]          # one brand, two products, the same number
        brand = a["key"].split("_")[0]
        return brand, {"briefs": {
            a["key"]: {"brand": brand, "product": a["key"].split("_")[1], "brief": "brief-0324", "lane": "video-teardown",
                       "state": "for-review", "title": "video one"},
            b["key"]: {"brand": brand, "product": b["key"].split("_")[1], "brief": "brief-0324", "state": "for-review",
                       "title": "picture one"},
            "%s_%s_brief-0325" % (brand, b["key"].split("_")[1]): {"brand": brand, "brief": "brief-0325", "state": "shipped"}}}

    def test_picture_briefs_come_by_full_key_and_lane(self):
        brand, reg = self.reg()
        got = VS.picture_briefs(brand, reg)
        self.assertEqual([x["key"] for x in got], [FX["briefs"][1]["key"]])     # the video brief and the shipped one stay out
        self.assertEqual(got[0]["lane"], "image")
        self.assertEqual(got[0]["id"], "image:" + FX["briefs"][1]["key"])
        self.assertEqual(got[0]["label"], FX["briefs"][1]["label"])

    def test_picture_lane_is_off_until_switched_on(self):
        os.environ.pop("VIDEO_STUDIO_PICTURES", None)
        self.assertFalse(VS.pictures_on())
        os.environ["VIDEO_STUDIO_PICTURES"] = "1"
        try:
            self.assertTrue(VS.pictures_on())
        finally:
            os.environ.pop("VIDEO_STUDIO_PICTURES", None)


if __name__ == "__main__":
    unittest.main()
