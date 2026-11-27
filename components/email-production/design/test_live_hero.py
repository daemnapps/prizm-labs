"""A hero_bg with style.live_button keeps its button OFF the picture and puts a live button on the photo (editor, 2026-11-10).

    /usr/bin/python3 test_live_hero.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402


class LiveHero(unittest.TestCase):
    def test_only_a_hero_bg_that_asks_for_it(self):
        self.assertTrue(build._live_hero({"s": "hero_bg", "cta": "GO", "style": {"live_button": True}}))
        self.assertFalse(build._live_hero({"s": "hero_bg", "cta": "GO", "style": {}}))
        self.assertFalse(build._live_hero({"s": "hero_bg", "style": {"live_button": True}}))
        self.assertFalse(build._live_hero({"s": "plain", "cta": "GO", "style": {"live_button": True}}))

    def test_the_drawn_button_is_taken_out_of_the_picture(self):
        h = '<section><h1>Hi</h1><div><a class="m-btn" style="x">GO</a></div></section>'
        self.assertNotIn("m-btn", build._no_button(h))
        self.assertIn("<h1>Hi</h1>", build._no_button(h))


if __name__ == "__main__":
    unittest.main()
