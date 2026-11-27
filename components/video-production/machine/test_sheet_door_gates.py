"""The voice, music, Suno, upscale, 3D and judge sheets (components/model-inputs/inputs) are enforced at the doors that
call those models. Behaviour only: a refusal names the rule; a clean request passes; nothing is sent, nothing is spent."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(path, name):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


SG = _load(HERE / "sheet_gates.py", "sdg_sheet_gates")
TD = _load(HERE.parents[1] / "3d" / "sheet_check.py", "sdg_3d_sheet_check")


def errs(found):
    return [f["id"] for f in found if f["level"] == "error"]


def chunk(ms=20000, text="one\ntwo", **kw):
    c = {"text": text, "duration_ms": ms, "positive_styles": ["a"], "negative_styles": []}
    c.update(kw)
    return c


def req(*chunks):
    return {"body": {"composition_plan": {"chunks": list(chunks)}}}


class Voice(unittest.TestCase):
    def test_empty_and_overlong_lines_are_refused(self):
        self.assertIn("empty-text", errs(SG.voice_text("eleven-v3", "  ")))
        self.assertIn("text-too-long", errs(SG.voice_text("eleven-v3", "x" * 5001)))
        self.assertEqual(errs(SG.voice_text("eleven-v3", "Hello there. " * 30)), [])

    def test_a_short_line_only_warns(self):
        found = SG.voice_text("eleven-v3", "Hi.")
        self.assertEqual(errs(found), [])
        self.assertIn("text-short", [f["id"] for f in found])

    def test_the_voice_door_stops_before_sending_an_overlong_line(self):
        voice = _load(HERE / "voice.py", "sdg_voice")
        with self.assertRaises(SystemExit) as cm:
            voice.body_for("y" * 6000, "eleven_v3", None)
        self.assertIn("text-too-long", str(cm.exception))

    def test_voice_design_text_range(self):
        self.assertIn("text-chars", errs(SG.voice_design("eleven-ttv-v3", "warm, slow", text="short")))
        self.assertEqual(errs(SG.voice_design("eleven-ttv-v3", "warm, slow", text="z" * 200)), [])
        self.assertEqual(errs(SG.voice_design("eleven-ttv-v3", "warm, slow", auto_text=True)), [])
        self.assertIn("voice-description", errs(SG.voice_design("eleven-ttv-v3", "", auto_text=True)))


class Music(unittest.TestCase):
    def test_sections_length_and_total(self):
        self.assertEqual(errs(SG.music_request(req(chunk(), chunk()))), [])
        self.assertIn("section-seconds", errs(SG.music_request(req(chunk(ms=1000)))))
        self.assertIn("section-seconds", errs(SG.music_request(req(chunk(ms=130000)))))
        self.assertIn("sections-max", errs(SG.music_request(req(*[chunk(ms=3000)] * 31))))
        self.assertIn("music-length", errs(SG.music_request(req(*[chunk(ms=120000)] * 6))))
        self.assertIn("no-sections", errs(SG.music_request(req())))

    def test_lines_and_styles(self):
        self.assertIn("lines-max", errs(SG.music_request(req(chunk(text="\n".join("l%d" % i for i in range(31)))))))
        self.assertIn("line-chars", errs(SG.music_request(req(chunk(text="x" * 201)))))
        self.assertIn("styles-max", errs(SG.music_request(req(chunk(positive_styles=["s"] * 51)))))

    def test_the_song_door_builds_a_request_the_sheet_accepts(self):
        song = _load(HERE / "song.py", "sdg_song")
        d = song.door()
        block = {"style_id": next(iter(song.load_styles().get("rows", song.load_styles()))), "sections": []}
        with self.assertRaises(song.Refused):                       # no sections: refused before any sheet or call
            song.build_request(block, {})


class Suno(unittest.TestCase):
    def test_boxes(self):
        self.assertEqual(errs(SG.suno_boxes("warm, folk", "[Verse]\nla la", "T")), [])
        self.assertIn("style-chars", errs(SG.suno_boxes("s" * 1001, "[Verse]\nla")))
        self.assertIn("lyrics-chars", errs(SG.suno_boxes("s", "l" * 2501)))
        self.assertIn("lyrics-empty", errs(SG.suno_boxes("s", " ")))
        self.assertIn("title-chars", errs(SG.suno_boxes("s", "l", "t" * 101)))

    def test_soft_limits_only_warn(self):
        found = SG.suno_boxes(",".join("t%d" % i for i in range(25)), "l", exclude="a,b,c,d")
        self.assertEqual(errs(found), [])
        self.assertEqual({f["id"] for f in found}, {"style-descriptors", "exclusions"})

    def test_sliders(self):
        self.assertEqual(errs(SG.suno_sliders({"weirdness": 50})), [])
        self.assertIn("slider", errs(SG.suno_sliders({"weirdness": 150})))


class Upscale(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def f(self, name, data=b"x"):
        p = self.tmp / name
        p.write_bytes(data)
        return p

    def test_local_upscaler(self):
        self.assertEqual(errs(SG.upscale("real-esrgan", self.f("a.mp4"), scale=3)), [])
        self.assertIn("input-missing", errs(SG.upscale("real-esrgan", self.tmp / "none.mp4")))
        self.assertIn("input-format", errs(SG.upscale("real-esrgan", self.f("a.xyz"))))
        self.assertIn("scale", errs(SG.upscale("real-esrgan", self.f("b.mp4"), scale=20)))

    def test_alternate_upscaler(self):
        c = self.f("c.mp4")
        self.assertEqual(errs(SG.upscale("bytedance-upscaler-video", c, target="4k", input_res="480p", fps=30)), [])
        self.assertIn("target-resolution", errs(SG.upscale("bytedance-upscaler-video", c, target="8k")))
        self.assertIn("input-resolution", errs(SG.upscale("bytedance-upscaler-video", c, input_res="240p")))
        self.assertIn("frame-rate", errs(SG.upscale("bytedance-upscaler-video", c, fps=120)))

    def test_the_upscale_door_refuses_a_missing_clip_before_launching(self):
        cr = _load(HERE / "clips_run.py", "sdg_clips_run")
        launched = []
        with self.assertRaises(SystemExit) as cm:
            cr.upscale_local(self.tmp / "gone.mp4", self.tmp / "o.mp4", {}, runner=lambda cmd: launched.append(cmd))
        self.assertIn("input-missing", str(cm.exception))
        self.assertEqual(launched, [])


class ThreeD(unittest.TestCase):
    def setUp(self):
        self.img = Path(tempfile.mkdtemp()) / "p.png"
        self.img.write_bytes(b"x")

    def test_one_picture_known_grid_and_texture(self):
        self.assertEqual(errs(TD.check(self.img, "512", 2048)), [])
        self.assertEqual(errs(TD.check(self.img, "1024_cascade", 4096)), [])
        self.assertIn("input-images", errs(TD.check([self.img, self.img])))
        self.assertIn("image-missing", errs(TD.check(self.img.parent / "no.png")))
        self.assertIn("grid-resolution", errs(TD.check(self.img, "2048")))
        self.assertIn("texture-size", errs(TD.check(self.img, "512", 8192)))

    def test_refuse_names_the_rule(self):
        with self.assertRaises(SystemExit) as cm:
            TD.refuse(TD.check(self.img, "9999"))
        self.assertIn("grid-resolution", str(cm.exception))


class Judge(unittest.TestCase):
    def test_count_and_inline_size(self):
        tmp = Path(tempfile.mkdtemp())
        vids = []
        for i in range(11):
            p = tmp / ("v%d.mp4" % i)
            p.write_bytes(b"x")
            vids.append(p)
        self.assertEqual(errs(SG.judge_files("gemini-3.1-pro-preview", vids[:2])), [])
        self.assertIn("videos-max", errs(SG.judge_files("gemini-3.1-pro-preview", vids)))
        big = tmp / "big.mp4"
        big.write_bytes(b"\0" * (21 * 1024 * 1024))
        self.assertIn("inline-size", errs(SG.judge_files("gemini-3.1-pro-preview", [big])))

    def test_an_oversize_take_is_not_sent_to_the_judge(self):
        cj = _load(HERE / "clip_judge.py", "sdg_clip_judge")
        tmp = Path(tempfile.mkdtemp())
        big = tmp / "take.mp4"
        big.write_bytes(b"\0" * (21 * 1024 * 1024))
        asked = []
        got = cj.judge(tmp, big, {"id": "c1"}, {}, ask=lambda *a, **k: asked.append(a))
        self.assertFalse(got["pass"])
        self.assertEqual(asked, [])
        self.assertIn("inline", got["problems"][0]["what"])


if __name__ == "__main__":
    unittest.main()
