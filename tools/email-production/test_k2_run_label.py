#!/usr/bin/env python3
"""The month's one home, read from email production (SI-22 (calendar months
home), K2 (brands write wall)): a run's label prefix comes from where the month
lives, and the Klaviyo push finds its send at runs/marketing-calendar/<brand>/
<YYYY-MM>/ — never at the component's old runs/ folder.

    /usr/bin/python3 tools/email-production/test_k2_run_label.py
"""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TMP = Path(tempfile.mkdtemp(prefix="k2-run-label-test-"))
WS = TMP / "ws"
os.environ["AI_WORKSPACE"] = str(WS)            # before anything imports paths.py

import brief                                      # noqa: E402
import simple_email as S                          # noqa: E402

BRAND = "testbrand"


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1))


def month(root, slot_id):
    write(root / "run.json", {"brand": BRAND, "month": "2026-10"})
    write(root / "slots.json", [{"id": slot_id, "date": "2026-10-09", "type": "what-went-wrong"}])


class Prefix(unittest.TestCase):
    def test_the_new_home_is_branded(self):
        self.assertEqual(brief.label_prefix(WS / "runs/marketing-calendar" / BRAND / "2026-10", BRAND),
                         BRAND + "-")

    def test_a_legacy_branded_folder_is_branded(self):
        self.assertEqual(brief.label_prefix(Path("x/calendar-2026-10-" + BRAND), BRAND), BRAND + "-")

    def test_a_legacy_unbranded_folder_stays_unbranded(self):
        self.assertEqual(brief.label_prefix(Path("x/calendar-2026-09"), BRAND), "")

    def test_run_month_asks_brief_for_the_prefix(self):
        src = (HERE / "run_month.py").read_text()
        self.assertIn("label_prefix(", src)
        self.assertNotIn("run_dir.name.endswith", src)


class TheSlot(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(str(WS / "runs"), ignore_errors=True)
        shutil.rmtree(str(WS / "components"), ignore_errors=True)

    def test_found_at_the_new_home(self):
        month(WS / "runs/marketing-calendar" / BRAND / "2026-10", "oct-06")
        got = S.the_slot(BRAND, BRAND + "-oct-06")
        self.assertIsNotNone(got)
        self.assertEqual(got["id"], "oct-06")

    def test_the_old_component_folder_is_not_read(self):
        month(WS / ("components/marketing-calendar/runs/calendar-2026-10-" + BRAND), "oct-07")
        self.assertIsNone(S.the_slot(BRAND, BRAND + "-oct-07"))


if __name__ == "__main__":
    try:
        unittest.main(verbosity=1)
    finally:
        shutil.rmtree(str(TMP), ignore_errors=True)
