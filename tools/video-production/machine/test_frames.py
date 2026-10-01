#!/usr/bin/env python3
"""python3 machine/test_frames.py — from any cwd. Stdlib unittest only.

THE SCENE SHAPE, end to end, on a fixture brief that names no brand, product
or person: a scene is one setting, one paragraph of voice, TWO stills (the
first frame and the last) and ONE clip whose timeline is written from the
beats. Plus the contract gate — every defect refused by its own name — and
the old timed shape, still planning.
"""
from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"test_vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


run = load("run")
mi = load("model_inputs")
scenes = load("scenes")

TIMING = json.loads((FIXTURES / "vo-timing.json").read_text())


def plan_of():
    return run.build_plan_from_brief(FIXTURES / "brief-frames.md", "_fixture")


def items_of():
    return run.batches_of(plan_of(), "_fixture", TIMING)


def by_id(items):
    return {it["id"]: it for it in items}


class TheSceneShape(unittest.TestCase):
    def test_the_piece_declares_aspect_and_resolution_once(self):
        piece = plan_of()["piece"]
        self.assertEqual(piece["aspect"], "9:16")
        self.assertEqual(piece["resolution"], "720p")
        # and no scene restates them
        for s in plan_of()["scenes"]:
            self.assertNotIn("aspect", s)
            self.assertNotIn("resolution", s)

    def test_a_scene_is_one_paragraph_and_no_length(self):
        s = plan_of()["scenes"][0]
        self.assertTrue(s["voice"].startswith("It comes back in the same place"))
        self.assertEqual(s["seconds"], 0.0)      # never a number the brief chose
        self.assertIsNone(s["start"])
        self.assertTrue(s["to_camera"])

    def test_two_stills_per_scene_and_nothing_between_them(self):
        items = items_of()
        stills = [it for it in items if it["kind"] in ("still", "edit")]
        self.assertEqual([it["id"] for it in stills],
                         ["S1-F1", "S1-FLAST", "S2-F1", "S2-FLAST"])
        self.assertEqual([it["kind"] for it in stills],
                         ["still", "edit", "still", "edit"])

    def test_the_first_frame_is_a_generation_in_the_stills_order(self):
        it = by_id(items_of())["S1-F1"]
        order = mi.station("still-generate")["assembly"]["order"]
        prompt = it["params"]["prompt"]
        at = [prompt.find(x) for x in
              ("THE SPEAKER, seated", "medium-close", "looking straight into the lens",
               "A TABLE", "flat daylight", "square on at chest height",
               "soft directional daylight")]
        self.assertEqual(at, sorted(at), f"{order} order not held: {prompt}")
        self.assertEqual(it["params"]["size"], mi.size_for("9:16"))
        self.assertEqual([m["value"] for m in it["medias"]],
                         ["the cast sheet for THE SPEAKER", "the style frame"])

    def test_the_last_frame_is_an_edit_of_the_first_naming_only_the_delta(self):
        it = by_id(items_of())["S1-FLAST"]
        self.assertEqual(it["edit_of"], "S1-F1")
        self.assertEqual(it["medias"][0]["value"], "S1-F1")
        self.assertTrue(it["params"]["prompt"].startswith(
            "the camera has pushed in close, the forearm face-up filling the lower "
            "half of the frame"), it["params"]["prompt"])
        # the delta, then the one line that says what may NOT change
        self.assertTrue(it["params"]["prompt"].endswith(
            "Keep the person, wardrobe, setting, colour, white balance and light "
            "exactly as in the reference. Change nothing else."))
        for word in ("A TABLE", "daylight", "medium-close"):
            self.assertNotIn(word, it["params"]["prompt"])

    def test_every_edit_sends_two_references_in_order(self):
        for iid in ("S1-FLAST", "S2-FLAST"):
            it = by_id(items_of())[iid]
            refs = [m["value"] for m in it["medias"]
                    if m["role"] == "image_references"]
            self.assertEqual(len(refs), 2, refs)
            self.assertEqual(refs[0], it["edit_of"])
            self.assertIn("cast sheet", refs[1])

    def test_every_edit_routes_to_the_fidelity_door(self):
        import tempfile
        # scene 1 already pushes in; give scene 2 a new angle, so both camera
        # words are exercised and both still land on the one image door
        text = (FIXTURES / "brief-frames.md").read_text().replace(
            "**LAST FRAME**\n**Camera:** same\n**Change:** the arm is back",
            "**LAST FRAME**\n**Camera:** new angle to a wide\n**Change:** the arm is back")
        tmp = Path(tempfile.mkdtemp()) / "brief.md"
        tmp.write_text(text)
        items = by_id(run.batches_of(run.build_plan_from_brief(tmp, "_fixture"),
                                     "_fixture", TIMING))
        pushed, plain = items["S1-FLAST"], items["S2-FLAST"]
        # 2026-09-18, Damon: one image door — EVERY edit goes to the GPT
        # fidelity door, push-in or not; the camera word is kept for the record.
        self.assertEqual(pushed["contract"], "still-edit-fidelity")
        self.assertEqual(pushed["params"]["input_fidelity"], "high")
        self.assertEqual(plain["contract"], "still-edit-fidelity")
        self.assertEqual(plain["params"]["input_fidelity"], "high")
        # and both still send two references, the edited frame first
        for it in (pushed, plain):
            refs = [m["value"] for m in it["medias"]]
            self.assertEqual(refs[0], it["edit_of"])
            self.assertEqual(len(refs), 2)

    def test_one_clip_per_scene_carrying_both_frames(self):
        items = items_of()
        clips = [it for it in items if it["kind"] in ("motion", "talking")]
        self.assertEqual([it["id"] for it in clips], ["S1", "S2"])
        s1 = by_id(items)["S1"]
        self.assertEqual(s1["kind"], "talking")          # to camera
        self.assertEqual(by_id(items)["S2"]["kind"], "motion")
        self.assertEqual(s1["start_frame"], "S1-F1")
        self.assertEqual(s1["end_frame"], "S1-FLAST")
        self.assertIn({"role": "end_image", "value": "S1-FLAST"}, s1["medias"])
        self.assertEqual(s1["params"]["mode"],
                         mi.house_default(mi.field_named("talking", "mode")))
        self.assertTrue(s1["params"]["generate_audio"])
        self.assertFalse(by_id(items)["S2"]["params"]["generate_audio"])

    def test_the_clip_is_assembled_in_the_makers_four_blocks(self):
        prompt = by_id(items_of())["S1"]["params"]["prompt"]
        blocks = prompt.split("\n\n")
        self.assertEqual(len(blocks), 4, prompt)
        self.assertTrue(blocks[0].startswith("@Image1 is the first frame:"))
        self.assertIn("@Image2 is the last frame:", blocks[0])
        self.assertIn("@Audio1 is THE SPEAKER's voice", blocks[0])
        self.assertIn("A TABLE", blocks[1])
        self.assertEqual(len(blocks[2].splitlines()), 4)
        self.assertTrue(blocks[3].startswith("One continuous take, no cuts,"))

    def test_the_timeline_is_timed_off_the_one_voice_track(self):
        prompt = by_id(items_of())["S1"]["params"]["prompt"]
        spans = [l.split(":")[0] for l in prompt.split("\n\n")[2].splitlines()]
        self.assertEqual(spans, ["0-2.54s", "3.18-4.55s", "4.59-6.69s", "7.06-8.92s"])

    def test_a_talking_clip_never_writes_the_words_twice(self):
        prompt = by_id(items_of())["S1"]["params"]["prompt"]
        self.assertNotIn("the words playing", prompt.split("\n\n")[2])
        self.assertNotIn("It comes back in the same place", prompt)
        self.assertIn("they speak the words in @Audio1 exactly, their lips moving with every word, nothing else is said",
                      prompt)
        # a silent scene DOES carry its words, because nothing else will
        self.assertIn("the words playing:",
                      by_id(items_of())["S2"]["params"]["prompt"])

    def test_the_clip_runs_as_long_as_its_paragraph(self):
        s1 = by_id(items_of())["S1"]
        self.assertEqual(s1["params"]["duration"], 9)     # 8.92s of voice, rounded up
        self.assertEqual(s1["params"]["aspect_ratio"], "9:16")
        self.assertEqual(s1["params"]["resolution"], "720p")

    def test_the_door_is_named_and_the_last_frame_is_a_real_input(self):
        s1 = by_id(items_of())["S1"]
        door_id, attached, how = mi.end_image_door("talking")
        self.assertTrue(attached)
        self.assertEqual(s1["door"], door_id)
        self.assertIn("end_image", s1["end_frame_how"])


