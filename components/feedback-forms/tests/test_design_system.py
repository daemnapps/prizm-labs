"""The form's look comes from the brand's design system (synthetic brands only)."""
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
        (self.brand / "brand-identity" / "design-system").mkdir(parents=True)

    def test_tokens_json_maps_roles_by_name_and_usage(self):
        (self.brand / "brand-identity/design-system/tokens.json").write_text(json.dumps({
            "color": {"tokens": [
                {"name": "canvas", "value": {"light": "#FAF8F2", "dark": "#111111"}, "usage": "The ground of every page."},
                {"name": "ink", "value": "#1A1A1A"},
                {"name": "deep", "value": "#0B3D2E"}, {"name": "ink-on-deep", "value": "#FFFFFF"},
                {"name": "coral", "value": "#FF6B57", "usage": "The one accent: button fill."},
                {"name": "coral-ink", "value": "#1A1A1A"}]},
            "type": {"families": {"display": "\"Display\", serif", "sans": "\"Body\", sans-serif"}},
            "radius": {"tokens": [{"name": "radius-button", "value": "6px"}]}}))
        (self.brand / "brand-identity/acme-logo.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
        look = DS.look_for(self.brand, self.root)
        t = look["tokens"]
        self.assertEqual((t["ground"], t["ink"], t["band"], t["band_ink"]), ("#FAF8F2", "#1A1A1A", "#0B3D2E", "#FFFFFF"))
        self.assertEqual((t["accent"], t["cta"], t["cta_ink"], t["radius"]), ("#FF6B57", "#FF6B57", "#1A1A1A", "6px"))
        self.assertEqual(look["font_head"], "\"Display\", serif")
        self.assertEqual(look["logo_source"], "brands/acme/brand-identity/acme-logo.svg")

    def test_web_tokens_md_skips_open_rows(self):
        (self.brand / "brand-identity/web-tokens.md").write_text(
            "| Token | Hex | What | Where |\n|---|---|---|---|\n| page | `#FFFFFF` | the page | x |\n| open | `#000000` | <..> | |\n"
            "| text | `#222222` | body text | x |\n| action | `#0055FF` | primary button | x |\n"
            ":root {\n  --brand--font--body: \"Inter\", sans-serif;\n  --brand--font--display: \"open\", serif;\n}\n")
        look = DS.look_for(self.brand, self.root)
        self.assertEqual(look["tokens"]["ground"], "#FFFFFF")
        self.assertEqual(look["tokens"]["cta"], "#0055FF")
        self.assertEqual(look["font_body"], "\"Inter\", sans-serif")
        self.assertNotIn("font_head", look)

    def test_typed_look_wins_and_template_reads_design_system(self):
        q = {"look": {"from": "design-system", "tokens": {"accent": "#123456"}}}
        (self.brand / "brand-identity/web-tokens.md").write_text("| page | `#EEEEEE` | the page | x |\n")
        look = DS.resolve(q, self.brand, self.root)
        self.assertEqual(look["tokens"]["ground"], "#EEEEEE")
        self.assertEqual(look["tokens"]["accent"], "#123456")
        self.assertEqual(DS.resolve({"look": {"tokens": {"ground": "#000000"}}}, self.brand, self.root)["tokens"], {"ground": "#000000"})

    def test_no_design_system_keeps_neutral(self):
        self.assertEqual(DS.look_for(self.root / "brands" / "nobody", self.root), {})

    def test_build_uses_it(self):
        tpl = HERE.parents[2] / "brands" / "_TEMPLATE" / "operations"
        (self.brand / "operations").mkdir()
        for f in ("feedback-stages.json", "feedback-questions.json"):
            (self.brand / "operations" / f).write_text((tpl / f).read_text())
        (self.brand / "brand-identity/web-tokens.md").write_text("| page | `#ABCDEF` | the page | x |\n")
        _, qs = B.load("acme", self.root)
        self.assertIn("--fb-ground: #ABCDEF;", B.brand_css(qs))


if __name__ == "__main__":
    unittest.main()
