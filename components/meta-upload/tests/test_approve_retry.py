#!/usr/bin/env python3
"""The approve page's upload queue: a card whose pictures the Drive is still moving, and Meta's request limit, wait and
go back on the queue by themselves; only after the last try is the card "didn't go in". No Meta, no Drive, no timer."""
import errno, http.client, os, socket, ssl, sys, tempfile, unittest, urllib.error
from pathlib import Path
from unittest import mock

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

    def test_a_lost_connection_is_told_from_metas_answer(self):
        for e in (urllib.error.URLError(OSError(errno.EHOSTUNREACH, "No route to host")),    # the two of 25 Nov 2026
                  TimeoutError("The read operation timed out"),
                  urllib.error.URLError(socket.gaierror(8, "nodename nor servname provided")),
                  ConnectionResetError(), http.client.RemoteDisconnected("closed"), ssl.SSLEOFError()):
            self.assertTrue(A.lost_connection(e), repr(e))
        for e in (urllib.error.HTTPError("u", 400, "bad", {}, None), FileNotFoundError("x.png"), KeyError("media"),
                  urllib.error.URLError(ssl.SSLCertVerificationError()), ValueError("x")):
            self.assertFalse(A.lost_connection(e), repr(e))

    def send(self, upload=None, online=True, passed=True, card=None):
        """upload_one on a stand-in card; returns the job."""
        with mock.patch.multiple(A, _approved_folder=lambda n: Path("/x") / n, score_diversity=mock.Mock(),
                                 online=lambda: online, meta_for=lambda b: None,
                                 run_upload=mock.Mock(side_effect=upload),
                                 _remember=lambda f, c, state, **k: A._job(f.name, state=state, **k)), \
                mock.patch.multiple(A.C, load=lambda f: {}, where=lambda f: {"brand": "b"}, passed=lambda c: passed,
                                    check_and_save=lambda *a, **k: card or {"checks": {}}):
            A.upload_one("card-n")
            self.calls = A.score_diversity.call_count, A.run_upload.call_count
        return A.JOBS["card-n"]

    def test_no_internet_waits_before_anything_is_read_or_sent(self):
        self.assertEqual(self.send(online=False)["state"], "waiting")
        self.assertEqual(self.calls, (0, 0))
        self.assertEqual(self.put, [(A.RETRY["offline"][0], ("card-n",))])

    def test_a_drop_mid_send_waits_then_gives_up_after_its_tries(self):
        for _ in range(A.RETRY["network"][1]):
            self.assertEqual(self.send(upload=TimeoutError("timed out"))["state"], "waiting")
        self.assertEqual(self.send(upload=TimeoutError("timed out"))["state"], "failed")

    def test_the_resend_goes_live(self):
        self.send(upload=urllib.error.URLError(OSError(errno.EHOSTUNREACH, "No route to host")))
        j = self.send(upload=lambda f: {"ok": True, "id": "x", "meta": [{}]})
        self.assertEqual((j["state"], j["ads"], j["error"]), ("live", 1, ""))

    def test_a_refusal_or_a_bug_still_fails_at_once(self):
        self.assertEqual(self.send(upload=lambda f: {"ok": False, "error": "Meta 400: Invalid parameter"})["state"], "failed")
        A.JOBS.clear()
        self.assertEqual(self.send(upload=KeyError("media"))["state"], "failed")
        A.JOBS.clear()
        bad = {"checks": {"words": {"ok": False, "why": "no headline"}}}
        self.assertEqual(self.send(passed=False, card=bad)["state"], "failed")
        self.assertEqual(self.put, [])


if __name__ == "__main__":
    unittest.main()
