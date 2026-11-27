"""The edit station's rows of the 2026-10-21 verify pass (runs/video-system/sync/2026-10-21/VERIFY.md rows 1, 2, 5, 6, 9,
16, 20), checked without a model, a network or a real run."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "machine"))
import edit_map as EM  # noqa: E402
import looks as LK  # noqa: E402


class TakesLaidWhole(unittest.TestCase):
    """Row 2 (V15): the next line of the same take keeps the take's own timing — one shot, no cut inside it."""

    def test_same_take(self):
        a = {"kind": "in clip", "clip": "C1", "in": 0.5, "len": 2.0}
        self.assertTrue(EM.same_take(a, {"kind": "in clip", "clip": "C1", "in": 3.1, "len": 1.0}))
        self.assertFalse(EM.same_take(a, {"kind": "in clip", "clip": "C2", "in": 3.1, "len": 1.0}))
        self.assertFalse(EM.same_take(a, {"kind": "own track", "clip": None, "in": 0, "len": 1.0}))
        self.assertFalse(EM.same_take(a, {"kind": "in clip", "clip": "C1", "in": 3.1, "len": 1.0, "joined": True}))


class NoRepairs(unittest.TestCase):
    """Row 6 (V15): the runner path lays no repair; line.py never re-says words."""

    def test_line_runs_no_word_fix(self):
        code = [l for l in (HERE.parent / "machine" / "line.py").read_text().splitlines() if not l.strip().startswith("#")]
        self.assertFalse(any("word_fix.py" in l for l in code))
        self.assertFalse(any("--repairs" in l for l in code))

    def test_repairs_are_a_flag(self):
        import inspect
        self.assertFalse(inspect.signature(EM.build).parameters["repairs"].default)


class TheProductWhereTheBriefPutsIt(unittest.TestCase):
    """Row 20 (V16): the real product photo goes where the scene's frame composition places it; a paid piece keeps
    Meta's safe zone."""

    def test_the_clear_space_clause(self):
        sc = {"frames": [{"composition": "Yai centred at 25 to 75 percent width, 15 to 85 percent height; a clear space on "
                                         "the counter at the lower right, 70 to 85 percent width, 70 to 88 percent height, "
                                         "where three tubes stand", "subject": "Yai at the counter"}]}
        box, why = EM.placed_box(sc)
        self.assertEqual(box, [0.7, 0.7, 0.85, 0.88])
        self.assertIn("clear space", why)

    def test_the_hands_hold_it(self):
        sc = {"frames": [{"composition": "Yai centred at 25 to 75 percent width, 15 to 85 percent height; hands at 45 to 60 "
                                         "percent width, 75 to 88 percent height",
                          "subject": "both hands curled as if gripping three slim upright tubes, the space inside her hands clear"}]}
        self.assertEqual(EM.placed_box(sc)[0], [0.45, 0.75, 0.6, 0.88])

    def test_no_place_named_no_box(self):
        self.assertIsNone(EM.placed_box({"frames": [{"composition": "Yai centred at 25 to 75 percent width, 15 to 85 percent height"}]}))

    def test_paid_keeps_metas_bottom_band_clear(self):
        import placement as PL
        safe = PL.safe_box({**LK.defaults(), "platform_surfaces": {"value": LK.surfaces("paid")}})
        self.assertLessEqual(safe[3], 65.0)                       # Meta Reels ads: bottom 35% free
        box, said = EM._inside([0.7, 0.7, 0.85, 0.88], safe)
        self.assertLessEqual(box[3], safe[3] / 100 + 1e-9)
        self.assertIn("up", said)
        self.assertIn("meta-reels-ads", LK.surfaces("paid"))
        self.assertNotIn("meta-reels-ads", LK.surfaces("organic"))

    def test_placement_reads_the_run(self):
        with tempfile.TemporaryDirectory() as d:
            vm = Path(d)
            (vm / "run.json").write_text(json.dumps({"placement": "organic"}))
            self.assertEqual(LK.placement_of(vm), "organic")
            (vm / "run.json").write_text("{}")
            self.assertEqual(LK.placement_of(vm), "paid")         # the line files a Meta ad card


class CaptionsByApp(unittest.TestCase):
    """Row 9 (V13): the app comes from the piece, the brief, else the swipe's own link."""

    def test_the_swipes_link(self):
        with tempfile.TemporaryDirectory() as d:
            td = Path(d) / "_work" / "x"; (td / "stages").mkdir(parents=True)
            (td / "run.json").write_text(json.dumps({"post_url": "https://www.tiktok.com/@a/video/1"}))
            vm = Path(d) / "prod"; vm.mkdir()
            (vm / "run.json").write_text(json.dumps({"brief_from": str(td / "stages" / "5-brief.md")}))
            self.assertEqual(LK.app_of(vm), "tiktok")
            self.assertEqual(LK.pick_caption(None, LK.app_of(vm)), "tiktok-native")

    def test_the_piece_wins(self):
        with tempfile.TemporaryDirectory() as d:
            vm = Path(d)
            (vm / "plan.json").write_text(json.dumps({"piece": {"app": "Instagram Reels"}}))
            self.assertEqual(LK.app_of(vm), "instagram")

    def test_the_face_check_reads_every_frame(self):
        src = (HERE.parent / "machine" / "audit.py").read_text()
        self.assertIn("TH.scenes(frames)", src)


class SoundWhenCalled(unittest.TestCase):
    """Row 5 (V14): music from the brief or the swipe, the one loudness table, effects mixed."""

    def test_music_called(self):
        self.assertIsNone(EM.music_called({}, {}))
        self.assertIsNone(EM.music_called({"music": [{"what": "none"}]}, {}))
        self.assertTrue(EM.music_called({"music": [{"what": "a lo-fi bed"}]}, {}))
        self.assertTrue(EM.music_called({}, {"music": {"energy": "mid", "mood": "calm"}}))

    def test_no_mix_key_left(self):
        for f in ("edit_map.py", "music_bed.py"):
            self.assertNotIn('["mix"]', (HERE.parent / "machine" / f).read_text(), f)

    def test_render_mixes_the_effects(self):
        self.assertIn('m.get("sfx")', (HERE.parent / "machine" / "render_map.py").read_text())


if __name__ == "__main__":
    unittest.main()
