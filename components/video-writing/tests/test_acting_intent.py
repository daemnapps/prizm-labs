"""AI-1 (acting intent, 2026-11-27): presenter body v7 and storyboard ask v4 read behind one switch. No network, no spend."""
import importlib.util
import json
import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
MACHINE = HERE.parent / "machine"
PROMPTS = HERE.parent / "prompts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(MACHINE))
import director as D  # noqa: E402
import acting_intent as AI  # noqa: E402

BASE = {"VISUALS_OURS_OFF": "", "VISUALS_DIRECTOR_BASE": "swipe"}      # the swipe-base mode, where v4 lives
FEELINGS = ("angry", "sad", "happy", "nervous", "excited", "furious", "anxious", "frustrated")


def presenter_body():
    spec = importlib.util.spec_from_file_location("t_presenter_body", MACHINE / "presenter_body.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Switch(unittest.TestCase):
    def test_on_by_default_and_off_by_env(self):
        with mock.patch.dict(os.environ, {"ACTING_INTENT_OFF": ""}):
            self.assertTrue(AI.on())
        with mock.patch.dict(os.environ, {"ACTING_INTENT_OFF": "1"}):
            self.assertFalse(AI.on())

    def test_the_json_switch_turns_it_off(self):
        with mock.patch.dict(os.environ, {"ACTING_INTENT_OFF": ""}):
            with mock.patch.object(Path, "read_text", return_value=json.dumps({"on": False})):
                self.assertFalse(AI.on())


class Director(unittest.TestCase):
    def test_v4_is_read_in_swipe_base_mode_when_on(self):
        with mock.patch.dict(os.environ, {**BASE, "ACTING_INTENT_OFF": ""}):
            self.assertEqual(D.mode(), "swipe-base")
            ask = D.prompt("storyboard-ask")
            self.assertIn("**Intent.**", ask)
            self.assertIn('"intent": {"want"', ask)
            self.assertIn("The face has a reason", ask)

    def test_off_reads_v3_exactly(self):
        with mock.patch.dict(os.environ, {**BASE, "ACTING_INTENT_OFF": "1"}):
            ask = D.prompt("storyboard-ask")
            self.assertNotIn("**Intent.**", ask)
            self.assertEqual(ask, (PROMPTS / "stage-5d-director" / "storyboard-ask-v3-owner.md").read_text())

    def test_pick_and_rulings_are_untouched(self):
        with mock.patch.dict(os.environ, {**BASE, "ACTING_INTENT_OFF": ""}):
            self.assertEqual(D.prompt("pick"), (PROMPTS / "stage-5d-director" / "pick-v3-owner.md").read_text())
            self.assertEqual(D.prompt("rulings"), (PROMPTS / "stage-5d-director" / "rulings-v3-owner.md").read_text())

    def test_v4_is_v3_plus_only_the_intent_additions(self):
        v3 = (PROMPTS / "stage-5d-director" / "storyboard-ask-v3-owner.md").read_text()
        v4 = (PROMPTS / "stage-5d-director" / "storyboard-ask-v4-owner.md").read_text()
        for line in v3.splitlines():
            self.assertIn(line, v4.splitlines(), f"v4 lost a v3 line: {line[:60]}")

    def test_the_v4_reply_example_is_still_valid_json_with_an_intent_object(self):
        v4 = (PROMPTS / "stage-5d-director" / "storyboard-ask-v4-owner.md").read_text()
        block = re.search(r"```STORYBOARD\n(.*?)```", v4, re.S).group(1)
        self.assertIn('"intent": {"want"', block)
        for k in ("want", "blocked_by", "tactic", "turn_on", "then"):
            self.assertIn(f'"{k}"', block)

    def test_the_new_paragraph_names_no_feeling(self):
        v4 = (PROMPTS / "stage-5d-director" / "storyboard-ask-v4-owner.md").read_text()
        v3 = (PROMPTS / "stage-5d-director" / "storyboard-ask-v3-owner.md").read_text()
        added = "\n".join(l for l in v4.splitlines() if l not in v3.splitlines())
        for w in FEELINGS:
            self.assertNotIn(w, added.lower().replace("no feeling words", ""))


class PresenterBody(unittest.TestCase):
    def test_v7_is_live_when_on_and_v6_when_off(self):
        pb = presenter_body()
        with mock.patch.dict(os.environ, {"ACTING_INTENT_OFF": ""}):
            self.assertEqual(pb.live_prompt().name, "presenter-body-v7-owner.md")
        with mock.patch.dict(os.environ, {"ACTING_INTENT_OFF": "1"}):
            self.assertEqual(pb.live_prompt().name, "presenter-body-v6-owner.md")

    def test_v7_keeps_the_table_columns_and_adds_rule_18(self):
        v6 = (PROMPTS / "stage-3p-presenter-body" / "presenter-body-v6-owner.md").read_text()
        v7 = (PROMPTS / "stage-3p-presenter-body" / "presenter-body-v7-owner.md").read_text()
        self.assertIn("| # | T-numbers | Swipe shot | What we see | Said | How it's said |", v7)
        self.assertIn("18. **Every scene wants something.**", v7)
        self.assertIn("`Wants:`", v7)
        for slot in re.findall(r"\{[a-z_]+\}", v6):
            self.assertIn(slot, v7, f"v7 lost the slot {slot}")

    def test_v7_asks_for_no_vertical_bar_inside_the_cell(self):
        v7 = (PROMPTS / "stage-3p-presenter-body" / "presenter-body-v7-owner.md").read_text()
        self.assertIn("no vertical bars in it", v7)


if __name__ == "__main__":
    unittest.main()
