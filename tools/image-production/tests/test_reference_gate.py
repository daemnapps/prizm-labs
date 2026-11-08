#!/usr/bin/env python3
"""The referencing process, enforced in the inputs gate (2026-11-08): a new picture needs a real frame or a real
reference, and a picture this tool made is never a reference for another.

    python3 tools/image-production/tests/test_reference_gate.py

Stdlib `unittest`, Python 3.9. No network, no model, no key.
"""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent))                  # APPEND — never insert at 0
from image_production import gates as G            # noqa: E402

PURPOSES = {"ad": {"reference_required": True}, "email-hero": {}}
ASPECTS = {"9:16": [1152, 2048]}


def req(**k):
    return {"direction": "a picture", "purpose": "ad", "aspect": "9:16", "out": "x", "people": False, **k}


def refs_problems(r, ctx):
    return [p for p in G.input_problems(r, ctx, PURPOSES, ASPECTS) if "reference" in p]


class ReferenceGate(unittest.TestCase):
    def test_words_alone_is_refused(self):
        self.assertTrue(refs_problems(req(), {"references": []}))

    def test_a_purpose_without_the_setting_only_notes_it(self):
        notes = []
        got = G.input_problems(req(purpose="email-hero"), {"references": []}, PURPOSES, ASPECTS, notes)
        self.assertFalse([p for p in got if "reference" in p])
        self.assertTrue([n for n in notes if "reference" in n])

    def test_a_real_frame_passes(self):
        self.assertEqual(refs_problems(req(from_image="frame.png"), {"references": []}), [])

    def test_real_references_pass(self):
        self.assertEqual(refs_problems(req(), {"references": ["photo.jpg"]}), [])

    def test_an_ai_made_reference_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            made = Path(d) / "made-01.png"
            made.write_bytes(b"x")
            made.with_suffix(".recipe.json").write_text("{}")
            got = refs_problems(req(from_image="frame.png", references=[str(made)]), {"references": [str(made)]})
        self.assertTrue(any("AI-made" in p for p in got))


if __name__ == "__main__":
    unittest.main()


class NearestRealAssets(unittest.TestCase):
    """When no word matches, the index is searched wider for REAL assets instead of refusing (2026-11-08)."""

    def setUp(self):
        from image_production import assets as AS
        self.AS = AS
        self.d = tempfile.mkdtemp()

    def file(self, name, made=False):
        p = Path(self.d) / name
        p.write_bytes(b"x")
        if made:
            p.with_suffix(".recipe.json").write_text("{}")
        return str(p)

    def rows(self, *spec):
        return [{"name": Path(path).stem, "kind": kind, "path": path, "bytes": 1} for kind, path in spec]

    def near(self, rows, words, people=None):
        from unittest import mock
        with mock.patch.object(self.AS, "described", return_value=[]):
            return self.AS.nearest("acme", rows, self.AS._words(words), people, limit=2)

    def test_word_roots_match(self):
        rows = self.rows(("creator", self.file("date-night-couple.jpg")), ("environment", self.file("gym.jpg")))
        got, why = self.near(rows, "a man dating")
        self.assertEqual([Path(r["path"]).name for r in got], ["date-night-couple.jpg"])

    def test_no_word_falls_back_to_the_right_kind(self):
        rows = self.rows(("environment", self.file("kitchen.jpg")), ("creator", self.file("creator-a.jpg")))
        got, _ = self.near(rows, "zzz qqq", people=True)
        self.assertEqual(got[0]["kind"], "creator")
        got, _ = self.near(rows, "zzz qqq", people=False)
        self.assertEqual(got[0]["kind"], "environment")

    def test_a_picture_we_made_is_never_pulled_in(self):
        rows = self.rows(("creator", self.file("made-01.png", made=True)))
        got, why = self.near(rows, "made")
        self.assertEqual(got, [])

    def test_a_file_not_on_this_machine_is_skipped(self):
        rows = self.rows(("creator", str(Path(self.d) / "missing.jpg")))
        got, _ = self.near(rows, "missing")
        self.assertEqual(got, [])
