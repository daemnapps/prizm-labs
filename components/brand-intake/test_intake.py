#!/usr/bin/env python3
"""Tests for brand intake on a synthetic Drive tree and a synthetic site."""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intake  # noqa: E402

F = intake.FOLDER_MIME
TREE = {
    "root": [{"id": "d1", "name": "Brand Stuff", "mimeType": F}, {"id": "d2", "name": "Raw footage", "mimeType": F},
             {"id": "f1", "name": "IMG_5476.MOV", "mimeType": "video/quicktime"}],
    "d1": [{"id": "f2", "name": "Logo final.png", "mimeType": "image/png"},
           {"id": "f3", "name": "Brand Guidelines 2024.pdf", "mimeType": "application/pdf"},
           {"id": "f4", "name": "About us - founder story", "mimeType": "application/vnd.google-apps.document"},
           {"id": "f5", "name": "Post purchase survey (Responses)", "mimeType": "application/vnd.google-apps.spreadsheet"},
           {"id": "f6", "name": "Downloads list", "mimeType": "text/plain"},
           {"id": "d3", "name": "Winning ads", "mimeType": F}],
    "d2": [{"id": "f7", "name": "clip1.mp4", "mimeType": "video/mp4"}],
    "d3": [{"id": "f8", "name": "hook test v2.mp4", "mimeType": "video/mp4"}],
}
HOME = """<html><head><title>Acme Skin</title><script src="https://cdn.shopify.com/x.js"></script></head>
<body><a href="/products/the-cream">Cream</a><script src="https://cdn.judge.me/widget.js"></script>
<a href="https://www.trustpilot.com/review/acme.example">Trustpilot</a>
<a href="https://www.instagram.com/acme">ig</a><img src="https://www.facebook.com/tr?id=1"></body></html>"""


class IntakeTest(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        (self.root / "brands" / "acme").mkdir(parents=True)
        (self.root / "brands" / "acme" / "story.md").write_text("# <brand> story\n<placeholder>\n")

    def run_i(self, *argv, **kw):
        out = io.StringIO()
        code = intake.main(list(argv), out=out, root=self.root, **kw)
        return code, out.getvalue()

    def test_word_matching_is_whole_words(self):
        self.assertEqual(intake.matches("Downloads list", "text/plain"), [])
        slots = [s for s, _ in intake.matches("Brand Stuff/Winning ads/hook test v2.mp4", "video/mp4")]
        self.assertEqual(slots[0], "past-ads")

    def test_drive_index_walks_every_folder_and_places_files(self):
        code, out = self.run_i("drive", "--brand", "acme", "--folder", "https://drive.google.com/drive/folders/root0000000",
                               children=lambda fid: TREE.get("root" if fid == "root0000000" else fid, []))
        self.assertEqual(code, 0, out)
        self.assertIn("Indexed 8 files in 3 folders", out)
        idx = json.loads((self.root / "runs/brand-intake/acme/drive-index.json").read_text())
        by = {f["path"]: f for f in idx["files"]}
        self.assertIn("look", by["Brand Stuff/Logo final.png"]["slots"])
        self.assertIn("surveys-support", by["Brand Stuff/Post purchase survey (Responses)"]["slots"])
        self.assertIn("brand-assets", by["IMG_5476.MOV"]["slots"])
        self.assertEqual(by["Brand Stuff/Downloads list"]["slots"], [])

    def test_site_finds_platform_reviews_and_social(self):
        pages = {"https://acme.example": HOME, "https://acme.example/products/the-cream": "<p>The cream</p>"}

        def get(url):
            if url in pages:
                return pages[url]
            raise OSError("404")
        data = intake.index_site("https://acme.example", get=get)
        self.assertEqual(data["platform"], "shopify")
        self.assertEqual(data["review_apps"], ["judgeme", "trustpilot"])
        self.assertEqual(data["review_pages"], ["https://www.trustpilot.com/review/acme.example"])
        self.assertEqual(data["social"], ["https://www.instagram.com/acme"])
        self.assertEqual(data["products"][0]["url"], "https://acme.example/products/the-cream")

    def test_plan_marks_blanks_and_sources(self):
        self.run_i("drive", "--brand", "acme", "--folder", "root0000000", children=lambda fid: TREE.get("root" if fid == "root0000000" else fid, []))
        code, out = self.run_i("plan", "--brand", "acme")
        rows = {r["slot"]: r for r in json.loads((self.root / "runs/brand-intake/acme/plan.json").read_text())["slots"]}
        self.assertEqual(rows["story"]["state"], "can fill")
        self.assertEqual(rows["story"]["files"][0]["path"], "Brand Stuff/About us - founder story")
        self.assertEqual(rows["offer"]["state"], "ask")
        (self.root / "brands/acme/story.md").write_text("Acme was started in a kitchen.\n")
        self.run_i("plan", "--brand", "acme")
        rows = {r["slot"]: r for r in json.loads((self.root / "runs/brand-intake/acme/plan.json").read_text())["slots"]}
        self.assertEqual(rows["story"]["state"], "filled")

    def test_bad_input(self):
        self.assertEqual(self.run_i("drive", "--brand", "acme", "--folder", "nope")[0], 2)
        self.assertEqual(self.run_i("site", "--brand", "acme", "--url", "acme.example")[0], 2)
        self.assertEqual(self.run_i("plan", "--brand", "../x")[0], 2)


if __name__ == "__main__":
    unittest.main()
