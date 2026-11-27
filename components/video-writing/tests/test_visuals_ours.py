"""Once the script is written, the swipe's job is done (owner ruling, 2026-11-20). No network, no spend."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "machine"))
from test_director import scene, pitch, score  # noqa: E402
import director as D  # noqa: E402
import visuals  # noqa: E402

ON = {"VISUALS_OURS_OFF": "", "VISUALS_DIRECTOR_BASE": "ours"}        # the staged-fresh mode, kept behind the switch
BASE = {"VISUALS_OURS_OFF": "", "VISUALS_DIRECTOR_BASE": "swipe"}      # the owner's last word, 2026-11-20
ALL_ON = {"on": True, "lanes": {"brief": True, "director": True}}
OFF = {"VISUALS_OURS_OFF": "director"}


def camera_scene():
    sc = scene("S2", "product", "rubs the paste on the shin", ["B1", "B2"])
    sc["shots"] = [{"id": "S2.1", "face": "a look", "angle": "low close-up on the shin", "camera_move": "hold"},
                   {"id": "S2.2", "face": "a look", "angle": "front, medium", "camera_move": "handheld"}]
    sc["beats"][1]["shot"] = "S2.2"
    return sc


def cam_pitch(title, cams, setting=None):
    p = pitch(title, "turns the shin into a race track", ["B1", "B2"])
    p["shots"] = [dict(id=i, face="eyes wide", gestures=["points"], **c) for i, c in cams]
    if setting:
        p["setting_id"] = setting
    return p


OURS = [("S2.1", {"angle": "floor height, macro on the spots", "camera_move": "push in", "camera_why": "the spots loom"}),
        ("S2.2", {"angle": "overhead, wide on both legs", "camera_move": "arc", "camera_why": "reveals the track"})]


@mock.patch.dict(os.environ, ON)
class TheCameraIsOurs(unittest.TestCase):
    def test_the_kept_pitch_writes_each_shots_camera_and_keeps_the_swipes_beside(self):
        sc = camera_scene()
        d = D.decide(sc, [cam_pitch("Race", OURS)], [dict(score("Race", 9), camera=9)])
        self.assertIsNotNone(d["keep"])
        self.assertIn("45/50", d["why"])
        D.apply_pick(sc, d["keep"], "r#S2")
        s1, s2 = sc["shots"]
        self.assertEqual((s1["angle"], s1["camera_move"]), ("floor height, macro on the spots", "push-in"))
        self.assertEqual((s1["angle_swipe"], s1["camera_move_swipe"]), ("low close-up on the shin", "hold"))
        self.assertEqual(s1["camera_why"], "the spots loom")
        self.assertEqual(s2["camera_move"], "arc")

    def test_a_hold_with_no_reason_is_out(self):
        cams = [("S2.1", {"angle": "macro", "camera_move": "hold"}), OURS[1]]
        d = D.decide(camera_scene(), [cam_pitch("Still", cams)], [score("Still", 9)])
        self.assertIsNone(d["keep"])
        self.assertIn("shot S2.1 holds the camera with no reason", d["table"][0]["out"])

    def test_a_hold_that_says_why_passes(self):
        cams = [("S2.1", {"angle": "macro", "camera_move": "hold", "camera_why": "the spot sits, unbudged"}), OURS[1]]
        self.assertIsNotNone(D.decide(camera_scene(), [cam_pitch("Still", cams)], [score("Still", 9)])["keep"])

    def test_the_swipes_camera_copied_shot_for_shot_is_out(self):
        cams = [("S2.1", {"angle": "low close-up on the shin", "camera_move": "hold", "camera_why": "x"}),
                ("S2.2", {"angle": "front, medium", "camera_move": "handheld"})]
        d = D.decide(camera_scene(), [cam_pitch("Copy", cams)], [score("Copy", 9)])
        self.assertIn("the camera is the swipe's, copied shot for shot", d["table"][0]["out"])

    def test_a_shot_with_no_camera_or_a_move_production_cannot_take_is_out(self):
        cams = [("S2.1", {"angle": "macro", "camera_move": "zoom-spin"}), OURS[1]]
        d = D.decide(camera_scene(), [cam_pitch("Odd", cams)], [score("Odd", 9)])
        self.assertTrue(any("S2.1 has no camera" in x for x in d["table"][0]["out"]))

    def test_the_pitch_sets_the_scene_in_one_of_our_places(self):
        sc = camera_scene()
        D.apply_pick(sc, cam_pitch("Race", OURS, "OFFICE"), "r#S2", [{"id": "BATHROOM"}, {"id": "OFFICE"}])
        self.assertEqual((sc["setting_id"], sc["setting_id_swipe"]), ("OFFICE", "BATHROOM"))
        sc = camera_scene()
        D.apply_pick(sc, cam_pitch("Race", OURS, "MOON"), "r#S2", [{"id": "BATHROOM"}])
        self.assertEqual(sc["setting_id"], "BATHROOM")          # a place not in the brief's world is never set


@mock.patch.dict(os.environ, ON)
class TheDirectorIsHandedNoSwipePicture(unittest.TestCase):
    def test_the_card_carries_our_words_and_places_and_nothing_of_the_swipe(self):
        sc = camera_scene()
        sc["happens_swipe"] = "SWIPE STAGING"
        sc["source"] = "K02: the swipe shot"
        sc["shots"][0]["face_swipe"] = "SWIPE FACE"
        sc["beats"][0]["do"] = "SWIPE DO"
        card = D.scene_card(sc, {"world": [{"id": "BATHROOM"}, {"id": "BOAT"}], "roll_sheet": [
            {"scene": "S2", "row": "[shows: SWIPE ROW]"}]})
        # the swipe as understanding (owner, 2026-11-20): what the moment does and why, labelled, never a shot to restage
        self.assertIn("What the swipe does here and why** (understanding only — never a shot to restage): "
                      "K02: the swipe shot · what happened there: SWIPE STAGING", card)
        for word in ("SWIPE FACE", "SWIPE DO", "SWIPE ROW", "backbone", "low close-up on the shin", "today"):
            self.assertNotIn(word, card)
        self.assertIn("BATHROOM, BOAT", card)
        self.assertIn("under \"words B1\"", card)
        self.assertIn("`S2.1`", card)

    def test_the_director_reads_what_the_swipe_does_and_why(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            run = Path(t)
            (run / "stages").mkdir()
            (run / "stages" / "1-teardown.md").write_text(
                "### TABLE\n| shot rows |\n### THE SCENE MECHANICS\nThe rip lands the pain.\n"
                "### THE PSYCHOLOGY\nThe crowd counts down, so you wait for it.\n### THE VOICE FINGERPRINT\nx\n")
            text = D.swipe_understanding(run)
            self.assertIn("The rip lands the pain.", text)
            self.assertIn("so you wait for it", text)
            self.assertNotIn("shot rows", text)
            shared = {"swipe_understanding": text, "rulings": "r"}
            doc = {"scenes": [camera_scene()], "world": [{"id": "BATHROOM"}]}
            with mock.patch.object(D, "fill", side_effect=lambda tpl, vals: tpl + str(vals.get("seed", ""))):
                sent = D.director_prompt(shared, doc, doc["scenes"], 3)
            self.assertIn("**What the swipe does and why** — read it to understand", sent)
            self.assertIn("The rip lands the pain.", sent)

    def test_the_live_prompts_ask_for_the_camera_and_drop_the_backbone(self):
        ask, pick, rulings = D.prompt("storyboard-ask"), D.prompt("pick"), D.prompt("rulings")
        self.assertIn('"camera_move": "push-in|pan|tilt|arc|handheld|hold"', ask)
        self.assertIn('"setting_id"', ask)
        self.assertNotIn("backbone", ask)
        self.assertIn('"camera": 0', pick)
        self.assertIn("We use the swipe as understanding of what is going on", rulings)
        self.assertIn("never restage a swipe", ask.lower())


class TheSwitch(unittest.TestCase):
    def test_one_machine_puts_the_director_back_to_v1(self):
        with mock.patch.dict(os.environ, OFF):
            self.assertFalse(visuals.ours("director"))
            self.assertEqual(visuals.ours("brief"), bool(visuals._cfg()["lanes"]["brief"]))   # the other lane untouched
            self.assertNotIn("camera_move", D.prompt("storyboard-ask"))
            card = D.scene_card(camera_scene(), {})
            self.assertIn("backbone only", card)
            d = D.decide(camera_scene(), [pitch("Plain", "does it", ["B1", "B2"])], [score("Plain", 9)])
            self.assertIsNotNone(d["keep"])                        # no camera asked for, none checked

    def test_the_brief_lane_puts_stage_5_back_to_v17(self):
        import writing_v2 as W
        with mock.patch.object(W.C, "stages", return_value=[]), mock.patch.object(W.C, "known_sources", return_value={}):
            with mock.patch.dict(os.environ, ON), mock.patch.object(visuals, "_cfg", return_value=ALL_ON):
                p = next(x for x in W.plan("fixture", "ai", "") if x["key"] == "stage5")
                self.assertTrue(p["prompt"].endswith("stage5-ai-brief-v18-owner.md"))
            with mock.patch.dict(os.environ, BASE):          # live: the swipe as backbone (owner, 2026-11-20)
                p = next(x for x in W.plan("fixture", "ai", "") if x["key"] == "stage5")
                self.assertTrue(p["prompt"].endswith("stage5-ai-brief-v17-owner.md"))
            with mock.patch.dict(os.environ, {"VISUALS_OURS_OFF": "brief"}):
                p = next(x for x in W.plan("fixture", "ai", "") if x["key"] == "stage5")
                self.assertTrue(p["prompt"].endswith("stage5-ai-brief-v17-owner.md"))

    def test_stage_5_v18_stages_nothing_from_the_swipe_and_keeps_every_slot(self):
        v2 = HERE.parent / "prompts" / "v2"
        new, old = (v2 / "stage5-ai-brief-v18-owner.md").read_text(), (v2 / "stage5-ai-brief-v17-owner.md").read_text()
        import re
        self.assertEqual(set(re.findall(r"\{[a-z_]+\}", new)), set(re.findall(r"\{[a-z_]+\}", old)))
        self.assertIn("ONCE THE SCRIPT IS WRITTEN, THE SWIPE'S JOB IS DONE", new)
        self.assertNotIn("the teardown record's setting and room inventory", new)
        self.assertNotIn("If the source cuts to a shop", new)


@mock.patch.dict(os.environ, BASE)
class TheSwipeIsTheBase(unittest.TestCase):
    """Owner, 2026-11-20: "we use the swipe image to generate our version, and we still extract the motion patterns
    from the swipe to generate our own." """

    def test_the_card_gives_the_swipes_shot_motion_camera_and_why_with_our_places(self):
        sc = camera_scene()
        sc["happens_swipe"] = "SWIPE STAGING"
        sc["source"] = "K02: the swipe shot"
        card = D.scene_card(sc, {"world": [{"id": "BATHROOM"}, {"id": "BOAT"}], "roll_sheet": [
            {"scene": "S2", "row": "[shows: SWIPE ROW]"}]})
        self.assertIn("SWIPE STAGING", card)
        self.assertIn("the swipe's camera (backbone only): low close-up on the shin, hold", card)
        self.assertIn("SWIPE ROW", card)
        self.assertIn("What the swipe does here and why:** K02: the swipe shot", card)
        self.assertIn("BATHROOM, BOAT", card)

    def test_the_prompts_build_on_the_swipes_picture_and_motion_pattern(self):
        ask, pick, rulings = D.prompt("storyboard-ask"), D.prompt("pick"), D.prompt("rulings")
        self.assertIn("That shot is\nthe BASE your idea is built on", ask)
        self.assertIn('"camera_move": "push-in|pan|tilt|arc|handheld|hold"', ask)
        self.assertIn("starts from the swipe's composition and camera", pick)
        self.assertIn("we use the swipe image to generate our version", rulings)

    def test_keeping_the_swipes_camera_passes_and_is_written_with_its_record(self):
        cams = [("S2.1", {"angle": "low close-up on the shin", "camera_move": "hold"}),
                ("S2.2", {"angle": "front, medium", "camera_move": "handheld"})]
        sc = camera_scene()
        d = D.decide(sc, [cam_pitch("Base", cams)], [score("Base", 9)])
        self.assertIsNotNone(d["keep"])
        D.apply_pick(sc, d["keep"], "r#S2")
        self.assertEqual(sc["shots"][0]["camera_move_swipe"], "hold")

    def test_a_shot_still_needs_a_camera_production_can_take(self):
        cams = [("S2.1", {"angle": "macro", "camera_move": "zoom-spin"}), OURS[1]]
        d = D.decide(camera_scene(), [cam_pitch("Odd", cams)], [score("Odd", 9)])
        self.assertIsNone(d["keep"])

    def test_the_seed_reads_the_swipe_with_its_shots(self):
        doc = {"scenes": [camera_scene()], "world": [{"id": "BATHROOM"}]}
        with mock.patch.object(D, "fill", side_effect=lambda tpl, vals: tpl + str(vals.get("seed", ""))):
            sent = D.director_prompt({"swipe_understanding": "WHY IT WORKS", "rulings": "r"}, doc, doc["scenes"], 3)
        self.assertIn("read it with each scene's swipe shot", sent)
        self.assertIn("WHY IT WORKS", sent)


if __name__ == "__main__":
    unittest.main()
