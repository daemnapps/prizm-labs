#!/usr/bin/env python3
"""Wan 3.0 reference mode is told the house prompt in its own terms (Image 1, Video 1, the cuts as shots).

    python3 components/video-studio/test_wan_words.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import take as T  # noqa: E402


class WanWords(unittest.TestCase):
    def test_media_named_by_position_and_cuts_listed(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "motion").mkdir()
            (Path(d) / "motion" / "ref.json").write_text(json.dumps({"cuts": [1.543, 4.63]}))
            take = {"script": [{"speaker": "A", "say": "x", "lips": "off"}], "motion": {"scene": d},
                    "cast": {"A": {"sheet": "a.jpg"}, "B": {"sheet": "b.jpg"}}}
            text = T.wan_words(T.prompt(take, [], True), take, True)
        # reference mode: no frame travels with references, so Image 1 is never called the first or opening frame
        self.assertIn("Image 1 is the scene's start picture", text)
        self.assertIn("it is a reference, not a frame of the video", text)
        self.assertNotIn("opening frame", text)
        self.assertNotIn("first frame", text)
        self.assertNotIn("starts exactly on it", text)
        self.assertIn("Image 2 is A", text)
        self.assertIn("Image 3 is B", text)
        self.assertIn("Video 1 is a motion guide", text)
        self.assertIn("shot 2 from 1.54 s", text)
        self.assertNotIn("reference picture", text)
        self.assertNotIn("motion reference", text)

    def test_the_product_picture_follows_the_sheets(self):
        with tempfile.TemporaryDirectory() as d:
            pic = Path(d) / "products" / "scrub" / "picture.png"
            pic.parent.mkdir(parents=True)
            pic.write_bytes(b"p")
            (Path(d) / "motion").mkdir()
            (Path(d) / "motion" / "first-frame.json").write_text(json.dumps({"product": "scrub", "references": [str(pic)]}))
            take = {"script": [{"speaker": "A", "say": "x", "lips": "off"}], "motion": {"scene": d},
                    "cast": {"A": {"sheet": "a.jpg"}}}
            self.assertEqual(T.product_of(take)["picture"], str(pic))
            text = T.wan_words(T.prompt(take, [], True), take, True)
        self.assertIn("Image 3 is the product, scrub", text)


if __name__ == "__main__":
    unittest.main()
