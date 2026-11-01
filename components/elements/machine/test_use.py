#!/usr/bin/env python3
"""The library seam's self-test (SI-100 (elements use seam)).

    python3 test_use.py

Proves: `use(a)` makes rows read from library a, `use(b)` from library b,
and the old way (writing `LIBRARY` and clearing `_cache`) still switches.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import elements as E  # noqa: E402


def _row(rid):
    return {"id": rid, "name": rid, "what": None, "why_it_works": None, "status": "draft",
            "state": None, "signed": None, "examples": None, "evidence": None, "approved": False,
            "source": "test", "extra": {}, "aliases": [], "note": None}


def _library(root, ids):
    root.mkdir()
    entry = {"element": "format", "asset": "video", "source": "test", "enforced_by": [],
             "note": None, "rows": [_row(i) for i in ids], "dropped": {}, "duplicates": [],
             "off_rule": [], "off_status": [], "unresolved": []}
    (root / "format.video.json").write_text(json.dumps(entry))
    return root


class Use(unittest.TestCase):
    def setUp(self):
        self.real = E.LIBRARY
        self.tmp = Path(tempfile.mkdtemp())
        self.a = _library(self.tmp / "a", ["alpha-ad"])
        self.b = _library(self.tmp / "b", ["beta-ad", "gamma-ad"])

    def tearDown(self):
        E.LIBRARY = self.real
        E._cache.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def ids(self):
        return [r["id"] for r in E.rows("format", "video")]

    def test_use_switches_and_clears(self):
        self.assertEqual(E.use(self.a), self.a)
        self.assertEqual(self.ids(), ["alpha-ad"])
        E.use(str(self.b))                        # a str path works too
        self.assertEqual(E.LIBRARY, self.b)
        self.assertEqual(self.ids(), ["beta-ad", "gamma-ad"])

    def test_old_names_still_switch(self):
        E.use(self.b)
        self.assertEqual(self.ids(), ["beta-ad", "gamma-ad"])
        E.LIBRARY = self.a
        E._cache.clear()
        self.assertEqual(self.ids(), ["alpha-ad"])


if __name__ == "__main__":
    unittest.main()
