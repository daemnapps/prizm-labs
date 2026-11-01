"""LD-58 (record frames on demand): a record with no frame pictures on this machine gets them back from its
clip, fetched by its Drive label through the key; a still gets one; a second call fetches nothing. A fake
reach (local) and a fake ffmpeg (_run) only — no Drive, no network, DRIVE_MOUNT=off."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shared_paths as SP  # noqa: E402


class RecordFrames(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        env = mock.patch.dict(os.environ, {"DRIVE_MOUNT": "off"})
        env.start()
        self.addCleanup(env.stop)
        self.fetched, self.cmds = [], []

        def local(ref):
            self.fetched.append(ref)
            return str(self.tmp / "clip.mov")

        def run(cmd):
            self.cmds.append(cmd)
            Path(cmd[-1]).write_bytes(b"jpg")
        for p in (mock.patch.object(SP, "local", local), mock.patch.object(SP, "_run", run)):
            p.start()
            self.addCleanup(p.stop)

    def record(self, name, frames, duration):
        d = self.tmp / name
        d.mkdir()
        (d / "clip.json").write_text(json.dumps({"label": "Shared Assets/brands/acme/raw/" + name + ".mov",
                                                 "meta": {"duration_s": duration}, "frames": frames}))
        return d

    def test_a_clip_gets_its_frames_back_once(self):
        d = self.record("clip", [{"file": "frame_01.jpg", "at_s": 1.5}, {"file": "frame_02.jpg", "at_s": 6.0}], 10.0)
        got = SP.record_frames(d)
        self.assertEqual([Path(f).name for f in got], ["frame_01.jpg", "frame_02.jpg"])
        self.assertEqual(self.fetched, ["Shared Assets/brands/acme/raw/clip.mov"])
        self.assertEqual([c[c.index("-ss") + 1] for c in self.cmds], ["1.5", "6.0"])
        self.assertTrue(all("scale=-2:480" in c for c in self.cmds))
        self.assertEqual(SP.record_frames(d), got)
        self.assertEqual(len(self.fetched), 1)                 # the second call fetches nothing

    def test_a_still_gets_one_picture(self):
        d = self.record("still", [{"file": "frame_01.jpg", "at_s": 0.0}], None)
        got = SP.record_frames(d)
        self.assertEqual([Path(f).name for f in got], ["frame_01.jpg"])
        self.assertNotIn("-ss", self.cmds[0])

    def test_no_label_or_no_fetch_is_empty(self):
        d = self.tmp / "nolabel"
        d.mkdir()
        (d / "clip.json").write_text(json.dumps({"frames": [{"file": "frame_01.jpg", "at_s": 1}]}))
        self.assertEqual(SP.record_frames(d), [])
        d2 = self.record("clip2", [{"file": "frame_01.jpg", "at_s": 1}], 5.0)
        self.assertEqual(SP.record_frames(d2, fetch=False), [])
        self.assertEqual(self.fetched, [])


if __name__ == "__main__":
    unittest.main()
