"""A brand's `email_defaults` reach every new layout, and the layout's own values win (2026-11-24)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line  # noqa: E402

LOOK = {"email_defaults": {"layout": {"noon": True, "button_radius": "0"},
                           "tokens": {"surface": "#1D2A22"},
                           "styles": {"foot": {"no_ornament": True}, "ticker": {"center": True, "repeat": 1}}}}


class EmailDefaults(unittest.TestCase):
    def test_defaults_land_on_a_new_layout(self):
        spec = {"sections": [{"s": "ticker", "text": "X"}, {"s": "foot"}, {"s": "letter"}]}
        line.apply_defaults(spec, LOOK)
        self.assertTrue(spec["layout"]["noon"])
        self.assertEqual(spec["tokens"]["surface"], "#1D2A22")
        self.assertEqual(spec["sections"][0]["style"], {"center": True, "repeat": 1})
        self.assertEqual(spec["sections"][1]["style"], {"no_ornament": True})
        self.assertNotIn("style", spec["sections"][2])

    def test_the_layouts_own_values_win(self):
        spec = {"layout": {"button_radius": "8px"}, "sections": [{"s": "ticker", "style": {"repeat": 3}}]}
        line.apply_defaults(spec, LOOK)
        self.assertEqual(spec["layout"]["button_radius"], "8px")
        self.assertTrue(spec["layout"]["noon"])
        self.assertEqual(spec["sections"][0]["style"]["repeat"], 3)

    def test_a_look_without_defaults_changes_nothing(self):
        spec = {"sections": [{"s": "foot"}]}
        line.apply_defaults(spec, {})
        self.assertEqual(spec, {"sections": [{"s": "foot"}]})


if __name__ == "__main__":
    unittest.main()
