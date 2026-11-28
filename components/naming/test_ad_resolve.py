"""Every live ad ties to a brief or a creator (ad_resolve.py)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ad_resolve as R  # noqa: E402
import names as N  # noqa: E402

ALIASES = [{"match": "Creator One #2", "creator": "Creator One"},
           {"match": "Story Images", "legacy": "Story Images"},
           {"match": "Old Video", "brief": "brief-0042", "product": "widget"}]
TRYBE = {"ab12cd34": "Jane Roe"}


def tie(name):
    return R.resolve("brand-a", name, ALIASES, TRYBE)


class ShortName(unittest.TestCase):
    def test_plain(self):
        r = tie("brand-a_widget_brief-0318_batch-2026-11-23-a_page-one")
        self.assertEqual((r["brief"], r["via"], r["extra"]), ("0318", "name", []))

    def test_extra_field_is_tolerated(self):
        n = "brand-a_widget_brief-0318_batch-2026-11-23-a_page-one_p-awnm"
        d = N.parse_any(n)
        self.assertEqual((d["brief_id"], d["funnel"], d["extra"]), ("brief-0318", "page-one", ["p-awnm"]))
        self.assertEqual(tie(n)["brief"], "0318")

    def test_nothing_follows_an_asset(self):
        self.assertIsNone(N.parse_short("brand-a_widget_brief-0318_batch-2026-11-23-a_asset-01_x"))

    def test_four_and_five_still_read(self):
        self.assertEqual(N.parse_short("brand-a_widget_brief-0318_batch-2026-11-23-a")["funnel"], None)
        self.assertEqual(N.parse_short("brand-a_widget_brief-0318_batch-2026-11-23-a_asset-02")["asset"], "asset-02")


class CreatorAd(unittest.TestCase):
    def test_id_maps_to_its_creator(self):
        r = tie("JaneRoe_WIDGET™Pro_20261114_trybe=ab12cd34")
        self.assertEqual((r["creator"], r["trybe_id"], r["via"]), ("Jane Roe", "ab12cd34", "trybe"))

    def test_unknown_id_falls_back_to_the_name(self):
        self.assertEqual(tie("SamDoe_WIDGET™Pro_20261114_trybe=ffff0000")["creator"], "Sam Doe")


class LegacyName(unittest.TestCase):
    def test_creator_alias_ignores_page_and_copy(self):
        for n in ("Creator One #2 - Some LP - Copy", "Creator One #2 - Some LP - page-one"):
            self.assertEqual((tie(n)["creator"], tie(n)["via"]), ("Creator One", "alias"))

    def test_brief_alias(self):
        r = tie("Old Video - Some LP - Copy")
        self.assertEqual((r["brief"], r["brief_id"], r["product"]), ("0042", "brief-0042", "widget"))

    def test_legacy_group(self):
        self.assertEqual(tie("Story Images - Some LP - Copy")["legacy"], "Story Images")

    def test_unknown_is_not_guessed(self):
        r = tie("Something Else - LP - Copy")
        self.assertIsNone(r["via"])
        self.assertIsNone(r["brief"] or r["creator"] or r["legacy"])


if __name__ == "__main__":
    unittest.main()
