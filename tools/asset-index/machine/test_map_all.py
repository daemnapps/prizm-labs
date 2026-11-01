#!/usr/bin/env python3
"""LD-59 (image records), widened 2026-10-21: every file the key reaches gets a free mapping record, and search
finds it by name words, scored below a described match, saying `described: false`.

    python3 tools/asset-index/machine/test_map_all.py

No network, no model: a faked key listing, and the describing call is made to fail if anything asks for it.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import map_all as MA  # noqa: E402
import search as S  # noqa: E402
import index_run as IR  # noqa: E402

B = "_brand"


def f(path, fid, **kw):
    d = {"path": "Shared Assets/brands/%s/%s" % (B, path), "name": path.rsplit("/", 1)[-1], "drive_id": fid,
         "bytes": 1000, "md5": "m-" + fid, "mime": None, "created": "2026-01-01T00:00:00Z",
         "modified": "2026-01-02T00:00:00Z", "width": 1080, "height": 1350, "duration_s": None}
    d.update(kw)
    return d


FILES = [
    f("products/brilliance-face-scrub/packshot/brand_b_scrub_white.jpg", "ID_PRODUCT_IMAGE_000000000001"),
    f("intake/organic/IMG_1942.jpg", "ID_DUMP_IMAGE_00000000000000002"),
    f("products/radiance-body-cream/packshot/cream-front.png", "ID_POINTED_IMAGE_0000000000003"),
    f("content-creators/female/raw/creator-kitchen-routine.mov", "ID_VIDEO_000000000000000000004",
      duration_s=42.5, width=1080, height=1920),
    f("archive/old-described-clip.mp4", "ID_ALREADY_RECORDED_00000000005", duration_s=10.0),
]


class MapAll(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp(prefix="ld59-"))
        self.runs = self.repo / "runs" / "asset-index"
        idx = self.repo / "brands" / B / "products"
        idx.mkdir(parents=True)
        (idx / "DRIVE-INDEX.json").write_text(json.dumps({"files": [
            {"drive_id": "ID_POINTED_IMAGE_0000000000003", "kind": "packshot", "folder": "radiance-body-cream",
             "best_for": "the cream tube upright on a marble ledge"}]}))
        old = self.runs / B / "archive" / "ID_ALREADY_RECORDED_00000000005"
        old.mkdir(parents=True)
        (old / "clip.json").write_text(json.dumps({"clip_id": old.name, "meta": {"duration_s": 10.0}}))
        (old / "breakdown.json").write_text(json.dumps({"scenes": [{"t_start": 0, "t_end": 10, "visuals": "a woman rubs scrub on her arm"}]}))
        (old.parent / "map.json").write_text(json.dumps({old.name: {"label": "Shared Assets/brands/%s/archive/old-described-clip.mp4" % B}}))
        self.saved = (IR.gb.req, IR.gb.upload)
        def no_model(*a, **k):
            raise AssertionError("a model was called")
        IR.gb.req = IR.gb.upload = no_model
        S._corpus.cache_clear()

    def tearDown(self):
        IR.gb.req, IR.gb.upload = self.saved
        S._corpus.cache_clear()
        shutil.rmtree(self.repo, ignore_errors=True)

    def go(self, files=FILES, dry=False):
        return MA.run(B, files, runs=self.runs, dry=dry, repo=self.repo)

    def rec(self, col, fid):
        return json.loads((self.runs / B / col / fid / "clip.json").read_text())

    def test_every_file_not_yet_recorded_gets_a_mapping_record(self):
        res = self.go()
        self.assertEqual((res["walked"], res["already"], res["new"]), (5, 1, 4))
        self.assertEqual(res["by_kind"], {"image": 3, "video": 1})
        p = self.rec("products", "ID_PRODUCT_IMAGE_000000000001")
        self.assertEqual((p["kind"], p["described"], p["label"]),
                         ("image", False, "Shared Assets/brands/%s/products/brilliance-face-scrub/packshot/brand_b_scrub_white.jpg" % B))
        for w in ("products", "brilliance", "face", "scrub", "packshot"):
            self.assertIn(w, p["words"])
        self.assertNotIn(B.strip("_"), p["words"])
        dump = self.rec("intake", "ID_DUMP_IMAGE_00000000000000002")
        self.assertEqual(dump["words"], ["intake", "organic"])            # IMG_1942 carries no words
        v = self.rec("content-creators", "ID_VIDEO_000000000000000000004")
        self.assertEqual((v["kind"], v["meta"]["duration_s"], v["meta"]["height"], v["frames"]), ("video", 42.5, 1920, []))
        pt = self.rec("products", "ID_POINTED_IMAGE_0000000000003")
        self.assertEqual(pt["pointer"], "brands/%s/products/DRIVE-INDEX.json" % B)
        self.assertEqual(pt["text"], "the cream tube upright on a marble ledge")
        m = json.loads((self.runs / B / "products" / "map.json").read_text())
        self.assertEqual(set(m), {"ID_PRODUCT_IMAGE_000000000001", "ID_POINTED_IMAGE_0000000000003"})
        # the described clip is untouched
        self.assertFalse((self.runs / B / "archive" / "ID_ALREADY_RECORDED_00000000005" / "words").exists())
        self.assertNotIn("described", self.rec("archive", "ID_ALREADY_RECORDED_00000000005"))

    def test_the_rewalk_adds_only_new_files_and_follows_a_move(self):
        self.go()
        moved = [dict(x) for x in FILES]
        moved[1]["path"] = "Shared Assets/brands/%s/intake/organic/kitchen-shoot/IMG_1942.jpg" % B
        moved.append(f("products/brilliance-face-scrub/packshot/new-upload.jpg", "ID_NEW_UPLOAD_00000000000000006"))
        res = self.go(moved)
        self.assertEqual((res["new"], res["moved"]), (1, 1))
        self.assertIn("kitchen", self.rec("intake", "ID_DUMP_IMAGE_00000000000000002")["words"])

    def test_dry_run_writes_nothing(self):
        res = self.go(dry=True)
        self.assertEqual(res["new"], 4)
        self.assertFalse((self.runs / B / "products").exists())

    def search(self, q, **kw):
        cols = sorted(p.name for p in (self.runs / B).iterdir() if p.is_dir())
        return S.search(q, "", B, work=self.runs / B, maps=self.runs / "_maps", collections=cols, per=5, **kw)

    def test_search_finds_mapping_records_by_name_and_says_so(self):
        self.go()
        hits = self.search("brilliance face scrub")
        self.assertEqual(hits[0]["clip_id"], "ID_PRODUCT_IMAGE_000000000001")
        self.assertEqual((hits[0]["described"], hits[0]["kind"], hits[0]["in"]), (False, "image", None))
        dump = self.search("intake organic")
        self.assertIn("ID_DUMP_IMAGE_00000000000000002", [h["clip_id"] for h in dump])
        pointed = self.search("cream tube marble ledge")
        self.assertEqual(pointed[0]["clip_id"], "ID_POINTED_IMAGE_0000000000003")

    def test_a_described_match_outranks_a_name_match_of_equal_overlap(self):
        self.go()
        hits = self.search("scrub")
        described = [h for h in hits if h["described"]]
        named = [h for h in hits if not h["described"]]
        self.assertTrue(described and named, hits)
        self.assertGreater(described[0]["score"], 0)

    def test_mapped_false_keeps_them_out(self):
        self.go()
        S._corpus.cache_clear()
        self.assertTrue(all(h["described"] for h in self.search("brilliance face scrub", mapped=False)))


if __name__ == "__main__":
    unittest.main()
