#!/usr/bin/env python3
"""LD-101 (Brand-B house look): a brand's `house` (in its look file) is its default style, as a style and not a fixed
sequence; every picture is made for its own box; a customer section shows customers' words or cleared people.

    /usr/bin/python3 tools/email-production/design/test_ld101_house_look.py

Offline: a fixture look (no brand file is read), pictures drawn by PIL into a temp run's media/.

  1  house(): the house default under the email's own style (the email wins); a variant ("cta" + "dark") takes its
     own default; an email not marked look "house", or a look with no house, comes back unchanged
  2  the house sections read their colours from the style, with today's values when the style says nothing; the
     engine's docstrings name no brand
  3  notes: the customers' words and who said them, no picture; on_camera: each person's picture at its own shape
     (a tall still stays tall), her name and her line
  4  the layout guide offers the house sections and the house rule only to a brand that has a house
  5  the validator holds: one picture twice (the hero pair excepted), one person twice, a picture whose shape is not
     its box's, a still that is not on the cleared list, and a customer picture from the proof index in a house email
  6  box_ratios(): every picture still to make in a house email takes its box's shape, and the picture chain makes it
     at the nearest shape the picture models make (16:9 for a wide ritual picture, never 9:16 cut down)
"""
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))      # design/ FIRST; never tools/email-production (its email.py shadows the stdlib's)
import engine as EN                # noqa: E402
import look as L                   # noqa: E402
import line as LN                  # noqa: E402
import picture_chain as PC         # noqa: E402
from PIL import Image              # noqa: E402

HOUSE = {"sections": ["hero_top", "hero_hands", "infographic", "ritual", "photo_card", "finale", "closing", "notes",
                      "on_camera", "cta", "guarantee"],
         "styles": {"cta": {"bg": "#FBFAF5", "button": "#19110E", "button_ink": "#FFFFFF", "pad": "22px 33px 40px"},
                    "cta:dark": {"bg": "#19110E", "button": "#FFFFFF", "button_ink": "#19110E", "pad": "0px 33px 26px"},
                    "ritual": {"base": "#3A2820", "pic_ratio": "16/9", "title_top": 22, "pad_bottom": 26},
                    "finale": {"base": "#3A2820", "split": True}}}


def look(house=True, run_dir=None):
    return L.Look("zz", {"house": HOUSE} if house else {}, run_dir)


class TestHouse(unittest.TestCase):
    def test_1_house_defaults_under_the_emails_own_style(self):
        spec = {"look": "house", "sections": [{"s": "cta", "label": "Go", "style": {"pad": "1px"}},
                                              {"s": "cta", "variant": "dark", "label": "Go"},
                                              {"s": "letter", "paras": ["x"]}]}
        got = EN.house(spec, look())
        self.assertEqual(got["sections"][0]["style"], dict(HOUSE["styles"]["cta"], pad="1px"))
        self.assertEqual(got["sections"][1]["style"], HOUSE["styles"]["cta:dark"])
        self.assertNotIn("style", got["sections"][2])
        self.assertNotIn("style", spec["sections"][1], "house() never changes the spec it is given")
        plain = {"sections": [{"s": "cta", "label": "Go"}]}
        self.assertEqual(EN.house(plain, look()), plain)
        self.assertEqual(EN.house(dict(plain, look="house"), look(house=False)), dict(plain, look="house"))

    def test_2_colours_from_the_style_and_no_brand_in_docstrings(self):
        s = {"s": "closing", "head": "H", "sub": "S"}
        self.assertIn("#422F28", EN.s_closing(look(), s, None))
        r = {"s": "infographic", "title": "T", "final": "F", "rows": [{"icon": "drop", "label": "L", "text": "t"}],
             "style": {"ink": "#010203"}}
        self.assertIn("#010203", EN.s_infographic(look(), r, None))
        self.assertIn("#71625B", EN.s_infographic(look(), dict(r, style={}), None))
        for name in ("hero_top", "hero_hands", "infographic", "ritual", "finale", "closing", "notes", "on_camera"):
            doc = EN.SECTIONS[name].__doc__ or ""
            self.assertNotIn("Brand-B", doc, name)
            self.assertNotIn("This email only", doc, name)


