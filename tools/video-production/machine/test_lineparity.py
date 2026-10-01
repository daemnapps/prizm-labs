#!/usr/bin/env python3
"""python3 machine/test_lineparity.py — from any cwd. Stdlib unittest only.

Never touches the network — every real call goes through a fake transport."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"test_vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lineparity = load("lineparity")
preflight = load("preflight")
REG = json.loads((HERE / "providers.json").read_text())


def run_quiet(fn, *a, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        result = fn(*a, **kw)
    return result, buf.getvalue()


@contextlib.contextmanager
def no_key():
    """A clean environment with ELEVENLABS_API_KEY reachable nowhere — env
    nor the Keychain vault — so the missing-key test means what it says
    regardless of what is actually set up on the machine running the suite."""
    saved_env = dict(os.environ)
    saved_mod = sys.modules.get("daemn_keys")
    os.environ.pop("ELEVENLABS_API_KEY", None)
    sys.modules["daemn_keys"] = types.SimpleNamespace(key=lambda name, required=False: None)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(saved_env)
        if saved_mod is None:
            sys.modules.pop("daemn_keys", None)
        else:
            sys.modules["daemn_keys"] = saved_mod


class FakeTranscriber:
    """Records every call it sees; returns a fixed transcript."""
    def __init__(self, text: str):
        self.text = text
        self.calls = []

    def __call__(self, method, url, headers, body):
        self.calls.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        return 200, {}, json.dumps({"text": self.text}).encode()


class Check(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-lineparity-"))
        self.clip = self.tmp / "clip.mp4"
        self.clip.write_bytes(b"fake-mp4-bytes")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_exact_line_is_pass(self):
        fake = FakeTranscriber("Wake up and choose greatness.")
        result = lineparity.check(self.clip, "Wake up and choose greatness.",
                                   transport=fake, key="test-key")
        self.assertEqual(result["heard"], "Wake up and choose greatness.")
        self.assertEqual(result["match"], 1.0)
        self.assertEqual(result["verdict"], "PASS")
        self.assertIn("T", result["at"])

        self.assertEqual(len(fake.calls), 1)
        call = fake.calls[0]
        self.assertIn("speech-to-text", call["url"])
        self.assertIn(b"fake-mp4-bytes", call["body"])
        self.assertIn(b'name="model_id"', call["body"])
        self.assertIn(b"scribe_v1", call["body"])
        self.assertIn(b'name="file"', call["body"])
        self.assertEqual(call["headers"]["xi-api-key"], "test-key")

    def test_different_words_is_flag(self):
        fake = FakeTranscriber("I wanted to share this with you today.")
        result = lineparity.check(self.clip, "Wake up and choose greatness.",
                                   transport=fake, key="test-key")
        self.assertEqual(result["verdict"], "FLAG")
        self.assertLess(result["match"], 0.85)

    def test_punctuation_and_case_are_ignored(self):
        fake = FakeTranscriber("wake up and choose greatness")
        result = lineparity.check(self.clip, "Wake up, and choose greatness!",
                                   transport=fake, key="test-key")
        self.assertEqual(result["match"], 1.0)
        self.assertEqual(result["verdict"], "PASS")

    def test_threshold_read_from_registry(self):
        # a stricter house threshold turns a near-match into a FLAG
        saved = lineparity.platform.registry
        lineparity.platform.registry = lambda: {"gates": {"line_parity": {"threshold": 0.99}}}
        try:
            fake = FakeTranscriber("Wake up and choose greatness now")
            result = lineparity.check(self.clip, "Wake up and choose greatness.",
                                       transport=fake, key="test-key")
            self.assertLess(result["match"], 0.99)
            self.assertEqual(result["verdict"], "FLAG")
        finally:
            lineparity.platform.registry = saved

    def test_default_threshold_matches_registry(self):
        gate = REG.get("gates", {}).get("line_parity", {})
        self.assertEqual(lineparity.threshold_of(), gate.get("threshold", lineparity.DEFAULT_THRESHOLD))

    def test_dry_run_writes_nothing_and_needs_no_key(self):
        result, printed = run_quiet(lineparity.check, self.clip, "a line",
                                     dry_run=True)
        self.assertIsNone(result)
        self.assertIn("speech-to-text", printed)
        self.assertNotIn("test-key", printed)

    def test_missing_key_is_a_hard_stop_naming_it(self):
        with no_key(), self.assertRaises(SystemExit) as ctx:
            lineparity.check(self.clip, "a line",
                              transport=lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
        self.assertIn("ELEVENLABS_API_KEY", str(ctx.exception))


class LineTextOf(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-lineparity-run-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_plain_string_lines(self):
        (self.tmp / "lines.json").write_text(json.dumps({"A1": "first line", "A2": "second line"}))
        text = lineparity.line_text_of(self.tmp, {"lines": ["A1", "A2"]})
        self.assertEqual(text, "first line second line")

    def test_dict_shaped_lines(self):
        (self.tmp / "lines.json").write_text(json.dumps({
            "L1": {"speaker": "lead", "text": "first line"},
            "L2": {"speaker": "lead", "text": "second line"}}))
        text = lineparity.line_text_of(self.tmp, {"lines": ["L1", "L2"]})
        self.assertEqual(text, "first line second line")

    def test_no_lines_is_empty(self):
        (self.tmp / "lines.json").write_text(json.dumps({"A1": "first line"}))
        self.assertEqual(lineparity.line_text_of(self.tmp, {"lines": []}), "")
        self.assertEqual(lineparity.line_text_of(self.tmp, {}), "")


class CLI(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-lineparity-cli-"))
        self.run = self.tmp / "run1"
        (self.run / "batches").mkdir(parents=True)
        (self.run / "lines.json").write_text(json.dumps({"A1": "Wake up and choose greatness."}))
        (self.run / "batches" / "01.json").write_text(json.dumps({"items": [
            {"id": "A1", "kind": "talking", "params": {}, "medias": [],
             "characters": [], "products": [], "lines": ["A1"]}]}))
        self.clip = self.tmp / "clip.mp4"
        self.clip.write_bytes(b"fake-mp4-bytes")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cli_writes_verdict(self):
        saved = lineparity.http_transport
        lineparity.http_transport = FakeTranscriber("Wake up and choose greatness.")
        try:
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code = lineparity.main(["--run", str(self.run), "A1", "--clip", str(self.clip)])
        finally:
            lineparity.http_transport = saved
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("verdict: PASS", out.getvalue())
        data = json.loads((self.run / "verdicts.json").read_text())
        self.assertEqual(data["A1"]["parity"]["verdict"], "PASS")
        self.assertEqual(data["A1"]["parity"]["heard"], "Wake up and choose greatness.")
        self.assertIn("at", data["A1"]["parity"])

    def test_dry_run_writes_no_verdict_file(self):
        code, out = run_quiet(lineparity.main,
                               ["--run", str(self.run), "A1", "--clip", str(self.clip), "--dry-run"])
        self.assertEqual(code, 0, out)
        self.assertFalse((self.run / "verdicts.json").exists())

    def test_unknown_item_is_bad_input(self):
        code, out = run_quiet(lineparity.main,
                               ["--run", str(self.run), "NOPE", "--clip", str(self.clip)])
        self.assertEqual(code, 3, out)

    def test_item_with_no_lines_is_bad_input(self):
        (self.run / "batches" / "02.json").write_text(json.dumps({"items": [
            {"id": "B1", "kind": "motion", "params": {}, "medias": [],
             "characters": [], "products": [], "lines": []}]}))
        code, out = run_quiet(lineparity.main,
                               ["--run", str(self.run), "B1", "--clip", str(self.clip)])
        self.assertEqual(code, 3, out)


if __name__ == "__main__":
    unittest.main()
