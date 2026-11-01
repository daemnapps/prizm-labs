#!/usr/bin/env python3
"""LD-101 (Brand-B house look), step 6: the usage-rights check knows the EMAIL use, from the same register.

    /usr/bin/python3 -m unittest tools/asset-index/machine/test_ld101_email_rights.py

the team's ruling, 2026-10-30: a creator is cleared for email only when her row says `email: true` ("treat them as no
until their row says `email: true`"), or she has no row and her folder is on the register's pre_registry list
(content that arrived before 2026-07-28). A row always wins over the list. Ads and website verdicts do not change:
a pre-registry folder is still `unknown` for them. search(use="email") returns only cleared people.
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
REGISTER = {
    "pre_registry": {"email": True, "before": "2026-07-28", "drive_folders": ["lillian", "victoria", "jackie"]},
    "creators": [
        {"creator": "said_yes", "drive_folder": "Becky", "paid_ads": True, "website": True, "email": True, "until": None},
        {"creator": "not_answered", "drive_folder": "joanna", "paid_ads": True, "website": True, "until": None},
        {"creator": "never", "drive_folder": "jackie", "paid_ads": False, "website": False, "email": False, "until": None},
        {"creator": "ended", "drive_folder": "kezia", "paid_ads": True, "email": True, "until": "2026-06-30"},
    ]}
TODAY = date(2026, 10, 30)


class EmailVerdict(unittest.TestCase):
    def setUp(self):
        self.reg = rights.load(path=None, register=REGISTER)

    def v(self, folder, use="email"):
        return rights.verdict(LABEL.format(folder), self.reg, use, TODAY)["state"]

    def test_a_row_that_says_yes_is_allowed(self):
        self.assertEqual(self.v("Becky"), "allowed")

    def test_a_row_with_no_email_field_is_refused(self):
        self.assertEqual(self.v("joanna"), "refused")
        self.assertEqual(self.v("joanna", "ads"), "allowed")

    def test_a_row_that_says_no_is_refused_and_wins_over_the_list(self):
        self.assertEqual(self.v("jackie"), "refused")

    def test_a_pre_registry_folder_with_no_row_is_allowed_for_email_only(self):
        self.assertEqual(self.v("lillian"), "allowed")
        self.assertEqual(self.v("Victoria"), "allowed")
        self.assertEqual(self.v("lillian", "ads"), "unknown")
        self.assertEqual(self.v("lillian", "website"), "unknown")

    def test_no_row_and_not_on_the_list_is_unknown(self):
        self.assertEqual(self.v("gabriela"), "unknown")

    def test_an_ended_window_is_expired_for_email_too(self):
        self.assertEqual(self.v("kezia"), "expired")

    def test_the_real_register_reads(self):
        reg = rights.load("brand-b")
        self.assertEqual(rights.verdict(LABEL.format("lillian"), reg, "email", TODAY)["state"], "allowed")
        for yes in ("Becky", "joanna"):     # Joanna said yes 2026-10-30 (e7667adca9)
            self.assertEqual(rights.verdict(LABEL.format(yes), reg, "email", TODAY)["state"], "allowed", yes)
        for no in ("Creator-A", "jenee", "Pixi", "Luciana", "jackie", "andrea"):
            self.assertEqual(rights.verdict(LABEL.format(no), reg, "email", TODAY)["state"], "refused", no)


class SearchForEmail(Base):
    def setUp(self):
        super().setUp()
        self.reg_file = self.tmp / "usage-rights.json"
        self.reg_file.write_text(json.dumps(REGISTER))
        files = []
        for cid, folder in (("yes", "Becky"), ("unasked", "joanna"), ("pre", "lillian"), ("never", "jackie"),
                            ("stranger", "gabriela")):
            files.append(self.put(f"content-creators/female/white/35-44/{folder}/raw/{cid}.MOV", 10.0))
            make_record(self.work, "acme-creators", cid, filename=f"{cid}.MOV", folder=folder, size_mb=10.0,
                        duration=10.0, scenes=[{"t_start": 0.0, "t_end": 10.0,
                                                "visuals": "Woman rubs turmeric scrub on her forearm at the sink.",
                                                "spoken": None, "on_screen_text": None}])
        shared_paths.build_map(self.work / "acme-creators", files, self.root, self.maps)
        search._corpus.cache_clear()

    def test_only_cleared_people_come_back_for_email(self):
        hits = search.search("woman rubs scrub on her forearm at the sink", "", "acme", work=self.work,
                             maps=self.maps, per=10, rights_file=self.reg_file, today=TODAY, use="email")
        self.assertEqual({h["clip_id"] for h in hits}, {"yes", "pre"})
        self.assertTrue(all(h["rights"]["state"] == "allowed" and h["rights"]["use"] == "email" for h in hits))

    def test_a_hit_carries_the_products_its_clip_shows(self):
        bd = self.work / "acme-creators" / "yes" / "breakdown.json"
        d = json.loads(bd.read_text())
        d["products_visible"] = ["brown tube, gold label 'acme body scrub'"]
        bd.write_text(json.dumps(d))
        search._corpus.cache_clear()
        hits = {h["clip_id"]: h for h in search.search("woman rubs scrub on her forearm at the sink", "", "acme", work=self.work,
                                                       maps=self.maps, per=10, rights_file=self.reg_file, today=TODAY, use="email")}
        self.assertEqual(hits["yes"]["products"], ["brown tube, gold label 'acme body scrub'"])
        self.assertEqual(hits["pre"]["products"], [])


if __name__ == "__main__":
    unittest.main()