class TheGoldenCall(unittest.TestCase):
    """THE CALL THAT WORKED, assembled by the chain.

    On 2026-09-18 evening one scene went through the settled door by hand and
    came back right — 9 s, line check 100%. Its shape is the contract: the
    first frame as `start_image`, the last frame as `end_image`, the scene's
    slice of the one voice track as `audio_references`, and the prompt in four
    blocks. This class holds the chain to that call, because the dry run the
    same day assembled it four different ways at once and every one of them
    was wrong."""

    GOLDEN = json.loads((FIXTURES / "golden-timing.json").read_text())

    def clip(self):
        return by_id(items_of())["S1"]

    def test_the_medias_are_the_three_the_door_takes_in_order(self):
        medias = self.clip()["medias"]
        self.assertEqual([m["role"] for m in medias],
                         ["start_image", "end_image", "audio_references"])
        self.assertEqual([m["value"] for m in medias],
                         ["S1-F1", "S1-FLAST", "vo/S1.mp3"])

    def test_no_reference_rides_along_on_the_clip(self):
        """The first frame carries the identity. A cast sheet or a style
        frame attached beside it is a second opinion about the same face —
        and is exactly what the broken dry run sent instead of the frame."""
        values = [m["value"] for m in self.clip()["medias"]]
        for stray in ("the cast sheet for THE SPEAKER", "the style frame"):
            self.assertNotIn(stray, values)

    def test_the_params_are_the_ones_that_came_back_right(self):
        p = self.clip()["params"]
        self.assertEqual(p["duration"], 9)           # 8.92 s of voice, rounded up
        self.assertEqual(p["mode"], "omni_reference")
        self.assertEqual(p["aspect_ratio"], "9:16")
        self.assertEqual(p["resolution"], "720p")
        self.assertTrue(p["generate_audio"])
        low, high = mi.station("talking")["limits"]["duration_seconds"]
        self.assertTrue(low <= p["duration"] <= high)

    def test_the_four_blocks_are_in_order(self):
        blocks = self.clip()["params"]["prompt"].split("\n\n")
        self.assertEqual(len(blocks), 4)
        self.assertTrue(blocks[0].startswith("@Image1 is the first frame:"))
        # 1 — the asset line names exactly @Image1, @Image2 and @Audio1
        self.assertEqual(sorted(set(re.findall(r"@\w+", blocks[0]))),
                         ["@Audio1", "@Image1", "@Image2"])
        self.assertIn("@Image2 is the last frame:", blocks[0])
        self.assertIn("@Audio1 is THE SPEAKER's voice; they speak the words in "
                      "@Audio1 exactly, their lips moving with every word, nothing else is said.", blocks[0])
        # 2 — ONE clean summary sentence, not a pile of fields
        self.assertEqual(blocks[1].count("."), 1, blocks[1])
        self.assertTrue(blocks[1].startswith("THE SPEAKER at A TABLE"))
        self.assertIn("one slow push-in from medium-close to close", blocks[1])
        # 3 — the timeline, anchored on both frames
        self.assertIn("the frame at @Image1", blocks[2].splitlines()[0])
        self.assertIn("settling on the framing of @Image2", blocks[2].splitlines()[-1])
        # 4 — the consistency block, last
        self.assertTrue(blocks[3].startswith("One continuous take, no cuts,"))
        self.assertIn("The speaker is talking for the whole clip: their lips, jaw and face move naturally with the voice throughout.", blocks[3])
        self.assertTrue(blocks[3].endswith("No subtitles. No background music."))

    def test_the_timeline_is_the_golden_timing_sheet(self):
        blocks = self.clip()["params"]["prompt"].split("\n\n")
        spans = [l.split(":")[0] for l in blocks[2].splitlines()]
        want = [f"{a:g}-{z:g}s" for a, z in self.GOLDEN["beats"].values()]
        self.assertEqual(spans, want)
        self.assertEqual(len(spans), 4)

    def test_one_verb_a_beat_and_a_performance_bracket_at_the_end(self):
        for line in self.clip()["params"]["prompt"].split("\n\n")[2].splitlines():
            do = line.split(": ", 1)[1]
            self.assertTrue(do.rstrip(".").endswith("]"), line)
            self.assertLessEqual(mi.action_count(do.split(",")[0]), 1, line)

    def test_a_silent_scene_carries_no_audio_and_no_lip_line(self):
        s2 = by_id(items_of())["S2"]
        self.assertEqual([m["role"] for m in s2["medias"]],
                         ["start_image", "end_image"])
        self.assertNotIn("@Audio1", s2["params"]["prompt"])
        self.assertNotIn("Natural lip movement", s2["params"]["prompt"])
        self.assertFalse(s2["params"]["generate_audio"])
        self.assertEqual(s2["params"]["duration"], 6)   # the beats' own end

    def test_the_gate_refuses_the_four_by_name(self):
        """A first frame, a last frame, a voice slice on a to-camera scene,
        a paragraph past the ceiling — each refused, each naming itself."""
        it = self.clip()
        it["start_frame"] = None
        self.assertTrue(any("no FIRST FRAME" in b for b in mi.violations(it)))
        it = self.clip()
        it["last_frame"] = None
        self.assertTrue(any("no LAST FRAME" in b for b in mi.violations(it)))
        it = self.clip()
        it["medias"] = [m for m in it["medias"] if m["role"] != "audio_references"]
        self.assertTrue(any("no audio slice" in b for b in mi.violations(it)))
        it = self.clip()
        it["params"]["duration"] = 31
        self.assertTrue(any("ceiling" in b for b in mi.violations(it)))

    def test_a_missing_field_is_a_refusal_and_never_a_fragment(self):
        """The summary is built from labelled slots. Take one away and no
        prompt is written at all — a fragment is how a clip ends up being
        about something else."""
        plan = plan_of()
        scene = plan["scenes"][0]
        for f in scene["frames"]:
            if f["role"] == "last":
                f["camera"] = "push-in"        # a move with nothing to land on
        items = by_id(run.batches_of(plan, "_fixture", TIMING))
        self.assertEqual(items["S1"]["params"]["prompt"], "")
        bad = mi.violations(items["S1"])
        self.assertTrue(any("the framing the move lands on" in b for b in bad), bad)
        self.assertTrue(any("'prompt'" in b for b in bad), bad)


