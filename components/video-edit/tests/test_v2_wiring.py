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


    def test_unchecked_review_is_retried_then_holds(self):
        """Owner ruling 2026-11-20: retry then fail loudly — an UNCHECKED review runs once more, then holds the version."""
        import types
        from unittest import mock
        calls = []

        def after_stage(*a, **k):
            calls.append(1)
            return {"line1": {"ok": None, "severity": "UNCHECKED", "problems": ["no key"]}}
        fake = types.SimpleNamespace(review=types.SimpleNamespace(_door=lambda: None, after_stage=after_stage))
        sheet = {"picture": [], "overlays": [], "captions": {"words": []}}
        with tempfile.TemporaryDirectory() as t, mock.patch.dict(sys.modules, {"marketing_chain_checks": fake}), \
                mock.patch.object(v2, "sh"), mock.patch.object(v2, "brief_of", return_value=None), \
                mock.patch.object(v2.CS, "probe_seconds", return_value=5.0), \
                mock.patch.object(v2, "caption_lines", return_value=[]):
            got = v2.review("control", Path(t) / "v.mp4", sheet, Path(t), Path(t) / "qc" / "control")
        self.assertEqual(len(calls), 2)
        self.assertTrue(got["held"])
        self.assertEqual(got["unchecked"], ["line1"])

if __name__ == "__main__":
    unittest.main()
