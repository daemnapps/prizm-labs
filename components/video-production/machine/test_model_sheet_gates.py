"""The model sheets (components/model-inputs/inputs) are enforced at the doors, not just written down.
Behaviour only: a refusal names the rule; a clean request passes; nothing is sent, nothing is spent."""
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name):
    sp = importlib.util.spec_from_file_location(f"msg_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def _clip(path, seconds):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=black:s=64x112:d={seconds}", "-pix_fmt", "yuv420p", str(path)], check=True)


class Gates(unittest.TestCase):
    def setUp(self):
        self.CL = _load("clip_limits")
        self.tmp = Path(tempfile.mkdtemp())

    def ids(self, model, dur, res, **kw):
        return [f["id"] for f in self.CL.check(model, dur, res, **kw) if f["level"] == "error"]

    def test_motion_control_refuses_the_master_as_the_person(self):
        self.assertIn("never-send", self.ids("higgsfield-motion-control", 5, "480p", images=[self.tmp / "master.png"]))
        self.assertEqual(self.ids("higgsfield-motion-control", 5, "480p", images=[self.tmp / "scene-still.png"]), [])

    def test_object_swap_refuses_the_master_too(self):
        self.assertIn("never-send", self.ids("higgsfield-object-swap", 5, "480p", images=[self.tmp / "headshot.png", self.tmp / "master.jpg"]))

    def test_motion_control_takes_one_image_one_video_in_range(self):
        ids = self.ids("higgsfield-motion-control", 5, "480p", images=[self.tmp / "a.png", self.tmp / "b.png"], videos=[self.tmp / "a.mp4", self.tmp / "b.mp4"], measure=False)
        self.assertIn("max-images", ids)
        self.assertIn("max-videos", ids)

    def test_motion_control_resolution_and_format(self):
        self.assertIn("resolution", self.ids("higgsfield-motion-control", 5, "8k"))
        self.assertIn("image-format", self.ids("higgsfield-motion-control", 5, "480p", images=[self.tmp / "a.gif"]))
        self.assertIn("video-format", self.ids("higgsfield-motion-control", 5, "480p", videos=[self.tmp / "a.avi"], measure=False))

    def test_reference_video_length_is_measured_against_the_sheet(self):
        short, ok = self.tmp / "short.mp4", self.tmp / "ok.mp4"
        _clip(short, 1)
        _clip(ok, 4)
        self.assertIn("video-clip-range", self.ids("higgsfield-motion-control", 1, "480p", videos=[short]))
        self.assertEqual(self.ids("higgsfield-motion-control", 4, "480p", videos=[ok]), [])
        self.assertIn("video-clip-range", self.ids("higgsfield-object-swap", 1, "480p", videos=[short]))   # the swap's 4 s minimum

    def test_raise_on_errors_stops_before_sending_and_names_the_rule(self):
        with self.assertRaises(SystemExit) as cm:
            self.CL.raise_on_errors(self.CL.check("higgsfield-motion-control", 5, "480p", images=[self.tmp / "master.png"]), "swap")
        self.assertIn("never-send", str(cm.exception))
        self.assertIn("baseline", str(cm.exception))

    def test_the_swap_door_sends_the_baseline_and_never_the_master(self):
        cs = _load("cast_swap")
        d = self.tmp / "full"
        (d / "sheets").mkdir(parents=True)
        for f in ("master.png", "sheets/headshot.png", "sheets/details.png", "sheets/angles-expressions.png", "sheets/turnaround.png", "sheets/look-a.png"):
            (d / f).write_bytes(b"x")
        cs.cast_dir = lambda slug, brand: d
        got = [p.name for p in cs.refs("x", "b")]
        self.assertEqual(got, ["headshot.png", "look-a.png", "details.png", "angles-expressions.png"])
        self.assertNotIn("master.png", got)
        (d / "sheets" / "details.png").unlink()
        (d / "sheets" / "angles-expressions.png").unlink()
        with self.assertRaises(SystemExit) as cm:
            cs.refs("x", "b")
        self.assertIn("no baseline", str(cm.exception))

    def test_no_swap_prompt_asks_for_the_master(self):
        self.assertNotIn("the master", _load("cast_swap").prompt().lower())


if __name__ == "__main__":
    unittest.main()
