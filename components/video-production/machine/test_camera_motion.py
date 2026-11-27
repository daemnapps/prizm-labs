#!/usr/bin/env python3
"""The camera and motion station (2026-11-20) and the stops fixed with it: every scene's plan comes from the
director's pick and reaches every clip prompt; a clip without one is a problem the live door refuses; production reads
the manifest without writing the accepted brief; a pending style name does not stop a run; a picture with no 3D print
is listed (dry run) instead of ending the picture step.

    python3 components/video-production/machine/test_camera_motion.py
"""
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import camera_motion as CM  # noqa: E402


def _mod(path, name):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


SCENES = [
    {"id": "S1", "kind": "talking", "director": {"title": "Demolition", "rung": "L5", "premise": "a demolition"},
     "happens": "counts down", "shots": [{"id": "S1.1", "angle": "front, eye level", "camera_move": "handheld"},
                                         {"id": "S1.2", "angle": "low on the shin", "camera_move": "push-in"}],
     "beats": [{"id": "B1", "who": "THE CROWD", "do": "lifts their hands", "action": "THE CROWD lifts their hands",
                "over": "Three, two, one,", "camera": "held"},
               {"id": "B2", "who": "RUTH", "do": "rips the strip", "action": "RUTH rips the strip down",
                "over": "go!", "camera": "push-in"}],
     "last_frame": {"camera": "push-in to close on the shin"}},
    {"id": "S2", "kind": "broll", "shots": [{"id": "S2.1", "angle": "low", "camera_move": "hold"}],
     "beats": [{"id": "B1", "do": "rubs the paste", "action": "she rubs the paste"}]},          # no director pick
    {"id": "S3", "kind": "endcard"},
]
PICKS = {"S1": {"kept": {"title": "Demolition"},
                "pitches": [{"title": "Demolition", "movement": "B1 a wave of hands, B2 the dust burst"}]}}


def make_run(tmp, scenes=SCENES, picks=PICKS):
    wr = Path(tmp) / "writing"
    (wr / "stages").mkdir(parents=True)
    (wr / "director").mkdir()
    brief = wr / "stages" / "5-brief.md"
    brief.write_text("# brief\n\n```json\n" + json.dumps({"piece": {}, "scenes": scenes}) + "\n```\n")
    (wr / "director" / "picks.json").write_text(json.dumps({"picks": picks}))
    run = Path(tmp) / "run"
    run.mkdir()
    (run / "run.json").write_text(json.dumps({"brief_from": str(brief)}))
    return run, brief


def call(cid, scenes, prompt="Image 1 is the first frame.\n\nShe does it.\n\nConstant throughout: one take."):
    return {"id": cid, "section": "Section 1", "scenes": scenes, "prompt": prompt,
            "seedance": {"prompt": prompt}, "params": {"prompt": prompt}}


