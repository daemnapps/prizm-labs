#!/usr/bin/env python3
"""python3 machine/test_style_status.py — the music style bank's status words (rule 6) and the song gate. No network."""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(f"t_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


song = _load("song")
RULE6 = {"draft", "approved", "deprecated"}
BANK = json.loads(song.STYLE_BANK.read_text())


def block_for(row):
    return {"style_id": row["id"], "vocal": row["vocal"],
            "sections": [{"name": n} for n in row["section_styles"]]}


class TheStyleStatus(unittest.TestCase):
    def test_every_row_status_is_a_rule6_word(self):
        for row in BANK["rows"]:
            self.assertIn(row.get("status"), RULE6, row.get("id"))
            self.assertNotEqual(row.get("status"), "ruled", row.get("id"))

    def test_the_heard_row_is_sung(self):
        styles = song.load_styles()
        approved = [r for r in BANK["rows"] if r.get("status") == "approved"]
        self.assertTrue(approved)
        self.assertIn("neo-soul-90s", [r["id"] for r in approved])
        for row in approved:
            got = song.style_row(block_for(row), styles)
            self.assertIs(got, styles[row["id"]])
            self.assertEqual(got["id"], row["id"])

    def test_every_draft_row_is_refused_by_name(self):
        styles = song.load_styles()
        drafts = [r for r in BANK["rows"] if r.get("status") == "draft"]
        self.assertGreaterEqual(len(drafts), 4)
        for row in drafts:
            with self.assertRaisesRegex(SystemExit, f"{row['id']!r} is a draft row, not approved"):
                song.style_row(block_for(row), styles)

    def test_the_old_word_no_longer_opens_the_gate(self):
        styles = {"x": {"id": "x", "status": "ruled", "vocal": "female", "section_styles": {"verse": "v"}}}
        block = {"style_id": "x", "vocal": "female", "sections": [{"name": "verse"}]}
        with self.assertRaisesRegex(SystemExit, "is a ruled row, not approved"):
            song.style_row(block, styles)

    def test_readme_names_approved(self):
        lines = [l for l in BANK["_readme"] if l.startswith("status:")]
        self.assertEqual(len(lines), 1)
        self.assertIn("`approved` rows are the only ones a run uses", lines[0])


if __name__ == "__main__":
    unittest.main()
