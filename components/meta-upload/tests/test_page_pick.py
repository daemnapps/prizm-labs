"""One card picked for two Facebook Pages: one ad per Page, the SAME ad name on both (the Page is never in the
name), each recorded with its Page so spend can be read per Page."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import upload as U  # noqa: E402

NAME = "brand-a_widget_brief-0042_batch-2026-11-20-a_page-one"


class StubBrand:
    name, page_id, instagram_id = "brand-a", "111", None


class StubMeta:
    ACCOUNT = "1"

    def __init__(self):
        self.ads, self.n = [], 100

    def post(self, path, **kw):
        self.n += 1
        if path.endswith("/ads"):
            self.ads.append(kw)
        return {"id": str(self.n)}

    def upload_image(self, path, name=None):
        return "hash-" + Path(path).name

    def paged(self, path, **kw):
        return []

    def get(self, path, **kw):
        return {}


def row(page, key):
    return {"meta_ad_name": NAME, "key": key, "campaign": "c", "ad_set": "s", "media": ["a.png"], "kind": "image",
            "format": "flexible", "fb_page": page, "fb_page_name": "Page " + page, "link_id": "l", "unit": NAME,
            "old_name": None}


class PagePick(unittest.TestCase):
    def test_two_pages_one_name_two_ads(self):
        p = {"brand": "brand-a", "ads": [row("111", NAME), row("222", NAME + "@222")],
             "campaigns": {"c": {"ad_sets": {"s": 2}}}, "held": []}
        m = StubMeta()
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(U, "Brand", return_value=StubBrand()), \
                mock.patch.object(U, "flexible_ad", return_value={}), \
                mock.patch.object(U, "known_ids", return_value=(Path(d) / "ids.json", {"campaigns": {}, "ad_sets": {}})), \
                mock.patch.object(U, "remember_ids"):
            st_f = Path(d) / "state.json"
            st_f.write_text(json.dumps({"campaigns": {"c": "9"}, "ad_sets": {"c|s": "8"}, "media": {}, "ads": {}}))
            st = U.go(d, p, {"start": "PAUSED"}, m=m, state_f=st_f, log=lambda *_: None)
        self.assertEqual([a["name"] for a in m.ads], [NAME, NAME])          # the Page is not in the name
        self.assertEqual(len({st["ads"][NAME], st["ads"][NAME + "@222"]}), 2)  # two ads, told apart by key
        self.assertNotIn("_p-", "".join(a["name"] for a in m.ads))

    def test_key(self):
        self.assertEqual(U.ad_key({"meta_ad_name": "n"}), "n")
        self.assertEqual(U.ad_key({"meta_ad_name": "n", "key": "n@2"}), "n@2")


if __name__ == "__main__":
    unittest.main()