class TheContractGate(unittest.TestCase):
    """Every defect refused by name — nothing submits red."""

    def clip(self):
        """The assembled clip — it already carries its slice; the shape puts
        it there rather than a test remembering to."""
        return by_id(items_of())["S1"]

    def test_a_complete_clip_is_green(self):
        self.assertEqual(mi.violations(self.clip()), [])

    def test_a_to_camera_scene_with_no_audio_slice_is_refused(self):
        it = self.clip()
        it["medias"] = [m for m in it["medias"] if m["role"] != "audio_references"]
        bad = mi.violations(it)
        self.assertTrue(any("audio_references" in b for b in bad), bad)
        self.assertTrue(any("no audio slice" in b for b in bad), bad)

    def test_a_reference_attached_beside_the_first_frame_is_refused(self):
        """The dry run that found this bug had sent the cast sheet and the
        style frame on the clip and no first frame at all."""
        it = self.clip()
        it["medias"].append({"role": "omni_reference", "value": "the cast sheet"})
        bad = mi.violations(it)
        self.assertTrue(any("omni_reference" in b and "takes only" in b for b in bad), bad)

    def test_a_clip_that_attaches_no_first_frame_is_refused(self):
        it = self.clip()
        it["medias"] = [m for m in it["medias"] if m["role"] != "start_image"]
        bad = mi.violations(it)
        self.assertTrue(any("attaches no 'start_image'" in b for b in bad), bad)

    def test_a_clip_with_no_duration_is_refused(self):
        it = self.clip()
        it["params"].pop("duration")
        self.assertTrue(any("no duration" in b for b in mi.violations(it)))

    def test_a_beat_with_two_verbs_is_refused(self):
        it = self.clip()
        it["beats"][1]["do"] = "turns the forearm up and taps it twice"
        bad = mi.violations(it)
        self.assertTrue(any("more than one action" in b for b in bad), bad)

    def test_a_beat_with_no_action_is_refused(self):
        it = self.clip()
        it["beats"][0]["do"] = ""
        self.assertTrue(any("names no action" in b for b in mi.violations(it)))

    def test_more_beats_than_the_maker_takes_is_refused(self):
        it = self.clip()
        cap = mi.station("talking")["limits"]["max_beats"]
        it["beats"] = [{"n": i, "do": "turns"} for i in range(cap + 2)]
        bad = mi.violations(it)
        self.assertTrue(any(f"limit of {cap}" in b for b in bad), bad)

    def test_a_clip_with_no_beats_is_refused(self):
        it = self.clip()
        it["beats"] = []
        self.assertTrue(any("no beats" in b for b in mi.violations(it)))

    def test_a_last_frame_the_door_takes_and_the_item_lacks_is_refused(self):
        it = self.clip()
        it["end_frame"] = None
        bad = mi.violations(it)
        self.assertTrue(any("'end_image'" in b for b in bad), bad)

    def test_a_missing_first_or_last_frame_is_refused(self):
        it = self.clip()
        it["start_frame"] = None
        self.assertTrue(any("no FIRST FRAME" in b for b in mi.violations(it)))
        it = self.clip()
        it["last_frame"] = None
        self.assertTrue(any("no LAST FRAME" in b for b in mi.violations(it)))

    def test_a_third_still_in_a_scene_is_refused(self):
        it = self.clip()
        it["frames"] = ["S1-F1", "S1-F2", "S1-FLAST"]
        bad = mi.violations(it)
        self.assertTrue(any("exactly 2" in b for b in bad), bad)

    def test_a_paragraph_past_the_doors_ceiling_is_refused(self):
        it = self.clip()
        cap = mi.station("talking")["limits"]["duration_seconds"][1]
        it["params"]["duration"] = cap + 5
        bad = mi.violations(it)
        self.assertTrue(any("ceiling" in b for b in bad), bad)

    def test_a_frame_with_no_delta_is_refused(self):
        it = by_id(items_of())["S1-FLAST"]
        self.assertEqual(mi.violations(it), [])
        it["delta"] = ""
        bad = mi.violations(it)
        self.assertTrue(any("no delta" in b for b in bad), bad)

    def test_an_edit_with_one_reference_is_refused(self):
        it = by_id(items_of())["S1-FLAST"]
        it["medias"] = it["medias"][:1]
        bad = mi.violations(it)
        self.assertTrue(any("fewer than two references" in b for b in bad), bad)

    def test_an_edit_whose_first_reference_is_not_the_frame_is_refused(self):
        it = by_id(items_of())["S1-FLAST"]
        it["medias"] = list(reversed(it["medias"]))
        bad = mi.violations(it)
        self.assertTrue(any("first reference" in b for b in bad), bad)

    def test_an_old_shape_item_is_not_asked_for_scene_shape_fields(self):
        item = {"id": "A1", "kind": "motion", "params": {"prompt": "x"},
                "medias": [], "characters": [], "products": [], "lines": []}
        self.assertEqual(mi.violations(item), [])

    def test_every_required_field_names_itself_when_missing(self):
        it = self.clip()
        it["params"].pop("prompt")
        bad = mi.violations(it)
        self.assertTrue(any("'prompt'" in b for b in bad), bad)


