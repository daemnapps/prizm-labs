#!/usr/bin/env python3
"""The approve page's upload queue: a card whose pictures the Drive is still moving, and Meta's request limit, wait and
go back on the queue by themselves; only after the last try is the card "didn't go in". No Meta, no Drive, no timer."""
import os, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
os.environ.setdefault("META_CARDS_ROOT", tempfile.mkdtemp())
import approve as A  # noqa: E402

# the error Meta returned on 25 Oct 2026 for brief 0216, as the page kept it
LIMIT = ('Meta 400: {"error":{"message":"User request limit reached","type":"OAuthException","is_transient":false,'
         '"code":17,"error_subcode":2446079,"error_user_title":"Ad account has too many API calls"}}')


class Retry(unittest.TestCase):
    def setUp(self):
        self.put = []
        self._timer = A.threading.Timer
        A.threading.Timer = lambda wait, fn, args=(): type("T", (), {"start": lambda s: self.put.append((wait, args))})()
        A.JOBS.clear()

    def tearDown(self):
        A.threading.Timer = self._timer

    def test_metas_request_limit_is_a_wait_not_a_failure(self):
        self.assertTrue(A.META_LIMIT.search(LIMIT))
        self.assertTrue(A.retry_later("card-a", "limit"))
        self.assertEqual(A.JOBS["card-a"]["state"], "waiting")
        self.assertEqual(self.put, [(A.RETRY["limit"][0], ("card-a",))])

    def test_a_real_refusal_is_not_mistaken_for_the_limit(self):
        self.assertFalse(A.META_LIMIT.search('Meta 400: {"error":{"message":"Invalid parameter","code":100}}'))

    def test_pictures_still_moving_retry_and_then_stop(self):
        card = {"checks": {"media": {"ok": False, "why": "missing: x_asset-03.png"}, "words": {"ok": True, "why": ""}}}
        self.assertTrue(A.only_missing_media(card))
        for _ in range(A.RETRY["media"][1]):
            self.assertTrue(A.retry_later("card-b", "media"))
        self.assertFalse(A.retry_later("card-b", "media"))       # out of tries: the caller marks it didn't go in

    def test_another_failing_check_is_not_a_wait(self):
        card = {"checks": {"media": {"ok": False, "why": "missing: x.png"}, "words": {"ok": False, "why": "no headline"}}}
        self.assertFalse(A.only_missing_media(card))


if __name__ == "__main__":
    unittest.main()
