#!/usr/bin/env python3
"""The email line's language pull (the owner, 2026-10-27: "awareness levels and verbatims and spice are the foundation of
what we're doing here"): every stage asks for the declared avatar's rows at the awareness level triage names, the
subject lines get the spice, the expansion gets the week's live read, and an empty pull is said out loud.
No model, no network.

    python3 test_language_awareness.py
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import email_line as E   # noqa: E402

SRC = (HERE / "email_line.py").read_text()


class Awareness(unittest.TestCase):
    def test_triage_level_is_read_in_every_shape_triage_prints_it(self):
        for line, want in (('AWARENESS: `product-aware` — Must NOT: "Reintroduce…"', "product-aware"),
                           ("**AWARENESS:** problem-aware", "problem-aware"),
                           ("AWARENESS: Unaware", "Unaware")):
            self.assertEqual(E._first(E.AWARENESS_LINE, "LANE: ORGANIC\n" + line + "\n"), want, line)
        self.assertIsNone(E._first(E.AWARENESS_LINE, "AWARENESS: [UNCLEAR: which]"))

    def test_the_pull_passes_the_level_and_says_an_empty_result(self):
        body = SRC[SRC.index("    def lang(stage):"):SRC.index("# THE DRY RUN COMES BEFORE ANY STAGE")]
        self.assertIn('used="fresh", awareness=aw', body)
        self.assertIn("no rows matched", body)
        self.assertIn("print(", body)
        # set from triage, after triage, before any writing stage pulls
        at = SRC.index("aw = (_first(AWARENESS_LINE, triage)")
        self.assertLess(SRC.index('triage = run_stage("stage0"'), at)
        self.assertLess(at, SRC.index('injection = run_stage("stage3"'))

    def test_subjects_get_spice_and_expansion_gets_the_week(self):
        call = SRC[SRC.index('subject_set = run_stage("stage5"'):]
        self.assertIn('spice_bank=lang("spice")', call[:call.index("save()")])
        call = SRC[SRC.index('body = run_stage("stage6"'):]
        self.assertIn("live_read=live_read", call[:call.index("save()")])
        self.assertIn("{spice_bank}", E.latest_prompt("stage5").read_text())
        self.assertIn("{live_read}", E.latest_prompt("stage6").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
