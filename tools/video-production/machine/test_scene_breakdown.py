"""The scene breakdown and the checks it feeds (2026-10-28). No network: the reader is faked."""
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(f"t_sb_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SB = _load("scene_breakdown")
SP = _load("seedance_prompt")
CR = _load("clips_run")


def _video(path: Path, moving: bool, sound: bool = True):
    # a textured picture; "moving" pans the crop a pixel or two back and forth like a hand holding the phone
    x = "2+2*sin(t*5)" if moving else "2"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=400x712:rate=12:duration=3"]
    if sound:
        cmd += ["-f", "lavfi", "-i", "sine=frequency=300:duration=3"]
    cmd += ["-vf", f"crop=392:704:'{x}':2", "-c:v", "libx264", "-pix_fmt", "yuv420p"]
    cmd += (["-c:a", "aac", "-shortest"] if sound else ["-an"]) + [str(path)]
    subprocess.run(cmd, check=True)


class CameraDrift(unittest.TestCase):
    """Held or propped is measured on the frames, never read by a model."""
    def test_a_still_frame_is_propped_and_a_drifting_one_is_held(self):
        with tempfile.TemporaryDirectory() as d:
            still, held = Path(d) / "still.mp4", Path(d) / "held.mp4"
            _video(still, False)
            _video(held, True)
            self.assertFalse(SB.camera_drift(still)["held"])
            got = SB.camera_drift(held)
            self.assertTrue(got["held"])
            self.assertIn("Held by a hand", got["line"])


class Prompt(unittest.TestCase):
    def test_the_breakdown_goes_into_the_clip_prompt_and_the_judge(self):
        rec = {"camera": ["Held by a hand, a subtle drift."], "gaze": ["Looks down at her hands at 0:02."],
               "props": ["The lemon is dropped into the pitcher."], "continuity": [], "actions": ["Drops the lemon."],
               "manner": ["Lifts each item smoothly to chest height, eyes on it."],
               "atmosphere": ["Steam rises at 0:04."], "sound": ["A thud."], "must_match": ["Steam rises after the pour."]}
        lines = SB.prompt_lines(rec)
        for want in ("Held by a hand", "Looks down at her hands", "Lifts each item smoothly", "Steam rises"):
            self.assertIn(want, lines)
        self.assertNotIn("lemon", lines, "the swipe's own objects never go into our clip")
        self.assertNotIn("thud", lines, "sound is laid by the edit, not asked of the clip")
        self.assertIn("Steam rises after the pour", SB.judge_lines(rec))

    def test_every_clip_prompt_says_props_make_physical_sense(self):
        self.assertIn("Every lid comes off before anything is taken out", SP.PHYSICAL)

    def test_a_call_reads_its_own_scene(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / SB.FILE).write_text(json.dumps({"G02": {"camera": ["x"]}}))
            self.assertEqual(SB.of_call(Path(d), {"id": "G02-C1-t3", "take_of": "G02-C1"}), {"camera": ["x"]})
            self.assertEqual(SB.of_call(Path(d), {"id": "G03-C1"}), {})


class SameObject(unittest.TestCase):
    """An object an earlier approved scene drew is carried into a later scene from that picture."""
    def test_a_later_scene_takes_the_earlier_scenes_picture(self):
        SS = _load("shot_swaps")
        self.assertEqual(SS._object_key("the peppered cheek model from scene 1 on its black base"), "cheek model")
        with tempfile.TemporaryDirectory() as d:
            run = Path(d)
            pic = run / "s1.png"
            pic.write_bytes(b"png")
            (run / "storyboard.json").write_text(json.dumps({"sections": [
                {"id": "G01", "start_frame": {"subject": "two oversized cheek models on black bases"}},
                {"id": "G02", "start_frame": {"subject": "a bowl"}},
                {"id": "G03", "start_frame": {"subject": "the cheek model at her right"}}]}))
            (run / "shot-approvals.json").write_text(json.dumps({"G01": {"picture": str(pic)}}))
            self.assertEqual(SS.earlier_picture(run, "G03", "a cheek model"), pic)
            self.assertIsNone(SS.earlier_picture(run, "G01", "a cheek model"), "never a later or its own scene")
            self.assertIsNone(SS.earlier_picture(run, "G03", "a teacup"))


class PropsInReach(unittest.TestCase):
    """A prop she picks up later in the scene is already in the start picture; one she never handles is not."""
    def test_a_later_pickup_is_in_the_picture(self):
        SS = _load("shot_swaps")
        with tempfile.TemporaryDirectory() as d:
            run = Path(d)
            (run / "plan.json").write_text(json.dumps({"scenes": [{"id": "S9", "beats": [
                {"do": "lifts the tube to her chest"}, {"do": "holds the tablespoon measure up to the lens"},
                {"do": "the paste darkens"}]}]}))
            g = {"id": "G04", "scenes": ["S9"]}
            got = [b for s in SS._scenes_of(run, g) for b in s["beats"]]
            self.assertEqual(len(got), 3)
        got = _swaps_for(SS, SS.PRONOUNS["f"])
        later = next(x["to"] for x in got["swaps"] if x["from"] == "the surface in front of her")
        self.assertIn("within her reach, ready to pick up later; her hands do not hold it yet", later)


def _swaps_for(SS, pron, place="the barber shop"):
    """swap_list on a fake brief: one person with the given pronouns, one place, one prop picked up later, a product."""
    import types
    d = Path(tempfile.mkdtemp())
    (d / "room.jpg").write_bytes(b"x"); (d / "comb.jpg").write_bytes(b"x")
    SS.brief_parts = lambda run, gid: {
        "brand": "anybrand", "section": {"id": gid, "scenes": []},
        "people": [{"id": "sam", "bank": "sam", "says": "", "pron": pron, "look_pic": None, "accessories": []}],
        "places": [{"id": "shop", "bank": "shop", "pic": d / "room.jpg", "name": place}],
        "props": [{"name": "comb", "pic": d / "comb.jpg", "later": True}],
        "start_frame": {"subject": "at the mirror"}, "product": "acme-face-wash"}
    SS._load = lambda name: types.SimpleNamespace(brief_doc=lambda *_: {"scenes": []}, picture_ids=lambda *_: {})
    return SS.swap_list(d, "G01", d / "frame.jpg", ask={"person": "a person", "room": None, "objects": []})


class AgnosticSwaps(unittest.TestCase):
    """The start picture's words name our person as their bank says they are and our place by its own name: no
    pronoun, room or product shape written into the code (2026-10-28)."""
    def test_a_man_is_he_a_woman_is_she_and_unknown_is_they(self):
        for key, poss in (("m", "his"), ("f", "her"), ("x", "their")):
            got = _swaps_for(_load("shot_swaps"), _load("shot_swaps").PRONOUNS[key])
            words = " ".join(str(x["to"]) + " " + str(x["from"]) for x in got["swaps"]) + " " + " ".join(got["stays"])
            self.assertIn(f"{poss} face is exactly {poss} headshot's", words)
            self.assertIn(f"in {poss} hands", got["product_where"])
            for other in {"his", "her", "their"} - {poss}:
                self.assertNotRegex(words, rf"\b{other}\b")

    def test_the_place_is_the_briefs_own_and_the_product_has_no_shape(self):
        words = " ".join(str(x["to"]) for x in _swaps_for(_load("shot_swaps"), _load("shot_swaps").PRONOUNS["m"])["swaps"])
        self.assertIn("the barber shop exactly as the room picture shows it", words)
        self.assertNotIn("kitchen", words)
        self.assertNotIn("tube", words)

    def test_pronouns_come_from_the_bank(self):
        SS = _load("shot_swaps")
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(SS.pronouns(Path(d), "")[0], "they")
            self.assertEqual(SS.pronouns(Path(d), "a barber in his forties")[0], "he")
            (Path(d) / "spec.json").write_text(json.dumps({"gender": "woman", "who": "a man's coat"}))
            self.assertEqual(SS.pronouns(Path(d), "")[0], "she")
            (Path(d) / "spec.json").write_text(json.dumps({"who": "a retired grandmother, her hair in a bun"}))
            self.assertEqual(SS.pronouns(Path(d), "")[2], "her")

    def test_the_product_is_in_the_shot_by_its_own_noun(self):
        src = (HERE / "shot_swaps.py").read_text()
        self.assertNotIn("scrub", src.split("in_shot = ")[1].split("\n")[0])


class BodyCheck(unittest.TestCase):
    """A third arm or an oversized hand fails; a normal body passes; an unreadable file is not checked."""
    def test_the_verdict(self):
        BC = _load("body_check")
        three = BC.verdict(json.dumps({"ok": True, "people": [{"arms": 3, "hands": 3}], "problems": []}))
        self.assertFalse(three["ok"], "a third arm fails even when the reader says ok")
        big = BC.verdict(json.dumps({"ok": False, "people": [{"arms": 2, "hands": 2, "oversized_hand": True}],
                                     "problems": [{"what": "huge hand"}]}))
        self.assertFalse(big["ok"])
        self.assertEqual(big["problems"], ["huge hand"])
        fine = BC.verdict(json.dumps({"ok": True, "people": [{"arms": 2, "hands": 2}]}))
        self.assertTrue(fine["ok"])
        with tempfile.TemporaryDirectory() as d:
            junk = Path(d) / "x.mp4"
            junk.write_bytes(b"not a video")
            self.assertEqual(BC.check(Path(d), junk), {})

    def test_a_wrong_body_fails_the_take(self):
        judged = {"score": 9, "pass": True, "problems": []}
        row = {"line_check": {"verdict": "PASS"}, "body": {"ok": False, "problems": ["a third arm under the bowl"]}}
        got = CR.score_take(row, judged, True)
        self.assertFalse(got["pass"])
        self.assertIn("body: a third arm under the bowl", got["why"])


class Voice(unittest.TestCase):
    """A talking take must carry the voice."""
    def test_a_silent_talking_take_fails_and_a_voiced_one_does_not(self):
        with tempfile.TemporaryDirectory() as d:
            mute, voiced = Path(d) / "mute.mp4", Path(d) / "voiced.mp4"
            _video(mute, False, sound=False)
            _video(voiced, False, sound=True)
            judged = {"score": 9, "pass": True, "problems": []}
            row = {"line_check": {"verdict": "PASS"}}
            self.assertFalse(CR.score_take({**row, "heard": CR.heard(mute)}, judged, True)["pass"])
            self.assertTrue(CR.score_take({**row, "heard": CR.heard(voiced)}, judged, True)["pass"])
            self.assertTrue(CR.score_take({**row, "heard": CR.heard(mute)}, judged, False)["pass"], "a silent clip may be silent")


if __name__ == "__main__":
    unittest.main()
