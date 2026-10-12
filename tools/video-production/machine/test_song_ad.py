"""A song ad runs straight through (2026-10-10, after the first one needed hand workarounds):
the storyboard is clocked from the song, every clip prompt carries the style lock first and
the scene's action, start pictures go at 9:16, a song ad is 360p + a local upscale and every
section is a clip. A made-up three-line song — no model, no network, no money."""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import omni_clips as oc
import storyboard_plan as sp

LINES = ["My whole street knew the secret", "Nobody told me a thing", "Everybody knew but me",
         "Now everybody sees me", "Everybody knew but me"]


def scene(sid, lyrics, happens="", subject="a woman in a kitchen", make="clip", product=""):
    return {"id": sid, "kind": "broll", "to_camera": False, "voice": "", "speaker": "", "lyrics": lyrics,
            "who": "the narrator, a woman about fifty", "happens": happens, "make": make, "product": product,
            "setting_id": "kitchen", "looks": {"LEAD": "look-1"}, "source": "K01 (swipe composition)",
            "frames": [{"role": "first", "subject": subject, "style": "STYLE LOCK — x"}]}


def plan_doc():
    return {"format": "song-ad", "piece": {"style_id": "family-3d", "style": "STYLE LOCK — old sentence"},
            "cast": {"name": "LEAD", "names": ["LEAD"]},
            "song": {"file": "song/song.mp3", "timing": "song/timing.json",
                     "sections": [{"name": "intro", "lines": ["A hook sung over the open"]},
                                  {"name": "verse", "lines": LINES[:2]}, {"name": "chorus", "lines": LINES[2:]}]},
            "scenes": [scene("S1", [], happens="she smiles at the camera"),
                       scene("S2", [LINES[0]], happens="she stirs a pot"),
                       scene("S3", [LINES[1]], happens="", subject="a framed photo on a shelf"),
                       scene("S4", [LINES[2]], happens="she turns to the window"),
                       scene("S5", [LINES[3]], happens="she walks in", product="the-scrub"),
                       scene("S6", [LINES[4]], happens="she turns to the window", make="reuse:S4")]}


TIMING = {"lines": [{"line": "A hook sung over the open", "match": 0.5},                    # never heard
                    {"line": LINES[0], "start": 10.0, "end": 14.0},
                    {"line": LINES[1], "start": 15.0, "end": 18.0},
                    {"line": LINES[2], "start": 20.0, "end": 23.0},
                    {"line": LINES[3], "start": 26.0, "end": 29.0},
                    {"line": LINES[4], "start": 31.0, "end": 34.0}]}


def transcript():
    words, t = [{"text": "[singing]", "start": 0.4, "end": 9.8, "type": "audio_event"}], {}
    for line in TIMING["lines"][1:]:
        ws = line["line"].split()
        step = (line["end"] - line["start"]) / len(ws)
        for i, w in enumerate(ws):
            a = line["start"] + i * step
            words.append({"text": w, "start": round(a, 2), "end": round(a + step * 0.8, 2), "type": "word"})
    return {"words": words, "audio_duration_secs": 40.0}


class SongRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = Path(self.tmp.name) / "run"
        (self.run / "song").mkdir(parents=True)
        (self.run / "plan.json").write_text(json.dumps(plan_doc()))
        (self.run / "run.json").write_text(json.dumps({"format": "song-ad", "style_id": "family-3d"}))
        (self.run / "song" / "timing.json").write_text(json.dumps(TIMING))
        (self.run / "song" / "transcript.json").write_text(json.dumps(transcript()))

    def tearDown(self):
        self.tmp.cleanup()

    def board(self):
        with redirect_stdout(io.StringIO()):
            return sp.build(self.run, None)


