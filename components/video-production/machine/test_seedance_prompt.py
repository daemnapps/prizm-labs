"""The Seedance prompt (2026-10-26): bound assets, one sentence, whole-second windows, no repeats. No network."""
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name):
    sp = importlib.util.spec_from_file_location(f"t_sp_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


SP = _load("seedance_prompt")

PEOPLE = {"YAI": {"noun": "woman", "pron": "she", "poss": "her"}}
STEPS = [{"do": f"does step {i}"} for i in range(1, 12)]
SCENES = {"S1": {"id": "S1", "happens": "stirs a pot", "beats": STEPS,
                 "shots": [{"id": "a", "face": "eyes on the pot"}, {"id": "b"}, {"id": "c"}, {"id": "d"}]}}
CALL = {"scenes": ["S1"], "talking": True, "duration": 10, "start_frame": "S1-F1", "end_frame": "S1-F1", "camera": "still",
        "lines": [{"speaker": "YAI", "on_camera": True, "scene": "S1", "text": "Add one tablespoon."}]}


class Cued(unittest.TestCase):
    """Each beat starts on its own words, never before (2026-10-28: the hand crossed before the words named the other side)."""
    CALL = {"scenes": ["A"], "duration": 6,
            "lines": [{"scene": "A", "on_camera": True, "text": "This one is old and this one is new.", "at": 0, "until": 4}]}
    SCENES = {"A": {"beats": [
        {"do": "touches the left object", "over": "This one is old"},
        {"do": "moves the finger to the right object", "over": "and this one is new."},
        {"do": "holds", "over": "the stop after new, no words"},
        {"do": "a glow spreads over the object", "over": "the stop", "bracket": "Effect-1 composited in the edit"}]}}

    def test_the_second_move_waits_for_its_words(self):
        b = SP.cued(self.CALL, self.SCENES)
        self.assertEqual(b[0]["a"], 0.0)
        self.assertGreater(b[1]["a"], 1.5)            # "and this one is new" starts about halfway through the line
        self.assertEqual(b[0]["z"], b[1]["a"])

    def test_a_pause_beat_follows_the_words_and_an_effect_is_not_acted(self):
        b = SP.cued(self.CALL, self.SCENES)
        self.assertFalse(b[2]["said"])
        self.assertGreaterEqual(b[2]["a"], b[1]["a"])
        self.assertNotIn("a glow spreads over the object", [x["do"] for x in b])

    def test_no_spoken_line_no_cues(self):
        self.assertEqual(SP.cued({**self.CALL, "lines": []}, self.SCENES), [])


class Prompt(unittest.TestCase):
    def test_every_step_is_said_once_not_once_per_shot(self):
        acts = SP.actions_of(CALL, SCENES)
        self.assertEqual(len(acts), 11)

    def test_windows_tile_the_clip_and_hold_two_actions_at_most(self):
        w, dropped = SP.windows([f"a{i}" for i in range(11)], 10)
        self.assertEqual(w[0][0], 0)
        self.assertEqual(w[-1][1], 10)
        self.assertTrue(all(len(g) <= SP.MAX_PER_WINDOW for _, _, g in w))
        self.assertTrue(all(w[i][1] == w[i + 1][0] for i in range(len(w) - 1)))
        self.assertEqual(len(dropped), 11 - sum(len(g) for _, _, g in w))
        self.assertTrue(all(z - a >= SP.MIN_WINDOW - 1 for a, z, _ in w))

    def test_talking_prompt_binds_picture_and_voice_and_never_types_the_line(self):
        r = SP.build(CALL, SCENES, PEOPLE, {}, "", "YAI")
        self.assertIn("Image 1 is the first frame", r["prompt"])
        self.assertIn("Audio 1 is the woman's voice", r["prompt"])
        self.assertNotIn("Add one tablespoon", r["prompt"])
        self.assertNotIn("Image 2", r["prompt"])

    def test_a_last_frame_is_named_only_when_it_differs_and_nobody_talks(self):
        silent = {**CALL, "talking": False, "end_frame": "S1-F2", "lines": []}
        self.assertIn("Image 2 is the last frame", SP.build(silent, SCENES, PEOPLE, {}, "", "YAI")["prompt"])
        same = {**silent, "end_frame": "S1-F1"}
        self.assertNotIn("Image 2", SP.build(same, SCENES, PEOPLE, {}, "", "YAI")["prompt"])

    def test_only_the_negatives_the_model_honours(self):
        p = SP.build(CALL, SCENES, PEOPLE, {}, "", "YAI")["prompt"]
        self.assertIn("No subtitles. No background music.", p)
        self.assertNotIn("cinematic", p.lower())

    def test_an_emotion_label_never_reaches_the_prompt(self):
        sc = {"S1": {**SCENES["S1"], "emotion": "furious", "face": "jaw set"}}
        p = SP.build(CALL, sc, PEOPLE, {}, "", "YAI")["prompt"]
        self.assertNotIn("furious", p)

    def test_an_action_that_names_its_subject_takes_no_second_one(self):
        sc = {"S1": {"id": "S1", "happens": "cleans a spot", "beats": [{"do": "the brown spot peels up"}, {"do": "smears the paste"}]}}
        p = SP.build({**CALL, "duration": 5}, sc, PEOPLE, {}, "", "YAI")["prompt"]
        self.assertNotIn("woman the brown", p)
        self.assertIn("The brown spot peels up", p)

    def test_a_propped_phone_is_not_called_handheld(self):
        p = SP.build(CALL, SCENES, PEOPLE, {}, "Native phone footage: handheld front camera, room light.", "YAI")["prompt"]
        self.assertNotIn("handheld", p)

    def test_a_motion_reference_video_is_bound_by_number_and_job(self):
        p = SP.build({**CALL, "refs": [{"file": "a.mp4"}, {"file": "b.mp4"}]}, SCENES, PEOPLE, {}, "", "YAI")["prompt"]
        self.assertIn("Video 1 is a motion reference only", p)
        self.assertIn("Video 2 is a motion reference only", p)
        self.assertLess(p.index("Video 2"), p.index("Audio 1"))
        self.assertNotIn("Video 1", SP.build(CALL, SCENES, PEOPLE, {}, "", "YAI")["prompt"])


# ------------------------------------------------------------------------------ the HB clip modes (2026-11-07)
import hashlib

HB_PEOPLE = {"ANA": {"noun": "host", "pron": "she", "poss": "her"}, "BO": {"noun": "guest", "pron": "he", "poss": "his"}}
HB_SCENES = {"A": {"id": "A", "setting_id": "KITCHEN", "who": "ANA, BO", "voice": "one two three four five six",
                   "first_frame": {"subject": "ANA on the left holds a bowl out to BO on the right", "location": "a bright kitchen"},
                   "beats": [{"shot": "A.1", "do": "lifts the bowl"}, {"shot": "A.2", "do": "nods"},
                             {"shot": "A.3", "do": "holds"}, {"shot": "A.4", "do": "smiles"}],
                   "shots": [{"id": "A.1", "angle": "front, waist-up two-shot", "camera_move": "handheld", "face": "eyes on the bowl",
                              "lines": [{"say": "Would you try this one?"}], "ends_on": "the bowl raised"},
                             {"id": "A.2", "angle": "front, close", "camera_move": "hold", "face": "a small smile",
                              "lines": [{"say": "Yes."}], "gestures": ["nods once", "taps the counter"]},
                             {"id": "A.3", "angle": "front, waist-up two-shot", "camera_move": "hold", "face": "eyes on the bowl", "lines": []},
                             {"id": "A.4", "angle": "front, close", "camera_move": "hold", "face": "n/a: no face in frame", "lines": [],
                              "ends_on": "the bowl set down"}]}}
HB_CALL = {"id": "A-C1", "scenes": ["A"], "talking": True, "start_frame": "A-F1", "people": ["ANA", "BO"],
           "lines": [{"scene": "A", "speaker": "ANA", "text": "Would you try this one?", "on_camera": True},
                     {"scene": "A", "speaker": "BO", "text": "Yes.", "on_camera": True}],
           "voice_samples": {"ANA": {"file": "v/ana.mp3", "seconds": 6}, "BO": {"file": "v/bo.mp3", "seconds": 5}}}


def _hb(**over):
    return SP.build({**HB_CALL, **over}, HB_SCENES, HB_PEOPLE, {}, "", "ANA")


class HbSwitchOff(unittest.TestCase):
    """With no hb mode named, the builder's output is byte-for-byte what it was before the modes existed. The hashes
    were taken from the builder at origin/main before this change (sha256 of the prompt)."""
    def sha(self, call, scenes=SCENES):
        return hashlib.sha256(SP.build(call, scenes, PEOPLE, {}, "", "YAI")["prompt"].encode()).hexdigest()[:16]

    def test_the_switch_reads_off_by_default(self):
        for v in (None, "", "narrator", "something-else", [], ["narrator"]):
            self.assertEqual(SP.hb_modes({"clip_mode": v}), ())
        self.assertEqual(SP.hb_modes({}), ())

    def test_talking_prompt_is_unchanged(self):
        self.assertEqual(self.sha(CALL), "df0bdab3f8976827")

    def test_silent_prompt_with_a_last_frame_is_unchanged(self):
        self.assertEqual(self.sha({**CALL, "talking": False, "end_frame": "S1-F2", "lines": []}), "e529fe0788bf5ae0")

    def test_naming_the_default_or_nonsense_changes_nothing(self):
        for v in ("narrator", "", "something-else"):
            self.assertEqual(self.sha({**CALL, "clip_mode": v}), "df0bdab3f8976827")
        r = SP.build({**CALL, "clip_mode": "narrator"}, SCENES, PEOPLE, {}, "", "YAI")
        self.assertEqual(set(r), {"prompt", "windows", "dropped", "words", "acting"})      # no hb keys leak in


class HbMultishot(unittest.TestCase):
    def test_two_to_four_shots_in_eight_to_fifteen_seconds_joined_by_hard_cuts(self):
        r = _hb(clip_mode="hb-multishot")
        self.assertEqual(r["missing"], [])
        self.assertTrue(8 <= r["duration"] <= 15)
        self.assertEqual(len(r["windows"]), 4)
        self.assertEqual((r["windows"][0][0], r["windows"][-1][1]), (0, r["duration"]))
        self.assertTrue(all(z - a >= SP.HB_MIN_SHOT for a, z in r["windows"]))
        self.assertTrue(all(r["windows"][i][1] == r["windows"][i + 1][0] for i in range(3)))
        self.assertEqual(r["cuts"], [w[0] for w in r["windows"][1:]])
        self.assertIn("hard cuts", r["prompt"])
        self.assertIn("no dissolves, fades, wipes or zooms", r["prompt"])

    def test_first_window_sets_the_place_and_each_later_window_opens_with_a_cut_and_restates_the_framing(self):
        lines = [l for l in _hb(clip_mode="hb-multishot")["prompt"].split("\n") if l[:1].isdigit()]
        self.assertTrue(lines[0].split("s: ", 1)[1].startswith("Opening shot, front, waist-up two-shot"))
        self.assertIn("the host on the left holds a bowl out to the guest on the right", lines[0])
        for l in lines[1:]:
            self.assertRegex(l.split("s: ", 1)[1], r"^Cut (?:back )?to front, ")

    def test_the_same_framing_straight_after_is_a_cut_not_a_return(self):
        lines = [l for l in _hb(clip_mode="hb-multishot")["prompt"].split("\n") if l[:1].isdigit()]
        self.assertIn(": Cut to front, close", lines[1])               # A.2 differs from A.1
        self.assertIn(": Cut back to front, waist-up two-shot", lines[2])   # A.3 returns to A.1's framing
        self.assertIn(": Cut back to front, close", lines[3])

    def test_a_window_acts_its_first_beat_and_the_beat_it_lands_on_and_the_ones_between_are_dropped(self):
        sc = {"A": {**HB_SCENES["A"], "beats": HB_SCENES["A"]["beats"] + [
            {"shot": "A.1", "do": "tilts the bowl"}, {"shot": "A.1", "do": "jerks back from the bowl"}]}}
        r = SP.build({**HB_CALL, "clip_mode": "hb-multishot"}, sc, HB_PEOPLE, {}, "", "ANA")
        first = [l for l in r["prompt"].split("\n") if l[:1].isdigit()][0]
        self.assertIn("lifts the bowl, then jerks back from the bowl", first)      # the payoff is acted, not dropped
        self.assertIn("tilts the bowl", r["dropped"])
        self.assertNotIn("tilts the bowl", r["prompt"])
        self.assertNotIn("holds", " ".join(l for l in r["prompt"].split("\n") if l[:1].isdigit()).replace("holds a bowl", ""))

    def test_a_shots_gestures_ride_with_it_as_its_body_and_one_the_action_says_is_not_repeated(self):
        r = _hb(clip_mode="hb-multishot")
        second = [l for l in r["prompt"].split("\n") if l[:1].isdigit()][1]
        self.assertIn("body: nods once, taps the counter", second)
        sc = {"A": {**HB_SCENES["A"], "shots": [dict(HB_SCENES["A"]["shots"][0], gestures=["lifts the bowl", "steps back"])]
                    + HB_SCENES["A"]["shots"][1:]}}
        first = [l for l in SP.build({**HB_CALL, "clip_mode": "hb-multishot"}, sc, HB_PEOPLE, {}, "", "ANA")["prompt"]
                 .split("\n") if l[:1].isdigit()][0]
        self.assertIn("body: steps back", first)
        self.assertNotIn("body: lifts the bowl", first)

    def test_a_shot_with_nobody_in_it_names_nobody_and_the_last_window_lands_on_the_result(self):
        last = [l for l in _hb(clip_mode="hb-multishot")["prompt"].split("\n") if l[:1].isdigit()][-1]
        self.assertNotIn("in frame", last)
        self.assertNotIn("face:", last)
        self.assertTrue(last.rstrip().endswith("At the end of the clip: the bowl set down."))

    def test_without_the_voice_mode_nobody_speaks_and_no_line_is_typed(self):
        p = _hb(clip_mode="hb-multishot")["prompt"]
        self.assertNotIn("Would you try this one", p)
        self.assertNotIn("Audio", p)
        self.assertIn("Nobody speaks", p)

    def test_the_motion_reference_video_is_not_sent_with_cuts(self):
        self.assertNotIn("Video 1", _hb(clip_mode="hb-multishot", refs=[{}])["prompt"])

    def test_refused_by_name_when_the_call_has_one_shot_five_shots_or_two_places(self):
        one = {"A": {**HB_SCENES["A"], "shots": HB_SCENES["A"]["shots"][:1]}}
        r = SP.build({**HB_CALL, "clip_mode": "hb-multishot"}, one, HB_PEOPLE, {}, "", "ANA")
        self.assertEqual(r["prompt"], "")
        self.assertIn("carries 2 to 4 shots", r["missing"][0])
        five = {"A": {**HB_SCENES["A"], "shots": HB_SCENES["A"]["shots"] + [{"id": "A.5", "angle": "wide"}]}}
        self.assertIn("this call has 5", SP.build({**HB_CALL, "clip_mode": "hb-multishot"}, five, HB_PEOPLE, {}, "", "ANA")["missing"][0])
        two_places = {"A": HB_SCENES["A"], "B": {**HB_SCENES["A"], "id": "B", "setting_id": "GARDEN"}}
        r = SP.build({**HB_CALL, "scenes": ["A", "B"], "clip_mode": "hb-multishot"}, two_places, HB_PEOPLE, {}, "", "ANA")
        self.assertTrue(any("one place per call" in m for m in r["missing"]))

    def test_shot_ids_narrow_the_call_to_the_planners_group(self):
        r = _hb(clip_mode="hb-multishot", shot_ids=["A.1", "A.2"])
        self.assertEqual(len(r["windows"]), 2)
        self.assertEqual(r["duration"], 8)

    def test_a_shot_picture_is_bound_only_when_one_is_sent(self):
        self.assertNotIn("Image 2", _hb(clip_mode="hb-multishot")["prompt"])
        p = _hb(clip_mode="hb-multishot", shot_pictures=[{"shot": "A.2", "job": "the close-up"}])["prompt"]
        self.assertIn("Image 2 is the opening picture of shot A.2: the close-up.", p)


class HbVoice(unittest.TestCase):
    def test_one_voice_sample_per_person_bound_by_number_and_each_line_typed_in_its_window(self):
        r = _hb(clip_mode="hb-voice")
        p = r["prompt"]
        self.assertEqual([v["audio"] for v in r["voices"]], [1, 2])
        self.assertIn("Audio 1 is the host's voice sample", p)
        self.assertIn("Audio 2 is the guest's voice sample", p)
        self.assertIn('the host says "Would you try this one?" in Audio 1\'s voice', p)
        self.assertIn('the guest says "Yes." in Audio 2\'s voice', p)
        self.assertIn("it sets how the host sounds and nothing else", p)
        self.assertNotIn("Cut to", p)                                   # one continuous take
        self.assertIn("No subtitles, no captions, no on-screen text.", p)

    def test_the_audio_goes_out_one_reference_per_voice_in_audio_order(self):
        r = _hb(clip_mode="hb-voice")
        self.assertEqual([v["file"] for v in r["voices"]], ["v/ana.mp3", "v/bo.mp3"])

    def test_a_person_who_speaks_without_a_sample_is_refused_by_name(self):
        r = _hb(clip_mode="hb-voice", voice_samples={"ANA": {"file": "v/ana.mp3", "seconds": 6}})
        self.assertEqual(r["prompt"], "")
        self.assertEqual(r["missing"], ["hb-voice needs a voice sample for BO, who speaks on screen"])

    def test_a_sample_outside_two_to_fifteen_seconds_is_refused(self):
        r = _hb(clip_mode="hb-voice", voice_samples={"ANA": {"file": "a", "seconds": 1}, "BO": {"file": "b", "seconds": 20}})
        self.assertEqual(len(r["missing"]), 2)
        self.assertTrue(all("must run 2 to 15 s" in m for m in r["missing"]))

    def test_more_than_five_voices_are_refused(self):
        ids = [f"P{i}" for i in range(6)]
        shots = [{"id": f"A.{i}", "angle": "front", "lines": [{"say": f"line {i}"}]} for i in range(6)]
        scenes = {"A": {**HB_SCENES["A"], "shots": shots, "beats": []}}
        call = {**HB_CALL, "clip_mode": "hb-voice", "people": ids,
                "lines": [{"scene": "A", "speaker": p, "text": f"line {i}", "on_camera": True} for i, p in enumerate(ids)],
                "voice_samples": {p: {"file": f"{p}.mp3", "seconds": 5} for p in ids}}
        people = {p: {"noun": p.lower(), "pron": "they", "poss": "their"} for p in ids}
        r = SP.build(call, scenes, people, {}, "", "P0")
        self.assertTrue(any("5 voices at most" in m for m in r["missing"]))

    def test_a_line_said_off_camera_is_never_typed_and_the_narrator_read_stays_on_the_edit(self):
        call = {**HB_CALL, "clip_mode": "hb-voice", "lines": [
            {"scene": "A", "speaker": "ANA", "text": "Would you try this one?", "on_camera": False},
            {"scene": "A", "speaker": "BO", "text": "Yes.", "on_camera": True}]}
        r = SP.build(call, HB_SCENES, HB_PEOPLE, {}, "", "ANA")
        self.assertNotIn("Would you try this one", r["prompt"])
        self.assertEqual(r["skipped_lines"][0]["text"], "Would you try this one?")
        self.assertEqual([v["person"] for v in r["voices"]], ["BO"])

    def test_no_line_said_on_camera_is_a_refusal_not_an_empty_voice_call(self):
        r = _hb(clip_mode="hb-voice", lines=[])
        self.assertIn("at least one line said on camera", r["missing"][0])

    def test_both_modes_together_cut_and_speak(self):
        r = _hb(clip_mode="hb-multishot+hb-voice")
        self.assertEqual(SP.hb_modes({"clip_mode": ["hb-voice", "hb-multishot"]}), ("hb-multishot", "hb-voice"))
        self.assertEqual(len(r["cuts"]), 3)
        self.assertIn("in Audio 2's voice", r["prompt"])
        self.assertIn("Cut to", r["prompt"])



class HbFilmedAndPlaces(unittest.TestCase):
    """Fix round 2026-11-07: a filmed take is never regenerated; a multi-cut call never joins two places."""
    def scene(self, **over):
        return {"A": {**HB_SCENES["A"], **over}}

    def test_a_filmed_scene_is_refused_by_name_in_both_modes(self):
        for mark in ({"speaker": "ANA · BO (as filmed)"}, {"happens": "Cut the actual interview; keep original recorded audio."},
                     {"first_frame": {**HB_SCENES["A"]["first_frame"], "style": "as filmed"}},
                     {"first_frame": {**HB_SCENES["A"]["first_frame"], "subject": "CUT [SLOT: named owned take]."}}):
            for mode in ("hb-multishot", "hb-voice", "hb-multishot+hb-voice"):
                r = SP.build({**HB_CALL, "clip_mode": mode}, self.scene(**mark), HB_PEOPLE, {}, "", "ANA")
                self.assertEqual(r["prompt"], "", (mark, mode))
                self.assertIn("never regenerated", r["missing"][0])
                self.assertEqual([f["shot"] for f in r["filmed"]], ["A.1", "A.2", "A.3", "A.4"])

    def test_a_filmed_shot_is_left_out_and_named_and_the_rest_is_built(self):
        shots = [dict(s) for s in HB_SCENES["A"]["shots"]]
        shots[3]["operation"] = "CUT"
        r = SP.build({**HB_CALL, "clip_mode": "hb-multishot"}, self.scene(shots=shots), HB_PEOPLE, {}, "", "ANA")
        self.assertEqual(r["missing"], [])
        self.assertEqual(len(r["windows"]), 3)
        self.assertEqual(r["filmed"], [{"shot": "A.4", "why": "operation CUT: cut from an owned take"}])

    def test_the_shots_own_generate_wins_over_scene_text(self):
        shots = [{**s, "operation": "GENERATE"} for s in HB_SCENES["A"]["shots"]]
        r = SP.build({**HB_CALL, "clip_mode": "hb-multishot"}, self.scene(shots=shots, speaker="ANA (as filmed)"),
                     HB_PEOPLE, {}, "", "ANA")
        self.assertEqual((r["missing"], r["filmed"]), ([], []))

    def test_shots_in_different_places_inside_one_scene_are_refused(self):
        each = self.scene(first_frame={**HB_SCENES["A"]["first_frame"], "location": "OWNED MONTAGE, separate original location for each listed shot"})
        r = SP.build({**HB_CALL, "clip_mode": "hb-multishot"}, each, HB_PEOPLE, {}, "", "ANA")
        self.assertTrue(any("shots are in different places" in m for m in r["missing"]))
        shots = [dict(s) for s in HB_SCENES["A"]["shots"]]
        shots[1]["start_picture"] = "a couple on a street, her forehead to his"
        r = SP.build({**HB_CALL, "clip_mode": "hb-multishot"}, self.scene(shots=shots), HB_PEOPLE, {}, "", "ANA")
        self.assertTrue(any("shots are in different places" in m for m in r["missing"]))

    def test_a_montage_scene_is_cut_across_places_and_never_one_call(self):
        r = SP.build({**HB_CALL, "clip_mode": "hb-multishot"}, self.scene(setting_id="MONTAGE-ROOMS"), HB_PEOPLE, {}, "", "ANA")
        self.assertTrue(any("shots are in different places" in m for m in r["missing"]))

    def test_a_call_that_opens_on_a_later_shot_opens_on_that_shots_picture(self):
        shots = [dict(s) for s in HB_SCENES["A"]["shots"]]
        shots[2]["start_picture"] = "close on the guest's hands on the counter"
        r = SP.build({**HB_CALL, "clip_mode": "hb-multishot", "shot_ids": ["A.3", "A.4"]}, self.scene(shots=shots),
                     HB_PEOPLE, {}, "", "ANA")
        first = [l for l in r["prompt"].split("\n") if l[:1].isdigit()][0]
        self.assertIn("close on the guest's hands on the counter", first)
        self.assertNotIn("holds a bowl out", first)

    def test_a_montage_names_each_shots_own_place_and_the_end_line_names_no_cast_id(self):
        sc = {"A": {**HB_SCENES["A"], "setting_id": "MONTAGE-ROOMS"}}
        self.assertEqual(SP.hb_place({**sc["A"], "id": "A.2"}), "shot A.2's own place (MONTAGE-ROOMS)")
        sc = {"A": {**HB_SCENES["A"], "shots": HB_SCENES["A"]["shots"][:3]
                    + [dict(HB_SCENES["A"]["shots"][3], ends_on="ANA sets the bowl down")]}}
        p = SP.build({**HB_CALL, "clip_mode": "hb-multishot"}, sc, HB_PEOPLE, {}, "", "ANA")["prompt"]
        self.assertIn("At the end of the clip: the host sets the bowl down.", p)

    def test_a_new_angle_in_the_same_place_still_joins(self):
        shots = [dict(s) for s in HB_SCENES["A"]["shots"]]
        shots[1]["start_picture"] = "close on the bowl in her hands, the same bright kitchen behind"
        r = SP.build({**HB_CALL, "clip_mode": "hb-multishot"}, self.scene(shots=shots), HB_PEOPLE, {}, "", "ANA")
        self.assertEqual(r["missing"], [])

    def test_the_planner_sees_each_shots_place_and_whether_it_is_filmed(self):
        shots = [dict(s) for s in HB_SCENES["A"]["shots"]]
        shots[2]["start_picture"] = "a man alone in his car"
        shots[3]["owned_asset"] = "[SLOT: owned take]"
        got = SP.hb_shots({**HB_CALL, "clip_mode": "hb-multishot"}, self.scene(shots=shots))
        self.assertEqual([g["setting"] for g in got], ["KITCHEN", "KITCHEN", "KITCHEN · car", "KITCHEN"])
        self.assertEqual([bool(g["filmed"]) for g in got], [False, False, False, True])


if __name__ == "__main__":
    unittest.main()
