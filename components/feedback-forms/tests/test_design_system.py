"""The form's look comes from the brand's design system by standard names, never by guessing (synthetic brands)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import design_system as DS  # noqa: E402
import build as B  # noqa: E402


class DesignSystem(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.brand = self.root / "brands" / "acme"
        (self.brand / "brand-identity").mkdir(parents=True)
        (self.brand / "email-sms").mkdir()

    def ds(self, tokens, **extra):
        (self.brand / "email-sms/design-system.json").write_text(json.dumps({"tokens": tokens, **extra}))

    def test_design_system_json_maps_exact_keys(self):
        (self.brand / "brand-identity/acme-logo-white.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
        self.ds({"canvas": "#FAF8F2", "surface": "#FFFFFF", "ink": "#1A1A1A", "muted": "#666666", "line": "#DDDDDD",
                 "band": "#0B3D2E", "band_ink": "#FFFFFF", "accent": "#FF6B57", "button": "#0B3D2E", "button_ink": "#FFFFFF"},
                fonts={"display": {"family": "Display", "fallback": "serif"}, "body": {"family": "Body", "fallback": "sans-serif"}},
                logo={"file": "brand:brand-identity/acme-logo-white.svg", "alt": "Acme"})
        look = DS.look_for(self.brand, self.root)
        t = look["tokens"]
        self.assertEqual((t["ground"], t["band"], t["cta"], t["cta_ink"]), ("#FAF8F2", "#0B3D2E", "#0B3D2E", "#FFFFFF"))
        self.assertEqual(look["font_head"], "'Display', serif")
        self.assertEqual(look["logo_source"], "brands/acme/brand-identity/acme-logo-white.svg")
        self.assertEqual(look["missing"], [])
        self.assertEqual(look["source"], "brands/acme/email-sms/design-system.json")

    def test_nothing_is_guessed(self):
        # brand-specific names that are not the standard keys are ignored, and what is missing is said
        self.ds({"canvas": "#FFFFFF", "sage": "#C7CFAD", "forest": "#062B14"})
        look = DS.look_for(self.brand, self.root)
        self.assertEqual(look["tokens"], {"ground": "#FFFFFF"})
        self.assertEqual(look["missing"], ["ink", "band", "band_ink", "button", "button_ink"])

    def test_web_tokens_standard_table_is_the_fallback(self):
        (self.brand / "brand-identity/web-tokens.md").write_text(
            "| Token | Value | From |\n|---|---|---|\n| surface-bg | `#FFFFFF` | x |\n| brand-cta | `#0055FF` | .btn |\n"
            "| brand-cta-ink | `#FFFFFF` | .btn |\n| Forest | `#062B14` | a brand name, not a standard token |\n"
            "| font-body | `inter, sans-serif` | x |\n")
        look = DS.look_for(self.brand, self.root)
        self.assertEqual(look["tokens"]["ground"], "#FFFFFF")
        self.assertEqual(look["tokens"]["cta"], "#0055FF")
        self.assertNotIn("band", look["tokens"])
        self.assertIn("brand-band", look["missing"])

    def test_typed_look_wins(self):
        self.ds({"canvas": "#EEEEEE"})
        look = DS.resolve({"look": {"from": "design-system", "tokens": {"accent": "#123456"}}}, self.brand, self.root)
        self.assertEqual((look["tokens"]["ground"], look["tokens"]["accent"]), ("#EEEEEE", "#123456"))
        self.assertEqual(DS.resolve({"look": {"tokens": {"ground": "#000000"}}}, self.brand, self.root)["tokens"], {"ground": "#000000"})

    def test_build_uses_it(self):
        tpl = HERE.parents[2] / "brands" / "_TEMPLATE" / "operations"
        (self.brand / "operations").mkdir()
        for f in ("feedback-stages.json", "feedback-questions.json"):
            (self.brand / "operations" / f).write_text((tpl / f).read_text())
        self.ds({"canvas": "#ABCDEF"})
        _, qs = B.load("acme", self.root)
        self.assertIn("--fb-ground: #ABCDEF;", B.brand_css(qs))


if __name__ == "__main__":
    unittest.main()