class CameraMotion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cm_")
        self.run, self.brief = make_run(self.tmp)

    def test_every_scene_is_planned_from_the_directors_pick(self):
        res = CM.plan(self.run)
        self.assertEqual(list(res["scenes"]), ["S1"])
        self.assertIn("S2", res["held"])                      # no director pick: held, with the reason
        self.assertIn("director", res["held"]["S2"])
        self.assertNotIn("S3", res["scenes"])                 # an endcard gets no clip and no plan
        w = res["scenes"]["S1"]["words"]
        for bit in ("Demolition", "front, eye level, handheld", "low on the shin, push-in", "B1 a wave of hands",
                    'over "go!": RUTH rips the strip down (camera: push-in)', "it ends push-in to close on the shin"):
            self.assertIn(bit, w)
        self.assertTrue((self.run / "clips" / "camera-motion.json").is_file())
        self.assertTrue((self.run / "clips" / "CAMERA-MOTION.md").is_file())

    def test_a_swipe_use_rule_that_cannot_load_stops_the_plan(self):
        # owner ruling 2026-11-20: retry then fail loudly — never a guessed "swipe on"
        from unittest import mock
        real = importlib.util.spec_from_file_location

        def broken(name, path, *a, **k):
            if name == "cm_swipe_use":
                raise OSError("swipe_use.py unreadable")
            return real(name, path, *a, **k)
        with mock.patch("importlib.util.spec_from_file_location", broken):
            with self.assertRaises(SystemExit) as cm:
                CM.plan(self.run)
        self.assertIn("swipe-use rule could not load", str(cm.exception))
        self.assertFalse((self.run / "clips" / "camera-motion.json").exists())

    def test_the_plan_carries_the_swipes_motion_pattern_and_the_directors_pick(self):
        wr = self.brief.parent.parent
        (wr / "framemap").mkdir()
        (wr / "framemap" / "framemap.json").write_text(json.dumps({"shots": [
            {"id": "K01", "start": 2.0, "seconds": 6.0, "map": {
                "camera": {"held": "handheld", "move": "slight drift", "height": "eye level"},
                "moments": [{"t": 2.0, "who": "Waxer 1", "does": "applies red wax to the armpit"},
                            {"t": 5.5, "who": "Waxer 1", "does": "pulls the strip down fast"}]}}]}))
        sc = json.loads(json.dumps(SCENES[0]))
        sc["shots"][0]["copies"] = "K01"
        sc["shots"][0]["camera_why"] = "the swipe's camera"
        self.brief.write_text("```json\n" + json.dumps({"piece": {}, "scenes": [sc]}) + "\n```\n")
        p = CM.plan(self.run)["scenes"]["S1"]
        self.assertEqual(p["sources"], ["the swipe's motion pattern (frame map)", "the director's pick (5d)"])
        self.assertEqual(p["motion"]["swipe"][0]["camera"], "handheld, slight drift, eye level")
        self.assertEqual([m["at"] for m in p["motion"]["swipe"][0]["moments"]], [0.0, 3.5])   # on the shot's clock
        w = p["words"]
        self.assertIn("The swipe's motion pattern, the base", w)
        self.assertIn("0.0 s applies red wax to", w)
        self.assertNotIn("Waxer", w)                                          # the swipe's people are never named
        self.assertIn("(the swipe's camera)", w)
        self.assertIn("Demolition", w)                                        # and the director's pick beside it

    def test_a_swipe_with_no_frame_map_gives_its_camera_from_the_teardown_table(self):
        rows = [{"shot": "W01", "start": 0.0, "end": 7.0, "camera": "Propped, front, eye level, static"},
                {"shot": "W02", "start": 7.0, "end": 16.0, "camera": "Handheld, close"}]
        pat = CM.pattern_from_rows({"source": "Demonstration 0:07 - 0:16 · the press"}, rows)
        self.assertEqual([x["shot"] for x in pat], ["W02"])
        self.assertEqual(pat[0]["camera"], "Handheld, close")
        p, _ = CM.scene_plan(dict(SCENES[0]), None, None, pat)
        self.assertEqual(p["sources"][0], "the swipe's camera (teardown table)")
        self.assertIn("W02 — camera Handheld, close", p["words"])

    def test_a_split_scene_is_planned_from_its_own_sides(self):
        side = lambda move: {"shots": [{"id": "x.1", "angle": "above", "camera_move": move}],
                             "beats": [{"id": "B1", "do": "lifts it", "action": "the crust lifts off"}]}
        p, why = CM.scene_plan({"id": "S5", "kind": "split", "split": {"left": side("hold"), "right": side("push-in")}})
        self.assertIsNone(why)
        self.assertEqual(p["sides"], ["left", "right"])
        self.assertIn("S5 left", p["words"])
        self.assertIn("S5 right", p["words"])
        self.assertIn("push-in", p["words"])

    def test_a_split_call_carries_only_the_side_its_pictures_show(self):
        side = lambda move, sid: {"shots": [{"id": sid, "angle": "above", "camera_move": move}],
                                  "beats": [{"id": "B1", "do": "acts", "action": "the " + sid + " acts"}]}
        p, _ = CM.scene_plan({"id": "S5", "kind": "split", "split": {"left": side("hold", "S5.L1"),
                                                                     "right": side("push-in", "S5.R1")}})
        w = CM.words_for(p, {"start_frame": "S5-F1", "shot_pictures": []})
        self.assertIn("S5.L1", w)
        self.assertNotIn("S5.R1", w)                                   # the right side has no picture in this call
        w2 = CM.words_for(p, {"start_frame": "S5-F1", "shot_pictures": [{"shot": "S5.R1"}]})
        self.assertIn("S5.R1", w2)

    def test_a_scene_with_no_camera_or_no_beat_is_held(self):
        p, why = CM.scene_plan({"id": "S9", "director": {"title": "x"}, "beats": [{"do": "moves"}]})
        self.assertIsNone(p)
        self.assertIn("camera", why)
        p, why = CM.scene_plan({"id": "S9", "director": {"title": "x"}, "shots": [{"angle": "low"}], "beats": []})
        self.assertIsNone(p)
        self.assertIn("beats", why)

    def test_the_plan_reaches_every_clip_prompt_and_a_clip_without_one_is_a_problem(self):
        CM.plan(self.run)
        (self.run / "clips" / "plan.json").write_text(json.dumps(
            {"route": "seedance", "calls": [call("G01-C1", ["S1"]), call("G02-C1", ["S2"])], "problems": []}))
        added = CM.apply(self.run)
        res = json.loads((self.run / "clips" / "plan.json").read_text())
        c1, c2 = res["calls"]
        self.assertIn("CAMERA AND MOTION", c1["prompt"])
        self.assertEqual(c1["prompt"], c1["seedance"]["prompt"])      # one text: the clip gate's SENT check holds
        self.assertEqual(c1["prompt"], c1["params"]["prompt"])
        self.assertLess(c1["prompt"].index("CAMERA AND MOTION"), c1["prompt"].index("Constant throughout"))
        self.assertTrue(c1["camera_motion"]["ok"])
        self.assertFalse(c2["camera_motion"]["ok"])
        self.assertNotIn("CAMERA AND MOTION", c2["prompt"])
        self.assertEqual(len(added), 1)
        self.assertTrue(any("G02-C1" in p for p in res["problems"]))  # clips_run.run_live stops on problems
        self.assertEqual(CM.missing(self.run), ["G02-C1"])
        CM.apply(self.run)                                             # stamping twice keeps one block
        again = json.loads((self.run / "clips" / "plan.json").read_text())["calls"][0]["prompt"]
        self.assertEqual(again.count("CAMERA AND MOTION ("), 1)

    def test_shot_pictures_are_named_in_the_prompt_in_send_order(self):
        pr = "Image 1 is the first frame and shows her.\nImage 2 is a reference for her face.\n\nShe works."
        out = CM.bind_shot_pictures(pr, [{"shot": "S4.2", "job": "it opens on it"}, {"shot": "S4.3", "job": "x"}])
        lines = out.split("\n")
        self.assertEqual(lines[1], "Image 2 is the opening picture of shot S4.2: it opens on it.")
        self.assertEqual(lines[2], "Image 3 is the opening picture of shot S4.3: x.")
        self.assertEqual(lines[3], "Image 4 is a reference for her face.")          # the references move down
        self.assertEqual(CM.bind_shot_pictures(out, [{"shot": "S4.2"}]), out)        # bound once

    def test_no_plan_at_all_refuses_every_clip(self):
        (self.run / "clips").mkdir()
        (self.run / "clips" / "plan.json").write_text(json.dumps({"calls": [call("G01-C1", ["S1"])], "problems": []}))
        self.assertEqual(len(CM.apply(self.run)), 1)
        self.assertEqual(CM.main(["check", str(self.run)]), 1)


