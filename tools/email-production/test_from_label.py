#!/usr/bin/env python3
"""An email's own from-name (the team, 2026-10-30: brand-b nov-10 is a letter in the founder's first person, sent from
"Brand-B Trakoonsri from Brand-B Beauty"): create_draft() uses the email's `from_label` when it has one, the brand's
look `from.label` otherwise; build.py puts it on the approval card only when the email sets it; the approval page's
Approve passes the card's to the draft. No network: Klaviyo is a stand-in.

    /usr/bin/python3 tools/email-production/test_from_label.py
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import simple_email as S  # noqa: E402

LK = {"from": {"email": "hello@zz.test", "label": "ZZ Beauty"}}


def draft(email):
    sent = []

    def kl(method, path, key, payload=None, form=None):
        sent.append((path, payload))
        if path == "campaigns":
            return {"data": {"id": "c1", "relationships": {"campaign-messages": {"data": [{"id": "m1"}]}}}}
        return {"data": {"id": "t1"}}
    with mock.patch.object(S, "kl", kl):
        S.create_draft("key", "<html></html>", dict(email, subjects=[{"subject": "S", "preview": "P"}]), LK, "zz",
                       "zz-nov-10", {"date": "2026-11-11"}, ["Core"], ["seg1"], 0, None)
    camp = [p for path, p in sent if path == "campaigns"][0]
    return camp["data"]["attributes"]["campaign-messages"]["data"][0]["attributes"]["definition"]["content"]


class TestFromLabel(unittest.TestCase):
    def test_the_emails_own_from_name_wins(self):
        self.assertEqual(draft({"from_label": "Ann Lee from ZZ Beauty"})["from_label"], "Ann Lee from ZZ Beauty")
        self.assertEqual(draft({})["from_label"], "ZZ Beauty")
        self.assertEqual(draft({"from_label": "Ann"})["from_email"], "hello@zz.test", "the address never changes")

    def test_build_and_approve_carry_it(self):
        build = (HERE / "design" / "build.py").read_text()
        self.assertIn('card["from_label"] = spec["from_label"]', build)
        approve = (HERE / "approve_klaviyo.py").read_text()
        self.assertIn('"from_label": c.get("from_label")', approve)
        self.assertIn("<dt>From</dt>", approve, "the approval page shows the email's own from-name")


if __name__ == "__main__":
    unittest.main(verbosity=2)
