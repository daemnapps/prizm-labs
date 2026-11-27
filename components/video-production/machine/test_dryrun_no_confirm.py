#!/usr/bin/env python3
"""python3 machine/test_dryrun_no_confirm.py — from any cwd. Stdlib unittest only.

LD-6 (dry run never confirms): a dry run on a provider whose `confirm` is
true reports the spend gate and goes on; it never calls platform.confirm.
A live run still asks, and a decline still returns 1."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"test_ld6_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


run = load("run")

# the provider the test drives must carry confirm: true, read from the
# registry itself rather than assumed
CONFIRM_PROVIDER = "higgsfield-ui"


class NotATerminal(io.StringIO):
    def isatty(self):
        return False


def no_voice_network(method, url, body, headers):
    # a live run voices its lines before the confirm gate; this stands in for
    # the voice door so no test ever reaches the network
    return f"FAKE-AUDIO:{body['text']}".encode()


class DryRunNeverConfirms(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-ld6-"))
        self.calls = []
        self.saved_confirm = run.platform.confirm
        self.saved_stdin = sys.stdin
        sys.stdin = NotATerminal("")
        # keys env standard: no key file, no fallback — the loader finds nothing
        self.saved_env = dict(os.environ)
        self.saved_keys_mod = sys.modules.get("daemn_keys")
        sys.modules["daemn_keys"] = types.SimpleNamespace(key=lambda name, required=False: "")
        os.environ["HOME"] = str(self.tmp / "home")
        os.environ["KEYS_NO_FALLBACK"] = "1"

    def tearDown(self):
        run.platform.confirm = self.saved_confirm
        sys.stdin = self.saved_stdin
        os.environ.clear()
        os.environ.update(self.saved_env)
        if self.saved_keys_mod is None:
            sys.modules.pop("daemn_keys", None)
        else:
            sys.modules["daemn_keys"] = self.saved_keys_mod
        shutil.rmtree(self.tmp, ignore_errors=True)

    def start_args(self, **over):
        a = ["start", str(FIX / "run-plan.json"),
             "--brand", "_fixture", "--format", "fixture-format", "--label", "t1",
             "--bank", str(FIX / "bank.json"), "--runs-root", str(self.tmp),
             "--cast-root", str(FIX / "cast-root"), "--composed", "--no-footage",
             "--provider", CONFIRM_PROVIDER]
        for k, v in over.items():
            if v is True:
                a.append(f"--{k.replace('_', '-')}")
        return run.build_parser().parse_args(a)

    def start(self, a):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = run.cmd_start(a, voice_transport=no_voice_network)
        return code, buf.getvalue()

    def test_provider_carries_confirm(self):
        _, prov, _ = run.platform.resolve_provider(CONFIRM_PROVIDER)
        self.assertTrue(prov.get("confirm"))

    def test_dry_run_never_calls_confirm(self):
        def must_not_confirm(prov, yes=False):
            self.fail("platform.confirm was called on a dry run")
        run.platform.confirm = must_not_confirm
        a = self.start_args(dry_run=True)
        self.assertTrue(a.dry_run)
        self.assertFalse(a.yes)
        code, out = self.start(a)
        self.assertIn(f"dry run — a live run would ask to confirm (provider {CONFIRM_PROVIDER})", out)
        self.assertNotIn("declined", out)
        self.assertNotIn("stdin is not a terminal", out)
        self.assertNotEqual(code, 1, out)
        self.assertEqual(code, 0, out)

    def test_live_run_still_confirms_and_a_decline_returns_1(self):
        def decline(prov, yes=False):
            self.calls.append((prov.get("confirm"), yes))
            return False
        run.platform.confirm = decline
        a = self.start_args()
        self.assertFalse(a.dry_run)
        self.assertFalse(a.yes)
        code, out = self.start(a)
        self.assertEqual(self.calls, [(True, False)])
        self.assertIn("declined", out)
        self.assertNotIn("a live run would ask to confirm", out)
        self.assertEqual(code, 1, out)

    def test_live_run_with_real_confirm_and_no_terminal_returns_1(self):
        a = self.start_args()
        code, out = self.start(a)
        self.assertIn("stdin is not a terminal — treating as NO", out)
        self.assertIn("declined", out)
        self.assertEqual(code, 1, out)


if __name__ == "__main__":
    unittest.main()
