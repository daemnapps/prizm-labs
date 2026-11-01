"""the team's missing list holds only pictures; words, prices and promises go to the team (the team, 2026-10-28).

    /usr/bin/python3 test_gap_split.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync  # noqa: E402


class GapSplit(unittest.TestCase):
    def test_pictures_to_eve_the_rest_to_steph(self):
        G = [{"kind": "picture", "why": "picture not made yet"}, {"kind": "product picture", "why": "cut out"},
             {"kind": "words", "type": "promise", "why": "a promise is missing"}, {"kind": "price", "why": "no price"}]
        eve, steph = sync.split_gaps(G)
        self.assertEqual([g["kind"] for g in eve], ["picture", "product picture"])
        self.assertEqual([g["kind"] for g in steph], ["words", "price"])


if __name__ == "__main__":
    unittest.main()
