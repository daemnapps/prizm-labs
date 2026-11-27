"""Orders from the Creative Options board (2026-11-21). No model is called.

An order made from a story preset or an arc has no story file: its locked concept is the preset (at the order's own
length) or the arc the scaffold wrote, so the scratch checks have something to hold the brief to. An order made in
Higgsfield (combo.tool) carries our production contract as a note, never a hold."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "machine"))
sys.path.insert(0, str(HERE.parents[1] / "video-teardown" / "machine"))

import swipe_match as SM  # noqa: E402


def scratch_run(tmp, **extra):
    d = Path(tmp) / "order-x"
    (d / "stages").mkdir(parents=True)
    st = {"lane": "scratch", "stages": {"stage1": {"from": "scratch"}}}
    st.update(extra)
    (d / "run.json").write_text(json.dumps(st))
    return d, st


class OrderConcept(unittest.TestCase):
    def test_a_preset_order_is_held_to_its_preset_at_its_own_length(self):
        with tempfile.TemporaryDirectory() as t:
            d, st = scratch_run(t, target_seconds=30)
            (d / "vars").mkdir()
            (d / "vars" / "story-preset.md").write_text("shrink-the-creature\n")
            text = SM.scratch_story(d, st)
            self.assertIn("THE STORY PRESET — `shrink-the-creature`", text)
            self.assertIn("| 49–72% | 0:15–0:22 |", text)     # the beats at 30 s, not the card's 45

    def test_an_arc_order_is_held_to_the_arc_it_was_scaffolded_on(self):
        with tempfile.TemporaryDirectory() as t:
            d, st = scratch_run(t)
            (d / "stages" / "1-teardown.md").write_text("# The structure to follow\n\n## The arc: But / therefore\n")
            self.assertIn("But / therefore", SM.scratch_story(d, st))

    def test_a_scratch_run_with_a_story_file_still_needs_it_locked(self):
        with tempfile.TemporaryDirectory() as t:
            d, st = scratch_run(t, story={"file": "story.md", "sha": "0000000000000000"})
            (d / "story.md").write_text("our concept")
            with self.assertRaises(RuntimeError):
                SM.scratch_story(d, st)

    def test_a_swipe_run_has_no_scratch_concept(self):
        with tempfile.TemporaryDirectory() as t:
            d, st = scratch_run(t)
            st["lane"] = "swipe"
            self.assertIsNone(SM.scratch_story(d, st))


class ContractNote(unittest.TestCase):
    def test_the_revalidation_contract_is_a_note_for_an_order_made_in_higgsfield(self):
        src = (HERE.parent / "machine" / "writing_revalidate.py").read_text()
        self.assertIn("tool = (st.get('combo') or {}).get('tool')", src)
        self.assertIn("'note_only'", src)

    def test_the_writing_chain_contract_is_a_note_for_an_order_made_in_higgsfield(self):
        src = (HERE.parents[1] / "video-teardown" / "machine" / "run.py").read_text()
        self.assertIn('if _bv and (st.get("combo") or {}).get("tool"):', src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
