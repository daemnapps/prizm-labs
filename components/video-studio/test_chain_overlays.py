#!/usr/bin/env python3
"""The brief's editor text and arrows on a chain-made scene (2026-11-21, brief-0380: the close's "Tap below to buy." and
its arrow never reached the cut): each lands on its words in a HyperFrames card the Studio renders. Nothing is called.

    python3 components/video-studio/test_chain_overlays.py
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_shots as A  # noqa: E402

WORDS = [{"w": "60-Day", "start": 1.8, "end": 2.4}, {"w": "Money", "start": 2.4, "end": 2.8},
         {"w": "Back.", "start": 2.8, "end": 3.1}, {"w": "Tap", "start": 7.7, "end": 8.0},
         {"w": "below", "start": 8.0, "end": 8.4}, {"w": "to", "start": 8.4, "end": 8.6}, {"w": "buy.", "start": 8.6, "end": 9.0}]


class Overlays(unittest.TestCase):
    def test_words_land_even_when_hyphenated(self):
        self.assertEqual(A.land_at(WORDS, "60-Day Money Back."), 1.8)
        self.assertEqual(A.land_at(WORDS, "Tap below to buy."), 7.7)
        self.assertIsNone(A.land_at(WORDS, "never said"))

    def test_the_card_carries_each_text_and_the_arrow_on_its_second(self):
        proj = Path(tempfile.mkdtemp()) / "card"
        marks = [{"kind": "text", "text": "60-Day Money Back", "where": "Centered", "t": 1.8},
                 {"kind": "text", "text": "Tap below to buy", "where": "Centered with downward arrow", "t": 7.7},
                 {"kind": "arrow", "text": "", "where": "Below", "t": 7.7}]
        A.overlay_card(proj, marks, 11.0, "t-card")
        page = (proj / "index.template.html").read_text()
        for s in ("60-Day Money Back", "Tap below to buy", "&#8595;", "{{DUR}}", "assets/bg.mp4", '"t-card"'):
            self.assertIn(s, page)
        self.assertIn("},1.800);", page)
        self.assertIn('tl.to("#g0",{opacity:0,duration:.08},7.620);', page)      # the first offer clears before the ask
        self.assertTrue((proj / "assets").is_dir())


if __name__ == "__main__":
    unittest.main()
