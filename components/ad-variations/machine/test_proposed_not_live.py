"""A prompt held for review is not live: the planner still takes the version under prompts/, and the held one sits
outside it. Run: /usr/bin/python3 components/ad-variations/machine/test_proposed_not_live.py"""
import json, sys, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
sys.path.append(str(COMP.parent / "run-kit"))
from run_kit import prompts as P  # noqa: E402


class Held(unittest.TestCase):
    def test_the_planner_still_runs_the_locks_prompt_under_prompts(self):
        live = P.latest(COMP / "prompts", "stage2")
        self.assertEqual(live.name, "stage2-locks-v3-owner.md")
        self.assertIn(COMP / "prompts", live.parents)

    def test_the_held_version_sits_outside_prompts_and_says_it_is_not_live(self):
        held = COMP / "proposed" / "stage2-locks-v4-owner.md"
        self.assertTrue(held.is_file())
        self.assertNotIn(COMP / "prompts", held.parents)
        text = held.read_text()
        self.assertIn("HELD FOR REVIEW: not live", text)
        for layer in ("1. openings", "2. format", "3. concept", "4. awareness"):
            self.assertIn(layer, text)
        self.assertEqual(sorted(p.name for p in (COMP / "prompts").rglob("stage2-*-v4-*.md")), [])

    def test_the_across_forms_rule_is_written_and_off(self):
        d = json.loads((COMP / "proposed" / "across-forms.json").read_text())
        self.assertIs(d["on"], False)
        self.assertEqual(d["status"], "draft")
        self.assertEqual([x["form"] for x in d["order"]], ["static", "ai-voiceover-video", "creator"])


if __name__ == "__main__":
    unittest.main()