class NothingSubmitsRed(unittest.TestCase):
    """The gate where it actually runs — `preflight.py check` on a batch."""

    def setUp(self):
        import shutil
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-gate-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.run_dir = self.tmp / "sample-run"
        shutil.copytree(FIXTURES / "sample-run", self.run_dir)
        (self.run_dir / "lines.json").write_text(json.dumps(
            {"S1": "the paragraph", "S2": "the other paragraph"}))
        self.preflight = load("preflight")

    def check(self, items):
        p = self.tmp / "batch.json"
        p.write_text(json.dumps({"items": items}))
        return self.preflight.check(p, self.run_dir, "higgsfield-ui",
                                    FIXTURES / "bank.json")

    def batch(self):
        return items_of()

    def test_a_scene_shape_batch_is_green(self):
        fails, _ = self.check(self.batch())
        self.assertEqual(fails, [], fails)

    def test_the_gate_names_the_field_and_the_rule(self):
        items = self.batch()
        clip = next(it for it in items if it["kind"] == "talking")
        clip["medias"] = [m for m in clip["medias"] if m["role"] != "audio_references"]
        clip["beats"][0]["do"] = "turns the arm over and taps it"
        fails, _ = self.check(items)
        text = "\n".join(fails)
        self.assertIn("[rule 12]", text)
        self.assertIn("audio_references", text)
        self.assertIn("more than one action", text)


