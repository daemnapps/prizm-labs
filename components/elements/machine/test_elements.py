#!/usr/bin/env python3
"""The element library's self-test.

    python3 test_elements.py

Proves: the build runs; every id follows the rule (lowercase, "-" between
words); an old spelling resolves through its alias to the same row and never
to a second row; a dropped id is refused with its reason; a library written
before rows had `aliases` still reads; check() is clean for both spellings.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import elements as E  # noqa: E402


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.real = E.LIBRARY
        E.LIBRARY = cls.tmp
        E._cache.clear()
        cls.index = E.build()

    @classmethod
    def tearDownClass(cls):
        E.LIBRARY = cls.real
        E._cache.clear()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_every_id_follows_the_rule(self):
        off = {f'{l["element"]}/{l["asset"]}': l["off_rule"] for l in self.index["lists"] if l["off_rule"]}
        self.assertEqual(off, {})
        for l in self.index["lists"]:
            self.assertEqual(l["duplicates"], [], f'{l["element"]}/{l["asset"]} has duplicate ids')
            self.assertEqual(l["unresolved"], [], f'{l["element"]}/{l["asset"]} has rulings that name nothing')

    def test_no_squashed_ids_remain(self):
        ids = {r["id"] for r in E.rows("format", "image")}
        for old in ("stickynote", "usvsthem", "notesapp", "barephoto", "benefitstack", "distressedposter"):
            self.assertNotIn(old, ids)
        self.assertNotIn("salespage", {r["id"] for r in E.rows("format", "page")})

    def test_old_spelling_resolves_to_the_same_row(self):
        self.assertIs(E.get("format", "image", "stickynote"), E.get("format", "image", "sticky-note"))
        self.assertEqual(E.canonical("format", "image", "usvsthem"), "us-vs-them")
        self.assertEqual(E.canonical("format", "image", "faceoff"), "us-vs-them")        # mapped
        self.assertEqual(E.canonical("format", "image", "illustrated"), "product-void")  # mapped: a style
        self.assertEqual(E.canonical("format", "image", "Apology"), "apology")           # case on an alias
        self.assertEqual(E.canonical("format", "image", "distressedposter"), "distressed-poster")
        self.assertEqual(E.canonical("format", "page", "salespage"), "sales-page")
        self.assertEqual(E.canonical("format", "page", "prelander"), "pre-lander")

    def test_an_alias_is_never_also_an_id(self):
        for l in self.index["lists"]:
            rows = E.rows(l["element"], l["asset"])
            ids = {r["id"] for r in rows}
            for r in rows:
                for a in r["aliases"]:
                    self.assertNotIn(a, ids, f"{a} is both an alias and an id in {l['element']}/{l['asset']}")

    def test_check_is_clean_for_both_spellings(self):
        self.assertEqual(E.check({("format", "image"): ["stickynote", "sticky-note", "faceoff", "two-panel", "twopanel"]}), [])

    def test_dropped_id_is_refused_with_its_reason(self):
        probs = E.check({("format", "image"): "mixed"})
        self.assertEqual(len(probs), 1)
        self.assertIn("dropped", probs[0])
        self.assertIn("not a format", probs[0])

    def test_unknown_names_the_real_ids_and_their_old_spellings(self):
        with self.assertRaises(E.Unknown) as cm:
            E.get("format", "page", "landing")
        self.assertIn("sales-page (was salespage)", cm.exception.args[0])

    def test_decision_8_rows(self):
        for id_ in ("apology", "distressed-poster", "portrait-void", "two-panel", "checklist", "mirror-selfie",
                    "product-void", "caption-box", "comment-reply", "routine-label", "macro-texture"):
            r = E.get("format", "image", id_)
            self.assertTrue(r["approved"], id_)
            self.assertTrue(r["what"] and not r["what"].startswith("[TO DEFINE"), id_)

    def test_damons_four_rows(self):
        for el, asset, id_ in (("structure", "video", "storytelling"),
                               ("delivery", "delivery_style", "holistic-healer-authority"),
                               ("format", "image", "native-facebook-image"),
                               ("style", "video", "claymation")):
            r = E.get(el, asset, id_)
            self.assertTrue(r["approved"], id_)
            self.assertIn("review pending", r["note"] or "", id_)
            self.assertTrue(r["examples"], id_)

    def test_first_carousel_list(self):
        rows = E.rows("format", "carousel")
        self.assertTrue(5 <= len(rows) <= 10)
        self.assertTrue(all(r["status"] == "proposed" for r in rows))


class OldLibraryShape(unittest.TestCase):
    """A library written before rows carried `aliases` (a tool's test stub,
    an older checkout) still reads and still refuses."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.real = E.LIBRARY
        E.LIBRARY = self.tmp
        E._cache.clear()
        (self.tmp / "format.image.json").write_text(json.dumps({
            "element": "format", "asset": "image",
            "rows": [{"id": "stickynote", "name": "x", "status": "draft", "approved": False}]}))

    def tearDown(self):
        E.LIBRARY = self.real
        E._cache.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_reads_and_refuses(self):
        self.assertEqual(E.get("format", "image", "stickynote")["id"], "stickynote")
        self.assertEqual(E.aliases("format", "image"), {})
        self.assertEqual(E.dropped("format", "image"), {})
        self.assertEqual(len(E.check({("format", "image"): "sticky-note"})), 1)


if __name__ == "__main__":
    unittest.main(verbosity=1)
