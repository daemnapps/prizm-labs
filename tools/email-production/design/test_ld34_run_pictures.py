#!/usr/bin/env python3
"""LD-34 (run pictures from Drive): a `run:` picture missing on disk is fetched
from the run's Drive mirror through the API, as `drive:` already is (LD-16
(email design by API)) — proven offline.

    /usr/bin/python3 tools/email-production/design/test_ld34_run_pictures.py

The Drive is a fake reach patched over look.reach(); no key, no network, no
Google package. Stdlib only, 3.9.

  a  a run: file on disk -> that path, and the fake is never asked
  b  a run: file missing -> the fake is asked for exactly
     "Shared Assets/runs/email-production/<brand>/<label>/media/x.png", and its
     path comes back
  c  the fake raising NoDrive (or SystemExit, no key) -> the local path, as before
"""
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))      # design/ FIRST; never tools/email-production (its email.py shadows the stdlib's)
import look as L                   # noqa: E402

BRAND = "zz-brand"
LABEL = "zz-brand-nov-99"


class NoDrive(Exception):
    pass


class Exploding(object):
    def __getattr__(self, name):
        raise AssertionError("the Drive was asked: %s" % name)


class TestRunPictures(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.tmp = Path(os.path.realpath(t.name))
        self.run = self.tmp / "runs" / "email-production" / BRAND / LABEL
        (self.run / "media").mkdir(parents=True)
        self.lk = L.Look(BRAND, {}, self.run)

    def reach_is(self, fake):
        p = mock.patch.object(L, "reach", lambda: fake)
        p.start()
        self.addCleanup(p.stop)

    def api(self, got, raises=None):
        asked = []

        def readable(label):
            asked.append(label)
            if raises is not None:
                raise raises
            return got
        self.reach_is(types.SimpleNamespace(readable=readable, NoDrive=NoDrive))
        return asked

    def test_a_file_on_disk_wins_and_the_drive_is_never_asked(self):
        f = self.run / "media" / "x.png"
        f.write_bytes(b"p")
        self.reach_is(Exploding())
        self.assertEqual(self.lk.path("run:media/x.png"), f)

    def test_a_missing_file_is_fetched_from_the_runs_drive_mirror(self):
        cached = self.tmp / "cache" / "x.png"
        asked = self.api(cached)
        self.assertEqual(self.lk.path("run:media/x.png"), cached)
        self.assertEqual(asked, ["Shared Assets/runs/email-production/%s/%s/media/x.png" % (BRAND, LABEL)])
        self.assertFalse((self.run / "media" / "x.png").exists())      # nothing written into the run

    def test_nodrive_or_no_key_gives_back_the_local_path(self):
        for exc in (NoDrive("not on the Drive"), SystemExit("no GDRIVE_SA_KEY")):
            asked = self.api(None, raises=exc)
            self.assertEqual(self.lk.path("run:media/x.png"), self.run / "media" / "x.png")
            self.assertEqual(len(asked), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
