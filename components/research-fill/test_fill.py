#!/usr/bin/env python3
"""Tests for research fill, on a synthetic brand folder."""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fill  # noqa: E402


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data) if not isinstance(data, str) else data)


class FillTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.b = self.root / "brands" / "acme"
        write(self.b / "core-avatars" / "avatars.json", {"avatars": [{"id": "busy-mom", "folder": "core-avatars/busy-mom"}, {"id": "<avatar-id>"}]})
        write(self.b / "core-avatars" / "busy-mom" / "profile.md", "# Busy mom\n")
        write(self.b / "operations" / "language-pulls.json", json.load(open(Path(fill.REPO) / "brands" / "_TEMPLATE" / "operations" / "language-pulls.json")))
        self.keys = {}
        self.lines = 0
        self.todo = ["busy-mom: build its card (who.py build)"]
        fill.Brand.bank_lines = lambda s, a: self.lines
        fill.Brand.profile_todo = lambda s, a: self.todo

    def run_fill(self, *argv):
        out = io.StringIO()
        code = fill.main(list(argv), out=out, root=self.root, key=lambda n: self.keys.get(n))
        return code, out.getvalue()

    def steps(self):
        b = fill.Brand("acme", root=self.root, key=lambda n: self.keys.get(n))
        return {s["id"]: s for s in b.steps(b.avatars()[0])}

    def test_template_placeholders_grant_nothing(self):
        b = fill.Brand("acme", root=self.root, key=lambda n: None)
        self.assertFalse(any(a["granted"] for a in b.access()))
        self.assertEqual([a["id"] for a in b.avatars()], ["busy-mom"])

    def test_access_follows_keys_and_files(self):
        self.keys = {"APIFY_TOKEN": "set", "JUDGEME_ACME": "set"}
        write(self.b / "operations" / "language-pulls.json", {"reviews": {"platform": "judgeme", "key": "JUDGEME_ACME", "shop_domain": "acme.example"}})
        granted = {a["id"]: a["granted"] for a in fill.Brand("acme", root=self.root, key=lambda n: self.keys.get(n)).access()}
        self.assertTrue(granted["apify"])
        self.assertTrue(granted["reviews"])
        self.assertFalse(granted["surveys"])
        self.keys.pop("JUDGEME_ACME")
        granted = {a["id"]: a["granted"] for a in fill.Brand("acme", root=self.root, key=lambda n: self.keys.get(n)).access()}
        self.assertFalse(granted["reviews"])

    def test_steps_block_without_access_and_never_print_keys(self):
        s = self.steps()
        self.assertEqual(s["avatar"]["state"], "done")
        self.assertEqual(s["sources"]["state"], "todo")
        self.assertEqual(s["bank"]["state"], "blocked")
        self.assertEqual(s["rooms"]["state"], "blocked")
        self.keys = {"APIFY_TOKEN": "secret-value-xyz", "DATABASE_URL": "postgres://x"}
        code, out = self.run_fill("access", "--brand", "acme")
        self.assertNotIn("secret-value-xyz", out)
        s = self.steps()
        self.assertEqual(s["sources"]["state"], "done")
        self.assertEqual(s["rooms"]["state"], "todo")

    def test_full_run_through(self):
        self.keys = {"APIFY_TOKEN": "x", "DATABASE_URL": "x"}
        self.lines = 30
        self.todo = []
        write(self.b / "core-avatars" / "busy-mom" / "profile.md", "# Busy mom\n### rooms\n- r/parenting\n")
        runs = self.root / "runs" / "swipe-organic" / "acme"
        write(runs / "research-busy-mom-2026-11-01-formats" / "ranking.json", {})
        s = self.steps()
        self.assertEqual(s["formats"]["state"], "done")
        self.assertEqual(s["problem"]["state"], "todo")
        write(runs / "research-busy-mom-2026-11-02-problem" / "ranking.json", {})
        write(runs / "matrix-busy-mom" / "concepts.json", {})
        code, out = self.run_fill("next", "--brand", "acme")
        self.assertIn("Owner picks concepts", out)
        code, out = self.run_fill("status", "--brand", "acme")
        self.assertIn("8 of 9 done", out)

    def test_next_names_the_command_and_price(self):
        self.keys = {"APIFY_TOKEN": "x", "DATABASE_URL": "x"}
        self.lines = 30
        code, out = self.run_fill("next", "--brand", "acme")
        self.assertIn("Find where he talks", out)
        self.assertIn("--brand acme --avatar busy-mom", out)
        self.assertIn("owner's go", out)

    def test_missing_brand_and_no_avatar(self):
        code, out = self.run_fill("status", "--brand", "nobody")
        self.assertEqual(code, 2)
        self.assertIn("brand-sync", out)
        write(self.b / "core-avatars" / "avatars.json", {"avatars": [{"id": "<avatar-id>"}]})
        code, out = self.run_fill("status", "--brand", "acme")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
