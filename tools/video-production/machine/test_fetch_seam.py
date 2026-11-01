#!/usr/bin/env python3
"""The fetch seam (SI-101 (public fetch seam), video-production#3 (private
image-production call)): image-production's `context.fetched` is public,
`context._fetched` stays as an alias to it, and `brandfiles._fetched` reaches
it by the public name. No network: a non-URL returns before any fetch, and
the brandfiles call runs against a stub.
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import brandfiles  # noqa: E402

# found the way brandfiles.py finds image_production
WS = brandfiles._workspace()
IP = WS / "tools" / "image-production"
if str(IP) not in sys.path:
    sys.path.insert(0, str(IP))

from image_production import context  # noqa: E402


class FetchSeam(unittest.TestCase):
    def test_the_old_private_name_is_the_public_function(self):
        self.assertIs(context._fetched, context.fetched)

    def test_a_non_url_is_refused_before_any_fetch(self):
        self.assertEqual(context.fetched("acme", "k", "not-a-url"), (None, "not a url"))

    def test_brandfiles_calls_the_public_name(self):
        with mock.patch.object(context, "fetched", return_value=("x", None)) as stub:
            got = brandfiles._fetched("acme", "k", "https://example.com/p.jpg")
        self.assertEqual(got, ("x", None))
        stub.assert_called_once_with("acme", "k", "https://example.com/p.jpg")


if __name__ == "__main__":
    unittest.main()
