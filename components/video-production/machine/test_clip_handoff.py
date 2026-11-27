"""The clip step always hands its clips to the edit (2026-10-19).

The 0312 production run made 25 clips and none reached the edit kit, so the edit had nothing to cut:
clip_publish never ran on it. This proves through the seam that a finished clip step calls it —
fakes only, no network, no money.

    /usr/bin/python3 -m unittest test_clip_handoff      (from machine/)
"""
import io
import json
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import clips_run as oc

TOTALS = {"clip_seconds": 0, "clip_usd": 0.0, "upscale_seconds": 0, "upscale_usd": 0.0, "spend_usd": 0.0,
          "voice_swaps": 0, "talking_calls": 0, "tts_lines": 0, "tts_chars": 0}


class ClipStepHandsOff(unittest.TestCase):
    def run_step(self, publish):
        orig = oc._load

        def fake(name):
            if name == "clip_publish":
                return types.SimpleNamespace(publish=publish)
            if name == "sound_map":
                return types.SimpleNamespace(main=lambda argv: 0)
            return orig(name)

        oc._load = fake
        try:
            with tempfile.TemporaryDirectory() as t:
                run = Path(t) / "run"
                (run / "clips").mkdir(parents=True)
                (run / "clips" / "plan.json").write_text(json.dumps(
                    {"route": "seedance", "calls": [], "tts": [], "totals": TOTALS}))
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    rc = oc.run_live(run, yes=True, make=lambda *a: None, tts=lambda *a: None,
                                     refs=lambda *a: None, gate=lambda *a: [])
                return rc, run, out.getvalue(), err.getvalue()
        finally:
            oc._load = orig

    def test_a_finished_clip_step_publishes_to_the_edit(self):
        seen = []
        rc, run, out, _ = self.run_step(lambda r: seen.append(Path(r)) or {"published": ["S1"], "held": []})
        self.assertEqual(seen, [run])
        self.assertIn("edit hand-off: 1 scene(s)", out)

    def test_a_failed_hand_off_is_said_out_loud(self):
        def boom(r):
            raise RuntimeError("no ledger")
        _, _, _, err = self.run_step(boom)
        self.assertIn("clips not handed to the edit", err)


if __name__ == "__main__":
    unittest.main()
