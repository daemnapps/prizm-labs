"""Each of these words is defined once (frameworks.json words). The files that used to define them only point."""
import json
import re
import unittest
from pathlib import Path

W = Path(__file__).resolve().parents[2]
HOME = "components/marketing-doctrine/slices/words.md"


class Words(unittest.TestCase):
    def test_every_word_has_a_meaning_a_test_and_a_place(self):
        b = json.loads((W / "components/marketing-doctrine/frameworks.json").read_text())["words"]
        self.assertEqual(len({x["word"] for x in b["rows"]}), len(b["rows"]))
        for x in b["rows"]:
            for k in ("is", "test", "kept_in"):
                self.assertTrue(x[k], (x["word"], k))
        t = (W / HOME).read_text()
        for x in b["rows"]:
            self.assertIn("| **%s** |" % x["word"], t)

    def test_the_others_point_and_do_not_define(self):
        for f in ("components/GLOSSARY.md", "components/naming/CLAUDE.md", "components/naming/PEOPLE.md", ".claude/skills/naming/SKILL.md"):
            t = (W / f).read_text()
            self.assertIn(HOME, t, f)
            self.assertNotIn("a claim family", t, f)
            self.assertNotRegex(t, r"Avatar: a whole person", f)


if __name__ == "__main__":
    unittest.main()
