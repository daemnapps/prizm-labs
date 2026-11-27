#!/usr/bin/env python3
"""Tests for the creator kit check: the kit file holds together and the check reports keys, brands and skills."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


class KitTest(unittest.TestCase):
    def test_every_skill_in_the_loop_exists(self):
        kit = json.loads((Path(__file__).parent / "kit.json").read_text())
        for s in kit["loop"]:
            self.assertTrue((REPO / ".claude" / "skills" / s["skill"] / "SKILL.md").is_file(), s["skill"])

    def test_every_key_is_in_the_key_list(self):
        kit = json.loads((Path(__file__).parent / "kit.json").read_text())
        example = (REPO / ".env.example").read_text()
        for group in kit["keys"].values():
            for name in group:
                self.assertIn(name + "=", example, name)

    def test_not_ready_without_a_brand(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "brands" / "_TEMPLATE").mkdir(parents=True)
            r = check.report(Path(d))
            self.assertEqual(r["brands"], [])
            self.assertFalse(r["ready"])


if __name__ == "__main__":
    unittest.main()
