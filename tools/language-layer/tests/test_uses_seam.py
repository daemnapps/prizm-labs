#!/usr/bin/env python3
"""The public uses seam — `engine.uses` is public, `_uses` stays as its alias
(SI-102 (public uses seam), language-layer#9 (public uses seam)).

    python3 -m unittest discover -s tests          # from tools/language-layer
    python3 tools/language-layer/tests/test_uses_seam.py
"""
import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from language_layer import engine as E  # noqa: E402


class UsesSeam(unittest.TestCase):
    def test_single_tag_is_a_list(self):
        self.assertEqual(E.uses({"use": "a"}), ["a"])

    def test_list_drops_blanks(self):
        self.assertEqual(E.uses({"use": ["a", None, "b"]}), ["a", "b"])

    def test_no_tag_is_empty(self):
        self.assertEqual(E.uses({}), [])

    def test_old_name_is_an_alias(self):
        self.assertIs(E._uses, E.uses)


if __name__ == "__main__":
    unittest.main()
