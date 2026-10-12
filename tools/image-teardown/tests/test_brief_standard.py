"""The standard brief check: the template passes itself, anything else is held."""
import sys, unittest
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
import gates as G, paths as P


class Standard(unittest.TestCase):
    def tpl(self):
        return P.BRIEF_STANDARD.read_text().split("\n=====\n")[1]

    def test_template_passes(self):
        self.assertEqual(G.standard_problems("# DOCUMENT ONE\n" + self.tpl() + "\n# DOCUMENT TWO"), [])

    def test_missing_section_held(self):
        b = self.tpl().replace("## 8 · Never on this ad", "## Things to avoid")
        self.assertTrue(any("8 · Never" in p for p in G.standard_problems(b)))

    def test_out_of_order_held(self):
        t = self.tpl()
        a, b = "## 6 · Headline options", "## 7 · Picture options"
        t = t.replace(a, "@@").replace(b, a).replace("@@", b)
        self.assertTrue(G.standard_problems(t))


if __name__ == "__main__":
    unittest.main()
