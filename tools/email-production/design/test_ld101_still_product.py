#!/usr/bin/env python3
"""LD-101 (Brand-B house look), the team 2026-10-30: a customer section's stills show the email's own product. A
face-scrub still in a body-scrub email is held, and so is a still whose record names no product at all (nobody
can say what it shows).

    /usr/bin/python3 tools/email-production/design/test_ld101_still_product.py

Offline: a fixture look and fixture product slugs (no brand file is read); the asset-index search is a stand-in.

  1  names_product(): a record names a product when it carries the product's name, the last words of its slug that
     no other product of the brand ends on, at least two ("body scrub", "body cream"); a colour word ("cream tube")
     never names the cream
  2  the validator holds a still that shows another product, or no product it can name, and keeps one that shows
     the email's own product
  3  cleared_people() offers only stills that show the email's product, and each one it offers carries what its
     clip shows
  4  a cleared still the layout wrote as a proof id is read as the still it is (nov-04's first run, 2026-10-30), and
     a still outside on_camera holds the email (the layout prompt says people show only through on_camera)
"""
import sys
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))      # design/ FIRST; never tools/email-production (its email.py shadows the stdlib's)
import look as L                   # noqa: E402
import line as LN                  # noqa: E402

SLUGS = ["zz-body-scrub", "zz-face-scrub", "glow-body-cream"]
BODY = ["brown tube, gold label 'zz skincare body scrub turmeric'"]
FACE = ["cream tube, gold label 'zz skincare face scrub turmeric'"]
NONE = ["thick pale cream scrub with dark flecks"]


def look():
    return L.Look("zz", {"house": {"sections": ["on_camera"], "styles": {}}}, None)


class TestNames(unittest.TestCase):
    def test_1_a_record_names_a_product_by_what_sets_it_apart(self):
        self.assertTrue(LN.names_product(BODY[0], "zz-body-scrub", SLUGS))
        self.assertFalse(LN.names_product(BODY[0], "zz-face-scrub", SLUGS))
        self.assertTrue(LN.names_product(FACE[0], "zz-face-scrub", SLUGS))
        self.assertFalse(LN.names_product(FACE[0], "zz-body-scrub", SLUGS))
        self.assertFalse(LN.names_product(NONE[0], "zz-body-scrub", SLUGS))
        self.assertTrue(LN.names_product("two body scrubs on the shelf", "zz-body-scrub", SLUGS))
        self.assertFalse(LN.names_product("a body cream jar", "zz-body-scrub", SLUGS))
        self.assertTrue(LN.names_product("a body cream jar", "glow-body-cream", SLUGS))
        self.assertFalse(LN.names_product(FACE[0], "glow-body-cream", SLUGS), "a cream tube is not the body cream")


class TestHold(unittest.TestCase):
    def v(self, products, product="zz-body-scrub"):
        cleared = {"c1@3": {"creator": "ann", "products": products, "shows": "Woman smiles at the camera."}}
        spec = {"look": "house", "sections": [
            {"s": "on_camera", "title": "T", "people": [{"picture": {"still": "c1@3", "alt": "Ann"}, "name": "Ann", "line": ""}]},
            {"s": "foot"}]}
        return LN.validate(spec, look(), set(), {}, None, cleared=cleared, product=product, slugs=SLUGS)

    def test_2_a_still_of_another_product_or_of_none_is_held(self):
        face = self.v(FACE)
        self.assertTrue(any("zz-face-scrub" in p and "zz-body-scrub" in p for p in face), face)
        none = self.v(NONE)
        self.assertTrue(any("names no product" in p for p in none), none)
        self.assertFalse([p for p in self.v(BODY) if "product" in p], self.v(BODY))
        both = self.v(BODY + FACE)
        self.assertTrue(any("zz-face-scrub" in p for p in both), both)
        self.assertFalse([p for p in self.v(FACE, product="") if "product" in p], "an email with no product is not checked")


class TestOffer(unittest.TestCase):
    def test_3_only_stills_of_the_emails_product_are_offered(self):
        hits = [{"clip_id": "b1", "in": 0, "out": 4, "rights": {"creator": "ann"}, "products": BODY, "shows": "body", "says": ""},
                {"clip_id": "f1", "in": 0, "out": 4, "rights": {"creator": "bea"}, "products": FACE, "shows": "face", "says": ""},
                {"clip_id": "n1", "in": 0, "out": 4, "rights": {"creator": "cat"}, "products": NONE, "shows": "none", "says": ""}]
        fake = types.SimpleNamespace(search=lambda *a, **k: list(hits))
        orig = LN._asset_index
        LN._asset_index = lambda: (fake, None)
        try:
            got, txt = LN.cleared_people("zz", "zz-body-scrub", slugs=SLUGS)
        finally:
            LN._asset_index = orig
        self.assertEqual(list(got), ["b1@2.0"])
        self.assertEqual(got["b1@2.0"]["products"], BODY)
        self.assertNotIn("f1", txt)
        self.assertNotIn("n1", txt)


class TestStillPlace(unittest.TestCase):
    def test_4_a_cleared_still_written_as_proof_is_a_still_and_lives_in_on_camera(self):
        cleared = {"c1@3": {"creator": "ann", "products": BODY, "shows": ""}}
        spec = {"look": "house", "sections": [{"s": "picture", "picture": {"proof": "c1@3", "alt": "Ann", "source": "proof"}},
                                              {"s": "picture", "picture": {"proof": "p9", "alt": "x"}}, {"s": "foot"}]}
        LN.stills_as_stills(spec, cleared)
        self.assertEqual(spec["sections"][0]["picture"], {"still": "c1@3", "alt": "Ann"})
        self.assertEqual(spec["sections"][1]["picture"], {"proof": "p9", "alt": "x"}, "a real proof id is left alone")
        held = LN.validate({"look": "house", "sections": spec["sections"][:1] + [{"s": "foot"}]}, look(), set(), {}, None,
                           cleared=cleared)
        self.assertTrue(any("only through on_camera" in p for p in held), held)
        clean = {"look": "house", "sections": [
            {"s": "on_camera", "title": "T", "people": [{"picture": {"still": "c1@3", "alt": "Ann"}, "name": "Ann", "line": ""}]},
            {"s": "foot"}]}
        self.assertEqual(LN.validate(clean, look(), set(), {}, None, cleared=cleared), [],
                         "a cleared still in on_camera renders in the validator's test draw")


if __name__ == "__main__":
    unittest.main(verbosity=2)