class ManifestReadOnly(unittest.TestCase):
    """Production's manifest re-check never writes the accepted brief (its hash binds the writing acceptance)."""

    def test_a_production_read_leaves_the_brief_byte_for_byte(self):
        mf = _mod(HERE.parents[1] / "video-writing" / "machine" / "manifest.py", "t_manifest")
        tmp = Path(tempfile.mkdtemp(prefix="mf_"))
        (tmp / "stages").mkdir()
        brief = tmp / "stages" / "5-brief.md"
        brief.write_text("# brief\n\n```json\n" + json.dumps({"piece": {}, "scenes": [{"id": "S1", "voice": "Hi."}]})
                         + "\n```\n")
        (tmp / "run.json").write_text(json.dumps({"brand": "_fixture"}))
        (tmp / "stages" / "2-spec.md").write_text("# spec\n")         # production re-checks only a run with a spec
        before = hashlib.sha256(brief.read_bytes()).hexdigest()
        ok, missing = mf.check(tmp, "_fixture", "5-brief.md", write=False, stamp_brief=False)
        self.assertEqual(hashlib.sha256(brief.read_bytes()).hexdigest(), before)
        self.assertFalse((tmp / "manifest.json").exists())
        self.assertFalse((tmp / "manifest-reviews").exists())
        self.assertIn("note", mf.LAST)                                  # the judge was not asked, and it says so


class PendingStyleName(unittest.TestCase):
    def test_an_unknown_style_is_never_set_and_a_define_is_still_refused(self):
        mc = _mod(HERE / "make_character.py", "t_make_character")
        self.assertIsNone(mc.style_lock("unknown"))
        with self.assertRaises(SystemExit):
            mc.style_lock("new:phone-real-hands-and-voiceover")        # a DEFINE waits for its row
        with self.assertRaises(SystemExit):
            mc.style_lock("not-a-style-row")