class TheBriefIsThePrompt(unittest.TestCase):
    """THE BRIEF IS THE PROMPT (Damon, 2026-09-19). A brief's truth is the
    fenced json block at the end of it; the prose above is the view a person
    reads, and nothing downstream parses it."""

    BRIEF = FIXTURES / "brief-block.md"

    def plan(self):
        return run.build_plan_from_brief(self.BRIEF, "_fixture")

    def items(self):
        return by_id(run.batches_of(self.plan(), "_fixture", TIMING))

    def block(self):
        doc, why = scenes.json_block(self.BRIEF.read_text())
        self.assertIsNone(why, why)
        return doc

    def test_the_block_is_read_and_the_prose_is_not(self):
        plan = self.plan()
        self.assertEqual(plan["piece"]["aspect"], "9:16")
        self.assertEqual([s["id"] for s in plan["scenes"]], ["S1", "S2"])
        self.assertEqual(plan["scenes"][0]["setting"], "A TABLE")
        self.assertTrue(plan["scenes"][0]["voice"].startswith(
            "It comes back in the same place"))
        self.assertEqual(plan["scenes"][0]["delivery"],
                         "dry · plain-flat · low · beat-and-pause")

    def test_a_block_brief_assembles_the_same_four_blocks(self):
        it = self.items()["S1"]
        self.assertTrue(it["params"]["prompt"].startswith("@Image1 is the first frame:"))
        self.assertIn("One continuous take, no cuts, the only camera movement "
                      "is the slow push in.", it["params"]["prompt"])
        self.assertEqual(mi.violations(it), [])

    def test_the_human_view_is_rendered_from_the_block(self):
        view = scenes.render_view(self.block())
        self.assertIn("A Fixture Piece, As A Block", view)
        self.assertIn("B-ROLL — the voice plays over it", view)
        self.assertIn("It comes back in the same place", view)

    def test_a_complete_block_is_green(self):
        self.assertEqual(mi.brief_violations(self.BRIEF.read_text()), [])

    def test_a_missing_key_is_named(self):
        doc = self.block()
        del doc["scenes"][0]["outcome"]
        del doc["piece"]["resolution"]
        doc["scenes"][1]["first_frame"].pop("lighting")
        bad = mi.brief_violations(doc)
        self.assertTrue(any("scene S1 is missing 'outcome'" in b for b in bad), bad)
        self.assertTrue(any("'piece' is missing 'resolution'" in b for b in bad), bad)
        self.assertTrue(any("first_frame' is missing 'lighting'" in b for b in bad), bad)

    def test_a_to_camera_that_is_not_a_boolean_is_refused(self):
        doc = self.block()
        doc["scenes"][0]["to_camera"] = "yes"
        bad = mi.brief_violations(doc)
        self.assertTrue(any("'to_camera' is 'yes'" in b for b in bad), bad)

    def test_a_setting_that_names_no_world_block_is_refused(self):
        doc = self.block()
        doc["scenes"][0]["setting_id"] = "A ROOM NOBODY BUILT"
        bad = mi.brief_violations(doc)
        self.assertTrue(any("names no world block" in b for b in bad), bad)

    def test_a_brief_with_no_block_still_plans(self):
        """Every run already on disk was written before the block existed."""
        self.assertEqual(mi.brief_violations(
            (FIXTURES / "brief-frames.md").read_text()), [])
        self.assertEqual([s["id"] for s in plan_of()["scenes"]], ["S1", "S2"])


