#!/usr/bin/env python3
"""Tests for sources.py: footage roots from a brand's settings, piece labels and offsets (no network)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class Sources(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        (t / "brands" / "acme").mkdir(parents=True)
        (t / "brands" / "acme" / "footage-library.json").write_text(json.dumps({"footage_roots": [
            {"prefix": "Shared Assets/", "reader": "gdrive"},
            {"prefix": "Vault/Main/", "reader": "shade", "api": "https://zz-a.invalid", "drive_id": "d1", "key": "ZZ_KEY",
             "id_field": "vault_id"}]}))
        rec = t / "runs" / "acme" / "vault-col" / "r1"
        rec.mkdir(parents=True)
        (rec / "clip.json").write_text(json.dumps({"label": "Vault/Main/a/b.MOV @ 1:30", "vault_id": "v-1",
                                                   "segment_start_s": 90}))
        os.environ["ASSET_INDEX_BRANDS"] = str(t / "brands")
        os.environ["ASSET_INDEX_RUNS"] = str(t / "runs")
        sys.modules.pop("sources", None)
        sys.path.insert(0, str(HERE))
        import sources
        self.S = sources

    def tearDown(self):
        del os.environ["ASSET_INDEX_BRANDS"], os.environ["ASSET_INDEX_RUNS"]
        self.tmp.cleanup()

    def test_roots_from_settings(self):
        self.assertEqual(self.S.admitted("acme", "Vault/Main/a/b.MOV")["reader"], "shade")
        self.assertIsNone(self.S.admitted("acme", "Personal/x.mov"))
        self.assertEqual(self.S.admitted("zz-a", "Shared Assets/x.mp4")["reader"], "gdrive")   # the default root
        self.assertIsNone(self.S.admitted("zz-a", "Vault/Main/a/b.MOV"))

    def test_piece_label_and_offset(self):
        self.assertEqual(self.S.base_label("Vault/Main/a/b.MOV @ 1:30"), "Vault/Main/a/b.MOV")
        self.assertEqual(self.S.offset({"segment_start_s": 90}), 90.0)
        self.assertEqual(self.S._index("acme"), {"Vault/Main/a/b.MOV": "v-1"})

    def test_ranged_asks_the_root_reader(self):
        self.S._shade = lambda root, aid: "https://link/" + aid
        self.assertEqual(self.S.ranged("acme", "Vault/Main/a/b.MOV"), ("https://link/v-1", ""))
        self.assertIsNone(self.S.ranged("acme", "Vault/Main/unknown.MOV"))


if __name__ == "__main__":
    unittest.main()
