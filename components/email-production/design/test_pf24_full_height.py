#!/usr/bin/env python3
"""PF-24 (full-height shots): the measure lays the email out at the width the picture is taken at, so the
whole-email picture is never cut short and the footer is always in it.

    /usr/bin/python3 tools/email-production/design/test_pf24_full_height.py

The cause, proven on brand-b oct-20 (2026-10-30): measure() ran Chrome WITH its scrollbar on a window shorter than
the email, so the page was 585 px wide; the email's own phone rule (@media (max-width:620px){.wrap{width:100%}})
then shrank every full-width picture by 15/600, and the email measured 3325 px where it draws 3398 at 600 wide.
shot() takes the picture with --hide-scrollbars at 600 wide and crops to the measured height, so the last ~74 px
(the footer) fell off. Not image loading: every <img> was complete when the measure fired.

  1  measure() asks Chrome for every layout flag shot() uses (--hide-scrollbars), so both lay out at one width
     (fake Chrome on CHROME_BIN, offline)
  2  a real email-shaped page taller than the window, whose last section sits below a full-width image with no
     width/height attributes and whose wrap obeys the phone rule: measure() gives its height at 600 wide and the
     whole-email picture ends on the footer (real headless Chrome; skipped by name when Chrome or PIL is absent)
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))      # design/ FIRST; never tools/email-production (its email.py shadows the stdlib's)
import layout_file as LF           # noqa: E402

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

REAL_CHROME = next((c for c in (os.environ.get("PF24_CHROME"), LF.APP, "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
                    if c and os.path.exists(c)), None)
FOOT = (255, 0, 255)
IMG_H = 3000                       # the picture, 600 x 3000: taller than measure()'s 3000 px window, as real emails are
FOOT_H = 60
PAGE = ('<!doctype html><html><head><style>@media (max-width:620px){.wrap{width:100%%!important}}</style></head>'
        '<body style="margin:0;padding:0;background:#FBFAF5">'
        '<table role="presentation" class="wrap" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px">'
        '<tr data-sec="0"><td><img src="assets/tall.png" alt="" style="display:block;width:100%%;max-width:600px;border:0"></td></tr>'
        '<tr data-sec="1"><td bgcolor="#FF00FF" style="height:%dpx;font-size:0">&nbsp;</td></tr>'
        '</table></body></html>') % FOOT_H
FAKE = r'''#!%(py)s
import sys
with open(%(count)r, "a") as f:
    f.write(" ".join(sys.argv[1:]) + "\n")
sys.stdout.write('<pre id="pos">{"H": 900, "o": {"0": [0, 900]}}</pre>')
'''


class TestMeasureWidth(unittest.TestCase):
    def test_1_measure_uses_every_layout_flag_the_shot_uses(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(os.path.realpath(t))
            (t / "email.html").write_text(PAGE)
            count, fake = t / "calls.txt", t / "fake-chrome"
            fake.write_text(FAKE % {"py": sys.executable, "count": str(count)})
            fake.chmod(0o755)
            with mock.patch.dict(os.environ, {"CHROME_BIN": str(fake)}):
                LF.measure(t / "email.html")
            argv = count.read_text().split()
        self.assertIn("--dump-dom", argv)
        self.assertIn("--hide-scrollbars", argv, "without it the page is 585 wide and the email's phone rule reflows it")


@unittest.skipUnless(REAL_CHROME and HAVE_PIL, "needs headless Chrome and PIL")
class TestRealEmail(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.run = Path(os.path.realpath(t.name)) / "zz-brand-nov-99"
        k = self.run / "klaviyo"
        (k / "assets").mkdir(parents=True)
        Image.new("RGB", (600, IMG_H), (40, 30, 20)).save(k / "assets" / "tall.png")
        (k / "email.html").write_text(PAGE)
        p = mock.patch.dict(os.environ, {"CHROME_BIN": REAL_CHROME})
        p.start()
        self.addCleanup(p.stop)

    def test_2_measured_at_600_and_the_picture_ends_on_the_footer(self):
        H, pos = LF.measure(self.run / "klaviyo" / "email.html")
        self.assertAlmostEqual(H, IMG_H + FOOT_H, delta=1, msg="measured at another width than 600")
        self.assertAlmostEqual(pos[1][1], IMG_H + FOOT_H, delta=1)
        f = LF.shot(self.run, H)
        with Image.open(f) as im:
            im = im.convert("RGB")
            self.assertEqual(im.size, (600, int(H)))
            for y in (int(H) - 2, int(H) - FOOT_H + 4):          # the footer's last and first rows are both in it
                r, g, b = im.getpixel((300, y))
                self.assertTrue(r > 200 and g < 60 and b > 200, "row %d is %s, not the footer" % (y, (r, g, b)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
