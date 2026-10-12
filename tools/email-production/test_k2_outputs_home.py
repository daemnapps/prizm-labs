#!/usr/bin/env python3
"""SI-53 (email outputs home): every run this component writes lands under
runs/email-production/<brand>/<label>/, through paths.run_home — never beside
the code (email-production#19, triage page 9).

    python3 test_k2_outputs_home.py

No network, no model, no key. The workspace is a temp folder (AI_WORKSPACE,
set before paths.py is imported); nothing is written under the real runs/ or
brands/.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
WS = Path(tempfile.mkdtemp(prefix="email-production-outputs-home-")) / "ws"
(WS / "brands" / "zz-brand").mkdir(parents=True)
(WS / "runs").mkdir()
os.environ["AI_WORKSPACE"] = str(WS)            # before anything imports paths.py

sys.path.insert(0, str(HERE))
from paths import run_home, brand_runs  # noqa: E402


def src(name):
    return (HERE / name).read_text()


class TheHome(unittest.TestCase):
    def test_the_home(self):
        tmp = Path(tempfile.mkdtemp(prefix="email-production-home-"))
        home = run_home("zz-brand", "l1", root=tmp)
        self.assertEqual(home, tmp.resolve() / "runs/email-production/zz-brand/l1")
        self.assertFalse(home.exists())          # named, never made here
        self.assertEqual(brand_runs("zz-brand", root=tmp), home.parent)

    def test_unplain_names_are_refused(self):
        tmp = Path(tempfile.mkdtemp(prefix="email-production-home-"))
        for label in ("", ".", "..", "../x", "a/b", "/abs"):
            with self.assertRaises(SystemExit) as cm:
                run_home("zz-brand", label, root=tmp)
            self.assertTrue(str(cm.exception).startswith("REFUSED:"), label)
        for brand in ("", "../brands"):
            with self.assertRaises(SystemExit) as cm:
                run_home(brand, "l1", root=tmp)
            self.assertTrue(str(cm.exception).startswith("REFUSED:"), brand)
            with self.assertRaises(SystemExit) as cm:
                brand_runs(brand, root=tmp)
            self.assertTrue(str(cm.exception).startswith("REFUSED:"), brand)


class WritersAndReaders(unittest.TestCase):
    OLD = {
        "compose.py": ['HERE / "results" / label'],
        "affiliate_email.py": ['HERE / "results" / s["id"]'],
        "live_read.py": ['HERE / "results" / f"research-'],
        "pull/derive.py": ['"brands" / f"{args.brand}-derived.md"'],
        "drafts_page.py": ['(HERE / "drafts.html")', '(HERE / "DRAFTS.md")'],
        "build_review.py": ['HERE / f"review-'],
    }

    def test_writers_use_the_home(self):
        for name, olds in self.OLD.items():
            text = src(name)
            self.assertIn("run_home(", text, name)
            for old in olds:
                self.assertNotIn(old, text, name)

    def test_readers_moved_with_them(self):
        self.assertNotIn("results/research-", src("brief.py"))
        review = src("build_review.py")
        self.assertNotIn('src="results/', review)
        self.assertNotIn('href="results/', review)
        self.assertIn("brand_runs(", src("push_klaviyo.py"))


class ReviewPage(unittest.TestCase):
    def test_review_links_are_relative_to_the_page(self):
        import build_review
        tmp = Path(tempfile.mkdtemp(prefix="email-production-review-"))
        run = tmp / "runs" / "email-production" / "zz-brand" / "zz-l1"
        run.mkdir(parents=True)
        (run / "email-final.html").write_text("<p>x</p>\n")
        (run / "run.json").write_text(json.dumps({"stages": {}}))
        page_dir = tmp / "runs" / "email-production" / "zz-brand" / "review-2026-10"
        html = build_review.variant_card("zz-l1", "none", None, "zz-brand", page_dir, root=tmp)
        self.assertIn('src="../zz-l1/email-final.html"', html)


class Ignored(unittest.TestCase):
    def test_generated_pages_are_ignored(self):
        ign = REPO / "runs" / "email-production" / ".gitignore"
        self.assertTrue(ign.is_file(), ign)
        lines = ign.read_text().splitlines()
        self.assertIn("*/drafts-*/drafts.html", lines)
        self.assertIn("*/review-*/review-*.html", lines)


if __name__ == "__main__":
    unittest.main()
