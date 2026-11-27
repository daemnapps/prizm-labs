"""editor's missing list holds only pictures; words, prices and promises go to email_lead (email_lead, 2026-10-28).

    /usr/bin/python3 test_gap_split.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync  # noqa: E402


class GapSplit(unittest.TestCase):
    def test_pictures_to_editor_the_rest_to_email_lead(self):
        G = [{"kind": "picture", "why": "picture not made yet"}, {"kind": "product picture", "why": "cut out"},
             {"kind": "words", "type": "promise", "why": "a promise is missing"}, {"kind": "price", "why": "no price"}]
        editor, email_lead = sync.split_gaps(G)
        self.assertEqual([g["kind"] for g in editor], ["picture", "product picture"])
        self.assertEqual([g["kind"] for g in email_lead], ["words", "price"])


if __name__ == "__main__":
    unittest.main()
