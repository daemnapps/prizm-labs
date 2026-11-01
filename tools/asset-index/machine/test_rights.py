#!/usr/bin/env python3
"""Tests for the usage-rights check (rights.py) and its use in the search (search.py). No network, no drive.

    /usr/bin/python3 -m unittest tools/asset-index/machine/test_rights.py
"""
from __future__ import annotations

import json
import sys
import unittest
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rights  # noqa: E402
import search  # noqa: E402
import shared_paths  # noqa: E402
from test_index import Base, make_record  # noqa: E402

LABEL = "Shared Assets/brands/acme/content-creators/female/white/35-44/{}/raw/clip.mp4"
REGISTER = {"creators": [
    {"creator": "no_ads_creator", "drive_folder": "Jackie", "paid_ads": False, "website": False, "until": None},
    {"creator": "web_only", "drive_folder": "creator-a", "paid_ads": False, "website": True, "until": None},
    {"creator": "ended", "drive_folder": "kezia", "paid_ads": True, "website": None, "until": "2026-06-30"},
    {"creator": "open", "drive_folder": "joanna", "paid_ads": True, "website": True, "until": None},
    {"creator": "window_unknown", "drive_folder": "kara", "paid_ads": True, "until": "see note"},
    {"creator": "no_folder_yet", "paid_ads": True},
]}
TODAY = date(2026, 10, 30)


class Verdict(unittest.TestCase):
    def setUp(self):
        self.reg = {r["drive_folder"].lower(): r for r in REGISTER["creators"] if r.get("drive_folder")}

    def v(self, folder, use="ads"):
        return rights.verdict(LABEL.format(folder), self.reg, use, TODAY)["state"]

    def test_a_creator_whose_row_says_no_is_refused_in_any_case(self):
        self.assertEqual(self.v("jackie"), "refused")
        self.assertEqual(self.v("JACKIE", "website"), "refused")

    def test_the_answer_depends_on_the_use(self):
        self.assertEqual(self.v("creator-a", "ads"), "refused")
        self.assertEqual(self.v("creator-a", "website"), "allowed")

    def test_a_window_that_has_ended_is_expired(self):
        self.assertEqual(self.v("kezia"), "expired")
        self.assertEqual(rights.verdict(LABEL.format("kezia"), self.reg, "ads", date(2026, 6, 1))["state"], "allowed")

    def test_a_window_with_no_known_start_is_not_refused_here(self):
        self.assertEqual(self.v("kara"), "allowed")

    def test_a_creator_with_no_row_is_unknown_and_other_footage_is_not_creator_footage(self):
        self.assertEqual(self.v("gabriela"), "unknown")
        self.assertEqual(rights.verdict("Shared Assets/brands/acme/products/tube.jpg", self.reg)["state"], "n/a")

    def test_a_missing_register_is_empty(self):
        self.assertEqual(rights.load(path=Path("/nonexistent/usage-rights.json")), {})


class SearchRespectsRights(Base):
    def setUp(self):
        super().setUp()
        self.reg_file = self.tmp / "usage-rights.json"
        self.reg_file.write_text(json.dumps(REGISTER))
        files = []
        for cid, folder in (("refused", "Jackie"), ("allowed", "joanna"), ("unknown", "gabriela"), ("ended", "kezia")):
            files.append(self.put(f"content-creators/female/white/35-44/{folder}/raw/{cid}.MOV", 10.0))
            make_record(self.work, "acme-creators", cid, filename=f"{cid}.MOV", folder=folder, size_mb=10.0,
                        duration=10.0, scenes=[{"t_start": 0.0, "t_end": 10.0,
                                                "visuals": "Woman rubs turmeric scrub on her forearm at the sink.",
                                                "spoken": None, "on_screen_text": None}])
        shared_paths.build_map(self.work / "acme-creators", files, self.root, self.maps)
        search._corpus.cache_clear()

    def find(self, **kw):
        return search.search("woman rubs scrub on her forearm at the sink", "", "acme", work=self.work,
                             maps=self.maps, per=10, rights_file=self.reg_file, today=TODAY, **kw)

    def test_refused_and_expired_footage_never_comes_back_for_ads(self):
        ids = {h["clip_id"] for h in self.find()}
        self.assertEqual(ids, {"allowed", "unknown"})

    def test_every_hit_carries_its_verdict(self):
        by = {h["clip_id"]: h["rights"]["state"] for h in self.find()}
        self.assertEqual(by, {"allowed": "allowed", "unknown": "unknown"})

    def test_no_filter_still_marks_every_hit(self):
        by = {h["clip_id"]: h["rights"]["state"] for h in self.find(use=None)}
        self.assertEqual(by["refused"], "refused")
        self.assertEqual(by["ended"], "expired")
        self.assertEqual(len(by), 4)


if __name__ == "__main__":
    unittest.main()
