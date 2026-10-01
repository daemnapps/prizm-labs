#!/usr/bin/env python3
"""python3 machine/test_direct.py — from any cwd. Stdlib unittest only.

Covers direct_openai.py and direct_google.py against fake transports —
nothing here ever touches the network. Every model id, URL and param comes
from providers.json's own `direct` section; this file names none as a
literal branch condition."""
from __future__ import annotations

import base64
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

# a real, tiny 1x1 PNG — enough for base64round-tripping in a test
PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"test_vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


direct_openai = load("direct_openai")
direct_google = load("direct_google")


def run_quiet(fn, *a, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        result = fn(*a, **kw)
    return result, buf.getvalue()


@contextlib.contextmanager
def no_keys():
    """A clean environment with neither key anywhere reachable — env nor the
    Keychain vault — so the 'missing key' tests mean what they say regardless
    of what is actually set up on the machine running the suite."""
    saved_env = dict(os.environ)
    saved_mod = sys.modules.get("daemn_keys")
    for var in ("OPENAI_API_KEY", "GEMINI_API_KEY"):
        os.environ.pop(var, None)
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


class FakeOpenAI:
    """Records every call it sees; returns a fixed b64_json image."""
    def __init__(self):
        self.calls = []

    def __call__(self, method, url, headers, body):
        self.calls.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        payload = {"data": [{"b64_json": PNG_B64}], "usage": {"total_tokens": 42}}
        return 200, {"x-request-id": "req-openai-1"}, json.dumps(payload).encode()


class OpenAIGenerate(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-direct-openai-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_edit_sends_references_in_order_and_decodes_image(self):
        ref1 = self.tmp / "cast.png"
        ref2 = self.tmp / "pack.png"
        ref1.write_bytes(b"cast-bytes")
        ref2.write_bytes(b"pack-bytes")
        out = self.tmp / "out.png"
        fake = FakeOpenAI()
        result = direct_openai.generate("a still of her", [ref1, ref2], out,
                                          transport=fake, key="test-key")
        self.assertTrue(out.is_file())
        self.assertEqual(out.read_bytes(), base64.b64decode(PNG_B64))
        expected = json.loads((HERE / "providers.json").read_text())["direct"]["openai"]["model"]
        self.assertEqual(result["model"], expected)
        self.assertEqual(result["request_id"], "req-openai-1")

        self.assertEqual(len(fake.calls), 1)
        call = fake.calls[0]
        self.assertIn("images/edits", call["url"])
        self.assertIn(b"cast-bytes", call["body"])
        self.assertIn(b"pack-bytes", call["body"])
        # order preserved — the first reference appears before the second
        self.assertLess(call["body"].index(b"cast-bytes"), call["body"].index(b"pack-bytes"))
        self.assertIn(b'name="image[]"', call["body"])

    def test_no_references_hits_generations_endpoint(self):
        out = self.tmp / "out.png"
        fake = FakeOpenAI()
        direct_openai.generate("a plate with no references", [], out, transport=fake, key="test-key")
        self.assertIn("images/generations", fake.calls[0]["url"])
        self.assertEqual(fake.calls[0]["headers"]["Content-Type"], "application/json")

    def test_dry_run_writes_nothing_and_needs_no_key(self):
        out = self.tmp / "out.png"
        code, printed = run_quiet(direct_openai.generate, "a prompt", [], out, dry_run=True)
        self.assertFalse(out.exists())
        self.assertIn("images/generations", printed)
        self.assertNotIn("test-key", printed)

    def test_missing_key_is_a_hard_stop_naming_it(self):
        out = self.tmp / "out.png"
        with no_keys(), self.assertRaises(SystemExit) as ctx:
            direct_openai.generate("a prompt", [], out,
                                    transport=lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
        self.assertIn("OPENAI_API_KEY", str(ctx.exception))


class FakeGoogleEdit:
    def __init__(self):
        self.calls = []

    def __call__(self, method, url, headers, body):
        self.calls.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        payload = {"candidates": [{"content": {"parts": [
            {"inlineData": {"mimeType": "image/png", "data": PNG_B64}}]}}]}
        return 200, {}, json.dumps(payload).encode()


class GoogleEditImage(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-direct-google-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_builds_inline_data_parts_and_decodes_image(self):
        ref1 = self.tmp / "approved.png"
        ref2 = self.tmp / "packshot.png"
        ref1.write_bytes(b"approved-frame")
        ref2.write_bytes(b"packshot-bytes")
        out = self.tmp / "out.png"
        fake = FakeGoogleEdit()
        result = direct_google.edit_image("swap the label", [ref1, ref2], out,
                                            transport=fake, key="test-key")
        self.assertTrue(out.is_file())
        self.assertEqual(out.read_bytes(), base64.b64decode(PNG_B64))
        self.assertEqual(result["model"], "gemini-3-pro-image")

        body = json.loads(fake.calls[0]["body"])
        parts = body["contents"][0]["parts"]
        # two inline_data parts (in order) then the text prompt
        self.assertIn("inline_data", parts[0])
        self.assertIn("inline_data", parts[1])
        self.assertEqual(parts[2]["text"], "swap the label")
        self.assertEqual(
            base64.b64decode(parts[0]["inline_data"]["data"]), b"approved-frame")
        self.assertEqual(
            base64.b64decode(parts[1]["inline_data"]["data"]), b"packshot-bytes")
        self.assertEqual(body["generationConfig"]["imageConfig"], {"aspectRatio": "9:16", "imageSize": "2K"})
        cats = {s["category"] for s in body["safetySettings"]}
        self.assertIn("HARM_CATEGORY_HARASSMENT", cats)
        self.assertTrue(all(s["threshold"] == "BLOCK_ONLY_HIGH" for s in body["safetySettings"]))

    def test_dry_run_writes_nothing_and_needs_no_key(self):
        out = self.tmp / "out.png"
        code, printed = run_quiet(direct_google.edit_image, "a prompt", [], out, dry_run=True)
        self.assertFalse(out.exists())
        self.assertIn("generateContent", printed)
        self.assertNotIn("test-key", printed)

    def test_missing_key_is_a_hard_stop_naming_it(self):
        out = self.tmp / "out.png"
        with no_keys(), self.assertRaises(SystemExit) as ctx:
            direct_google.edit_image("a prompt", [], out,
                                       transport=lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
        self.assertIn("GEMINI_API_KEY", str(ctx.exception))


class FakeGoogleSong:
    def __init__(self, lyric_text: str):
        self.lyric_text = lyric_text
        self.calls = []

    def __call__(self, method, url, headers, body):
        self.calls.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        wav_b64 = base64.b64encode(b"RIFF-fake-wav-bytes").decode()
        payload = {"candidates": [{"content": {"parts": [
            {"inlineData": {"mimeType": "audio/wav", "data": wav_b64}},
            {"text": self.lyric_text},
        ]}}]}
        return 200, {}, json.dumps(payload).encode()


class GoogleSong(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-direct-song-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_writes_both_files_and_reports_timed_true(self):
        out_wav = self.tmp / "song.wav"
        timing_out = self.tmp / "song-timings.txt"
        fake = FakeGoogleSong("[0:00] verse one\n[0:05] verse two")
        result = direct_google.song("a vocal-forward song", out_wav, timing_out,
                                      transport=fake, key="test-key")
        self.assertTrue(out_wav.is_file())
        self.assertEqual(out_wav.read_bytes(), b"RIFF-fake-wav-bytes")
        self.assertEqual(timing_out.read_text(), "[0:00] verse one\n[0:05] verse two")
        self.assertTrue(result["timed"])
        self.assertEqual(result["model"], "lyria-3-pro-preview")
        body = json.loads(fake.calls[0]["body"])
        # the API rejects a requested audio mime type (live, 2026-09-18) — none is sent
        self.assertNotIn("responseFormat", body["generationConfig"])

    def test_reports_timed_false_when_no_time_markers(self):
        out_wav = self.tmp / "song.wav"
        timing_out = self.tmp / "song-timings.txt"
        fake = FakeGoogleSong("just plain lyrics, no times at all")
        result = direct_google.song("a song", out_wav, timing_out, transport=fake, key="test-key")
        self.assertFalse(result["timed"])

    def test_clip_model_selected(self):
        out_wav = self.tmp / "song.wav"
        timing_out = self.tmp / "song-timings.txt"
        fake = FakeGoogleSong("no times")
        result = direct_google.song("a song", out_wav, timing_out, model="clip",
                                      transport=fake, key="test-key")
        self.assertEqual(result["model"], "lyria-3-clip-preview")

    def test_dry_run_writes_nothing_and_needs_no_key(self):
        out_wav = self.tmp / "song.wav"
        timing_out = self.tmp / "song-timings.txt"
        code, printed = run_quiet(direct_google.song, "a song", out_wav, timing_out, dry_run=True)
        self.assertFalse(out_wav.exists())
        self.assertFalse(timing_out.exists())
        self.assertIn("generateContent", printed)

    def test_missing_key_is_a_hard_stop_naming_it(self):
        out_wav = self.tmp / "song.wav"
        timing_out = self.tmp / "song-timings.txt"
        with no_keys(), self.assertRaises(SystemExit) as ctx:
            direct_google.song("a song", out_wav, timing_out,
                                transport=lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
        self.assertIn("GEMINI_API_KEY", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
