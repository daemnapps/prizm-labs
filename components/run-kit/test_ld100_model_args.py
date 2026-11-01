#!/usr/bin/env python3
"""python3 test_ld100_model_args.py — LD-100 (chain model explicit): every chain's `claude -p`
names its model, the way LD-73 (explicit effort) made it name its effort. A fake `claude` on
PATH records the argv the door sends. Stdlib unittest, no network, no model call."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_kit import claude_door, claude_flags   # noqa: E402

KEYS = ("CHAIN_MODEL", "DAEMN_HAND_DIR", "HAND_DIR", "DAEMN_HAND_FIRST", "PATH")


class Base(unittest.TestCase):
    def setUp(self):
        self.prev = {k: os.environ.get(k) for k in KEYS}
        for k in KEYS[:-1]:
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self.prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class ModelArgs(Base):
    def test_default_is_the_registry_entry(self):
        self.assertEqual(claude_flags.MODEL, "claude-opus-5-5")
        self.assertIn(claude_flags.MODEL, claude_flags._registry_ids())
        self.assertEqual(claude_flags.model_args(), ["--model", "claude-opus-5-5"])

    def test_listed_override_is_honoured(self):
        os.environ["CHAIN_MODEL"] = "claude-sonnet-5-5"
        self.assertEqual(claude_flags.model_args(), ["--model", "claude-sonnet-5-5"])

    def test_unlisted_override_falls_back(self):
        for bad in ("sonnet", "claude-opus-9", "claude-opus-5-5; rm -rf /", ""):
            os.environ["CHAIN_MODEL"] = bad
            self.assertEqual(claude_flags.model_args(), ["--model", "claude-opus-5-5"], bad)

    def test_read_at_call_time(self):
        self.assertEqual(claude_flags.model(), "claude-opus-5-5")
        os.environ["CHAIN_MODEL"] = "claude-haiku-4-5"
        self.assertEqual(claude_flags.model(), "claude-haiku-4-5")

    def test_effort_untouched(self):
        self.assertEqual(claude_flags.effort_args(), ["--effort", "medium"])


class DoorAddsModel(Base):
    """The door with a fake `claude` first on PATH; the fake writes its argv, one per line."""

    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.seen = d / "argv.txt"
        fake = d / "claude"
        fake.write_text("#!/bin/sh\nprintf '%%s\\n' \"$@\" > '%s'\necho a plain answer\n" % self.seen)
        fake.chmod(0o755)
        os.environ["PATH"] = str(d) + os.pathsep + (self.prev["PATH"] or "")

    def tearDown(self):
        self.tmp.cleanup()
        super().tearDown()

    def argv(self, args):
        r = claude_door.run(args, "prompt", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return self.seen.read_text().splitlines()

    def test_no_model_gets_the_default(self):
        argv = self.argv(["--output-format", "text"])
        self.assertEqual(argv[0], "-p")
        self.assertEqual(argv.count("--model"), 1)
        self.assertEqual(argv[argv.index("--model") + 1], "claude-opus-5-5")
        self.assertEqual(argv[argv.index("--effort") + 1], "medium")

    def test_named_model_kept(self):
        argv = self.argv(["--model", "claude-sonnet-5", "--output-format", "text"])
        self.assertEqual(argv.count("--model"), 1)
        self.assertEqual(argv[argv.index("--model") + 1], "claude-sonnet-5")

    def test_unlisted_chain_model_falls_back_in_the_door(self):
        os.environ["CHAIN_MODEL"] = "not-a-registry-model"
        argv = self.argv(["--output-format", "text"])
        self.assertEqual(argv[argv.index("--model") + 1], "claude-opus-5-5")

    def test_listed_chain_model_reaches_the_door(self):
        os.environ["CHAIN_MODEL"] = "claude-sonnet-5-5"
        argv = self.argv(["--output-format", "text"])
        self.assertEqual(argv[argv.index("--model") + 1], "claude-sonnet-5-5")


if __name__ == "__main__":
    unittest.main()
