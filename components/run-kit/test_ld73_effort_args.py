#!/usr/bin/env python3
"""python3 test_ld73_effort_args.py — LD-73 (explicit effort): every chain's `claude -p` names
its effort from one place, fixed at "medium" with no environment knob (the team, 2026-10-21).
Stdlib unittest, no network, no model call."""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_kit import claude_flags   # noqa: E402
from run_kit.claude_flags import effort_args   # noqa: E402


class EffortArgs(unittest.TestCase):
    def setUp(self):
        self.prev = os.environ.pop("CHAIN_EFFORT", None)

    def tearDown(self):
        os.environ.pop("CHAIN_EFFORT", None)
        if self.prev is not None:
            os.environ["CHAIN_EFFORT"] = self.prev

    def test_is_medium(self):
        self.assertEqual(effort_args(), ["--effort", "medium"])
        self.assertEqual(claude_flags.effort(), "medium")

    def test_no_environment_knob(self):
        for level in ("low", "high", "xhigh", "max", "turbo"):
            os.environ["CHAIN_EFFORT"] = level
            self.assertEqual(effort_args(), ["--effort", "medium"], level)

    def test_public_surface(self):
        import run_kit
        self.assertIs(run_kit.claude_flags, claude_flags)
        self.assertEqual(claude_flags.EFFORT, "medium")

    def test_model_call_passes_it(self):
        # run_kit.model's default runner builds its argv with the flag; seen through a fake subprocess.run
        from run_kit import model
        seen = []

        class Done:
            returncode, stdout, stderr = 0, "a plain answer", ""

        real, hand = model.subprocess.run, os.environ.pop("DAEMN_HAND_DIR", None)
        model.subprocess.run = lambda argv, **kw: seen.append(argv) or Done()
        try:
            model.call("prompt", "claude-sonnet-5", label="t", tries=1)
        finally:
            model.subprocess.run = real
            if hand is not None:
                os.environ["DAEMN_HAND_DIR"] = hand
        argv = seen[0]
        self.assertEqual(argv[argv.index("--effort") + 1], "medium")
        self.assertEqual(argv.count("--effort"), 1)


if __name__ == "__main__":
    unittest.main()