class WalkNeedsItsOwnRoot(unittest.TestCase):
    def test_walk_refuses_without_a_runs_root_and_dry_run_stays_the_preview(self):
        import subprocess
        tmp = Path(tempfile.mkdtemp(prefix="walk_"))
        src = tmp / "plan.json"
        src.write_text('{"scenes":[]}')
        base = [sys.executable, str(HERE / "run.py"), "start", str(src), "--brand", "fixture", "--format",
                "single-presenter", "--label", "w"]
        r = subprocess.run(base + ["--walk"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 3)
        self.assertIn("--runs-root", r.stderr)
        r = subprocess.run(base + ["--dry-run", "--runs-root", str(tmp / "runs")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('"preview"', r.stdout)
        self.assertFalse((tmp / "runs").exists())


class PicturesWaitForPrints(unittest.TestCase):
    def test_a_refused_picture_is_listed_and_the_next_one_goes_on(self):
        run = _mod(HERE / "run.py", "t_run")
        self.assertTrue(run.is_set_refusal(SystemExit("refuses this picture: its first picture is not a filed 3D "
                                                      "set's kept print (x.jpg)")))
        self.assertFalse(run.is_set_refusal(SystemExit("no OPENAI_API_KEY")))
        tmp = Path(tempfile.mkdtemp(prefix="pw_"))
        (tmp / "run.json").write_text(json.dumps({"brief": "brief-0001"}))
        row = run.held_for_print({"id": "S1-F1"}, "S1-F1", "a picture", tmp, "_fixture", dry_run=True)
        self.assertIsNone(row["request"])                               # a dry run files nothing
        self.assertEqual([w["picture"] for w in run.PRINT_WAITS[str(tmp)]], ["S1-F1"])



class PostEffectWords(unittest.TestCase):
    """The edit-stage effect is matched, not the word (2026-11-20)."""

    def test_a_garment_border_and_a_kept_clear_caption_area_are_not_effects(self):
        import preflight as PF
        self.assertEqual(PF.post_effect_hits("a gold-brocade wrap skirt with a woven border, bare feet"), [])
        self.assertEqual(PF.post_effect_hits("The lower caption area is clear"), [])
        self.assertTrue(PF.post_effect_hits("add a white border"))
        self.assertTrue(PF.post_effect_hits("a border around the frame"))
        self.assertTrue(PF.post_effect_hits("add captions along the bottom"))



class SwipeOff(unittest.TestCase):
    """Owner ruling 2026-11-20: an AI-lane ad copies nothing from the swipe after the script (swipe-use.json)."""

    def setUp(self):
        import swipe_use as SU
        from unittest import mock
        f = Path(tempfile.mkdtemp(prefix="swsw_")) / "swipe-use.json"
        f.write_text(json.dumps({"ai_lane_uses_swipe": False}))               # the switch at "off" for these tests
        m = mock.patch.dict("os.environ", {"VP_SWIPE_USE": str(f)})
        m.start()
        self.addCleanup(m.stop)
        self.switch = f

    def test_the_switch_is_off_for_the_ai_lane_only(self):
        import swipe_use as SU
        self.assertFalse(SU.uses_swipe())
        self.assertTrue(SU.off({"lane": "ai"}))
        self.assertFalse(SU.off({"lane": "mix"}))
        self.assertFalse(SU.off({}))

    def test_a_picture_loses_every_swipe_frame_and_its_binding_words(self):
        import swipe_use as SU
        it = {"id": "S1-F1", "swipe_camera": "K01",
              "medias": [{"role": "image_references", "value": "/x/framemap/shots/K01-camera.jpg"},
                         {"role": "image_references", "value": "runs/ai-elements/b/casting/yai/master.png"}],
              "params": {"prompt": "Yai at the stall. The swipe composition reference (K01) is a starting point for "
                                   "composition only. Warm light."}}
        it, gone = SU.strip(it)
        self.assertEqual(gone, ["/x/framemap/shots/K01-camera.jpg"])
        self.assertEqual([m["value"] for m in it["medias"]], ["runs/ai-elements/b/casting/yai/master.png"])
        self.assertNotIn("swipe", it["params"]["prompt"].lower())
        self.assertNotIn("swipe_camera", it)

    def test_a_clip_carrying_swipe_footage_is_a_problem(self):
        tmp = tempfile.mkdtemp(prefix="swoff_")
        scenes = [dict(SCENES[0])]
        run, brief = make_run(tmp, scenes=scenes)
        doc = {"lane": "ai", "piece": {}, "scenes": scenes}
        brief.write_text("```json\n" + json.dumps(doc) + "\n```\n")
        res = CM.plan(run)
        self.assertTrue(res["swipe_off"])
        c = call("G01-C1", ["S1"])
        c["refs"] = [{"file": "/w/framemap/shots/K01.mp4"}]
        (run / "clips" / "plan.json").write_text(json.dumps({"calls": [c], "problems": []}))
        added = CM.apply(run)
        self.assertTrue(any("carries the swipe" in p for p in added))

    def test_no_swap_route_with_the_swipe_off(self):
        import route_facts as RF
        import inspect
        self.assertIn("swipe", inspect.signature(RF.write).parameters)


if __name__ == "__main__":
    unittest.main()
