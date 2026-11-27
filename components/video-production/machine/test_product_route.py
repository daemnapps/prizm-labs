"""V58 (2026-11-18): the style's family decides the product route at production."""
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name):
    sp = importlib.util.spec_from_file_location(f"t58_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


class StyleDecidesProduct(unittest.TestCase):
    def test_animated_families_are_in_look(self):
        PR = _load("product_route")
        for sid in ("family-3d", "claymation", "anime"):
            self.assertEqual(PR.route_of_style(sid), "in-look", sid)

    def test_photoreal_and_unknown_are_in_scene(self):       # V59 (2026-11-25) replaces V58's photoreal line
        PR = _load("product_route")
        for sid in ("phone-ugc", "studio-hero", "", None, "no-such-style"):
            self.assertEqual(PR.route_of_style(sid), "in-scene", sid)
            self.assertFalse(PR.in_look({"style_id": sid}), sid)

    def test_piece_style_wins(self):
        PR = _load("product_route")
        self.assertTrue(PR.in_look({"style_id": "family-3d"}))
        self.assertFalse(PR.in_look({"style_id": "phone-ugc"}))

    def test_in_look_product_words_never_say_laid_on(self):
        ER = _load("element_refs")
        doc = {"piece": {"style_id": "family-3d", "product": "x"}}
        sc = {"id": "S1", "product": True, "who": "", "first_frame": {}}
        words = ER.product_words(sc, doc, "_fixture")
        self.assertIn("own look", words)
        self.assertNotIn("laid on", words)

    def test_in_look_end_card_uses_the_3d_build(self):
        PR = _load("product_route")
        got, why = PR.endcard_ref("brand_a", "flex-face-brush")
        if got is None:
            self.skipTest(why)       # a checkout without the brand's kits
        self.assertIn("/model/", str(got))
        self.assertNotIn("packshot", got.name)


if __name__ == "__main__":
    unittest.main()