class Storyboard(SongRun):
    def test_a_song_ad_is_recognised_and_needs_no_teardown(self):
        self.assertTrue(sp.is_song(plan_doc(), self.run))
        voiced = plan_doc(); voiced["scenes"][1]["voice"] = "a spoken line"
        self.assertFalse(sp.is_song(voiced, self.run))
        p = self.board()
        self.assertTrue(p["song"])
        self.assertTrue((self.run / "storyboard.json").exists() and (self.run / "STORYBOARD.md").exists())

    def test_one_section_per_scene_each_starting_on_its_sung_line(self):
        p = self.board()
        got = {g["scenes"][0]: (g["starts"], g["seconds"]) for g in p["sections"]}
        self.assertEqual(got["S2"], (10.0, 5.0))       # starts on its line, runs to the next scene
        self.assertEqual(got["S3"], (15.0, 5.0))
        self.assertEqual(got["S4"], (20.0, 6.0))
        self.assertEqual(got["S5"], (26.0, 5.0))
        self.assertEqual(got["S6"], (31.0, 9.0))       # the last runs to the end of the song
        self.assertEqual(got["S1"], (0.0, 10.0))       # no line of its own: the time before the first sung line
        self.assertEqual(p["seconds"], 40.0)
        self.assertEqual(p["check"], [])
        self.assertIn("song/timing.json", p["notes"][0])

    def test_scenes_without_lines_share_the_time_before_the_next(self):
        doc = plan_doc()
        doc["scenes"].insert(1, scene("S1b", [], happens="steam rises"))
        (self.run / "plan.json").write_text(json.dumps(doc))
        got = {g["scenes"][0]: (g["starts"], g["seconds"]) for g in self.board()["sections"]}
        self.assertEqual(got["S1"], (0.0, 5.0))
        self.assertEqual(got["S1b"], (5.0, 5.0))

    def test_a_repeated_chorus_line_is_found_in_order_and_reuses_its_clip(self):
        p = self.board()
        g6 = next(g for g in p["sections"] if g["scenes"] == ["S6"])
        self.assertEqual(g6["starts"], 31.0)             # the SECOND "Everybody knew but me", not the first
        self.assertEqual(g6["reuses"], "G04")
        self.assertEqual(g6["frames"], [])

    def test_every_section_is_a_silent_clip_from_its_picture(self):
        p = self.board()
        for g in p["sections"]:
            self.assertEqual(g["maker"], "from the brief")
            self.assertEqual(len(g["clips"]), 1, g["id"])
            self.assertEqual(g["clips"][0]["seconds"], g["seconds"])
            self.assertEqual(g["voice"], {})
            if not g.get("reuses"):
                self.assertEqual(g["frames"], [{"what": "start frame", "from": g["scenes"][0]}])
        self.assertEqual(p["layers"]["song"], "song/song.mp3")
        self.assertEqual(p["layers"]["voice"], [])
        self.assertIn("product · real packshot", next(g for g in p["sections"] if g["scenes"] == ["S5"])["elements"])
        self.assertEqual(p["sections"][1]["lyric"], LINES[0])

    def test_without_timing_the_transcript_word_times_clock_it(self):
        (self.run / "song" / "timing.json").unlink()
        p = self.board()
        got = {g["scenes"][0]: g["starts"] for g in p["sections"]}
        self.assertEqual([got[s] for s in ("S2", "S3", "S4", "S5", "S6")], [10.0, 15.0, 20.0, 26.0, 31.0])
        self.assertIn("transcript", p["notes"][0])

    def test_an_unheard_line_is_timed_between_its_neighbours_and_named(self):
        t = json.loads(json.dumps(TIMING))
        t["lines"][2].pop("start"); t["lines"][2].pop("end")
        (self.run / "song" / "timing.json").write_text(json.dumps(t))
        p = self.board()
        got = {g["scenes"][0]: g["starts"] for g in p["sections"]}
        self.assertTrue(14.0 <= got["S3"] < 20.0, got)
        self.assertTrue(any(c.startswith("S3:") and "not heard" in c for c in p["check"]), p["check"])


