#!/usr/bin/env python3
"""python3 machine/test_direct_byteplus.py — from any cwd. Stdlib unittest only.

Covers direct_byteplus.py against a fake transport — nothing here touches
the network. Every model id, URL, role and default comes from
providers.json's own `direct.byteplus` section; this file names none."""
from __future__ import annotations

import base64
import contextlib
import importlib.util
import io
import json
import os
import shutil
import struct
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"test_vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bp = load("direct_byteplus")
platform = load("platform")
CFG = platform.registry()["direct"]["byteplus"]


def wav_bytes(seconds: float, rate: int = 8000) -> bytes:
    n = int(seconds * rate)
    data = b"\x00\x00" * n
    fmt = struct.pack("<4sIHHIIHH", b"fmt ", 16, 1, 1, rate, rate * 2, 2, 16)
    return b"RIFF" + struct.pack("<I", 4 + len(fmt) + 8 + len(data)) + b"WAVE" + fmt + b"data" + struct.pack("<I", len(data)) + data


class FakeArk:
    """POST → a task id; GET → queued once, then succeeded with a video url;
    GET on the video url → bytes."""
    def __init__(self, fail_with: str | None = None):
        self.calls = []
        self.polls = 0
        self.fail_with = fail_with

    def __call__(self, method, url, headers, body):
        self.calls.append({"method": method, "url": url, "headers": dict(headers),
                           "body": json.loads(body) if body else None})
        if method == "POST":
            return 200, {}, json.dumps({"id": "cgt-test-1"}).encode()
        if "/tasks/" in url:
            self.polls += 1
            if self.fail_with:
                return 200, {}, json.dumps({"id": "cgt-test-1", "status": "failed",
                                            "error": {"message": self.fail_with}}).encode()
            if self.polls == 1:
                return 200, {}, json.dumps({"id": "cgt-test-1", "status": "running"}).encode()
            return 200, {}, json.dumps({"id": "cgt-test-1", "status": "succeeded", "model": CFG["model"],
                                        "content": {"video_url": "https://cdn.test/clip.mp4"},
                                        "usage": {"completion_tokens": 129600}}).encode()
        return 200, {}, b"MP4BYTES"


@contextlib.contextmanager
def no_keys():
    saved_env = dict(os.environ)
    saved_mod = sys.modules.get("daemn_keys")
    os.environ.pop("BYTEPLUS_API_KEY", None)
    sys.modules["daemn_keys"] = types.SimpleNamespace(key=lambda name, required=False: None)
    try:
        yield
    finally:
        os.environ.clear(); os.environ.update(saved_env)
        if saved_mod is None:
            sys.modules.pop("daemn_keys", None)
        else:
            sys.modules["daemn_keys"] = saved_mod


