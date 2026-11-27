"""The edit's two review points under the ruling of 2026-11-18: timeline and captions approval sit with the video
editor role, the owner steps in only on a trip-wire, so `start` goes straight through by default and still writes both
pages; `--stops` brings the two waits back. Nothing renders: the render, the pages and the checks are fakes, and the
run lives in the test's own runs root."""
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

MACHINE = Path(__file__).resolve().parents[1] / "machine"
sys.path.insert(0, str(MACHINE))
import run as R  # noqa: E402

SHEET = {"meta": {"brand": "b", "label": "l", "format": "single-presenter"}, "cut_by": "the test",
         "picture": [{"id": "s01", "start": 0.0, "duration": 2.0, "roll": "a", "why": "carries the line"}],
         "captions": {"words": []}, "controls": {"captions": {"value": "on"}}}
KIT = {"format": "single-presenter", "clips": [{"id": "s01", "src": "a.mp4", "roll": "a", "approved": True, "talks": True}]}


class Stops(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ve_straight_")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.kit = self.tmp / "kit"
        self.kit.mkdir()
        self.renders = []

        def render(run, kit_dir, sheet, name, captions, quality, out=None):
            self.renders.append(name)
            f = out or run / "work" / f"{name}.mp4"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"video")
            return f

        def page(run, sheet, stage, video=None, checks=None):
            f = run / "timeline.html"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(f"<h1>{stage}</h1>{video.name if video else ''}")
            return f

        fake_rt = types.ModuleType("retention")
        fake_rt.check = lambda sheet, final=None: {}
        fake_rt.lines = lambda rt: []
        fake_au = types.ModuleType("audit")
        fake_au.audit_sheet = lambda sheet, kit_dir, final, kit: {"found": []}
        fake_td = types.ModuleType("to_drive")
        fake_td.hand = lambda run: None
        patches = [
            mock.patch.object(R, "gather", lambda kit_dir: (json.loads(json.dumps(KIT)), [])),
            mock.patch.object(R, "auto_cut", lambda *a, **k: json.loads(json.dumps(SHEET))),
            mock.patch.object(R.A, "assemble", lambda *a, **k: None),
            mock.patch.object(R, "helpers_pass", lambda *a, **k: None),
            mock.patch.object(R.CS, "check", lambda sheet, kit_dir: []),
            mock.patch.object(R.CS, "warnings", lambda sheet: []),
            mock.patch.object(R, "render", render),
            mock.patch.object(R.TP, "write", page),
            mock.patch.object(R, "final_checks", lambda final, sheet: [{"check": "length", "pass": True, "detail": "ok"}]),
            mock.patch.object(R.subprocess, "run", mock.Mock(side_effect=OSError("no renders in a test"))),
            mock.patch.dict(sys.modules, {"retention": fake_rt, "audit": fake_au, "to_drive": fake_td}),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.run = self.tmp / "runs" / "b" / "l"

    def start(self, *extra):
        return R.main(["start", str(self.kit), "--brand", "b", "--label", "l", "--runs-root", str(self.tmp / "runs"),
                       "--cut", "auto", *extra])

    def state(self):
        return json.loads((self.run / "run.json").read_text())

    def test_the_default_goes_straight_through_and_still_writes_both_pages(self):
        self.assertEqual(self.start(), 0)
        st = self.state()
        self.assertEqual(st["stops"], {"timeline": "approved", "captions": "approved"})
        self.assertEqual(self.renders, ["final"], "no draft is rendered for a stop nobody waits at")
        for name, stage in (("stop-1-timeline.html", "timeline"), ("stop-2-captions.html", "captions")):
            self.assertIn(f"<h1>{stage}</h1>", (self.run / name).read_text())
        self.assertIn("<h1>done</h1>", (self.run / "timeline.html").read_text())
        self.assertEqual(st["steps"]["export"]["state"], "done")
        self.assertEqual(st["stop_pages"], ["stop-1-timeline.html", "stop-2-captions.html"])

    def test_the_record_says_nobody_waited_and_whose_the_review_is(self):
        self.start()
        rows = self.state()["approvals"]
        self.assertEqual([r["stop"] for r in rows], ["timeline", "captions"])
        for r in rows:
            self.assertEqual(r["by"], "the line")
            self.assertIn("video editor role", r["note"])
            self.assertIn("ruled 2026-11-18", r["note"])
            self.assertIn("nobody waited", r["note"])
        self.assertIn("straight through", self.state()["stops_mode"])

    def test_with_stops_the_run_waits_at_the_timeline_then_the_captions(self):
        self.assertEqual(self.start("--stops"), 0)
        self.assertEqual(self.state()["stops"], {"timeline": "waiting"})
        self.assertEqual(self.renders, ["rough-cut"])
        self.assertFalse((self.run / "stop-1-timeline.html").exists())
        R.main(["approve", str(self.run), "timeline"])
        self.assertEqual(self.start("--stops", "--from", "gate"), 0)
        self.assertEqual(self.state()["stops"], {"timeline": "approved", "captions": "waiting"})
        self.assertEqual(self.renders, ["rough-cut", "captioned"])
        R.main(["approve", str(self.run), "captions"])
        self.assertEqual(self.start("--stops", "--from", "gate"), 0)
        self.assertEqual(self.renders, ["rough-cut", "captioned", "final"])
        self.assertNotIn("the line", [r.get("by") for r in self.state()["approvals"]])

    def test_a_red_gate_still_holds_the_run(self):
        """The trip-wire is the check that already holds a run: straight through never means past a red gate."""
        with mock.patch.object(R.CS, "check", lambda sheet, kit_dir: ["kit.clips (s01): a hole in the picture"]):
            self.assertEqual(self.start(), 1)
        self.assertEqual(self.renders, [])
        self.assertFalse((self.run / "stop-1-timeline.html").exists())

    def test_a_held_final_check_still_fails_the_run(self):
        with mock.patch.object(R, "final_checks", lambda final, sheet: [{"check": "length", "pass": False, "detail": "short"}]):
            self.assertEqual(self.start(), 1)
        self.assertFalse(self.state()["steps"]["checks"]["passed"])

    def test_the_learn_step_runs_last_and_calls_no_model_without_changes(self):
        self.start()
        step = self.state()["steps"]["learn"]
        self.assertEqual(step["state"], "done")
        self.assertEqual(step["lessons"], 0)
        self.assertIn("nothing to learn", step["note"])

    def test_the_settings_and_their_reasons_are_on_the_trail(self):
        self.start()
        rows = {r["decision"]: r for r in self.state()["trail"] if r["stage"] == "edit"}
        self.assertEqual(rows["the caption look"]["choice"], "tiktok-native")
        self.assertEqual(rows["the pace"]["choice"], "whole")
        for r in rows.values():
            self.assertTrue(r["why"].strip())
            self.assertTrue(r["by"].strip())

    def test_the_declared_steps_say_who_reviews_and_that_nothing_waits(self):
        steps = {s["id"]: s for s in json.loads((MACHINE / "steps.json").read_text())["steps"]}
        for sid in ("timeline", "captions"):
            self.assertEqual(steps[sid]["who"], "video-editor")
            self.assertFalse(steps[sid]["stop"])
            self.assertIn("2026-11-18", steps[sid]["ruled"])

    def test_a_caller_that_says_nothing_goes_straight_through(self):
        """The hand-off road and any door that builds its own arguments: straight unless it asks for the waits."""
        self.assertTrue(R.straight_through(types.SimpleNamespace()))
        self.assertTrue(R.straight_through(types.SimpleNamespace(straight=True)))
        self.assertFalse(R.straight_through(types.SimpleNamespace(straight=False)))


if __name__ == "__main__":
    unittest.main()
