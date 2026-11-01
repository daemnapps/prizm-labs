"""The final check asks each page once per batch, whatever its tracking tags, and asks a 429 again after the
store's wait (the team, 2026-10-27). No network: the request is replaced.

    /usr/bin/python3 test_link_check.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check  # noqa: E402

FLEX = "https://brand-a.com/products/flex?utm_source=klaviyo&utm_content=%s"


class LinkCheck(unittest.TestCase):
    def setUp(self):
        check.ANSWERS.clear()
        self.asked, self.waited = [], []
        self.real = check.ask

    def tearDown(self):
        check.ask = self.real

    def answers(self, *replies):
        replies = list(replies)
        def fake(url):
            self.asked.append(url)
            return replies.pop(0)
        check.ask = fake

    def test_tagged_links_to_one_page_are_asked_once(self):
        self.answers(("200", ""))
        for n in range(8):
            self.assertEqual(check.code(FLEX % n, wait=self.waited.append), "200")
        self.assertEqual(self.asked, ["https://brand-a.com/products/flex"])

    def test_a_429_is_asked_again_after_the_named_wait(self):
        self.answers(("429", "60"), ("200", ""))
        self.assertEqual(check.code(FLEX % 1, wait=self.waited.append), "200")
        self.assertEqual(self.waited, [60])
        self.assertEqual(len(self.asked), 2)

    def test_the_wait_is_capped(self):
        self.answers(("429", "3600"), ("200", ""))
        check.code(FLEX % 1, wait=self.waited.append)
        self.assertEqual(self.waited, [90])

    def test_a_429_that_never_clears_still_fails(self):
        self.answers(("429", ""), ("429", "30"), ("429", ""))
        self.assertEqual(check.code(FLEX % 1, wait=self.waited.append), "429")
        self.assertEqual(self.waited, [60, 30])
        self.assertEqual(len(self.asked), 3)

    def test_a_cloudflare_challenge_is_kept_out_and_not_retried(self):
        self.answers((check.CHALLENGE, ""))
        self.assertEqual(check.code(FLEX % 1, wait=self.waited.append), check.CHALLENGE)
        self.assertIn(check.CHALLENGE, check.KEPT_OUT)
        self.assertEqual((self.waited, len(self.asked)), ([], 1))

    def test_ask_reads_the_challenge_header(self):
        class R:
            stdout = ""
        def run(argv, **kw):
            R.stdout = self.reply
            return R
        real = check.subprocess.run
        check.subprocess.run = run
        try:
            self.reply = "403||challenge"
            self.assertEqual(check.ask("https://x.test/"), (check.CHALLENGE, ""))
            self.reply = "403||"                     # a 403 with no challenge is the store's own refusal: it holds
            self.assertEqual(check.ask("https://x.test/"), ("403", ""))
            self.reply = "429|60|"
            self.assertEqual(check.ask("https://x.test/"), ("429", "60"))
        finally:
            check.subprocess.run = real

    def test_a_dead_page_is_not_retried(self):
        self.answers(("404", ""))
        self.assertEqual(check.code("https://brand-a.com/products/gone", wait=self.waited.append), "404")
        self.assertEqual(self.waited, [])

    def test_different_pages_are_each_asked(self):
        self.answers(("200", ""), ("200", ""))
        check.code("https://brand-a.com/?utm_source=klaviyo", wait=self.waited.append)
        check.code(FLEX % 1, wait=self.waited.append)
        self.assertEqual(self.asked, ["https://brand-a.com/", "https://brand-a.com/products/flex"])
        self.assertEqual(self.waited, [check.PACE])


if __name__ == "__main__":
    unittest.main()
