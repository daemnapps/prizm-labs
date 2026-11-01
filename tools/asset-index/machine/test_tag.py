#!/usr/bin/env python3
"""tag.py describes product photos too, for any brand (the team, 2026-10-28): the email layout picked product photos
by file name and wrote what it guessed was in them.

    /usr/bin/python3 tools/asset-index/machine/test_tag.py

  a  drive_items turns map_all's picture records into tag items: id = Drive id, ref = the drive: reference the
     email layout uses; videos and records outside Shared Assets are left out
  b  the question names no brand's packaging or ingredients: products come from the brand's folders AND its
     images.json (a brand whose products are flat .md files still gets its names), looks from its product files
  c  sheet() takes a loader, so a picture fetched from Drive needs no thumb on disk
  d  a picture that will not load (no thumb in this clone, gone from Drive) is left out of its sheet and never
     tagged: a blank cell would still get a description
No network, no key: the repo root is a temp folder.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
import tag as T  # noqa: E402

BRAND = "zz-brand"


class Tag(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patch = mock.patch.object(T, "REPO", self.root)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_a_drive_items(self):
        d = self.root / "runs" / "asset-index" / BRAND / "products"
        recs = {"img1": {"kind": "image", "drive_id": "img1",
                         "label": "Shared Assets/brands/%s/products/crush/lifestyle/model-face.jpg" % BRAND},
                "vid1": {"kind": "video", "drive_id": "vid1", "label": "Shared Assets/brands/%s/products/crush/v.mp4" % BRAND},
                "odd1": {"kind": "image", "drive_id": "odd1", "label": "My Drive/x.jpg"}}
        for k, r in recs.items():
            (d / k).mkdir(parents=True)
            (d / k / "clip.json").write_text(json.dumps(r))
        old = d.parent / "stills" / "still1"           # an older record with no kind (the stills collection)
        old.mkdir(parents=True)
        (old / "clip.json").write_text(json.dumps({"drive_id": "still1",
                                                   "label": "Shared Assets/brands/%s/products/_shared/lifestyle/luis-1.jpg" % BRAND}))
        self.assertEqual([e["ref"] for e in T.drive_items(old.parent)],
                         ["drive:brands/%s/products/_shared/lifestyle/luis-1.jpg" % BRAND])
        items = T.drive_items(d)
        self.assertEqual([e["id"] for e in items], ["img1"])
        self.assertEqual(items[0]["ref"], "drive:brands/%s/products/crush/lifestyle/model-face.jpg" % BRAND)

    def test_b_question_is_brand_agnostic(self):
        for word in ("turmeric", "moringa", "tall slim tube", "crest", "skincare brand"):
            self.assertNotIn(word, T.ASK)
        p = self.root / "brands" / BRAND / "products"
        (p / "scrub").mkdir(parents=True)
        (p / "scrub" / "product.md").write_text("| **Container** | A squeeze tube, not a jar. |\n")
        (p / "brush.md").write_text("| **Container** | A round silicone brush head. |\n")
        (p / "reference").mkdir()
        (p / "images.json").write_text(json.dumps({"products": {"brush": {"title": "BRUSH Face Brush"}, "_note": {}}}))
        self.assertEqual(T.products_of(BRAND), "brush (BRUSH Face Brush), scrub")
        looks = T.looks_of(BRAND)
        self.assertIn("scrub: A squeeze tube, not a jar.", looks)
        self.assertIn("brush: A round silicone brush head.", looks)
        q = T.ASK.format(n=2, products=T.products_of(BRAND), looks=looks)
        self.assertIn("BRUSH Face Brush", q)

    def test_c_sheet_takes_a_loader(self):
        seen = []

        def load(e):
            seen.append(e["id"])
            return Image.new("RGB", (40, 40), (200, 10, 10))
        jpg = T.sheet([{"id": "a"}, {"id": "b"}], load)
        self.assertEqual(seen, ["a", "b"])
        self.assertTrue(jpg.startswith(b"\xff\xd8"))

    def test_e_one_drive_connection_per_thread(self):
        import io
        import threading
        import types as _t
        b = io.BytesIO()
        Image.new("RGB", (8, 8)).save(b, "JPEG")
        made = []

        class Svc(object):
            def files(self):
                return self

            def get_media(self, **kw):
                return self

            def execute(self):
                return b.getvalue()

        def service():
            made.append(threading.get_ident())
            return Svc()
        fake = _t.ModuleType("gdrive_creator")
        fake.engine = _t.SimpleNamespace(service=service)
        with mock.patch.dict(sys.modules, {"gdrive_creator": fake, "gdrive_creator.engine": fake.engine}):
            load = T.drive_loader()
            together = threading.Barrier(4)            # all four alive at once, so no thread id is reused

            def work():
                for _ in range(3):
                    load({"id": "x"})
                together.wait()
            ts = [threading.Thread(target=work) for _ in range(4)]
            for th in ts:
                th.start()
            for th in ts:
                th.join()
        self.assertEqual(len(made), 4)                 # one per thread, never shared, never one per picture
        self.assertEqual(len(set(made)), 4)

    def test_d_unloadable_picture_is_never_tagged(self):
        d = self.root / "runs" / "asset-index" / BRAND / "proof"
        (d / "thumbs").mkdir(parents=True)
        Image.new("RGB", (40, 40)).save(d / "thumbs" / "a.jpg")
        items = [{"id": "a", "kind": "review", "media": "image", "thumb": "thumbs/a.jpg"},
                 {"id": "b", "kind": "review", "media": "image", "thumb": "thumbs/b.jpg", "drive_id": "gone"}]
        (d / "proof.json").write_text(json.dumps({"items": items}))
        (self.root / "brands" / BRAND / "products").mkdir(parents=True)
        asked = []

        def gone(e):
            raise IOError("no such file on Drive")

        def call(entry, jpg, prompt):
            asked.append(prompt)
            return [{"n": 1, "one_line": "a real picture"}]
        with mock.patch.object(T, "drive_loader", return_value=gone), mock.patch.object(T, "judge_entry", return_value={}), \
                mock.patch.object(T, "call", side_effect=call), mock.patch.object(sys, "argv", ["tag.py", "--brand", BRAND]), \
                mock.patch("builtins.print"):
            T.main()
        tags = json.loads((d / "tags.json").read_text())
        self.assertEqual(list(tags), ["a"])
        self.assertIn("1 pictures", asked[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
