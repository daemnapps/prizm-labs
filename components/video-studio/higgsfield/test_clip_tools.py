"""clip_tools.py: only the broken seconds are bought, nothing goes over the cap, sound and length never move."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clip_tools as CT  # noqa: E402


def clip(path, color, seconds, audio=True, size="270x480"):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=%s:s=%s:r=30:d=%g" % (color, size, seconds)]
    if audio:
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440:duration=%g" % seconds, "-shortest"]
    subprocess.run(cmd + ["-pix_fmt", "yuv420p", str(path)], check=True)
    return path


class Fake:
    """The command line, without the account."""
    def __init__(self, back, price=14):
        self.back, self.price, self.sent = back, price, []

    def _run(self, args, timeout=0):
        if args[1] == "cost":
            return 0, json.dumps({"credits": self.price}), ""
        self.sent.append(args)
        return 0, json.dumps({"id": "11111111-1111-1111-1111-111111111111"}), ""

    def _job_id(self, t):
        return json.loads(t)["id"]

    def wait(self, j):
        return {"status": "completed", "result_url": "x"}

    def outputs(self, b):
        return [b["result_url"]]

    def job_type(self, p):
        return "seedance_2_5"

    def download(self, url, dest):
        Path(dest).write_bytes(Path(self.back).read_bytes())


class ClipTools(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.dir = Path(self.d.name)
        os.environ["UPRIGHT_SPEND_LEDGER"] = str(self.dir / "ledger")
        os.environ.pop("UPRIGHT_SPEND_OK", None)

    def tearDown(self):
        self.d.cleanup()
        os.environ.pop("UPRIGHT_SPEND_LEDGER", None)

    def test_only_the_broken_seconds_are_bought(self):
        ref = self.dir / "sheet.png"
        ref.write_bytes(b"x")
        with self.assertRaises(CT.Refused):                          # a product is never put in from words alone
            CT.plan("fix", "x.mp4", "b", 9, 10, say="the bottle is missing from the hand", length=14)
        p = CT.plan("fix", "x.mp4", "b", 9, 10, say="the bottle is missing from the hand", length=14, refs=[ref])
        self.assertIn("@Image1", p["words"])
        self.assertFalse(p["words"].startswith("@"))                 # the command line reads a leading @ as a file
        self.assertEqual(p["seconds"], 4)
        self.assertEqual((p["start"], p["end"]), (7.5, 11.5))
        self.assertLess(p["credits"], p["remake_credits"] / 2)
        self.assertIn("the bottle is missing", p["words"])

    def test_our_own_tools_are_never_bought(self):
        for tid in ("grade", "sound", "upscale", "cutout", "versions", "swipe-edit", "reframe"):
            with self.assertRaises(CT.Refused):
                CT.plan(tid, "x.mp4", "b", length=10)

    def test_says_what_it_needs(self):
        for tid, kw in (("fix", {}), ("relight", {"look": "nope"}), ("angle", {"move": "nope"}), ("extend", {}), ("dub", {"lang": "xx"})):
            with self.assertRaises(CT.Refused):
                CT.plan(tid, "x.mp4", "b", length=10, **kw)
        with self.assertRaises(CT.Refused):
            CT.plan("fix", "x.mp4", "b", 8, 12, say="y", length=10)

    def test_over_the_cap_sends_nothing(self):
        src = clip(self.dir / "s.mp4", "red", 8)
        fake = Fake(clip(self.dir / "n.mp4", "blue", 4, False), price=99)
        p = CT.plan("fix", src, "b", 2, 6, say="make the towel white")
        with self.assertRaises(CT.Refused):
            CT.make(p, self.dir / "o.mp4", 20, hc=fake)
        self.assertEqual(fake.sent, [])

    def test_a_fix_keeps_the_sound_and_the_length_and_is_never_paid_twice(self):
        src = clip(self.dir / "s.mp4", "red", 8)
        fake = Fake(clip(self.dir / "n.mp4", "blue", 3.9, False))
        p = CT.plan("fix", src, "b", 2, 6, say="make the towel white")
        r = CT.make(p, self.dir / "o.mp4", 20, hc=fake)
        SE = CT._mod("video-edit/machine/shot_engine.py", "ct_shot_engine")
        self.assertAlmostEqual(SE.length(r["file"]), 8, delta=0.1)
        self.assertTrue(SE.has_audio(r["file"]))
        px = lambda t: subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", r["file"], "-frames:v", "1", "-vf", "scale=1:1", "-f", "rawvideo",   # noqa: E731
                                       "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        self.assertGreater(px(1)[0], 150)
        self.assertGreater(px(4)[2], 150)
        self.assertGreater(px(7)[0], 150)
        with self.assertRaises(RuntimeError):
            CT.make(p, self.dir / "o2.mp4", 20, hc=fake)
        self.assertEqual(len(fake.sent), 1)

    def test_what_comes_back_the_wrong_length_is_not_put_in(self):
        src = clip(self.dir / "s.mp4", "red", 8)
        fake = Fake(clip(self.dir / "n.mp4", "blue", 2, False))
        with self.assertRaises(CT.Refused):
            CT.make(CT.plan("fix", src, "b", 2, 6, say="z"), self.dir / "o.mp4", 20, hc=fake)


if __name__ == "__main__":
    unittest.main()
