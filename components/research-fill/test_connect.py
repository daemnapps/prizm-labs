#!/usr/bin/env python3
"""Tests for connect: writes only the brand's own config, names keys never values, proves each source with a dry run."""
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import connect  # noqa: E402
import fill  # noqa: E402

TEMPLATE = Path(connect.REPO) / "brands" / "_TEMPLATE" / "operations"


class ConnectTest(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.b = self.root / "brands" / "acme"
        (self.b / "operations").mkdir(parents=True)
        (self.b / "core-avatars").mkdir()
        (self.b / "core-avatars" / "avatars.json").write_text(json.dumps({"avatars": [{"id": "busy-mom"}]}))
        for f in ("language-pulls.json", "brand.json"):
            (self.b / "operations" / f).write_text((TEMPLATE / f).read_text())
        self.calls = []

    def runner(self, argv, **kw):
        self.calls.append(argv)
        return SimpleNamespace(returncode=0, stdout="pulled 12 · new 12 · filed 0\n", stderr="")

    def run_c(self, *argv):
        out = io.StringIO()
        code = connect.main(list(argv), out=out, root=self.root, runner=self.runner)
        return code, out.getvalue()

    def pulls(self):
        return json.loads((self.b / "operations" / "language-pulls.json").read_text())

    def test_reviews_writes_key_name_and_dry_runs(self):
        code, out = self.run_c("reviews", "--brand", "acme", "--platform", "judgeme", "--key", "JUDGEME_ACME", "--shop-domain", "acme.example")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.pulls()["reviews"]["key"], "JUDGEME_ACME")
        self.assertEqual(self.pulls()["language_avatar"], "busy-mom")
        self.assertIn("reviews", self.calls[-1])
        self.assertIn("--dry-run", self.calls[-1])
        self.assertIn("it pulls", out)

    def test_refuses_key_values_and_bad_input(self):
        for argv in (["reviews", "--brand", "acme", "--platform", "junip", "--key", "sk_live_abcdef123"],
                     ["reviews", "--brand", "acme", "--platform", "judgeme", "--key", "JUDGEME_ACME"],
                     ["surveys", "--brand", "acme", "--sheet", "short", "--name", "x", "--relationship", "ordered"],
                     ["ad-comments", "--brand", "acme", "--meta-account", "12345"],
                     ["interviews", "--brand", "acme", "--inbox", "../../outside"]):
            code, out = self.run_c(*argv)
            self.assertEqual(code, 2, argv)
        self.assertNotIn("sk_live", (self.b / "operations" / "language-pulls.json").read_text())
        self.assertFalse((self.root / "outside").exists())
        self.assertEqual(self.calls, [])

    def test_surveys_replace_template_and_add(self):
        sheet = "1AbCdEfGhIjKlMnOpQrStUvWxYz012345"
        self.run_c("surveys", "--brand", "acme", "--sheet", sheet, "--name", "Post purchase", "--relationship", "ordered")
        self.run_c("surveys", "--brand", "acme", "--sheet", sheet[::-1], "--name", "Refunds", "--relationship", "refund")
        rows = self.pulls()["surveys"]
        self.assertEqual([r["survey"] for r in rows], ["post-purchase", "refunds"])

    def test_interviews_helpdesk_ad_comments_and_test_all(self):
        self.run_c("interviews", "--brand", "acme", "--speaker", "Founder")
        self.assertTrue((self.b / "core-avatars/busy-mom/language/evidence/inbox").is_dir())
        self.run_c("helpdesk", "--brand", "acme", "--helpdesk", "gorgias")
        self.run_c("ad-comments", "--brand", "acme", "--meta-account", "act_1234567890")
        brand = json.loads((self.b / "operations" / "brand.json").read_text())
        self.assertEqual(brand["accounts"]["helpdesk"], "gorgias")
        self.assertEqual(brand["ad_accounts"][0]["account"], "act_1234567890")
        self.assertIn("--no-scrape", self.calls[-1])
        self.calls.clear()
        code, out = self.run_c("test", "--brand", "acme")
        self.assertEqual(code, 0)
        self.assertEqual(sorted(c[2] for c in self.calls), ["interviews", "ownvoice"])

    def test_daily_runs_in_place_and_schedule_prints(self):
        code, out = self.run_c("daily", "--brand", "acme", "--dry-run")
        self.assertIn("--inside", self.calls[-1])
        out = io.StringIO()
        connect.main(["schedule", "--print"], out=out, root=self.root)
        self.assertIn("--inside", out.getvalue())
        self.assertIn(str(self.root), out.getvalue())

    def test_connected_sources_count_in_fill(self):
        self.run_c("reviews", "--brand", "acme", "--platform", "junip", "--key", "JUNIP_ACME")
        b = fill.Brand("acme", root=self.root, key=lambda n: "x" if n == "JUNIP_ACME" else None)
        self.assertTrue({a["id"]: a["granted"] for a in b.access()}["reviews"])


class SwitchTest(ConnectTest):
    def test_daily_switch_is_off_until_turned_on(self):
        b = fill.Brand("acme", root=self.root, key=lambda n: None)
        self.assertFalse({a["id"]: a["granted"] for a in b.access()}["daily"])
        code, out = self.run_c("daily-on", "--brand", "acme")
        self.assertIn("Daily pull on", out)
        self.assertTrue(self.pulls()["daily"]["on"])
        self.assertTrue({a["id"]: a["granted"] for a in b.access()}["daily"])
        sys.path.insert(0, str(Path(connect.REPO) / "components" / "research-gatherer"))
        import importlib
        daily = importlib.import_module("daily")
        self.assertEqual(daily.brands(self.root, None), ["acme"])
        self.run_c("daily-off", "--brand", "acme")
        self.assertFalse(self.pulls()["daily"]["on"])
        self.assertEqual(daily.brands(self.root, None), [])
        self.assertEqual(daily.brands(self.root, ["acme"]), ["acme"])
        self.assertEqual(self.calls, [])


class StaleTest(unittest.TestCase):
    def test_old_rounds_come_up_again(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            b = root / "brands" / "acme"
            (b / "core-avatars" / "busy-mom").mkdir(parents=True)
            (b / "core-avatars" / "avatars.json").write_text(json.dumps({"avatars": [{"id": "busy-mom"}]}))
            (b / "core-avatars" / "busy-mom" / "profile.md").write_text("### rooms\n")
            for label in ("a", "b"):
                f = root / "runs" / "swipe-organic" / "acme" / f"research-busy-mom-{label}" / "ranking.json"
                f.parent.mkdir(parents=True)
                f.write_text("{}")
                old = time.time() - 40 * 86400
                os.utime(f, (old, old))
            brand = fill.Brand("acme", root=root, key=lambda n: "x")
            brand.bank_lines = lambda a: 30
            brand.profile_todo = lambda a: []
            steps = {s["id"]: s for s in brand.steps(brand.avatars()[0])}
            self.assertEqual(steps["formats"]["state"], "stale")
            self.assertIn("40 days", steps["formats"]["detail"])


if __name__ == "__main__":
    unittest.main()
