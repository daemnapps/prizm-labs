#!/usr/bin/env python3
"""repick.py: a laid-out email's real pictures chosen again, every section and word kept (the team, 2026-10-28).

    python3 tools/email-production/design/test_repick.py

  a  slots: brand photos and customer pictures only; made pictures (run:), cut-outs, todos and a customer picture
     sitting with that customer's own words are never touched
  b  problems: an answer that picks a photo not offered, one used in another email, keeps one used elsewhere, or
     repeats a picture is held slot by slot
  c  apply: keep leaves the slot alone; a new photo keeps the slot's crop; a todo carries its brief; every change
     is recorded; the words are byte for byte the same
  d  used_elsewhere: the brand's other emails' pictures, the batch's own emails left out
  e  a model answer with words or a second object after its JSON is read, not refused
The brand-a-nov-02--glow-up layout (charging case in THE CHECK) is the fixture. No network, no model.
"""
import copy
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
try:
    import PIL  # noqa: F401
except ImportError:
    PIL = types.ModuleType("PIL")
    for _n in ("Image", "ImageDraw", "ImageFilter"):
        setattr(PIL, _n, types.ModuleType("PIL." + _n))
        sys.modules["PIL." + _n] = getattr(PIL, _n)
    sys.modules["PIL"] = PIL
import repick as RP  # noqa: E402

CASE = "drive:brands/b/products/nova-charging-case/lifestyle/x_mirror.jpg"
FOAM = "drive:brands/b/products/nova-face-brush/lifestyle/x_in-hand-foam.jpg"
WASH = "drive:brands/b/products/war-face-wash/lifestyle/x_in-hand-with-flex.jpg"


def email():
    return {"sections": [
        {"s": "band"},
        {"s": "hero_type", "eyebrow": "SAVE THIS", "headline": "That's not acne on your <i>jaw</i>",
         "picture": {"photo": "run:media/hero.png", "alt": "the chart", "source": "made"}},
        {"s": "photo_card", "title": "THE CHECK", "text": "You can check it on your own jaw tonight.",
         "picture": {"photo": CASE, "ratio": 0.8, "focus": [0.5, 0.3], "alt": "NOVA in its case on the shelf", "source": "photo"}},
        {"s": "example", "picture": {"proof": "p-andrew", "alt": "Andrew"}, "quote": "My hair grows in curly", "who": "Andrew", "ask": "a"},
        {"s": "tiles", "title": "Two bumps. Two answers.", "tiles": [
            {"picture": {"stage": "product:crush", "alt": "tube", "source": "cut"}, "name": "CRUSH", "line": "The jaw"},
            {"picture": {"photo": FOAM, "alt": "brush", "source": "photo"}, "name": "NOVA", "line": "WAR goes on with this"}]},
        {"s": "picture", "picture": {"todo": "a razor", "alt": "a razor"}},
        {"s": "foot"}]}


def words(spec):
    return [w for s in spec["sections"] for w in RP._words(s)]


class Repick(unittest.TestCase):
    def test_a_slots(self):
        sl = RP.slots(email())
        self.assertEqual([(n, i, k, p.get("photo")) for n, i, k, p in sl], [(1, 2, "photo_card", CASE), (2, 4, "tiles", FOAM)])
        self.assertIn("THE CHECK", RP.slot_lines(email(), sl, {}))

    def test_b_problems(self):
        sl = RP.slots(email())
        offered = {CASE, FOAM, WASH}
        ok = {"slots": [{"n": 1, "photo": WASH}, {"n": 2, "keep": True}]}
        self.assertEqual(RP.problems(ok, sl, offered, set(), {}), {})
        self.assertIn(1, RP.problems({"slots": [{"n": 1, "photo": "drive:not-offered.jpg"}, {"n": 2, "keep": True}]}, sl, offered, set(), {}))
        self.assertIn(1, RP.problems(ok, sl, offered, set(), {WASH: "brand-a-nov-04"}))
        self.assertIn(2, RP.problems(ok, sl, offered, set(), {FOAM: "brand-a-nov-05--glow-up"}))     # kept, but taken
        self.assertIn(2, RP.problems({"slots": [{"n": 1, "photo": WASH}, {"n": 2, "photo": WASH}]}, sl, offered, set(), {}))
        self.assertIn(2, RP.problems({"slots": [{"n": 1, "keep": True}]}, sl, offered, set(), {}))

    def test_c_apply_keeps_words(self):
        spec = email()
        before = copy.deepcopy(words(spec))
        sl = RP.slots(spec)
        changed = RP.apply(sl, {"slots": [{"n": 1, "photo": WASH, "why": "the case is sold separately"},
                                          {"n": 2, "todo": "NOVA in a hand, WAR on it", "brief": "real NOVA", "why": "x"}]}, {})
        self.assertEqual(words(spec), before)
        card = spec["sections"][2]["picture"]
        self.assertEqual(card, {"photo": WASH, "ratio": 0.8, "focus": [0.5, 0.3], "source": "photo"})
        self.assertEqual(spec["sections"][4]["tiles"][1]["picture"]["todo"], "NOVA in a hand, WAR on it")
        self.assertEqual([c["from"] for c in changed], [CASE, FOAM])
        self.assertEqual(spec["sections"][1]["picture"]["photo"], "run:media/hero.png")
        self.assertEqual(spec["sections"][3]["picture"]["proof"], "p-andrew")
        spec2 = email()
        self.assertEqual(RP.apply(RP.slots(spec2), {"slots": [{"n": 1, "keep": True}, {"n": 2, "keep": True}]}, {}), [])
        self.assertEqual(spec2, email())

    def test_f_words_inside_lists(self):
        sec = {"s": "letter", "greeting": "Hey,", "paras": ["I'm a pharmacist.", "That still gets me."],
               "items": [["Your skin", "renews on its own clock"]]}
        self.assertEqual(RP._words(sec), ["Hey,", "I'm a pharmacist.", "That still gets me.", "Your skin", "renews on its own clock"])

    def test_e_answer_with_text_after_it(self):
        text = 'Here:\n{"slots": [{"n": 1, "keep": true}]}\n\n{"note": "a second object"}\nThanks.'
        self.assertEqual(RP.answer_of(text), {"slots": [{"n": 1, "keep": True}]})
        with self.assertRaises(ValueError):
            RP.answer_of("no json here")

    def test_d_used_elsewhere(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            for name, spec in (("b-nov-01", email()), ("b-nov-02", {"sections": [{"s": "picture", "picture": {"photo": WASH}}]})):
                (root / "b" / name / "design").mkdir(parents=True)
                (root / "b" / name / "design" / "email.json").write_text(json.dumps(spec))
            with mock.patch.object(RP.LI, "RUNS", root):
                used = RP.used_elsewhere("b", {"b-nov-02"})
        self.assertEqual(used, {CASE: "b-nov-01", "p-andrew": "b-nov-01", FOAM: "b-nov-01"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
