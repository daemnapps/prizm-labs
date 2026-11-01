#!/usr/bin/env python3
"""Tests for image-production reading clip records through asset-index's own
reader (SI-99 (asset-index readers)): runs/asset-index/<brand>/* first, the old
lab folder still read when it is the only source, each row carrying its
frames, and the cache renamed so old frame-less caches are not served.

    /usr/bin/python3 tools/image-production/tests/test_assets_index_reader.py

Stdlib `unittest`. Temp folders only: asset-index's shared_paths is loaded
under a private name with its RUNS / WORK / LAB_WORK pointed at temp folders,
and the cache is a temp folder — never the real runs/, lab/, brands/ or ~/.cache.
"""
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent))                  # APPEND — never insert at 0
from image_production import assets as A           # noqa: E402

SHARED_PATHS = HERE.parents[1] / "asset-index" / "machine" / "shared_paths.py"


def _load_private():
    spec = importlib.util.spec_from_file_location("_si99_shared_paths_under_test", SHARED_PATHS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SP = _load_private()


def _record(coll, cid, subject="a baker", setting="a bakery"):
    d = coll / cid
    d.mkdir(parents=True)
    (d / "clip.json").write_text(json.dumps({
        "clip_id": cid, "path": "/x/a.mp4", "filename": "a.mp4",
        "frames": [{"file": "f_01.jpg", "t": 0.0}]}))
    (d / "breakdown.json").write_text(json.dumps({"subject": subject, "setting": setting}))
    (d / "f_01.jpg").write_bytes(b"jpg")
    return d


class ReadsThroughAssetIndex(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="image-production-index-reader-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.runs, self.work, self.lab = self.tmp / "runs", self.tmp / "work", self.tmp / "lab"
        self.cache = self.tmp / "cache"
        for p in (mock.patch.object(SP, "RUNS", self.runs),
                  mock.patch.object(SP, "WORK", self.work),
                  mock.patch.object(SP, "LAB_WORK", self.lab),
                  mock.patch.object(A, "_asset_index", lambda: SP),
                  mock.patch.object(A, "CACHE", self.cache)):
            p.start()
            self.addCleanup(p.stop)

    def test_lab_leftover_only(self):
        rec = _record(self.lab / "fx-creators", "c1")
        rows = A.described("fx", force=True)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["collection"], "fx-creators")
        self.assertIn("baker", rows[0]["said"])
        self.assertEqual(rows[0]["frames"], [str(rec / "f_01.jpg")])

    def test_runs_come_first(self):
        _record(self.lab / "fx-old", "old1", subject="a baker at dawn")
        _record(self.runs / "fx" / "pull1", "new1")
        rows = A.described("fx", force=True)
        self.assertEqual([r["collection"] for r in rows], ["pull1", "fx-old"])

    def test_cache_is_v2(self):
        _record(self.lab / "fx-creators", "c1")
        A.described("fx", force=True)
        self.assertTrue((self.cache / "fx-described.v2.json").is_file())
        self.assertFalse((self.cache / "fx-described.json").exists())

    def test_a_broken_reader_gives_nothing(self):
        def broken():
            raise RuntimeError("no asset-index here")
        with mock.patch.object(A, "_asset_index", broken):
            self.assertEqual(A._index_work("fx"), [])
            self.assertEqual(A._frames_of(self.tmp), [])


if __name__ == "__main__":
    unittest.main()