class Clips(SongRun):
    def plan(self, sb=None, cfg=None):
        sb = sb or self.board()
        doc = plan_doc()
        for g in sb["sections"]:
            for sid in g["scenes"]:
                (self.run / "media").mkdir(exist_ok=True)
                (self.run / "media" / f"{sid}-F1.png").write_bytes(b"png")
        cfg = cfg or oc.route_cfg(None, oc.format_of(self.run, doc))
        return oc.plan(self.run, sb, doc["scenes"], cfg=cfg, people={}, style=oc.style_line(self.run, doc)), cfg

    def test_the_song_ad_route_is_360p_upscaled_locally_for_nothing(self):
        res, cfg = self.plan()
        self.assertEqual(cfg["resolution"], "360p")
        self.assertEqual(res["format"], "song-ad")
        self.assertEqual(res["problems"], [])
        for c in res["calls"]:
            self.assertEqual(c["params"]["resolution"], "360p")
            self.assertEqual(c["upscale"], "local")
            self.assertEqual(c["upscale_usd"], 0.0)
            self.assertTrue(any("on this Mac" in s for s in c["steps"]))
        self.assertEqual(res["totals"]["fal_usd"], res["totals"]["omni_usd"])
        self.assertEqual(res["totals"]["omni_usd"], round(sum(c["duration"] for c in res["calls"]) * 0.03, 2))
        own = oc.platform.registry()["direct"]["omni_route"]["resolution"]
        self.assertEqual(oc.route_cfg()["resolution"], own, "other formats keep the route's own resolution")
        self.assertEqual(oc.route_cfg(None, "micro-drama")["resolution"], own)

    def test_every_prompt_starts_with_the_style_lock(self):
        res, _ = self.plan()
        for c in res["calls"]:
            self.assertTrue(c["prompt"].startswith("STYLE LOCK — big-studio 3D animated feature"), c["prompt"][:80])
            self.assertIn("Motion: full fluid character animation", c["prompt"].split("\n\n")[0])
            self.assertNotIn("old sentence", c["prompt"])
            self.assertNotIn("push-in", c["prompt"].split("\n\n")[0], "framing never rides in on the style")

    def test_every_wordless_clip_carries_its_scenes_action(self):
        res, _ = self.plan()
        by = {c["section_id"]: c for c in res["calls"]}
        self.assertIn("She stirs a pot.", by["G02"]["prompt"])
        self.assertIn("She smiles at the camera.", by["G01"]["prompt"])
        # no `happens`: the scene's first picture, brought gently alive
        self.assertIn("moves gently and naturally: a framed photo on a shelf", by["G03"]["prompt"])
        self.assertNotIn("G06", by, "a reused chorus clip is not made twice")
        for c in res["calls"]:
            self.assertIn("lips stay closed", c["prompt"])
            self.assertEqual(c["scenes"], [c["section_id"].replace("G0", "S")])

    def test_a_song_section_with_no_clip_is_stopped(self):
        sb = self.board()
        sb["sections"][2]["clips"] = []
        res, _ = self.plan(sb)
        self.assertTrue(any("Section 3 has no clip" in p and "never a still or a hold" in p for p in res["problems"]),
                        res["problems"])

    def test_the_step_uses_the_runs_format_and_style(self):
        sbf = self.run / "storyboard.json"
        self.board()
        for sid in ("S1", "S2", "S3", "S4", "S5"):
            (self.run / "media").mkdir(exist_ok=True)
            (self.run / "media" / f"{sid}-F1.png").write_bytes(b"png")
        (self.run / "elements.json").write_text(json.dumps({"items": []}))
        import argparse
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            rc = oc.start(argparse.Namespace(only=None, storyboard=False), self.run, plan_doc(), None)
        self.assertEqual(rc, 0)
        res = json.loads((self.run / "clips" / "plan.json").read_text())
        self.assertTrue(sbf.exists())
        self.assertEqual(res["format"], "song-ad")
        self.assertTrue(all(c["prompt"].startswith("STYLE LOCK") for c in res["calls"]))


class NineSixteen(unittest.TestCase):
    def test_a_two_by_three_picture_is_cut_to_nine_by_sixteen(self):
        x0, y0, x1, y1 = oc.crop_box(1024, 1536)
        self.assertEqual((y0, y1 - y0), (0, 1536))
        self.assertAlmostEqual((x1 - x0) / 1536, 9 / 16, places=2)
        self.assertEqual(x0, 1024 - x1, "centred")

    def test_a_too_wide_and_a_too_tall_picture(self):
        x0, y0, x1, y1 = oc.crop_box(1080, 2400)
        self.assertEqual((x0, x1), (0, 1080))
        self.assertAlmostEqual(1080 / (y1 - y0), 9 / 16, places=2)
        self.assertIsNone(oc.crop_box(1080, 1920))
        self.assertIsNone(oc.crop_box(1078, 1920), "within a percent is left alone")

    def test_the_sent_copy_is_nine_by_sixteen_and_the_approved_picture_untouched(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            src, out = Path(d) / "S1-F1.png", Path(d) / "call" / "start-9x16.png"
            Image.new("RGB", (1024, 1536), (10, 20, 30)).save(src)
            before = src.read_bytes()
            got = oc.to_aspect(src, out)
            self.assertEqual(got, out)
            with Image.open(got) as im:
                self.assertAlmostEqual(im.width / im.height, 9 / 16, places=2)
                self.assertEqual(im.height, 1536)
            self.assertEqual(src.read_bytes(), before)
            ok = Path(d) / "ok.png"
            Image.new("RGB", (1080, 1920)).save(ok)
            self.assertEqual(oc.to_aspect(ok, Path(d) / "x.png"), ok)


class LocalUpscale(unittest.TestCase):
    def test_the_upscale_runs_local_studios_launcher_to_1920(self):
        cfg = oc.route_cfg(None, "song-ad")
        seen, real = [], oc._height
        oc._height = lambda p: 640
        try:
            out = oc.upscale_local(Path("in.mp4"), Path("out.mp4"), cfg, runner=seen.append)
        finally:
            oc._height = real
        cmd = seen[0]
        self.assertEqual(out, Path("out.mp4"))
        self.assertEqual(cmd[0], sys.executable)
        self.assertTrue(cmd[1].endswith("components/local-studio/local.py") and Path(cmd[1]).is_file(), cmd[1])
        self.assertEqual(cmd[2:4], ["upscale", "in.mp4"])
        self.assertEqual(cmd[cmd.index("--scale") + 1], "3")


if __name__ == "__main__":
    unittest.main()
