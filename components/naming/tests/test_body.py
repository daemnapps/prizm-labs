"""body.py and every door that reads it (no model, no brand: made-up lists)."""
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

WS = Path(__file__).resolve().parents[3]
for p in ("naming", "copywriter/machine", "video-production/machine", "winners", "image-production", "image-teardown/tools"):
    sys.path.append(str(WS / "components" / p))
import anatomy as A  # noqa: E402
import body  # noqa: E402

BOOK = {"brush": {"cheeks": {"ok": "yes"}, "back-of-head": {"ok": "yes"}, "heels": {"ok": "no"}, "lips": {"ok": "no"}, "palms": {"ok": "no"}}}


class Body(unittest.TestCase):
    def setUp(self):
        self.m = mock.patch.object(body, "load", lambda b, root=None: BOOK)
        self.m.start()

    def tearDown(self):
        self.m.stop()

    def test_a_spot_fits_or_says_why(self):
        self.assertIsNone(body.why_not("acme", "brush", "back-of-head"))
        self.assertIn("ruled out for heels", body.why_not("acme", "brush", "heels"))
        self.assertIn("not ruled for knees", body.why_not("acme", "brush", "knees"))
        self.assertIsNone(body.why_not("acme", "brush", ""))
        self.assertIsNone(body.why_not("acme", "a thing with no list", "heels"))
        self.assertEqual(body.members("acme", "brands/acme/products/brush/product.md"), ["brush"])
        self.assertEqual(body.members("acme", "brands/acme/products/brush.md"), ["brush"])

    def test_a_group_fits_where_some_of_it_does(self):
        with mock.patch.object(body, "load", lambda b, root=None: {"balm": {"forearms": {"ok": "yes"}, "armpits": {"ok": "no"}}, "mask": {"armpits": {"ok": "no"}, "cheeks": {"ok": "yes"}}}):
            self.assertIsNone(body.why_not("acme", "balm", "arms"))
            self.assertIn("never the armpits", body.rule("acme", "balm", "arms"))
            self.assertIn("ruled out for arms", body.why_not("acme", "mask", "arms"))

    def test_a_wrong_part_is_found_and_a_right_one_is_not(self):
        bad = lambda t: [x for _, x in body.misuse("acme", "brush", t)]                        # noqa: E731
        self.assertEqual(bad("Use it on your heels every night."), ["heels"])
        self.assertEqual(bad("Run the brush over both heels."), ["heels"])
        for ok in ("Use it on your cheeks.", "Never use it on your heels.", "He clicks his heels.", "Rub it between your palms, then use it on your cheeks.",
                   "She put her lips together.", "Use it when your heels hurt.", "I scrubbed my heels for years.", "A woman with spots on her lips holds the brush."):
            self.assertEqual(bad(ok), [], ok)

    def test_the_draft_is_read_until_the_brand_files_one(self):
        self.m.stop()
        with tempfile.TemporaryDirectory() as d:
            for rel, ok in (("runs/creative-strategist/acme/products", "no"), ("brands/acme/products", "yes")):
                f = Path(d) / rel / "body-parts.json"
                f.parent.mkdir(parents=True)
                f.write_text(json.dumps({"products": {"brush": {"cheeks": {"ok": ok}}}}))
                self.assertEqual(body.load("acme", d)["brush"]["cheeks"]["ok"], ok)
        self.m.start()

    def test_close_parts_go_together_and_far_ones_do_not(self):
        t = A.together("back-of-head")
        self.assertTrue({"nape", "crown", "behind-ears"} <= set(t))
        self.assertFalse({"chest", "knees", "lips"} & set(t))
        self.assertEqual([p for p in A.parts() if not A.together(p)], [])          # no part stands alone
        self.assertNotIn("lips", body.together("acme", "brush", "chin"))           # never one ruled out for the product
        self.assertIn("jaw", body.together("acme", "brush", "chin"))

    def test_people_words_for_a_part(self):
        self.assertIn("back of my head", A.phrases("back-of-head"))
        for p in A.parts():
            for w in A.phrases(p):
                self.assertNotRegex(w, r"[\\|()\[\]?*]", p)

    def test_copy_is_held(self):
        import copy_set as CS
        with mock.patch.dict(sys.modules, {"body": body}):
            self.assertEqual(len(CS.body_problems("acme", "brush", "Use it on your heels.")), 1)
            self.assertEqual(CS.body_problems("acme", None, "Use it on your heels."), [])

    def test_a_clip_call_is_held(self):
        import clip_checklist as CK
        cr = types.SimpleNamespace(product_ids=lambda *a: ["brush"])
        with mock.patch.dict(sys.modules, {"body": body}), mock.patch.object(CK, "_read", lambda *a: {"brand": "acme"}):
            self.assertTrue(CK.body_lines(Path("x"), {}, "He rubs the brush over his heels.", cr)[0])
            self.assertEqual(CK.body_lines(Path("x"), {}, "He uses it on his cheeks.", cr)[0], [])

    def test_a_picture_is_told_and_judged_by_it(self):
        from image_production import brand_facts as BF
        rows = [{"name": "brush", "facts": ["It is round."]}]
        with mock.patch.dict(sys.modules, {"body": body}), mock.patch.object(BF, "product_rows", lambda *a, **k: rows):
            self.assertIn("If it is shown on skin: Used only on", BF.facts_for_prompt("acme", "brush"))
            tests, _ = BF.product_checks("acme", "", "brush")
            self.assertTrue(any("ruled-out place" in t for t in tests))

    def test_video_words_are_judged_by_it(self):
        src = (WS / "components/video-production/machine/claimfix.py").read_text()
        self.assertIn("body.rule(brand, product, root=WS)", src)

    def test_sales_know_the_part(self):
        import who_view as V
        self.assertIn(("where", "Body part"), V.DIMS)
        import people
        with mock.patch.object(people, "new_names", lambda b, a, s="": (a, "where-nape")):
            self.assertEqual(V.body_part("acme", "x", "y"), "nape")
        with mock.patch.object(people, "new_names", lambda b, a, s="": (a, "tried-all")):
            self.assertIsNone(V.body_part("acme", "x", "y"))


if __name__ == "__main__":
    unittest.main()
