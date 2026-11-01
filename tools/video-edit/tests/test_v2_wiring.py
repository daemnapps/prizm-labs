"""v2.py wiring (2026-10-20): the control cut sheet carries the name the timeline page reads, and the review
step survives a sheet whose `elements` is a plain true/false."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import v2  # noqa: E402


class V2Wiring(unittest.TestCase):
    def test_latest_cutsheet_is_the_highest_version(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            self.assertIsNone(v2.latest_cutsheet(r))
            (r / "cutsheet-control.json").write_text("{}")      # the old name is not a version
            self.assertIsNone(v2.latest_cutsheet(r))
            for n in (1, 2, 10):
                (r / f"cutsheet-v{n}.json").write_text("{}")
            self.assertEqual(v2.latest_cutsheet(r).name, "cutsheet-v10.json")

    def test_boolean_elements_do_not_crash(self):
        sheet = {"elements": True, "overlays": [{"kind": "end card", "text": "Buy"}], "picture": []}
        self.assertEqual(v2.end_card(sheet)["text"], "Buy")
        self.assertEqual(v2._element_rows({"elements": True}), [])
        self.assertEqual(v2._element_rows({"elements": [{"start": 1}]}), [{"start": 1}])
        self.assertEqual([k for k, _ in v2._timed_items({"elements": True})], [])


if __name__ == "__main__":
    unittest.main()