class Talking(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-bp-"))
        self.still = self.tmp / "still.png"; self.still.write_bytes(base64.b64decode(PNG_B64))
        self.audio = self.tmp / "line.wav"; self.audio.write_bytes(wav_bytes(4.3))
        bp.time.sleep = lambda *_: None

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_builds_the_documented_shape_and_downloads(self):
        fake = FakeArk()
        out = self.tmp / "A1.mp4"
        res = bp.talking("she says it", self.still, self.audio, out, transport=fake, key="k")
        post = fake.calls[0]
        self.assertEqual(post["url"], CFG["create_task"])
        self.assertEqual(post["headers"]["Authorization"], "Bearer k")
        body = post["body"]
        self.assertEqual(body["model"], CFG["model"])
        kinds = [(c["type"], c.get("role")) for c in body["content"]]
        self.assertEqual(kinds, [("text", None),
                                 ("image_url", CFG["talking_roles"]["image"]),
                                 ("audio_url", CFG["talking_roles"]["audio"])])
        self.assertTrue(body["content"][1]["image_url"]["url"].startswith("data:image/png;base64,"))
        self.assertTrue(body["content"][2]["audio_url"]["url"].startswith("data:audio/wav;base64,"))
        self.assertTrue(body["content"][0]["text"].startswith(CFG["talking_prefix"]))
        self.assertTrue(body["content"][0]["text"].endswith("she says it"))
        self.assertEqual(body["duration"], 5)          # 4.3 s of audio → ceil → 5
        self.assertTrue(body["generate_audio"])
        self.assertEqual(body["ratio"], CFG["defaults"]["ratio"])
        self.assertEqual(body["resolution"], CFG["defaults"]["resolution"])
        self.assertEqual(body.get("omni_reference_task_type"), CFG["talking_task_type"])
        self.assertEqual(fake.polls, 2)
        self.assertEqual(out.read_bytes(), b"MP4BYTES")
        self.assertEqual(res["task_id"], "cgt-test-1")
        self.assertEqual(res["usage"]["completion_tokens"], 129600)

    def test_duration_clamped_to_model_floor(self):
        self.audio.write_bytes(wav_bytes(1.2))
        fake = FakeArk()
        bp.talking("x", self.still, self.audio, self.tmp / "o.mp4", transport=fake, key="k")
        self.assertEqual(fake.calls[0]["body"]["duration"], CFG["seconds_range"][0])

    def test_failed_task_is_a_hard_stop_with_the_api_message(self):
        fake = FakeArk(fail_with="content policy")
        with self.assertRaises(SystemExit) as cm:
            bp.talking("x", self.still, self.audio, self.tmp / "o.mp4", transport=fake, key="k")
        self.assertIn("content policy", str(cm.exception))
        self.assertFalse((self.tmp / "o.mp4").exists())

    def test_dry_run_writes_nothing_and_needs_no_key(self):
        with no_keys():
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                res = bp.talking("x", self.still, self.audio, self.tmp / "o.mp4",
                                 transport=lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")),
                                 dry_run=True)
        self.assertIn("<redacted>", buf.getvalue())
        self.assertIn("<elided>", buf.getvalue())
        self.assertNotIn(base64.b64encode(b"\x00\x00").decode() * 3, buf.getvalue())
        self.assertIsNone(res["file"])
        self.assertFalse((self.tmp / "o.mp4").exists())

    def test_missing_key_is_a_hard_stop_naming_it(self):
        with no_keys():
            with self.assertRaises(SystemExit) as cm:
                bp.talking("x", self.still, self.audio, self.tmp / "o.mp4",
                           transport=lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
        self.assertIn("BYTEPLUS_API_KEY", str(cm.exception))


class Motion(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-bp-"))
        self.first = self.tmp / "first.png"; self.first.write_bytes(base64.b64decode(PNG_B64))
        self.last = self.tmp / "last.png"; self.last.write_bytes(base64.b64decode(PNG_B64))
        bp.time.sleep = lambda *_: None

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_first_and_last_frame_roles_silent(self):
        fake = FakeArk()
        bp.motion("push in", self.first, self.last, self.tmp / "B1.mp4", seconds=6,
                  resolution="1080p", transport=fake, key="k")
        body = fake.calls[0]["body"]
        roles = [c.get("role") for c in body["content"][1:]]
        self.assertEqual(roles, [CFG["motion_roles"]["first"], CFG["motion_roles"]["last"]])
        self.assertFalse(body["generate_audio"])
        self.assertEqual(body["duration"], 6)
        self.assertEqual(body["resolution"], "1080p")
        self.assertNotIn("omni_reference_task_type", body)

    def test_first_frame_only(self):
        fake = FakeArk()
        bp.motion("push in", self.first, None, self.tmp / "B1.mp4", transport=fake, key="k")
        self.assertEqual(len(fake.calls[0]["body"]["content"]), 2)


class AudioLength(unittest.TestCase):
    def test_wav_header_read(self):
        tmp = Path(tempfile.mkdtemp(prefix="vm-bp-"))
        p = tmp / "a.wav"; p.write_bytes(wav_bytes(7.5))
        self.assertAlmostEqual(bp.audio_seconds(p), 7.5, places=2)
        shutil.rmtree(tmp, ignore_errors=True)

    def test_unreadable_is_none(self):
        self.assertIsNone(bp.audio_seconds(Path("/nonexistent/x.wav")))


if __name__ == "__main__":
    unittest.main(verbosity=1)
