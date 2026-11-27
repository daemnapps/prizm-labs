#!/usr/bin/env python3
"""Tests for the records: the definition holds together, a good chain passes and traces, bad records are named."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import records as R  # noqa: E402

D = R.load()


def chain():
    return [
        {"id": "brand_1", "record": "brand", "name": "Sample Co", "website": "https://example.com", "folder": "sample-co"},
        {"id": "offer_1", "brand": "brand_1", "product": "widget", "promise": "fixes it", "price": 39},
        {"id": "presell_1", "brand": "brand_1", "offer": "offer_1", "kind": "presell"},
        {"id": "funnel_1", "brand": "brand_1", "offer": "offer_1", "pages": ["presell_1"]},
        {"id": "research_1", "brand": "brand_1", "avatar": "busy parent", "findings": ["x"], "sources": ["y"]},
        {"id": "brief_1", "brand": "brand_1", "offer": "offer_1", "research": "research_1", "angle": "a",
         "core_message": "m", "form": "dr"},
        {"id": "dr_1", "brief": "brief_1", "script": "s"},
        {"id": "ad_1", "brand": "brand_1", "offer": "offer_1", "funnel": "funnel_1", "brief": "brief_1",
         "made_from": "dr_1", "type": "video", "route": "ai", "ad_name": "n", "files": ["f.mp4"]},
    ]


class DefinitionTest(unittest.TestCase):
    def test_sixteen_plus_session(self):
        self.assertEqual(len(D), 17)
        self.assertIn("session", D)

    def test_prefixes_unique_and_links_known(self):
        prefixes = [d["prefix"] for d in D.values()]
        self.assertEqual(len(prefixes), len(set(prefixes)))
        for name in D:
            for kind in R.shape(D, name).values():
                if kind.startswith(("id:", "ids:")):
                    self.assertIn(kind.split(":", 1)[1].rstrip("?"), D, name)


class CheckTest(unittest.TestCase):
    def test_good_chain_passes(self):
        for rec in chain():
            self.assertEqual(R.check(D, rec), [], rec["id"])

    def test_bad_records_named(self):
        self.assertIn("form should be one of organic, dr, creator",
                      R.check(D, {**chain()[5], "form": "meme"}))
        self.assertTrue(any("is not a offer id" in p for p in R.check(D, {**chain()[5], "offer": "brand_1"})))
        self.assertEqual(R.check(D, {"id": "zzz_1"})[0][:5], "id 'z")

    def test_presell_is_a_page(self):
        self.assertEqual(R.check(D, chain()[3]), [])

    def test_blank_has_every_field(self):
        rec = R.blank(D, "ad", brand="brand_1")
        self.assertTrue(rec["id"].startswith("ad_"))
        self.assertEqual(rec["brand"], "brand_1")
        self.assertIn("results", rec)


class TraceTest(unittest.TestCase):
    def test_ad_traces_to_brand(self):
        with tempfile.TemporaryDirectory() as d:
            for rec in chain():
                (Path(d) / (rec["id"] + ".json")).write_text(json.dumps(rec))
            names = [n for _, n in R.trace(D, "ad_1", d)]
            for want in ("ad", "brand", "offer", "funnel", "ad-brief", "research", "presell-page"):
                self.assertIn(want, names)


if __name__ == "__main__":
    unittest.main()
