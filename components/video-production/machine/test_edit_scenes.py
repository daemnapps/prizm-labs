#!/usr/bin/env python3
"""The AI lane's scenes ready to cut (edit_scenes.py) and a split stacked by the hand-off (clip_publish._pieces).
Made with ffmpeg test sources; nothing is called.

    python3 components/video-production/machine/test_edit_scenes.py
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clip_publish as CP  # noqa: E402
import edit_scenes as ES  # noqa: E402


def clip(dst, seconds, tone=False):
    a = ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}" if tone else f"anullsrc=r=48000:cl=stereo"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=gray:s=96x170:d={seconds}"] + a
                   + ["-t", str(seconds), "-shortest", "-c:v", "libx264", "-c:a", "aac", str(dst)], check=True)


class EditScenes(unittest.TestCase):
    def setUp(self):
        self.run = Path(tempfile.mkdtemp(prefix="edsc_"))
        for d in ("media", "vo"):
            (self.run / d).mkdir()
        clip(self.run / "media" / "S1.mp4", 2, tone=True)            # a talking scene: its own sound
        clip(self.run / "media" / "S2.mp4", 1, tone=False)           # a silent scene, shorter than its read
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=300:duration=3",
                        str(self.run / "vo" / "S2.mp3")], check=True)
        (self.run / "plan.json").write_text(json.dumps({"scenes": [{"id": "S1"}, {"id": "S2"}]}))
        (self.run / "vo" / "timing.json").write_text(json.dumps({"scenes": {
            "S1": {"file": "vo/S1.mp3", "lines": [{"text": "Hi there.", "start": 0.0, "end": 1.0}]},
            "S2": {"file": "vo/S2.mp3", "lines": [{"text": "It works.", "start": 0.5, "end": 2.5}]}}}))

    def test_a_scenes_words_are_on_its_own_sounds_clock(self):
        # brief-0380: the times were on the whole ad's voice timeline, so the Studio's captions started late
        t = json.loads((self.run / "vo" / "timing.json").read_text())
        t["scenes"]["S2"].update(start=9.6, lines=[{"text": "It works.", "start": 10.1, "end": 12.1}])
        (self.run / "vo" / "timing.json").write_text(json.dumps(t))
        ES.build(self.run)
        w = json.loads((self.run / "edit" / "S2.words.json").read_text())["words"]
        self.assertAlmostEqual(w[0]["start"], 0.5, places=3)

    def test_each_scene_gets_its_voice_and_words(self):
        res = ES.build(self.run)
        rows = {r["scene"]: r for r in res["scenes"]}
        self.assertIn("own lip-synced sound", rows["S1"]["voice_from"])
        self.assertIn("voice-over", rows["S2"]["voice_from"])
        self.assertGreaterEqual(rows["S2"]["seconds"], 3.0)            # the picture holds to the end of the read
        self.assertAlmostEqual(ES.dur(self.run / "edit" / "S2.mp4"), rows["S2"]["seconds"], delta=0.15)
        w = json.loads((self.run / "edit" / "S2.words.json").read_text())["words"]
        self.assertEqual([x["w"] for x in w], ["It", "works."])
        self.assertEqual(w[0]["start"], 0.5)
        self.assertTrue((self.run / "edit" / "EDIT.json").is_file())


class SplitStacks(unittest.TestCase):
    def test_a_layout_pair_is_one_stacked_piece(self):
        top = {"id": "C1", "layout": {"kind": "stack", "position": "top", "with": "C1-B"}}
        bottom = {"id": "C1-B", "layout": {"kind": "stack", "position": "bottom", "with": "C1"}}
        other = {"id": "C2"}
        got = CP._pieces([(bottom, {}), (other, {}), (top, {})])
        self.assertEqual([(k, [c["id"] for c in cs]) for k, cs in got], [("stack", ["C1", "C1-B"]), ("one", ["C2"])])

    def test_the_stack_is_render_on_top_people_below_with_the_peoples_sound(self):
        d = Path(tempfile.mkdtemp(prefix="stk_"))
        clip(d / "t.mp4", 1)
        clip(d / "b.mp4", 1, tone=True)
        CP._stack(d / "t.mp4", d / "b.mp4", d / "o.mp4")
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                            "-of", "csv=p=0", str(d / "o.mp4")], capture_output=True, text=True).stdout.strip()
        self.assertEqual(r, "96,168")
        self.assertTrue(ES.has_sound(d / "o.mp4"))


if __name__ == "__main__":
    unittest.main()
