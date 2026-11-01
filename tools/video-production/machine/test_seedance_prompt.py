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


if __name__ == "__main__":
    unittest.main()