class BRollIsAScene(unittest.TestCase):
    """Damon, 2026-09-19: "there is no B-roll" — every scene was the speaker
    to camera. A B-roll scene is a scene of its own: its own setting, its own
    two frames, its own beats, and the slice of the one read that plays OVER
    it at the edit."""

    def items(self):
        return by_id(run.batches_of(
            run.build_plan_from_brief(FIXTURES / "brief-block.md", "_fixture"),
            "_fixture", TIMING))

    def test_a_b_roll_scene_is_motion_with_no_audio(self):
        it = self.items()["S2"]
        self.assertEqual(it["kind"], "motion")
        self.assertFalse(it["to_camera"])
        self.assertEqual([m["role"] for m in it["medias"]],
                         ["start_image", "end_image"])
        self.assertEqual(it["lines"], [])
        self.assertEqual(mi.violations(it), [])

    def test_its_duration_is_its_own_slice_of_the_one_track(self):
        it = self.items()["S2"]
        # vo/timing.json: S2 runs 8.92 → 14.92, its own 6.0 s of the one read
        self.assertEqual(it["params"]["duration"], 6)

    def test_the_voice_is_still_recorded_and_laid_over_at_the_edit(self):
        it = self.items()["S2"]
        self.assertEqual(it["vo_over"], "vo/S2.mp3")

    def test_the_prompt_drops_the_lip_line_and_says_nobody_speaks(self):
        prompt = self.items()["S2"]["params"]["prompt"]
        self.assertNotIn("Natural lip movement", prompt)
        self.assertIn("Nobody speaks.", prompt)
        self.assertNotIn("@Audio1", prompt)

    def test_a_b_roll_scene_with_audio_attached_is_refused(self):
        it = self.items()["S2"]
        it["medias"].append({"role": "audio_references", "value": "vo/S2.mp3"})
        bad = mi.violations(it)
        self.assertTrue(any("B-roll scene with audio attached" in b for b in bad), bad)

    def test_an_insert_inside_another_scenes_beat_is_refused(self):
        it = self.items()["S1"]
        it["beats"][2]["do"] = ("*(insert, cut over the running voice)* seated "
                                "at the other table")
        bad = mi.violations(it)
        self.assertTrue(any("B-roll is a scene, not an insert" in b for b in bad), bad)

    def test_a_scene_that_lists_cutaways_is_refused(self):
        it = self.items()["S1"]
        it["cutaways"] = "the tube in the hand, the jars on the shelf"
        bad = mi.violations(it)
        self.assertTrue(any("B-roll is a scene, not an insert" in b for b in bad), bad)
        self.assertTrue(any("Cutaways" in b for b in bad), bad)


class TheBeatGrammar(unittest.TestCase):
    """One visible action, one verb, present tense. How a line is delivered
    belongs in the bracket; a pause is a beat whose action is `holds`."""

    def doc(self):
        return scenes.json_block((FIXTURES / "brief-block.md").read_text())[0]

    def test_a_beat_with_two_verbs_is_refused_by_name(self):
        doc = self.doc()
        doc["scenes"][0]["beats"][1]["do"] = "says the two words and shrugs"
        bad = mi.brief_violations(doc)
        self.assertTrue(any("names more than one action" in b for b in bad), bad)
        self.assertTrue(any("B2 of scene S1" in b for b in bad), bad)

    def test_a_delivery_note_is_not_an_action(self):
        doc = self.doc()
        doc["scenes"][0]["beats"][1]["do"] = "stops"
        bad = mi.brief_violations(doc)
        self.assertTrue(any("that is a delivery note, not an action" in b.lower()
                            for b in bad), bad)

    def test_a_pause_is_a_beat_and_holds_is_an_action(self):
        self.assertEqual(mi.delivery_note("holds"), "")
        self.assertEqual(mi.beat_faults({"n": 2, "do": "holds", "over": "the pause"}), [])

    def test_what_counts_as_two_actions_and_what_does_not(self):
        """The table these rules were tuned against — every line a real beat
        from a brief written to this grammar (2026-09-19)."""
        one = ["taps the back of her right hand once with her left fingertip",
               "steadies the tube front-on and square to the lens",
               "sets the tube down front-on and square to the lens",
               "presses the grains flat until they break down",
               "turns the forearm face-up", "nods once, small", "holds",
               "counts four off on the fingers, one clause each"]
        two = ["says the two words and shrugs, small, after them",
               "taps one finger against the tube, then a second",
               "brings the hand out from under the tap, and turns it to camera",
               "stands and walks out of frame",
               "takes the hand out of frame and leaves the tube standing"]
        for t in one:
            self.assertEqual(mi.action_count(t), 1, t)
        for t in two:
            self.assertGreater(mi.action_count(t), 1, t)

    def test_a_voice_paragraph_with_a_dash_is_refused_by_name(self):
        """Damon, 2026-09-19: humans don't use em dashes when speaking. The
        voice model read every dash as 1.3-1.7 s of silence; the gate refuses
        the written marks rather than letting a take carry them."""
        doc = self.doc()
        doc["scenes"][0]["voice"] = "This \u2014 the old surface \u2014 is why; it failed (again)."
        bad = mi.brief_violations(doc)
        names = [b for b in bad if "scene S1's 'voice' carries" in b]
        self.assertEqual(len(names), 4, bad)
        self.assertTrue(any("'em-dash' (2\u00d7)" in b for b in names), names)
        self.assertTrue(any("'semicolon'" in b for b in names), names)
        self.assertTrue(any("'opening parenthesis'" in b for b in names), names)
        self.assertTrue(any("'closing parenthesis'" in b for b in names), names)

    def test_an_ellipsis_in_the_voice_is_the_breath_and_passes(self):
        # Damon, 2026-09-19: the ellipsis is the mid-thought breath — kept
        doc = self.doc()
        doc["scenes"][1]["voice"] = "Reaching for the top shelf... and checking first."
        bad = mi.brief_violations(doc)
        self.assertFalse(any("ellipsis" in b for b in bad), bad)

    def test_a_spoken_paragraph_is_green(self):
        doc = self.doc()
        doc["scenes"][0]["voice"] = ("It comes back in the same place, every time. "
                                     "That's not the product failing. Right? "
                                     "That's the thing underneath it, doing what it does.")
        self.assertEqual([b for b in mi.brief_violations(doc) if "'voice'" in b], [])
        self.assertEqual(mi.voice_faults(doc["scenes"][0]["voice"]), [])
        self.assertEqual([r["name"] for r in mi.voice_forbidden()][:2], ["em-dash", "en-dash"])

    def test_per_scene_voice_settings_are_checked_against_the_model_limits(self):
        doc = self.doc()
        doc["scenes"][0]["voice_settings"] = {"stability": 0.6, "style": 0.1, "speed": 1.0}
        self.assertEqual([b for b in mi.brief_violations(doc) if "voice_settings" in b], [])
        doc["scenes"][0]["voice_settings"] = {"stability": 1.4, "speed": 0.5, "pitch": 2}
        bad = [b for b in mi.brief_violations(doc) if "voice_settings" in b]
        self.assertEqual(len(bad), 3, bad)
        self.assertTrue(any("stability is 1.4" in b for b in bad), bad)
        self.assertTrue(any("speed is 0.5" in b for b in bad), bad)
        self.assertTrue(any("carries 'pitch'" in b for b in bad), bad)
        plan = scenes.scenes_from_block(doc)
        self.assertEqual(plan[0]["voice_settings"], {"stability": 1.4, "speed": 0.5, "pitch": 2})
        self.assertEqual(plan[1]["voice_settings"], {})

    def test_a_last_frame_camera_without_its_framing_is_refused(self):
        doc = self.doc()
        doc["scenes"][0]["last_frame"]["camera"] = "new angle"
        bad = mi.brief_violations(doc)
        self.assertTrue(any("needs 'new angle to <framing>'" in b for b in bad), bad)

    def test_a_camera_word_the_door_does_not_take_is_refused(self):
        doc = self.doc()
        doc["scenes"][0]["last_frame"]["camera"] = "a slow orbit"
        bad = mi.brief_violations(doc)
        self.assertTrue(any("it is one of:" in b for b in bad), bad)

    def test_all_four_camera_words_assemble(self):
        for word, expect in (("same", "a locked frame"),
                             ("push-in to close", "one slow push-in"),
                             ("pull-out to a wide", "one slow pull-out"),
                             ("new angle to a wide", "one move to a new angle")):
            self.assertEqual(mi.camera_fault(word), "", word)
            scene = {"frames": [
                {"role": "first", "composition": "medium-close, chest up"},
                {"role": "last", "camera": word}]}
            phrase, sentence, missing = mi.camera_of(scene)
            self.assertEqual(missing, [], word)
            self.assertIn(expect, phrase, word)


