"""The designer's agreed rules, checked in code.

    /usr/bin/python3 test_rules_check.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rules_check as RC  # noqa: E402


def spec(*blocks):
    return {"sections": [{"s": "fg_header"}, {"s": "fg_block", "bg": "#B19A6F", "items": [{"t": "marquee", "text": "X"}]}] + list(blocks) + [{"s": "fg_foot"}]}


def block(bg, *items, **kw):
    return dict({"s": "fg_block", "bg": bg, "items": list(items)}, **kw)


class Rules(unittest.TestCase):
    def rules(self, sp, **kw):
        return {r for _, r, _ in RC.check(sp, **kw)}

    def test_a_clean_layout_breaks_nothing(self):
        sp = spec(block("#FFFFFF", {"t": "headline", "lines": ["A", "<i>b</i>"]}, {"t": "button", "label": "Shop the bundle"}),
                  block("#F4EDDA", {"t": "voicecards", "rows": [{"text": "x", "who": "A", "picture": {"todo": "s", "alt": "a"}}]}))
        self.assertEqual(self.rules(sp), set())

    def test_each_agreed_rule_is_caught(self):
        sp = spec(block("#FFFFFF", {"t": "headline", "lines": ["WANTING IT WAS", "NEVER HARD"], "tone": ["#422F28", "#B19A6F"]}, {"t": "button", "label": "SHOP →"},
                        {"t": "quote", "text": "x"}, {"t": "freecard"}, {"t": "minicard"}, {"t": "voicecards", "rows": [{"text": "x"}]}),
                  block("#FFFFFF"), {"s": "fg_band", "items": []})
        got = self.rules(sp)
        for rule in ("normal case, never all capitals", "no gold text on a light ground", "buttons: normal case, no arrow", "customer words as voice cards",
                     "no thin gold outlines", "flat colours only", "no thin outlines", "voice cards carry the creator's still", "sections alternate colours"):
            self.assertIn(rule, got, rule)

    def test_the_strip_must_carry_the_ruled_wording(self):
        sp = spec()
        self.assertIn("the ruled top-strip wording", self.rules(sp, ruled_strip="BLACK FRIDAY"))

    def test_a_marquee_strip_with_no_padding_is_not_a_spacing_fault(self):
        sp = spec()
        sp["sections"][1]["pad_top"] = 18
        self.assertNotIn("72px above and below a section", self.rules(sp))


if __name__ == "__main__":
    unittest.main()
