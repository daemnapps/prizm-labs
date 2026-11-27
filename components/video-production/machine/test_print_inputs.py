#!/usr/bin/env python3
"""What a 3D print request carries (run.py print_inputs, frame_words, reused_from): one picture's own words under the
cap, the chain's own lines on top; a card plate with no people; a plate the brief reuses never prints on its own.

    python3 components/video-production/machine/test_print_inputs.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run as R  # noqa: E402


class PrintInputs(unittest.TestCase):
    def setUp(self):
        self.run = Path(tempfile.mkdtemp(prefix="pin_"))
        doc = {"cast": [{"id": "yai", "bank_id": "yai"}], "scenes": [
            {"id": "S1", "kind": "talking", "looks": {"yai": "gold"},
             "first_frame": {"subject": "YAI " + "x" * 1900, "location": "PORCH"}},
            {"id": "S8", "kind": "card", "plate": "A turmeric ornament with a blank tag."},
            {"id": "S9", "kind": "card", "plate": "S8's plate, reused: the same ornament."}]}
        bf = self.run / "brief.md"
        bf.write_text("```json\n" + json.dumps(doc) + "\n```\n")
        (self.run / "run.json").write_text(json.dumps({"brief_from": str(bf), "brand": "nobrand"}))

    def test_the_cap_measures_the_pictures_own_words(self):
        x = R.print_inputs(self.run, "S1-F1", {})
        self.assertEqual(x["problems"], [])                       # 1,900 of description, chain lines on top
        self.assertIn("Every prop is plain", x["scene"])

    def test_a_card_plate_needs_no_cast(self):
        x = R.print_inputs(self.run, "S8-PLATE", {})
        self.assertEqual((x["cast"], x["problems"]), ([], []))
        self.assertIn("turmeric ornament", x["scene"])

    def test_a_reused_plate_points_at_the_one_it_reuses(self):
        self.assertEqual(R.reused_from(self.run, "S9-PLATE"), "S8-PLATE")
        self.assertIsNone(R.reused_from(self.run, "S8-PLATE"))
        self.assertIsNone(R.reused_from(self.run, "S1-F1"))



class BodyWords(unittest.TestCase):
    """brief-0380: a pour onto the column printed at table height, the lotion read as water, a resting forearm printed
    as a towel, and a sparse set that grew jars, a mug and books under the stand."""
    def test_a_pour_onto_something_raises_the_arm_and_the_lotion_is_thick(self):
        w = R.frame_words({"subject": "YAI pours lotion onto the supported clear column", "action": "Lotion runs off."},
                          [], False)
        self.assertIn("raised so the vessel's lip is directly above the supported clear column", w)
        self.assertIn("The lotion is thick and opaque", w)

    def test_a_named_forearm_stays_an_arm(self):
        self.assertIn("never a towel", R.frame_words({"subject": "face and forearm together"}, [], False))

    def test_with_no_props_named_the_open_space_stays_empty(self):
        self.assertIn("nothing stands under a stand", R.frame_words({"subject": "a column on a stand"}, [], False))

    def test_a_render_gets_none_of_it(self):
        w = R.frame_words({"subject": "a cross-section render, no person", "action": "cream pours onto skin"}, [], True)
        self.assertNotIn("pouring arm", w)
        self.assertNotIn("open space", w)


class ContainerShown(unittest.TestCase):
    """brief-0380 S4.2: the shot's subject was the scrub's grains on a shin; the tube rode along and was pasted on skin."""
    P = {"kind": "tube", "what": "the brown tube",
         "in_shot": ["S4: S4.2, granular scrub material on the shin. No generated product texture.",
                     "S2: S2.3, the tube beside the mortar, scrub label read."]}

    def test_material_on_skin_carries_no_product(self):
        self.assertFalse(R.container_shown({"id": "S4.2", "start_picture": "Her damp shin, fingertips above it."}, self.P))

    def test_a_shot_naming_the_tube_keeps_it(self):
        self.assertTrue(R.container_shown({"id": "S2.3", "gestures": ["her palm opens toward the tube"]}, self.P))

    def test_a_shot_that_says_no_product_has_none(self):
        self.assertFalse(R.container_shown({"id": "S2.3", "start_picture": "the table, no product or lettering"}, self.P))


class OwnPrint(unittest.TestCase):
    """brief-0380: a picture with its own 3D print request is its kept print, or it waits; never a generation."""
    def test_own_request_with_and_without_a_kept_print(self):
        from unittest import mock
        sys.path.append(str(Path(__file__).resolve().parents[2] / "image-production")); import image_production  # noqa: E702
        q = mock.MagicMock(); q.read.side_effect = lambda b, rid: {"id": rid} if rid.endswith("s1-f1") or rid.endswith("s2-f1") else None
        sg = mock.MagicMock(); sg.kept_print.side_effect = lambda b, rid: Path("/k.png") if rid.endswith("s1-f1") else None
        with mock.patch.object(image_production, "set_queue", q, create=True), \
                mock.patch.dict(sys.modules, {"image_production.set_queue": q}), mock.patch.object(R, "_set_gate", lambda: sg):
            run = Path("/r/b_x_brief-0001")
            self.assertEqual(R.own_print(run, "S1-F1", "b"), (Path("/k.png"), "b-x-brief-0001-s1-f1"))
            self.assertEqual(R.own_print(run, "S2-F1", "b"), (None, "b-x-brief-0001-s2-f1"))     # waits
            self.assertIsNone(R.own_print(run, "S3-F1", "b"))                                   # no request
            self.assertIsNone(R.own_print(run, "S1-F1", None))


class LooksOnTheRequest(unittest.TestCase):
    """brief-0380: the board put creator in her first look; the brief's scene named look-2-denim."""
    def test_the_scene_looks_ride_on_the_print_inputs(self):
        run = Path(__file__).resolve().parents[3] / "runs/video-production/brand_b/brand_b_brilliance-body-scrub_brief-0380"
        if not (run / "run.json").is_file():
            self.skipTest("the 0380 run is not on this machine")
        ins = R.print_inputs(run, "S2-F1", {})
        self.assertEqual(ins["looks"].get("creator"), "look-2-denim")
        self.assertIn("wears exactly the outfit", ins["scene"])

if __name__ == "__main__":
    unittest.main()