class TheGateReadsTheBrief(unittest.TestCase):
    """rule 12's other half — `preflight.py check` reads the run's own brief
    and names the key its block is missing."""

    def setUp(self):
        import shutil
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-brief-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.run_dir = self.tmp / "sample-run"
        shutil.copytree(FIXTURES / "sample-run", self.run_dir)
        (self.run_dir / "lines.json").write_text(json.dumps(
            {"S1": "the paragraph", "S2": "the other paragraph"}))
        self.preflight = load("preflight")

    def check(self, brief_text):
        (self.run_dir / "brief.md").write_text(brief_text)
        p = self.tmp / "batch.json"
        p.write_text(json.dumps({"items": []}))
        return self.preflight.check(p, self.run_dir, "higgsfield-ui",
                                    FIXTURES / "bank.json")[0]

    def test_a_good_block_passes_the_gate(self):
        fails = self.check((FIXTURES / "brief-block.md").read_text())
        self.assertEqual([f for f in fails if "[rule 12]" in f], [], fails)

    def test_the_gate_names_the_missing_key(self):
        text = (FIXTURES / "brief-block.md").read_text().replace(
            '"emotion": "recognition",', "")
        fails = "\n".join(self.check(text))
        self.assertIn("[rule 12]", fails)
        self.assertIn("scene S1 is missing 'emotion'", fails)

    def test_a_block_that_will_not_parse_is_refused(self):
        text = (FIXTURES / "brief-block.md").read_text().replace(
            '"lane": "ai",', '"lane": "ai",,')
        fails = "\n".join(self.check(text))
        self.assertIn("will not parse", fails)


