"""A kept product print must come from the product's own 3D build project (2026-11-26)."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import picture_sets as S


class OwnBuild(unittest.TestCase):
    def setUp(self):
        self.p = S.set_product
        S.set_product = lambda brand, r, run=None: {"kit": "k", "jutsu_project": "OWN"}

    def tearDown(self):
        S.set_product = self.p

    def test_other_project_refused(self):
        with self.assertRaises(ValueError):
            S.own_build("b", "s", {}, {"project": "OTHER"})

    def test_own_project_passes(self):
        self.assertTrue(S.own_build("b", "s", {}, {"project": "OWN"}))

    def test_no_product_passes(self):
        S.set_product = lambda brand, r, run=None: {}
        self.assertTrue(S.own_build("b", "s", {}, {"project": "OTHER"}))

    def test_product_without_build_refused(self):
        S.set_product = lambda brand, r, run=None: {"kit": "k", "jutsu_project": None}
        with self.assertRaises(ValueError):
            S.own_build("b", "s", {}, {"project": "ANY"})

    def test_print_words_keep_always_and_never(self):
        w = S.print_prompt({"shot": "a shelf", "light": "dim", "product": "the brush", "product_always": ["its ring light glowing"],
                            "product_never": ["stood upright"]})
        self.assertIn("Always: the product with its ring light glowing.", w)
        self.assertIn("Never: stood upright.", w)
        self.assertIn("its own true 3D build", w)


if __name__ == "__main__":
    unittest.main()
