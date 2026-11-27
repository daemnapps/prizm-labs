#!/usr/bin/env python3
"""LD-67 (design keeps segment): the design step keeps the send's segment when
it is pointed at a run whose folder name matches no calendar slot, and the
build never crashes on an empty segment — proven offline.

    python3 tools/email-production/test_ld67_design_segment.py

design/line.py and design/build.py are imported, never run (main() is not
called). PIL is stood in only when this interpreter has none (engine.py and
build.py import it; nothing here draws). No key, no network, no model call.
Stdlib only, 3.9.

  1  a run with copy-argv.json carrying --segment and --send-date → the
     fallback slot has that segment and date
  2  no copy-argv.json, or one that is not a JSON list → no segment key, no raise
  3  segments_of keeps only non-empty strings: [] for a missing segment, never [null]
  4  build.py's audience_of: [None] → "", names joined, an explicit audience wins
"""
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESIGN = HERE / "design"
try:
    import PIL  # noqa: F401
except ImportError:
    PIL = types.ModuleType("PIL")
    for _n in ("Image", "ImageDraw", "ImageFilter"):
        setattr(PIL, _n, types.ModuleType("PIL." + _n))
        sys.modules["PIL." + _n] = getattr(PIL, _n)
    sys.modules["PIL"] = PIL
sys.path.insert(0, str(DESIGN))    # design/ FIRST; never tools/email-production (its runner shadowed the stdlib's `email` until LD-49 (stdlib-name renames))
import line as LINE                # noqa: E402
import build as BUILD              # noqa: E402

ARGV = ["email_line.py", "/tmp/zz-send.md", "--brand", "brand-a", "--avatar", "zz-avatar", "--segment", "Core | Lead",
        "--label", "brand-a-nov-01-ab-a", "--send-date", "2026-11-01", "--type", "routine"]


class TestSlotFromRun(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.run = Path(os.path.realpath(t.name)) / "brand-a-nov-01-ab-a"
        self.run.mkdir()

    def test_1_segment_and_date_from_copy_argv(self):
        (self.run / "copy-argv.json").write_text(json.dumps(ARGV, indent=1))
        slot = LINE.slot_from_run(self.run, "nov-01-zz", "routine")
        self.assertEqual(slot["segment"], "Core | Lead")
        self.assertEqual(slot["date"], "2026-11-01")
        self.assertEqual((slot["id"], slot["type"], slot["kind"], slot["format"]), ("nov-01-zz", "routine", "design", None))
        self.assertEqual(LINE.segments_of(slot), ["Core | Lead"])

    def test_2_no_file_or_not_a_list(self):
        slot = LINE.slot_from_run(self.run, "nov-01-zz", "routine")
        self.assertNotIn("segment", slot)
        self.assertNotIn("date", slot)
        self.assertEqual(LINE.segments_of(slot), [])
        for body in ('{"--segment": "Core | Lead"}', "not json", '"--segment"'):
            (self.run / "copy-argv.json").write_text(body)
            slot = LINE.slot_from_run(self.run, "nov-01-zz", "routine")
            self.assertNotIn("segment", slot, body)
            self.assertNotIn("date", slot, body)

    def test_2b_flag_with_no_value(self):
        (self.run / "copy-argv.json").write_text(json.dumps(["email_line.py", "--send-date", "2026-11-01", "--segment"]))
        slot = LINE.slot_from_run(self.run, "nov-01-zz", "routine")
        self.assertNotIn("segment", slot)
        self.assertEqual(slot["date"], "2026-11-01")


class TestSegmentsOf(unittest.TestCase):
    def test_3_only_non_empty_strings(self):
        self.assertEqual(LINE.segments_of({"segment": None}), [])
        self.assertEqual(LINE.segments_of({}), [])
        self.assertEqual(LINE.segments_of({"segments": ["A", None, ""]}), ["A"])
        self.assertEqual(LINE.segments_of({"segment": "B"}), ["B"])
        self.assertEqual(LINE.segments_of({"segments": [], "segment": "B"}), ["B"])


class TestAudienceOf(unittest.TestCase):
    def test_4_build_audience(self):
        self.assertEqual(BUILD.audience_of({"segments": [None]}), "")
        self.assertEqual(BUILD.audience_of({"segments": ["A", "B"]}), "A, B")
        self.assertEqual(BUILD.audience_of({}), "")
        self.assertEqual(BUILD.audience_of({"segments": [None], "audience": "VIPs"}), "VIPs")


if __name__ == "__main__":
    unittest.main()