class TestNewSections(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.run = Path(t.name) / "zz-nov-99"
        (self.run / "media").mkdir(parents=True)
        Image.new("RGB", (540, 960), (200, 30, 30)).save(self.run / "media" / "still-a.jpg")
        Image.new("RGB", (540, 960), (30, 200, 30)).save(self.run / "media" / "still-b.jpg")

    def test_3_notes_are_words_and_on_camera_keeps_each_shape(self):
        n = EN.s_notes(look(), {"s": "notes", "title": "Loved by our customers",
                                "notes": [{"quote": "So smooth.", "who": "A zz customer"}]}, None)
        self.assertIn("So smooth.", n)
        self.assertIn("A zz customer", n)
        self.assertNotIn("<img", n)
        people = [{"picture": {"photo": "run:media/still-a.jpg", "ratio": 0.5625, "alt": "Ann"}, "name": "Ann", "line": "I love it."},
                  {"picture": {"photo": "run:media/still-b.jpg", "ratio": 0.5625, "alt": "Bea"}, "name": "Bea", "line": "Soft."}]
        c = EN.s_on_camera(look(run_dir=self.run), {"s": "on_camera", "title": "On camera", "people": people}, None)
        self.assertEqual(c.count("<img"), 2)
        self.assertIn("I love it.", c)
        self.assertIn("BEA", c.upper())
        import base64, io, re
        for uri in re.findall(r'src="data:image/[a-z]+;base64,([^"]+)"', c):
            with Image.open(io.BytesIO(base64.b64decode(uri))) as im:
                self.assertAlmostEqual(im.size[0] / im.size[1], 0.5625, places=2)


class TestLayout(unittest.TestCase):
    def test_4_guide_offers_house_sections_only_to_a_house_brand(self):
        with_house = LN.sections_text(look())
        without = LN.sections_text(look(house=False))
        for name in ("notes:", "on_camera:", "ritual:", "infographic:"):
            self.assertIn(name, with_house)
            self.assertNotIn(name, without)
        self.assertIn("HOUSE LOOK", with_house)
        self.assertNotIn("HOUSE LOOK", without)

    def v(self, sections, **kw):
        spec = {"look": "house", "sections": sections + [{"s": "foot"}]}
        return LN.validate(spec, look(), set(kw.get("proof", ())), {}, None, cleared=kw.get("cleared"))

    def test_5_the_validator_holds_repeats_shapes_strangers_and_proof(self):
        pic = {"todo": "the scrub at a sink", "alt": "a"}
        held = self.v([{"s": "photo_card", "picture": dict(pic), "text": "t"}, {"s": "photo_card", "picture": dict(pic), "text": "u"}])
        self.assertTrue(any("twice" in p for p in held), held)
        hero = {"todo": "her hands under warm light", "alt": "h"}
        ok = self.v([{"s": "hero_top", "headline": "H", "sub": "S", "picture": dict(hero)}, {"s": "cta", "variant": "dark", "label": "Go"},
                     {"s": "hero_hands", "picture": dict(hero)}])
        self.assertFalse([p for p in ok if "twice" in p], ok)
        cleared = {"c1@3": {"creator": "ann"}, "c2@5": {"creator": "ann"}, "c3@1": {"creator": "bea"}}
        cam = lambda *ids: {"s": "on_camera", "title": "T", "people": [{"picture": {"still": i, "alt": "x"}, "name": "N", "line": ""} for i in ids]}
        self.assertTrue(any("same person" in p for p in self.v([cam("c1@3", "c2@5")], cleared=cleared)))
        self.assertFalse([p for p in self.v([cam("c1@3", "c3@1")], cleared=cleared) if "person" in p or "cleared" in p])
        self.assertTrue(any("cleared" in p for p in self.v([cam("zz@1")], cleared=cleared)))
        wide = self.v([{"s": "ritual", "title": "T", "picture": {"todo": "a wide bath", "alt": "w", "ratio": 0.8}, "steps": []}])
        self.assertTrue(any("shape" in p for p in wide), wide)
        proof = self.v([{"s": "picture", "picture": {"proof": "p1", "alt": "x"}}], proof={"p1"})
        self.assertTrue(any("customer picture" in p for p in proof), proof)


class TestStills(unittest.TestCase):
    def test_7_a_still_becomes_the_runs_own_picture_at_its_shape(self):
        with tempfile.TemporaryDirectory() as t:
            run = Path(t) / "zz-nov-99"
            cleared = {"c1@3.5": {"creator": "ann", "clip_id": "c1", "t": 3.5, "drive_id": "c1"}}
            spec = {"sections": [{"s": "on_camera", "title": "T", "people": [{"picture": {"still": "c1@3.5", "alt": ""}, "name": "Ann", "line": ""}]}]}
            asked = []
            def fetch(sid, info, out):
                asked.append(sid)
                Image.new("RGB", (720, 1280)).save(out)
            LN.resolve_stills(spec, run, cleared, fetch=fetch)
            LN.resolve_stills(spec, run, cleared, fetch=fetch)       # nothing left to fetch the second time
            p = spec["sections"][0]["people"][0]["picture"]
            self.assertEqual(asked, ["c1@3.5"])
            self.assertEqual(p["photo"], "run:media/still-c1-3_5.jpg")
            self.assertEqual(p["ratio"], 0.5625)
            self.assertEqual((p["creator"], p["still"], p["source"]), ("ann", "c1@3.5", "creator"))
            self.assertTrue((run / "media" / "still-c1-3_5.jpg").is_file())


class TestShapes(unittest.TestCase):
    def test_6_each_picture_is_made_at_its_box_shape(self):
        spec = {"look": "house", "sections": [
            {"s": "ritual", "title": "T", "picture": {"todo": "wide", "alt": "w"},
             "steps": [{"picture": {"todo": "step", "alt": "s"}, "eyebrow": "e", "title": "t", "text": "x"}]},
            {"s": "finale", "title": "T", "sub": "S", "quote": "Q", "picture": {"todo": "tall", "alt": "t"}},
            {"s": "photo_card", "text": "x", "picture": {"todo": "card", "alt": "c"}}]}
        LN.box_ratios(spec, look())
        r = spec["sections"]
        self.assertAlmostEqual(r[0]["picture"]["ratio"], 16 / 9, places=3)
        self.assertEqual(r[0]["steps"][0]["picture"]["ratio"], 1.0)
        self.assertEqual(r[1]["picture"]["ratio"], 0.75)            # the house finale is split: tall picture
        self.assertEqual(r[2]["picture"]["ratio"], 0.8)
        self.assertEqual(PC.aspect_for(16 / 9), "16:9")
        self.assertEqual(PC.aspect_for(2.1), "16:9")
        self.assertEqual(PC.aspect_for(1.0), "1:1")
        self.assertEqual(PC.aspect_for(0.75), "3:4")
        self.assertEqual(PC.aspect_for(0.8), "4:5")


if __name__ == "__main__":
    unittest.main(verbosity=2)
