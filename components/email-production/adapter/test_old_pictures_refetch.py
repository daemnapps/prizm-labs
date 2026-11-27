#!/usr/bin/env python3
"""A picture that is here but from an older build is fetched again, not shown as current (email_lead, 2026-11-18).

brand_a-nov-34: the page server pulled editor's commit before her new pictures reached the Drive and kept the older
build's hero; nothing looked again, because only a MISSING picture sent the page back to the Drive. No network.

    python3 adapter/test_old_pictures_refetch.py
"""
import json
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "design"))
import sync  # noqa: E402
import layout_file as LF  # noqa: E402
from PIL import Image  # noqa: E402

PAGE = '<table><tr data-sec="0"><td><img src="assets/s01.jpg"></td></tr><tr data-sec="1"><td><img src="assets/s02.jpg"></td></tr></table>'


def run_with(tmp, s02_height):
    run = Path(tmp) / "brand" / "brand-nov-34"
    k = run / "klaviyo"
    (k / "assets").mkdir(parents=True)
    (k / "email.html").write_text(PAGE)
    (k / "layout.json").write_text(json.dumps({"schema": LF.SCHEMA, "height": 900, "sections": [
        {"i": 0, "top": 0, "bottom": 400}, {"i": 1, "top": 400, "bottom": 900}]}))
    Image.new("RGB", (1200, 800)).save(k / "assets" / "s01.jpg")
    Image.new("RGB", (1200, s02_height)).save(k / "assets" / "s02.jpg")
    return run


class OldPictures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="old-pics-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_pictures_that_fit_are_left_alone(self):
        self.assertEqual(sync._cuts_old(run_with(self.tmp, 1000)), [])

    def test_an_older_builds_picture_is_named(self):
        self.assertEqual(sync._cuts_old(run_with(self.tmp, 834)), ["s02.jpg"])

    def test_the_maker_fetches_old_pictures_and_shoots_once_they_fit(self):
        run = run_with(self.tmp, 834)
        shot = []

        def pull(brand, r):          # the Drive now holds the new build
            Image.new("RGB", (1200, 1000)).save(r / "klaviyo" / "assets" / "s02.jpg")
            return {"got": ["s02.jpg"], "missing": [], "error": None}
        said = sync.make_pictures([run], pull=pull, shoot=shot.append, received=lambda runs: None)
        self.assertEqual(said[str(run)], "shot")
        self.assertEqual(sync._cuts_old(run), [])
        self.assertFalse(sync._drive_mark(run).exists())

    def test_a_drive_holding_the_old_build_is_not_asked_again_at_every_page_load(self):
        run = run_with(self.tmp, 834)
        pulls = []

        def pull(brand, r):          # the Drive still has the older pictures
            pulls.append(r)
            return {"got": ["s02.jpg"], "missing": [], "error": None}
        said = sync.make_pictures([run], pull=pull, shoot=lambda r: None, received=lambda runs: None)
        self.assertIn("older build", said[str(run)])
        self.assertEqual(len(pulls), 1)
        self.assertEqual(sync._cuts_old(run), [])                                   # within the window: shown as is
        self.assertEqual(sync._cuts_old(run, now=time.time() + sync.DRIVE_RECHECK + 1), ["s02.jpg"])   # asked again later

    def test_a_new_layout_is_asked_about_at_once(self):
        run = run_with(self.tmp, 834)
        sync.make_pictures([run], pull=lambda b, r: {"got": [], "missing": [], "error": None},
                           shoot=lambda r: None, received=lambda runs: None)
        lay = run / "klaviyo" / "layout.json"
        lay.write_text(lay.read_text().replace("900", "901"))
        self.assertEqual(sync._cuts_old(run), ["s02.jpg"])


if __name__ == "__main__":
    unittest.main()
