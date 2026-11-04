"""The standard brief check: the template passes itself, anything else is held.
The template is the writing station's (templates/, newest version wins); the check is the teardown's copy gate."""
import sys, unittest
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
import writing as W  # noqa: E402,F401  — puts the teardown's tools on the path
import gates as G, paths as P  # noqa: E402


class Standard(unittest.TestCase):
    def tpl(self):
        return P.BRIEF_STANDARD.read_text().split("\n=====\n")[1]

    def test_the_newest_template_is_the_one_held_to(self):
        self.assertEqual(P.BRIEF_STANDARD.name, "brief-standard-static-v3-owner.md")
        self.assertEqual(P.BRIEF_STANDARD.parent, HERE / "templates")

    def test_template_passes(self):
        self.assertEqual(G.standard_problems("# DOCUMENT ONE\n" + self.tpl() + "\n# DOCUMENT TWO"), [])

    def test_missing_section_held(self):
        b = self.tpl().replace("## 7 · Never on this ad", "## Things to avoid")
        self.assertTrue(any("7 · Never" in p for p in G.standard_problems(b)))

    def test_out_of_order_held(self):
        t = self.tpl()
        a, b = "## 6 · Variations", "## 7 · Never on this ad"
        t = t.replace(a, "@@").replace(b, a).replace("@@", b)
        self.assertTrue(G.standard_problems(t))

    def test_one_variations_section_replaces_the_two_options_sections(self):
        t = self.tpl()
        self.assertIn("## 6 · Variations", t)
        self.assertNotIn("Headline options", t)
        self.assertNotIn("Picture options", t)
        self.assertEqual(t.count("\n| 5 |"), 1)          # row 0 the approved picture, then exactly five


if __name__ == "__main__":
    unittest.main()
