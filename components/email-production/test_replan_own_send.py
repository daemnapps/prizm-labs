#!/usr/bin/env python3
"""A re-plan renumbers a month's slots after its emails are built (email_lead, 2026-11-03): the Klaviyo
push finds an email's send by the email's own run.json (its angle and send date), never by the
slot number in its label alone, and refuses when that cannot be settled.

    /usr/bin/python3 components/email-production/test_replan_own_send.py
"""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="replan-own-send-test-"))
WS = TMP / "ws"
os.environ["AI_WORKSPACE"] = str(WS)            # before anything imports paths.py

import simple_email as S                          # noqa: E402

BRAND = "testbrand"
MONTH = WS / "runs/marketing-calendar" / BRAND / "2026-11"


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1))


def slot(sid, date, angle, segment="Core | Lead"):
    return {"id": sid, "date": date, "segment": segment, "variants": [{"avatar": "a", "angle": angle}]}


def email(label, date, angle):
    write(WS / "runs/email-production" / BRAND / label / "run.json",
          {"assignment": {"send_date": date, "angle": angle}})


class OwnSend(unittest.TestCase):
    def setUp(self):
        write(MONTH / "run.json", {"brand": BRAND, "month": "2026-11"})

    def tearDown(self):
        shutil.rmtree(str(WS / "runs"), ignore_errors=True)

    def test_a_renumbered_send_is_found_by_its_angle_and_keeps_its_own_date(self):
        write(MONTH / "slots.json", [slot("nov-07", "2026-11-09", "spotlight"),
                                     slot("nov-09", "2026-11-11", "reader question", "Core | VIP")])
        email(BRAND + "-nov-07", "2026-11-08", "reader question")
        got = S.the_slot(BRAND, BRAND + "-nov-07")
        self.assertEqual(got["id"], "nov-09")
        self.assertEqual(got["date"], "2026-11-08")
        self.assertEqual(got["segment"], "Core | VIP")

    def test_a_number_that_is_another_send_now_is_refused(self):
        write(MONTH / "slots.json", [slot("nov-19", "2026-11-20", "black friday opens")])
        email(BRAND + "-nov-19", "2026-11-19", "the holiday season")
        self.assertIsNone(S.the_slot(BRAND, BRAND + "-nov-19"))

    def test_a_shared_angle_picks_the_send_on_the_emails_own_date(self):
        write(MONTH / "slots.json", [slot("nov-30", "2026-11-25", "the sale"),
                                     slot("nov-34", "2026-11-27", "the sale", "Core | VIP")])
        email(BRAND + "-nov-34", "2026-11-27", "the sale")
        self.assertEqual(S.the_slot(BRAND, BRAND + "-nov-34")["id"], "nov-34")

    def test_a_shared_angle_with_no_send_on_that_date_is_refused(self):
        write(MONTH / "slots.json", [slot("nov-30", "2026-11-25", "the sale"),
                                     slot("nov-31", "2026-11-26", "the sale")])
        email(BRAND + "-nov-34", "2026-11-27", "the sale")
        self.assertIsNone(S.the_slot(BRAND, BRAND + "-nov-34"))

    def test_an_email_with_no_record_is_found_by_its_number_as_before(self):
        write(MONTH / "slots.json", [slot("nov-09", "2026-11-09", "a guarantee")])
        self.assertEqual(S.the_slot(BRAND, BRAND + "-nov-09")["id"], "nov-09")


if __name__ == "__main__":
    try:
        unittest.main(verbosity=1)
    finally:
        shutil.rmtree(str(TMP), ignore_errors=True)
