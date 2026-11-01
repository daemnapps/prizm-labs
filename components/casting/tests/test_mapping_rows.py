#!/usr/bin/env python3
"""Casting reads the asset index's name-only records (LD-59 (image records), thread 20261020T0755Z post 139
item 3): image-production's described() lists them without fetching anything, and baselines() fetches frames
only for the few rows it keeps (the full-download guard, 2026-10-21).

    /usr/bin/python3 components/casting/tests/test_mapping_rows.py

Stdlib only; a temp workspace and a fake asset-index; no network, no Drive, no model.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent))                                        # APPEND — never insert at 0
sys.path.append(str(HERE.parents[1] / "image-production"))
import casting as C                                                      # noqa: E402
from image_production import assets as A                                # noqa: E402


class FakeIndex:
    """asset-index's shared_paths, as image-production sees it."""

    def __init__(self, cols):
        self.cols, self.asked = cols, []

    def collections(self, brand):
        return self.cols

    def record_frames(self, record_dir, fetch=True):
        self.asked.append((Path(record_dir).name, fetch))
        if not fetch:
            return []
        f = Path(record_dir) / "frame_01.jpg"
        f.write_bytes(b"jpg")
        return [str(f)]


class MappingRows(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="casting-mapping-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        col = self.tmp / "acme" / "products"
        for i in range(6):
            d = col / ("ID_%02d" % i)
            d.mkdir(parents=True)
            (d / "clip.json").write_text(json.dumps({
                "clip_id": d.name, "drive_id": d.name, "kind": "image", "described": False,
                "label": "Shared Assets/brands/acme/products/bakery-counter/shot-%d.jpg" % i,
                "filename": "shot-%d.jpg" % i, "words": ["products", "bakery", "counter", "shot"],
                "frames": [{"file": "frame_01.jpg", "at_s": 0}]}))
        self.ix = FakeIndex([col])
        for p in (mock.patch.object(A, "_asset_index", lambda: self.ix),
                  mock.patch.object(A, "CACHE", self.tmp / "cache")):
            p.start()
            self.addCleanup(p.stop)

    def test_described_lists_name_only_records_and_fetches_nothing(self):
        rows = A.described("acme", force=True)
        self.assertEqual(len(rows), 6)
        r = rows[0]
        self.assertEqual((r["kind"], r["described"], r["frames"]), ("still", False, []))
        self.assertIn("bakery", r["said"])
        self.assertTrue(all(fetch is False for _n, fetch in self.ix.asked), self.ix.asked)

    def test_baselines_fetch_frames_only_for_the_rows_kept(self):
        rows, _why = C.search.baselines("acme", "bakery counter", limit=2, reader=A)
        self.assertEqual(len(rows), 2, rows)
        self.assertTrue(all(r["baseline"] and r["baseline"].endswith("frame_01.jpg") for r in rows))
        fetched = [n for n, fetch in self.ix.asked if fetch]
        self.assertEqual(len(fetched), 2, self.ix.asked)                   # never all six


if __name__ == "__main__":
    unittest.main()