class TheEditorSheet(unittest.TestCase):
    """What the editor receives per scene: the two frames by name, the door,
    and the prompt exactly as the model gets it."""

    def sheet(self):
        import shutil
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="vm-sheet-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        items = items_of()
        clips = [it for it in items if it["kind"] in ("motion", "talking")]
        stills = [it for it in items if it["kind"] not in ("motion", "talking")]
        manifest = {it["id"]: {"file": f"media/{it['id']}.png", "model": "fixture-model"}
                    for it in stills}
        platform = load("platform")
        reg = platform.registry()
        _, prov, _ = platform.resolve_provider("higgsfield-ui")
        run.write_submit_md(tmp, clips, prov, reg, direct_manifest=manifest,
                            still_for=run.still_for_map(stills))
        return (tmp / "SUBMIT.md").read_text()

    def test_the_sheet_names_both_frames_the_door_and_the_prompt(self):
        text = self.sheet()
        self.assertIn("**start_image (upload first)**: `media/S1-F1.png`", text)
        self.assertIn("**end image (upload too)**: `media/S1-FLAST.png`", text)
        self.assertIn("higgsfield:connector", text)
        self.assertIn("**beats**: 4", text)
        self.assertIn("**Prompt — exactly as the model receives it:**", text)
        prompt = by_id(items_of())["S1"]["params"]["prompt"]
        self.assertIn(prompt, text)

    def test_the_sheet_prints_the_exact_call(self):
        """Every media by its role, in order, and every param — so what is
        printed is what is sent, with nothing to look up."""
        text = self.sheet()
        block = text[text.index("## S1"):text.index("## S2")]
        self.assertIn("- **medias** (in this order):", block)
        self.assertIn("- **start_image**: `media/S1-F1.png` (S1-F1)", block)
        self.assertIn("- **end_image**: `media/S1-FLAST.png` (S1-FLAST)", block)
        self.assertIn("- **audio_references**: `vo/S1.mp3`", block)
        for param in ("**duration**: 9", "**mode**: omni_reference",
                      "**aspect_ratio**: 9:16", "**resolution**: 720p"):
            self.assertIn(param, block)

    def test_the_sheet_never_lists_a_frame_as_its_own_editor_block(self):
        text = self.sheet()
        self.assertNotIn("## S1-F1", text)
        self.assertNotIn("## S1-FLAST", text)


class TheColourMatch(unittest.TestCase):
    """Every edit is held to the frame it came from — resized, then matched
    per channel. Pure PIL; skipped where PIL is not installed."""

    def setUp(self):
        self.cm = load("colour_match")
        if not self.cm.HAVE_PIL:
            self.skipTest("no PIL on this machine")
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-cm-"))

    def images(self):
        from PIL import Image
        ref = Image.new("RGB", (40, 60), (120, 130, 140))
        src = Image.new("RGB", (20, 30), (30, 200, 60))   # wrong size, wrong colour
        return src, ref

    def test_the_edit_is_resized_and_matched_to_the_frame(self):
        src, ref = self.images()
        out = self.cm.colour_match(src, ref)
        self.assertEqual(out.size, ref.size)
        self.assertEqual(out.getpixel((1, 1)), ref.getpixel((1, 1)))

    def test_match_file_writes_in_place_and_never_raises(self):
        src, ref = self.images()
        s, r = self.tmp / "edit.png", self.tmp / "first.png"
        src.save(s)
        ref.save(r)
        self.assertTrue(self.cm.match_file(s, r))
        from PIL import Image
        with Image.open(s) as got:
            self.assertEqual(got.size, ref.size)
        self.assertFalse(self.cm.match_file(self.tmp / "nope.png", r))

    def test_the_machine_hand_matches_an_edit_to_the_frame_it_edits(self):
        seen = {}
        saved = run.colour_match_to
        item = {"id": "S1-FLAST", "edit_of": "S1-F1"}
        manifest = {"S1-F1": {"file": "media/S1-F1.png"}}
        self.assertFalse(run.colour_match_to(item, None, manifest))     # nothing made
        self.assertFalse(run.colour_match_to({"id": "S1-F1"}, "x.png", {}))  # not an edit
        run.colour_match_to = saved
        del seen


class TheOldShapeStillPlans(unittest.TestCase):
    def test_a_timed_brief_still_parses_as_one_frame_one_line(self):
        text = (FIXTURES / "brief-frames.md").read_text()
        timed = ("**Scene 1 · 0:00–0:05 · 5s · TYPE A**\n\n"
                 "**Who:** THE SPEAKER · **Still:** new — a table, chest up\n"
                 "> **Say:** \"One line only.\"\n"
                 "**Delivery:** [flat]\n")
        ss = scenes.parse(timed)
        self.assertEqual(len(ss), 1)
        self.assertEqual(ss[0]["shape"], "timed")
        self.assertEqual(ss[0]["seconds"], 5.0)
        self.assertEqual(len(ss[0]["frames"]), 1)
        self.assertEqual(ss[0]["beats"], [])
        self.assertEqual(ss[0]["voice"], "One line only.")
        self.assertNotEqual(scenes.parse(text)[0]["shape"], "timed")

    def test_an_old_plan_still_makes_the_old_items(self):
        plan = json.loads((FIXTURES / "run-plan.json").read_text())
        run.prompt_mod.use_brand(plan.get("brand") or "_fixture")
        items = run.batches_of(plan, "_fixture")
        self.assertTrue(items)
        self.assertTrue(all(it["kind"] in ("motion", "still", "cast", "edit", "audio")
                            for it in items))
        self.assertFalse(any("beats" in it for it in items))


if __name__ == "__main__":
    unittest.main()
