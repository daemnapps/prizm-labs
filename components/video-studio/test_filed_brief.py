#!/usr/bin/env python3
"""A production whose own record never got its brief number finds it in the brand's brief list (12 Nov 2026).

    python3 components/video-studio/test_filed_brief.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_studio as V  # noqa: E402


class FiledBrief(unittest.TestCase):
    def test_the_lowest_brief_naming_the_run_wins(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "brands" / "acme" / "briefs" / "briefs.json"
            f.parent.mkdir(parents=True)
            f.write_text(json.dumps({"briefs": [
                {"brief": "brief-0368", "product": "scrub", "aliases": ["idea-11-B", "run-x"]},
                {"brief": "brief-0367", "product": "scrub", "aliases": ["idea-11-A", "run-x"]},
                {"brief": "brief-0100", "product": "scrub", "aliases": ["other"]}]}))
            with mock.patch.object(V, "_ws", return_value=Path(d)):
                self.assertEqual(V.filed_brief({"brief": "run-x", "brand": "acme"}, "idea-11"), "acme_scrub_brief-0367")
                self.assertIsNone(V.filed_brief({"brief": "run-y", "brand": "acme"}, "idea-99"))


if __name__ == "__main__":
    unittest.main()
