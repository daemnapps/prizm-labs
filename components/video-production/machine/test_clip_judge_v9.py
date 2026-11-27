"""PR-1 (2026-11-27): clip judge v9 sharpens check 6 (the acting) into four named looks. No network, no spend."""
import importlib.util
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROMPTS = HERE.parent / "prompts" / "v2"


def _load():
    spec = importlib.util.spec_from_file_location("t_cj9", HERE / "clip_judge.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class V9(unittest.TestCase):
    def setUp(self):
        self.v8 = (PROMPTS / "clip-judge-v8-owner.md").read_text()
        self.v9 = (PROMPTS / "clip-judge-v9-owner.md").read_text()

    def test_the_judge_reads_v9_and_v8_stays_beside_it_for_rollback(self):
        self.assertEqual(_load().PROMPT.name, "clip-judge-v9-owner.md")
        self.assertTrue((PROMPTS / "clip-judge-v8-owner.md").is_file())

    def test_check_6_names_four_looks(self):
        for s in ("The eyes are alive", "Reactions land with their cause", "The face changes over the take", "Quiet where the shot is quiet"):
            self.assertIn(s, self.v9)

    def test_it_flags_and_never_holds(self):
        self.assertIn("They never stop the chain", self.v9)

    def test_every_other_v8_line_stands_word_for_word(self):
        have = self.v9.splitlines()
        for line in self.v8.splitlines()[1:]:
            if line.startswith("6. **The acting.**") or line.startswith("# Clip judge"):
                continue
            self.assertIn(line, have, f"v9 lost a v8 line: {line[:70]}")

    def test_the_slots_and_the_reply_shape_are_unchanged(self):
        for slot in ("{shot}", "{swipe}", "{staging}", "{consistency}"):
            self.assertIn(slot, self.v9)
        reply = lambda t: re.search(r'Reply with JSON only:\n\n(\{.*\})', t, re.S).group(1)
        self.assertEqual(reply(self.v9), reply(self.v8))


if __name__ == "__main__":
    unittest.main()
