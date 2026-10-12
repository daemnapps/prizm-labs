#!/usr/bin/env python3
"""python3 machine/test_safezone.py — from any cwd. Stdlib unittest; no
network, no paid call. The vision judge is a stub caller; the stills door is a
fake that writes a real picture.

THE SUBJECT ZONE (the owner, 2026-09-23): every still production makes has its
face / product / hands inside the centred 4:5 zone of the 9:16 frame. The box
is asked of a vision model; the zone is geometry; a frame outside it gets ONE
fix edit and is measured again; still outside, it is held — no clip, no pack.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"test_sz_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sz = load("safezone")
run = load("run")
preflight = load("preflight")
STILL_MODEL = (run.platform.registry().get("doors") or {})["still"]["model"]

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:                                   # pragma: no cover
    HAVE_PIL = False


def picture(path: Path, size=(1024, 1536), colour=(120, 90, 70)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, colour).save(path)
    return path


def answer(*boxes) -> str:
    return json.dumps({"subjects": [
        {"what": w, "label": w, "x_pct": x, "y_pct": y, "w_pct": bw, "h_pct": bh}
        for (w, x, y, bw, bh) in boxes]})


IN_ZONE = answer(("face", 35, 25, 30, 20))
FACE_HIGH = answer(("face", 35, 3, 30, 18))            # the top of the head in the top 15%
PRODUCT_LOW = answer(("face", 35, 25, 30, 20), ("product", 40, 80, 20, 18))


class Stub:
    """caller(prompt, image_path, entry) -> str, answering in order."""
    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def __call__(self, prompt, img, entry):
        self.calls.append((prompt, img))
        a = self.answers.pop(0)
        if isinstance(a, BaseException):
            raise a
        return a


class Geometry(unittest.TestCase):
    def test_a_9x16_still_zone_is_the_middle_70_percent(self):
        g = sz.zone_of(1080, 1920)
        self.assertEqual(g["frame"], {"x_pct": 0.0, "y_pct": 0.0, "w_pct": 100.0, "h_pct": 100.0})
        self.assertAlmostEqual(g["zone"]["y_pct"], 14.84, places=2)
        self.assertAlmostEqual(g["zone"]["h_pct"], 70.31, places=2)
        self.assertEqual(g["zone"]["w_pct"], 100.0)

    def test_a_2x3_still_is_read_as_the_clip_frames_it(self):
        # the stills door makes 1024x1536; the 9:16 clip is its centred crop
        g = sz.zone_of(1024, 1536)
        self.assertAlmostEqual(g["frame"]["x_pct"], 7.81, places=2)
        self.assertAlmostEqual(g["zone"]["w_pct"], 84.38, places=2)
        self.assertAlmostEqual(g["zone"]["y_pct"], 14.84, places=2)

    def test_to_frame_maps_a_still_box_onto_the_9x16_frame(self):
        g = sz.zone_of(1024, 1536)
        b = sz.to_frame({"x_pct": 7.81, "y_pct": 10, "w_pct": 84.38, "h_pct": 20, "what": "face"},
                        g["frame"])
        self.assertAlmostEqual(b["x_pct"], 0.0, places=1)
        self.assertAlmostEqual(b["w_pct"], 100.0, places=1)
        self.assertEqual((b["y_pct"], b["h_pct"], b["what"]), (10.0, 20.0, "face"))

    def test_outside_has_a_small_tolerance_and_no_more(self):
        z = sz.zone_of(1080, 1920)["zone"]
        self.assertFalse(sz.outside({"x_pct": 10, "y_pct": 14, "w_pct": 20, "h_pct": 20}, z))
        self.assertTrue(sz.outside({"x_pct": 10, "y_pct": 10, "w_pct": 20, "h_pct": 20}, z))
        self.assertTrue(sz.outside({"x_pct": 10, "y_pct": 70, "w_pct": 20, "h_pct": 20}, z))


class ThePrompt(unittest.TestCase):
    def test_the_prompt_is_read_from_its_file_and_asks_where_not_whether(self):
        self.assertEqual(sz.prompt_path().name, "stage5-subject-zone-v1-damon.md")
        body = sz.prompt_text()
        self.assertIn('"subjects"', body)
        self.assertNotIn("```delta", body)           # the fix line is never sent to the judge

    def test_the_fix_is_one_change_naming_what_was_outside_and_the_zone(self):
        r = {"zone": sz.zone_of(1080, 1920)["zone"], "outside": ["face"]}
        d = sz.move_delta(r)
        self.assertIn("Move the face", d)
        self.assertIn("between 15% and 85%", d)


@unittest.skipUnless(HAVE_PIL, "PIL not on this machine")
class TheCheck(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="vm-sz-"))
        self.addCleanup(shutil.rmtree, self.d, True)
        self.still = picture(self.d / "S1-F1.png")

    def test_pass_records_the_face_box_on_the_9x16_frame(self):
        r = sz.check(self.still, caller=Stub(IN_ZONE), entry={"vendor_model": "stub"})
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["subject_box"]["what"], "face")
        self.assertEqual(set(r["subject_box"]), {"x_pct", "y_pct", "w_pct", "h_pct", "what"})

    def test_the_face_comes_first_whatever_order_the_judge_answers_in(self):
        a = answer(("product", 40, 60, 20, 15), ("face", 35, 25, 30, 20))
        r = sz.check(self.still, caller=Stub(a), entry={})
        self.assertEqual(r["subject_box"]["what"], "face")

    def test_fail_names_what_crossed_out(self):
        r = sz.check(self.still, caller=Stub(PRODUCT_LOW), entry={})
        self.assertEqual((r["verdict"], r["outside"]), ("FAIL", ["product"]))

    def test_an_empty_plate_passes_with_no_box(self):
        r = sz.check(self.still, caller=Stub(answer()), entry={})
        self.assertEqual((r["verdict"], r["subject_box"]), ("PASS", None))

    def test_a_judge_that_did_not_run_is_not_a_pass(self):
        r = sz.check(self.still, caller=Stub(SystemExit("no GEMINI_API_KEY")), entry={})
        self.assertEqual(r["verdict"], "UNCHECKED")
        r = sz.check(self.still, caller=Stub("I think it is fine"), entry={})
        self.assertEqual(r["verdict"], "UNCHECKED")
        r = sz.check(self.still, caller=Stub(answer(("face", 35, 90, 30, 40))), entry={})
        self.assertEqual(r["verdict"], "UNCHECKED")          # a box off the picture is unreadable

    def test_which_items_are_frames(self):
        self.assertTrue(sz.is_frame({"kind": "still", "frame_role": "first"}))
        self.assertTrue(sz.is_frame({"kind": "edit", "frame_role": "last"}))
        self.assertTrue(sz.is_frame({"kind": "still", "frame_role": "plate"}))
        self.assertTrue(sz.is_frame({"kind": "edit", "frame_role": "packshot"}))
        self.assertTrue(sz.is_frame({"kind": "still", "id": "A1-still"}))
        self.assertFalse(sz.is_frame({"kind": "cast", "id": "cast"}))
        self.assertFalse(sz.is_frame({"kind": "motion", "id": "S1"}))


@unittest.skipUnless(HAVE_PIL, "PIL not on this machine")
class TheMachineHand(unittest.TestCase):
    """run_machine_hand: check every frame, one fix, hold, record."""

    def setUp(self):
        self.r = Path(tempfile.mkdtemp(prefix="vm-sz-run-"))
        self.addCleanup(shutil.rmtree, self.r, True)
        (self.r / "media").mkdir()
        self.cast = picture(self.r / "cast-sheet.png", colour=(200, 180, 160))
        (self.r / "plan.json").write_text(json.dumps({"scenes": [
            {"id": "S1", "frames": [{"role": "first", "n": 1}, {"role": "last", "n": 2}]}]}))
        self.gen_calls = []
        self.motion_calls = []
        orig = run._load
        test = self

        def fake_generate(prompt, refs, out, **kw):
            test.gen_calls.append({"prompt": prompt, "refs": [str(x) for x in refs], "out": str(out)})
            picture(Path(out), colour=(100 + len(test.gen_calls) * 10, 90, 70))
            return {"model": STILL_MODEL, "file": str(out)}

        def fake_motion(prompt, still, end, out, **kw):
            test.motion_calls.append(str(still))
            Path(out).write_bytes(b"clip")
            return {"model": STILL_MODEL, "file": str(out), "task_id": "t"}

        def patched(name):
            mod = orig(name)
            if name == "direct_openai":
                mod.generate = fake_generate
            if name == "direct_byteplus":
                mod.motion = fake_motion
            return mod

        reg = run.platform.registry()
        run._load = patched
        orig_reg = run.platform.registry
        run.platform.registry = lambda: {**reg, "doors": {**reg.get("doors", {}), "motion": {
            **(reg.get("doors") or {}).get("motion", {}), "primary": "direct:byteplus"}}}
        self.addCleanup(setattr, run, "_load", orig)
        self.addCleanup(setattr, run.platform, "registry", orig_reg)

    def items(self):
        return [{"id": "S1-F1", "kind": "still", "frame_role": "first", "for": "S1",
                 "params": {"prompt": "her at the sink"},
                 "medias": [{"role": "image_references", "value": str(self.cast)}]},
                {"id": "S1", "kind": "motion", "params": {"prompt": "she turns", "duration": 5},
                 "medias": [], "start_frame": "S1-F1", "clip_colour": False}]

    def go(self, caller):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            m = run.run_machine_hand(self.items(), self.r, dry_run=False, brand="_fixture",
                                     zone_caller=caller, clip_colour=False)
        return m, out.getvalue()

    def test_a_frame_in_the_zone_ships_its_box_into_the_record_and_the_plan(self):
        m, out = self.go(Stub(IN_ZONE))
        self.assertEqual(m["S1-F1"]["zone"]["verdict"], "PASS")
        self.assertEqual(m["S1-F1"]["subject_box"]["what"], "face")
        self.assertEqual(len(self.gen_calls), 1)                   # no fix edit
        plan = json.loads((self.r / "plan.json").read_text())
        self.assertEqual(plan["subject_boxes"]["S1-F1"]["what"], "face")
        self.assertEqual(plan["scenes"][0]["frames"][0]["subject_box"]["what"], "face")
        self.assertNotIn("subject_box", plan["scenes"][0]["frames"][1])
        v = json.loads((self.r / "verdicts.json").read_text())["S1-F1"]["subject_zone"]
        self.assertEqual(v["verdict"], "PASS")
        self.assertEqual(len(self.motion_calls), 1)

    def test_a_frame_outside_gets_one_edit_frame_first_cast_second_then_passes(self):
        m, out = self.go(Stub(FACE_HIGH, IN_ZONE))
        self.assertEqual(len(self.gen_calls), 2)
        fix = self.gen_calls[1]
        self.assertEqual(fix["refs"][0], str(self.r / "media" / "S1-F1.png"))
        self.assertEqual(fix["refs"][1], str(self.cast))
        self.assertTrue(fix["prompt"].startswith("Move the face"))
        self.assertIn("Change nothing else", fix["prompt"])        # the house keep-line
        self.assertTrue((self.r / "media" / "versions" / "S1-F1-offzone.png").is_file())
        z = m["S1-F1"]["zone"]
        self.assertEqual(z["verdict"], "PASS")
        self.assertEqual(z["remade"]["first_outside"], ["face"])
        self.assertIn("moved into the 4:5 zone by one edit", out)
        ledger = json.loads((self.r / "ledger.json").read_text())
        self.assertIn("S1-F1-zone-fix", [row["job"] for row in ledger])
        self.assertEqual(len(self.motion_calls), 1)

    def test_still_outside_after_one_fix_is_held_no_clip_and_pack_refuses(self):
        m, out = self.go(Stub(FACE_HIGH, FACE_HIGH))
        self.assertEqual(len(self.gen_calls), 2)                   # one fix, never a third try
        self.assertEqual(m["S1-F1"]["zone"]["verdict"], "FAIL")
        self.assertIn("HELD", out)
        self.assertIn("S1: clip NOT made", out)
        self.assertEqual(self.motion_calls, [])
        self.assertNotIn("S1", m)
        (self.r / "lines.json").write_text("{}")
        _u, _d, not_shippable, _c = preflight.coverage(self.r)
        self.assertTrue(any("face outside the 4:5 zone after one fix" in x and "S1-F1" in x
                            for x in not_shippable), not_shippable)

    def test_an_unchecked_frame_makes_its_clip_but_does_not_pack(self):
        m, out = self.go(Stub(SystemExit("no GEMINI_API_KEY")))
        self.assertEqual(m["S1-F1"]["zone"]["verdict"], "UNCHECKED")
        self.assertEqual(len(self.gen_calls), 1)                   # a fix cannot help an unmeasured frame
        self.assertEqual(len(self.motion_calls), 1)
        (self.r / "lines.json").write_text("{}")
        _u, _d, not_shippable, _c = preflight.coverage(self.r)
        self.assertTrue(any("subject zone not checked" in x for x in not_shippable), not_shippable)

    def test_dry_run_calls_nothing_and_states_the_cost(self):
        stub = Stub()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            m = run.run_machine_hand(self.items()[:1], self.r, dry_run=True, brand="_fixture",
                                     zone_caller=stub)
        self.assertEqual((m, stub.calls), ({}, []))
        self.assertIn("S1-F1: subject zone — would send", out.getvalue())
        self.assertIn("1 frame(s) would be checked", out.getvalue())


if __name__ == "__main__":
    unittest.main()
