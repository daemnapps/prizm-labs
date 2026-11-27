"""The team page lists a wireframe (design/wireframe/card.json) until a real build, newer than design/email.json, replaces it.

    /usr/bin/python3 test_wireframe_page.py
"""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent))
sys.path.append(str(HERE.parent / "design"))
sys.path.insert(0, str(HERE.parent.parent / "run-kit"))
import sync  # noqa: E402


def touch(p, text="x", at=None):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    if at:
        os.utime(p, (at, at))


class WireframePage(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.runs = Path(self.t.name)
        self._old = sync.RUNS
        sync.RUNS = self.runs
        self.run = self.runs / "b" / "b-nov-01"

    def tearDown(self):
        sync.RUNS = self._old
        self.t.cleanup()

    def test_a_wireframe_with_no_built_email_is_listed(self):
        touch(self.run / "design" / "wireframe" / "card.json", "{}")
        touch(self.run / "design" / "email.json", "{}")
        self.assertEqual(sync._cards("b"), [self.run / "design" / "wireframe" / "card.json"])

    def test_a_new_layout_newer_than_the_built_email_shows_the_wireframe(self):
        now = time.time()
        touch(self.run / "klaviyo" / "card.json", "{}", now - 300)
        touch(self.run / "klaviyo" / "email.html", "x", now - 200)
        touch(self.run / "design" / "email.json", "{}", now - 100)
        touch(self.run / "design" / "wireframe" / "card.json", "{}", now - 90)
        self.assertEqual(sync._cards("b"), [self.run / "design" / "wireframe" / "card.json"])

    def test_a_real_build_newer_than_the_layout_replaces_the_wireframe(self):
        now = time.time()
        touch(self.run / "design" / "email.json", "{}", now - 300)
        touch(self.run / "design" / "wireframe" / "card.json", "{}", now - 290)
        touch(self.run / "klaviyo" / "card.json", "{}", now - 10)
        touch(self.run / "klaviyo" / "email.html", "x", now - 10)
        self.assertEqual(sync._cards("b"), [self.run / "klaviyo" / "card.json"])

    def test_an_email_with_no_wireframe_is_as_before(self):
        touch(self.run / "klaviyo" / "card.json", "{}")
        self.assertEqual(sync._cards("b"), [self.run / "klaviyo" / "card.json"])


if __name__ == "__main__":
    unittest.main()
