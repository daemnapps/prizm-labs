"""Brief IDs: a brief is brand + product + number, and people see it as one readable ID (2026-11-11).

The cases are the three real briefs numbered 0324 (fixtures/brief-ids-0324.json): two products of one brand and one
of another. A number alone must never match one to another."""
import json
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import names as N  # noqa: E402

FX = json.loads((HERE / "fixtures" / "brief-ids-0324.json").read_text())
A, B, C = FX["briefs"]          # A and B: one brand, two products; C: another brand


class BriefIds(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("BRIEF_IDS_OFF", None)

    def test_readable_id_for_each_0324(self):
        for b in FX["briefs"]:
            self.assertEqual(N.brief_label(b["key"]), b["label"])
        self.assertEqual(len({b["label"] for b in FX["briefs"]}), 3)

    def test_readable_id_from_ad_names(self):
        for b in FX["briefs"]:
            self.assertEqual(N.brief_label(b["ad_name"]), b["label"])
        self.assertEqual(N.brief_label(FX["store_handle"]["key"]), FX["store_handle"]["label"])

    def test_a_bare_number_is_not_passed_off_as_one_brief(self):
        self.assertEqual(N.brief_label("brief-0324"), "Brief 0324")
        self.assertEqual(N.brief_label(FX["no_product"]["key"]), FX["no_product"]["label"])
        self.assertEqual(N.brief_label(FX["idea"]), "")

    def test_full_key_and_same_brief(self):
        for b in FX["briefs"]:
            self.assertEqual(N.full_brief_key(b["ad_name"]), b["key"])
        self.assertIsNone(N.full_brief_key("brief-0324"))
        self.assertFalse(N.same_brief(A["key"], B["key"]))
        self.assertFalse(N.same_brief(B["key"], C["key"]))
        self.assertTrue(N.same_brief(A["ad_name"], A["key"]))
        self.assertTrue(N.same_brief(FX["store_handle"]["key"] + "_batch-x", FX["store_handle"]["catalog"]))
        self.assertFalse(N.same_brief("brief-0324", "brief-0324"))       # a number alone never matches

    def test_rollback_switch(self):
        os.environ["BRIEF_IDS_OFF"] = "1"
        self.assertFalse(N.brief_ids_on())
        self.assertEqual(N.brief_label(A["key"]), "Brief 0324")


if __name__ == "__main__":
    unittest.main()
