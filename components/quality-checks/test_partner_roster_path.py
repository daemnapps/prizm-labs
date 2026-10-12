#!/usr/bin/env python3
"""python3 test_partner_roster_path.py — SI-114 (chain-checks seams):
`partner_on_file` finds a brand's affiliate roster through brandpath, so a
brand on the new layout (email-sms/) and one built from the template (email/)
both resolve. Stdlib unittest; no network, no model, no git. Every file lands
in a temp workspace."""
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import marketing_chain_checks as Q                          # noqa: E402

ROSTER = {"affiliates": [
    {"key": "p1", "name": "A Partner", "link": "https://x.example", "status": "active"},
    {"key": "p2", "name": "Paused Partner", "link": "https://y.example", "status": "paused"},
]}


class PartnerRosterPath(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="si114-roster-")
        self.root = Path(self._tmp.name).resolve()
        (self.root / "components").mkdir()                  # brandpath's repo() wants both
        self.brands = self.root / "brands"
        for brand, folder in (("zz-a", "email-sms"), ("zz-b", "email")):
            d = self.brands / brand / folder
            d.mkdir(parents=True)
            (d / "affiliates.json").write_text(json.dumps(ROSTER))
        (self.brands / "zz-c").mkdir()                      # a brand with no roster at all
        env = unittest.mock.patch.dict(os.environ, {"AI_WORKSPACE": str(self.root)})
        env.start()
        self.addCleanup(env.stop)
        self.addCleanup(self._tmp.cleanup)

    def test_new_layout_returns_the_active_entry(self):
        self.assertEqual(Q.partner_on_file(self.brands / "zz-a", "p1")["name"], "A Partner")

    def test_template_layout_returns_the_active_entry(self):
        self.assertEqual(Q.partner_on_file(self.brands / "zz-b", "p1")["name"], "A Partner")

    def test_a_paused_entry_is_none(self):
        self.assertIsNone(Q.partner_on_file(self.brands / "zz-a", "p2"))
        self.assertIsNone(Q.partner_on_file(self.brands / "zz-b", "p2"))

    def test_a_missing_roster_or_key_is_none(self):
        self.assertIsNone(Q.partner_on_file(self.brands / "zz-c", "p1"))
        self.assertIsNone(Q.partner_on_file(self.brands / "zz-a", "nobody"))
        self.assertIsNone(Q.partner_on_file(self.brands / "zz-a", ""))

    def test_a_string_brand_dir_still_works(self):
        self.assertEqual(Q.partner_on_file(str(self.brands / "zz-b"), "p1")["key"], "p1")

    def test_without_brandpath_the_old_path_still_reads_and_nothing_crashes(self):
        with unittest.mock.patch.dict(sys.modules, {"brandpath": None}):   # import fails
            self.assertEqual(Q.partner_on_file(self.brands / "zz-a", "p1")["key"], "p1")
            self.assertIsNone(Q.partner_on_file(self.brands / "zz-b", "p1"))


if __name__ == "__main__":
    unittest.main()
