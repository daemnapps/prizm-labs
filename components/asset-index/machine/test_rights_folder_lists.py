#!/usr/bin/env python3
"""Folder lists in the usage-rights register: every block with `drive_folders` clears the uses it marks true.

    /usr/bin/python3 -m unittest components/asset-index/machine/test_rights_folder_lists.py

email_lead, 2026-11-10: content from before August may be used on the website too (pre_registry gains `website`), and
creators from the earliest era are cleared for everything — ads, website, social, email — listed as their own
block. A row always wins over every list; a use no list marks stays `unknown`.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rights  # noqa: E402

LABEL = "Shared Assets/brands/acme/content-creators/female/white/35-44/{}/raw/clip.mp4"
REGISTER = {
    "pre_registry": {"email": True, "website": True, "drive_folders": ["amy", "late", "jackie"]},
    "early_era": {"paid_ads": True, "website": True, "social": True, "email": True, "drive_folders": ["amy", "jackie"]},
    "email_only": {"email": True, "drive_folders": ["olda"]},
    "_fields": {"drive_folders": "not a list here: a description"},
    "creators": [
        {"creator": "never", "drive_folder": "jackie", "paid_ads": False, "website": False, "email": False, "until": None},
    ]}


class FolderLists(unittest.TestCase):
    def setUp(self):
        self.reg = rights.load(path=None, register=REGISTER)

    def v(self, folder, use):
        return rights.verdict(LABEL.format(folder), self.reg, use)["state"]

    def test_a_folder_on_the_early_era_list_is_cleared_for_every_use(self):
        for use in ("ads", "website", "social", "email"):
            self.assertEqual(self.v("amy", use), "allowed", use)

    def test_a_pre_registry_folder_is_cleared_for_website_and_email_only(self):
        self.assertEqual(self.v("late", "website"), "allowed")
        self.assertEqual(self.v("late", "email"), "allowed")
        self.assertEqual(self.v("late", "ads"), "unknown")
        self.assertEqual(self.v("late", "social"), "unknown")

    def test_a_list_that_marks_one_use_leaves_the_others_unknown(self):
        self.assertEqual(self.v("olda", "email"), "allowed")
        self.assertEqual(self.v("olda", "website"), "unknown")

    def test_a_row_wins_over_every_list(self):
        for use in ("ads", "website", "email"):
            self.assertEqual(self.v("jackie", use), "refused", use)

    def test_the_real_brand_b_register_reads_the_early_era(self):
        reg = rights.load("brand_b")
        if not reg:
            self.skipTest("no brand_b register in this checkout")
        blocked = [k for k, r in reg.items() if r.get("_block")]
        self.assertTrue(blocked)
        self.assertEqual(rights.verdict(LABEL.format("jennie"), reg, "ads")["state"], "allowed")
        self.assertEqual(rights.verdict(LABEL.format("andrea"), reg, "website")["state"], "refused")
        # off the lists (arrived August 2026), and since 2026-11-10 a row of her own that refuses every use
        self.assertEqual(rights.verdict(LABEL.format("gail"), reg, "email")["state"], "refused")


if __name__ == "__main__":
    unittest.main()
