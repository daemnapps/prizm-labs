#!/usr/bin/env python3
"""place_own (the team, 2026-10-23, the team Drive flow): a picture the team brings from a link (a Higgsfield result) keeps where
it came from, and every place writes one model-outcome record, the same as "use my newest".

    python3 tools/email-production/adapter/test_place_own.py     (from the repo root, as test_use_my_newest.py)

Runs on test_use_my_newest's fixture run and fakes (no network, no key, every record under a temp root).

  1  a Higgsfield link keeps made_from {link, id} on the picture, beside made_with
  2  a file from this Mac keeps no made_from; a Drive link is not a link here
  3  exactly one model-outcome record per place: door own, its model the tool, a real photo when none is named
"""
import contextlib
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import own_picture as OP                      # noqa: E402
from test_use_my_newest import Base, JPEG     # noqa: E402

LINK = "https://cdn.example.test/u/abc/result.png?sig=1"


class TestPlaceOwn(Base):
    def setUp(self):
        super().setUp()
        self.read = []
        real = OP.fetch

        def fetch(src, tmp):
            if OP.is_link(src):
                self.read.append(src)
                f = Path(tmp) / "link.png"
                f.write_bytes(JPEG + b"link")
                return f
            return real(src, tmp)
        OP.fetch = fetch
        self.addCleanup(setattr, OP, "fetch", real)

    def place(self, src, made_with="Higgsfield", source_id=None):
        with contextlib.redirect_stdout(self.out):
            return OP.place_own(self.run, "P1", src, "a jar on a sink in morning light", "the team", made_with, "own", None,
                                True, source_id, outcome_root=self.tmp / "plane")

    def test_1_a_higgsfield_link_keeps_where_it_came_from(self):
        r = self.place(LINK, source_id="gen-123")
        pic = self.picture()
        self.assertEqual(pic["made_from"], {"link": LINK, "id": "gen-123"})
        self.assertEqual(pic["made_with"], "Higgsfield")
        self.assertEqual(self.read, [LINK])
        self.assertTrue(r["outcome"])

    def test_2_a_local_file_keeps_no_made_from(self):
        f = self.tmp / "mine.jpg"
        f.write_bytes(JPEG + b"mine")
        self.place(str(f), made_with="Photoshop")
        self.assertNotIn("made_from", self.picture())
        self.assertFalse(OP.is_link("https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz012345/view"))

    def test_3_one_outcome_record_per_place(self):
        self.place(LINK, source_id="gen-1")
        f = self.tmp / "photo.jpg"
        f.write_bytes(JPEG + b"cam")
        self.place(str(f), made_with="")
        recs = self.outcomes()
        self.assertEqual(len(recs), 2)
        by_model = {x["verdict"]["model"]: x["verdict"] for x in recs}     # same-second records: file order is not
        self.assertEqual(sorted(by_model), ["Higgsfield", "real photo"])   # the order they were written in
        self.assertEqual({v["door"] for v in by_model.values()}, {"own"})
        self.assertEqual(by_model["Higgsfield"]["purpose"], "email-story")


if __name__ == "__main__":
    unittest.main()
