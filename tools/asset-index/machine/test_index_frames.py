#!/usr/bin/env python3
"""index_run.one() times its three frames on the PROXY, never past its end (post 123, 2026-10-21: four clips
failed when the seek came from the original's duration and landed after the proxy's last frame).

    python3 tools/asset-index/machine/test_index_frames.py

Local only: a short clip made by ffmpeg, the model calls stubbed, nothing on the Drive. Skips without ffmpeg.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import index_run as IR  # noqa: E402


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "needs ffmpeg and ffprobe")
class FramesInsideTheProxy(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.clip = self.tmp / "short.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30",
                        "-t", "1.2", "-pix_fmt", "yuv420p", str(self.clip)], check=True)
        self.saved = (IR.gb.upload, IR.gb.req, IR.ffprobe)
        IR.gb.upload = lambda k, p: ("uri", "video/mp4", None)
        IR.gb.req = lambda *a, **k: {"candidates": [{"content": {"parts": [{"text": json.dumps({"format": "b-roll"})}]}}],
                                    "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 2}}

    def tearDown(self):
        IR.gb.upload, IR.gb.req, IR.ffprobe = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_frames_land_even_when_the_original_claims_a_longer_duration(self):
        real = self.saved[2]
        # the original's container says 100 s (as a long or oddly muxed file does); the proxy is 1.2 s
        IR.ffprobe = lambda p, hdr=None: dict(real(p, hdr), duration_s=100.0) if Path(str(p)) == self.clip else real(p, hdr)
        out = self.tmp / "out"
        out.mkdir()
        cid, how, use = IR.one(self.clip, out, "any-brand", "k", [])
        self.assertEqual(how, "recorded")
        clip = json.loads((out / cid / "clip.json").read_text())
        self.assertEqual([f["file"] for f in clip["frames"]], ["frame_01.jpg", "frame_02.jpg", "frame_03.jpg"])
        for f in clip["frames"]:
            self.assertTrue((out / cid / f["file"]).is_file(), f)
            self.assertLess(f["at_s"], 1.3)


if __name__ == "__main__":
    unittest.main()
