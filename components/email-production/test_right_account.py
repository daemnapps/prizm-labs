#!/usr/bin/env python3
"""The right-account check: a brand's Klaviyo key must open that brand's own account (the team, 2026-10-22).

    python3 test_right_account.py

No network: simple_email.kl is replaced. The brand's From domain (simple.json from.email) must match the
account's website or default sender; otherwise nothing goes to Klaviyo.
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import simple_email as S  # noqa: E402

LOOK = {"klaviyo_key": "KLAVIYO_TEST_KEY", "from": {"email": "support@brand-a.test"}}


def account(website, sender=""):
    return lambda m, p, k, *a, **kw: {"data": [{"attributes": {"contact_information": {
        "organization_name": "Some LLC", "website_url": website, "default_sender_email": sender}}}]}


class RightAccount(unittest.TestCase):
    def setUp(self):
        S._ACCOUNTS_OK.clear()

    def test_own_account_passes(self):
        with mock.patch.object(S, "kl", account("http://www.brand-a.test")):
            S.right_account("k1", LOOK)

    def test_sender_domain_alone_passes(self):
        with mock.patch.object(S, "kl", account("", "hello@brand-a.test")):
            S.right_account("k2", LOOK)

    def test_other_brands_account_is_refused(self):
        with mock.patch.object(S, "kl", account("https://brand-b.test", "x@brand-b.test")):
            with self.assertRaises(SystemExit) as cm:
                S.right_account("k3", LOOK)
        self.assertIn("REFUSED", str(cm.exception.code))
        self.assertIn("brand-b.test", str(cm.exception.code))
        self.assertIn("Nothing went to Klaviyo", str(cm.exception.code))

    def test_no_from_address_is_refused(self):
        with mock.patch.object(S, "kl", account("https://brand-a.test")):
            with self.assertRaises(SystemExit):
                S.right_account("k4", {"klaviyo_key": "X"})

    def test_checked_once_per_key(self):
        calls = []
        def kl(*a, **kw):
            calls.append(a)
            return account("https://brand-a.test")(*a)
        with mock.patch.object(S, "kl", kl):
            S.right_account("k5", LOOK)
            S.right_account("k5", LOOK)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
