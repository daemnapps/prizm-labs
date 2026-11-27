#!/usr/bin/env python3
"""Tests for the onboarding page's back end, on a temporary repo copy: keys catalog, .env writing, brands, ad account."""
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import serve as S  # noqa: E402


class OnboardingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "brands" / "_TEMPLATE" / "operations").mkdir(parents=True)
        (root / "brands" / "_TEMPLATE" / "onboarding.json").write_text(json.dumps([{"id": "brand-name"}, {"id": "website"}]))
        (root / "brands" / "_TEMPLATE" / "ONBOARDING.md").write_text("- [ ] brand name\n")
        (root / "brands" / "_TEMPLATE" / "operations" / "brand.json").write_text('{"brand": "<brand>"}')
        (root / ".env.example").write_text(
            "# --- AI models ---\n# Gemini: reads videos. Get it: https://aistudio.google.com/apikey\nGEMINI_API_KEY=\n\n"
            "# AudD (optional): finds music. Get it: https://dashboard.audd.io\nAUDD_API_TOKEN=\n")
        self.old = (S.ENV, S.EXAMPLE, S.BRANDS, S.TEMPLATE, S.loader.DOTENV, S.loader.KEY_FILE)
        S.ENV, S.EXAMPLE = root / ".env", root / ".env.example"
        S.BRANDS, S.TEMPLATE = root / "brands", root / "brands" / "_TEMPLATE"
        S.loader.DOTENV = S.loader.KEY_FILE = root / ".env"
        os.environ.pop("GEMINI_API_KEY", None)
        self.root = root

    def tearDown(self):
        S.ENV, S.EXAMPLE, S.BRANDS, S.TEMPLATE, S.loader.DOTENV, S.loader.KEY_FILE = self.old
        self.tmp.cleanup()

    def test_catalog_reads_names_where_and_optional(self):
        c = {k["name"]: k for k in S.catalog()}
        self.assertEqual(c["GEMINI_API_KEY"]["where"], "https://aistudio.google.com/apikey")
        self.assertFalse(c["GEMINI_API_KEY"]["optional"])
        self.assertTrue(c["AUDD_API_TOKEN"]["optional"])
        self.assertEqual(c["GEMINI_API_KEY"]["section"], "AI models")

    def test_save_key_writes_env_private_and_keeps_other_lines(self):
        S.save_key("GEMINI_API_KEY", "abc123")
        S.save_key("AUDD_API_TOKEN", "zzz")
        text = S.ENV.read_text()
        self.assertIn("GEMINI_API_KEY=abc123", text)
        self.assertIn("AUDD_API_TOKEN=zzz", text)
        self.assertEqual(stat.S_IMODE(os.stat(S.ENV).st_mode), 0o600)
        self.assertTrue(S.key_status()["GEMINI_API_KEY"])

    def test_bad_key_refused(self):
        with self.assertRaises(ValueError):
            S.save_key("bad name", "x")
        with self.assertRaises(ValueError):
            S.save_key("GEMINI_API_KEY", "two\nlines")

    def test_new_and_linked_brand(self):
        self.assertEqual(S.add_brand("Sample Co"), "sample-co")
        self.assertTrue((S.BRANDS / "sample-co" / "operations" / "brand.json").is_file())
        elsewhere = self.root / "their-repo" / "brand"
        elsewhere.mkdir(parents=True)
        S.add_brand("Other", str(elsewhere))
        self.assertTrue((S.BRANDS / "other").is_symlink())
        self.assertEqual([b["brand"] for b in S.brands()], ["other", "sample-co"])
        with self.assertRaises(ValueError):
            S.add_brand("Sample Co")

    def test_ad_account(self):
        S.add_brand("Sample Co")
        S.save_account("sample-co", "1234567890")
        d = json.loads((S.BRANDS / "sample-co" / "operations" / "brand.json").read_text())
        self.assertEqual(d["ad_accounts"], [{"network": "meta", "account": "act_1234567890"}])
        with self.assertRaises(ValueError):
            S.save_account("sample-co", "nope")


if __name__ == "__main__":
    unittest.main()
