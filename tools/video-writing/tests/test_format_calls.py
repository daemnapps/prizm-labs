"""the owner's format call releases a held run, whatever shape it was saved in (2026-10-19).

Outlier's Swipes tab saves a call under the BARE format name ("xyz"); the teardown looked for
"format:new:xyz", the batch runner for "new:xyz", and writing v2 for a {format, call} row nobody
writes — so a call made on Outlier never released a held run. One reader now: layers.call_for.
No network, no spend.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TD = HERE.parents[1] / "video-teardown" / "machine"
sys.path.insert(0, str(HERE.parent / "machine"))
sys.path.insert(0, str(TD))
import layers as L        # noqa: E402
import writing_v2 as W    # noqa: E402


class CallsReleaseRuns(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.prev = L.TEARDOWN_RUNS
        L.TEARDOWN_RUNS = Path(self.tmp.name)
        (L.TEARDOWN_RUNS / "format-calls.json").write_text(json.dumps(
            {"podcast-clip": {"decision": "own", "into": "", "note": ""},     # exactly what Outlier writes
             "street-quiz": {"decision": "fold", "into": "expert-consult", "note": ""},
             "slideshow-thing": {"decision": "drop", "into": "", "note": ""}}))

    def tearDown(self):
        L.TEARDOWN_RUNS = self.prev
        self.tmp.cleanup()

    def test_every_shape_finds_the_call(self):
        for name in ("podcast-clip", "new:podcast-clip", "format:new:podcast-clip"):
            self.assertEqual((L.call_for(name) or {}).get("decision"), "own", name)
        self.assertIsNone(L.call_for("new:never-called"))

    def test_the_teardown_no_longer_waits_once_called(self):
        self.assertEqual(L.pending({"format": "new:podcast-clip"}, "k"), [])
        self.assertEqual(L.pending({"format": "new:never-called"}, "k"), ["format:new:never-called"])

    def test_writing_v2_is_released_by_the_call(self):
        called = {"layers": {"format": "new:podcast-clip"}, "layers_pending": ["format:new:podcast-clip"]}
        self.assertTrue(W.format_approved(called))
        waiting = {"layers": {"format": "new:never-called"}, "layers_pending": ["format:new:never-called"]}
        self.assertFalse(W.format_approved(waiting))
        self.assertTrue(W.format_approved({"format_id": "expert-consult"}))


    def test_same_as_x_writes_it_as_x_and_not_a_format_drops_it(self):
        with tempfile.TemporaryDirectory() as t:
            st = W.apply_call(t, {"layers": {"format": "new:street-quiz"}, "layers_pending": ["format:new:street-quiz"]})
            self.assertEqual((st["layers"]["format"], st["format_id"], st["layers_pending"]),
                             ("expert-consult", "expert-consult", []))
            st = W.apply_call(t, {"layers": {"format": "new:slideshow-thing"}})
            self.assertIsNone(st["layers"]["format"])
            self.assertTrue(W.format_approved(st))
            st = W.apply_call(t, {"layers": {"format": "new:podcast-clip"}})
            self.assertEqual(st["layers"]["format"], "new:podcast-clip")
            self.assertTrue(W.format_approved(st))


if __name__ == "__main__":
    unittest.main()
