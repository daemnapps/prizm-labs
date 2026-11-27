#!/usr/bin/env python3
"""Tests for cast.py: person ids, scene fields and story-beat matching (no model, no network)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cast  # noqa: E402

ANS = {"persons": [{"p": "A", "gender": "man", "age": "30s", "skin_tone": "deep", "look": "beard", "main": True},
                   {"p": "B", "gender": "woman", "age": "20s", "skin_tone": "medium", "look": "long hair", "main": False}],
       "letterbox": False,
       "scenes": [{"n": 1, "on_screen": ["A", "B"], "face_visible": True, "couple": True, "action": "hugs her",
                   "action_tags": ["hugging-kissing", "made-up"], "product_in_use": "none", "competitor": None,
                   "room": "bedroom", "framing": "medium", "angle": "eye-level", "camera": "handheld", "emotion": "happy"},
                  {"n": 2, "on_screen": ["hands"], "face_visible": False, "couple": False, "action": "holds a box",
                   "action_tags": ["showing-product"], "product_in_use": "nope", "room": "attic", "emotion": "odd"}]}


class CastFields(unittest.TestCase):
    def test_named_creator_owns_main_person(self):
        f = cast.fields_for("b", {"clip": "c1", "scene": 1, "creator": "sam"}, ANS)
        self.assertEqual(f["main_person"], "b/sam")
        self.assertEqual(f["person_ids"], ["b/sam", "b/clip/c1#B"])
        self.assertTrue(f["woman_present"] and f["couple"] and f["face_visible"])
        self.assertEqual(f["people_count"], 2)
        self.assertEqual(f["action_tags"], ["hugging-kissing"])          # words outside the list are dropped

    def test_bucket_creator_gets_clip_scoped_id(self):
        f = cast.fields_for("b", {"clip": "c1", "scene": 1, "creator": "intake/organic"}, ANS)
        self.assertEqual(f["main_person"], "b/clip/c1#A")

    def test_hands_and_unknown_words(self):
        f = cast.fields_for("b", {"clip": "c1", "scene": 2, "creator": "sam"}, ANS)
        self.assertEqual(f["people_count"], "hands")
        self.assertEqual(f["room"], "unclear")
        self.assertEqual(f["emotion"], "unclear")
        self.assertEqual(f["product_in_use"], "none")

    def test_scene_not_answered_says_why(self):
        f = cast.fields_for("b", {"clip": "c1", "scene": 9, "creator": "sam"}, ANS)
        self.assertFalse(f["cast_checked"])
        self.assertTrue(f["cast_reason"])

    def test_brand_settings_add_words_and_aliases(self):
        cast._CFG["acme"] = {"actions": ["polishing-shoes"], "person_aliases": {"sam-handle": "sam"},
                             "category": "shoe care product", "competitors": ["zz-a"]}
        ans = {"persons": ANS["persons"], "scenes": [dict(ANS["scenes"][0], action_tags=["polishing-shoes"])]}
        f = cast.fields_for("acme", {"clip": "c1", "scene": 1, "creator": "sam-handle"}, ans)
        self.assertEqual(f["action_tags"], ["polishing-shoes"])
        self.assertEqual(f["main_person"], "acme/sam")
        p = cast.prompt_for({"scenes": [(1, 0, 2, "x")]}, "{category} | {competitors} | {actions}", "acme")
        self.assertIn("shoe care product", p); self.assertIn("zz-a", p); self.assertIn("polishing-shoes", p)
        f2 = cast.fields_for("b", {"clip": "c1", "scene": 1, "creator": "sam"}, ans)
        self.assertEqual(f2["action_tags"], [])                          # another brand does not get acme's words

    def test_daily_brands_from_settings(self):
        import json, os, tempfile, importlib
        with tempfile.TemporaryDirectory() as d:
            for b, on in (("acme", True), ("zz-a", False), ("_TEMPLATE", True)):
                Path(d, b).mkdir()
                Path(d, b, "footage-library.json").write_text(json.dumps({"daily": {"on": on, "usd": 3}}))
            os.environ["ASSET_INDEX_BRANDS"] = d
            import daily_brands
            importlib.reload(daily_brands)
            self.assertEqual(daily_brands.daily(), [("acme", 3.0)])
            del os.environ["ASSET_INDEX_BRANDS"]

    def test_story_beats(self):
        row = {"room": "bedroom", "action_tags": ["hugging-kissing"], "couple": True, "product_in_use": "none"}
        self.assertTrue(cast._match(row, {"couple": True, "actions": ["hugging-kissing"]}))
        self.assertFalse(cast._match(dict(row, action_tags=[]), {"couple": True, "actions": ["hugging-kissing"]}))
        self.assertTrue(cast._match({"room": "gym", "action_tags": []}, {"rooms": ["gym"], "actions": ["working-out"]}))
        self.assertFalse(cast._match(row, {"product_in_use": True}))


if __name__ == "__main__":
    unittest.main()
