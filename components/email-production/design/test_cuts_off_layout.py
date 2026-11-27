#!/usr/bin/env python3
"""layout_file.cuts_off_layout: a cut picture that does not fit its section is from an older build (email_lead, 2026-11-16).

The case is brand_b-nov-25: editor's last build had 13 cuts and never reached the Drive; the Drive held 12 from an earlier
build with other heights and order, and the Go pulls the Drive's pictures before Klaviyo. No network.

    python3 design/test_cuts_off_layout.py
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout_file as LF  # noqa: E402

HTML = ('<table class="wrap"><tbody>'
        '<tr data-sec="0"><td><img src="assets/s01.jpg" width="600"></td></tr>'
        '<tr data-sec="1"><td background="assets/s02.jpg" style="background-image:url(assets/s02.jpg)">'
        '<a class="cta-btn">SEE IT</a></td></tr>'
        '<tr data-sec="2"><td>Live words, no picture</td></tr>'
        '<tr data-sec="3"><td><img src="assets/s03.jpg"><img src="assets/s04.jpg"></td></tr>'
        '<tr data-sec="4"><td><img src="assets/s05.jpg" width="600"></td></tr>'
        '</tbody></table>')
HEIGHTS = [90, 750, 120, 400, 970]          # section heights at 600 wide


class CutsOffLayout(unittest.TestCase):
    def setUp(self):
        self.run = Path(tempfile.mkdtemp(prefix="cuts-off-layout-")) / "brand_b-nov-25"
        k = self.run / "klaviyo"
        (k / "assets").mkdir(parents=True)
        (k / "email.html").write_text(HTML)
        top, secs = 0.0, []
        for i, h in enumerate(HEIGHTS):
            secs.append({"i": i, "top": top, "bottom": top + h})
            top += h
        (k / LF.NAME).write_text(json.dumps({"schema": LF.SCHEMA, "height": top, "sections": secs}))
        # this build's cuts, at 2x
        self.pic("s01.jpg", 90)
        self.pic("s02.jpg", 750)
        self.pic("s03.jpg", 50)              # two pictures in one section: not a single cut, never compared
        self.pic("s04.jpg", 60)
        self.pic("s05.jpg", 970)

    def tearDown(self):
        shutil.rmtree(self.run.parent, ignore_errors=True)

    def pic(self, name, h):
        Image.new("RGB", (1200, h * 2)).save(self.run / "klaviyo" / "assets" / name)

    def test_this_builds_pictures_fit(self):
        self.assertEqual(LF.cuts_off_layout(self.run), [])

    def test_an_older_builds_picture_is_named(self):
        self.pic("s05.jpg", 1380 // 2)       # nov-25: the Drive's s05 was 690 tall where this build's section is 970
        out = LF.cuts_off_layout(self.run)
        self.assertEqual(len(out), 1)
        self.assertIn("s05.jpg (section 5) is 690px tall, its section 970px", out[0])

    def test_a_background_hero_is_checked_too(self):
        self.pic("s02.jpg", 500)
        self.assertIn("s02.jpg (section 2)", LF.cuts_off_layout(self.run)[0])

    def test_a_missing_cut_is_named(self):
        (self.run / "klaviyo" / "assets" / "s01.jpg").unlink()
        self.assertEqual(LF.cuts_off_layout(self.run), ["s01.jpg (section 1) is not here"])

    def test_no_layout_file_checks_nothing(self):
        (self.run / "klaviyo" / LF.NAME).unlink()
        self.assertEqual(LF.cuts_off_layout(self.run), [])


if __name__ == "__main__":
    unittest.main()
