"""A brand whose look file says "default_look": "figma" is offered the Figma-look sections, not the older ones.

    /usr/bin/python3 test_figma_default.py
"""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import figma_look as FG  # noqa: E402
import line  # noqa: E402


class FigmaDefault(unittest.TestCase):
    def test_only_a_brand_that_asks_gets_the_figma_sections(self):
        self.assertTrue(line.figma_default({"default_look": "figma"}))
        self.assertFalse(line.figma_default({}))
        self.assertFalse(line.figma_default({"default_look": "house"}))
        txt = line.sections_text({"default_look": "figma", "figma": {"recipes": {"offer": "fg_header, fg_hero, fg_foot"}}})
        self.assertIn("fg_hero", txt)
        self.assertIn("offer: fg_header, fg_hero, fg_foot", txt)
        self.assertIn("never a dark overlay", txt)
        self.assertNotIn("HOUSE SECTIONS", txt)

    def test_every_guided_section_and_item_exists(self):
        for name in FG.FG_SECTIONS_GUIDE:
            self.assertIn(name, FG.FG, name)
        src = (HERE / "figma_look.py").read_text()
        handled = set(re.findall(r'if t == "(\w+)"', src))
        for name in FG.FG_ITEMS_GUIDE:
            self.assertIn(name, handled, name)

    def test_a_picture_to_make_takes_its_box_shape(self):
        spec = {"sections": [{"s": "fg_hero", "photo_h": 800, "picture": {"todo": "x", "alt": "a"}},
                             {"s": "fg_block", "items": [{"t": "picture", "w": 536, "h": 268, "picture": {"todo": "y", "alt": "b"}}]}]}
        line.figma_box_ratios(spec, {})
        self.assertAlmostEqual(spec["sections"][0]["picture"]["ratio"], 0.75)
        self.assertAlmostEqual(spec["sections"][1]["items"][0]["picture"]["ratio"], 2.0)


if __name__ == "__main__":
    unittest.main()
