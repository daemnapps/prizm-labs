#!/usr/bin/env python3
"""LD-79 (Drive ref resolver): stored references hand out and read back portably, through ONE lasting
cache — proven offline.

    python3 components/gdrive-creator/tests/test_ld79_refs.py

The fake Drive, the fake mount and the stood-in Google media classes are test_reach.py's own (its
Base): the REAL engine runs against them, so no Google package, no key and no network. HOME and
DRIVE_CACHE point into the test's temp folder and are restored. Stdlib only, 3.9.

  a  put: the api route returns {drive_id from put_ids' row, label, bytes}; the mount route returns
     drive_id None and the label; no route is a named NoDrive
  b  local({drive_id}): fetched once by id into cache_home()/<label after "Shared Assets/">; a SECOND
     local() after every module-level memo is cleared (a new process) is a hit with no Drive call; a
     size mismatch fetches again; a ref with no drive_id reads the label and lands in the same place
  c  local(str): repo-relative is the repo file; a missing one is FileNotFoundError; an absolute path
     that exists is itself, one that does not is Unportable naming it
  d  the cache: with DRIVE_CACHE unset, cache_home() and cache_root() are under
     $HOME/.upright/cache/drive and not under tempfile.gettempdir(); DRIVE_CACHE wins
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))                         # test_reach, beside this file
import test_reach as TR                            # noqa: E402  (appends the component to sys.path)

from gdrive_creator import reach as R, refs, shared as SH   # noqa: E402

FOLDER = "Shared Assets/runs/m/b/l"


class Base(TR.Base):
    def setUp(self):
        super().setUp()                            # os.environ is patched and restored there
        self.home = self.tmp / "home"
        self.home.mkdir()
        os.environ["HOME"] = str(self.home)
        os.environ.pop("DRIVE_CACHE", None)
        SH._SYNCED.clear()
        self.src = self.tmp / "work" / "x.png"
        self.src.parent.mkdir()
        self.src.write_bytes(b"picture-bytes")

    def gets(self):
        return self.svc.names().count("files.get_media")

    def new_process(self):
        """Every module-level memo cleared, as a fresh interpreter would have them."""
        R._READABLE.clear()
        SH._SYNCED.clear()


class TestPut(Base):
    def test_api_route_returns_the_rows_id_label_and_bytes(self):
        os.environ[R.KEY_ENV] = "x"
        ref = refs.put(self.src, FOLDER, svc=self.svc)
        fid = self.svc.path("runs", "m", "b", "l", "x.png")
        self.assertEqual(ref, {"drive_id": fid, "label": FOLDER + "/x.png", "bytes": 13})
        self.assertTrue(refs.is_ref(ref))
        self.no_harm()

    def test_mount_route_has_no_id_and_the_label(self):
        sa = self.a_mount()
        ref = refs.put(self.src, FOLDER, svc=TR.Exploding(), find_engine=TR.Exploding)
        self.assertEqual(ref, {"drive_id": None, "label": FOLDER + "/x.png", "bytes": 13})
        self.assertEqual((sa / "runs" / "m" / "b" / "l" / "x.png").read_bytes(), b"picture-bytes")

    def test_no_route_is_a_named_nodrive(self):
        with self.assertRaises(R.NoDrive) as c:
            refs.put(self.src, FOLDER, svc=self.svc)
        self.assertIn("x.png", str(c.exception))
        self.assertIn("GDRIVE_SA_KEY", str(c.exception))

    def test_a_label_off_the_drive_is_refused(self):
        with self.assertRaises(ValueError):
            refs.put(self.src, "runs/m/b/l", svc=self.svc)


class TestLocalRef(Base):
    def put(self):
        os.environ[R.KEY_ENV] = "x"
        return refs.put(self.src, FOLDER, svc=self.svc)

    def test_fetched_once_by_id_then_a_hit_in_a_new_process(self):
        ref = self.put()
        got = refs.local(ref, svc=self.svc)
        want = SH.cache_home() / "runs" / "m" / "b" / "l" / "x.png"
        self.assertEqual(got, want)
        self.assertEqual(got.read_bytes(), b"picture-bytes")
        self.assertEqual(self.gets(), 1)
        self.new_process()
        again = refs.local(ref, svc=TR.Exploding(), find_engine=TR.Exploding)
        self.assertEqual(again, want)
        self.assertEqual(self.gets(), 1)            # no Drive call at all
        self.no_harm()

    def test_a_size_mismatch_fetches_again(self):
        ref = self.put()
        got = refs.local(ref, svc=self.svc)
        got.write_bytes(b"short")                   # a truncated copy
        self.new_process()
        again = refs.local(ref, svc=self.svc)
        self.assertEqual(self.gets(), 2)
        self.assertEqual(again.read_bytes(), b"picture-bytes")

    def test_a_ref_with_no_id_reads_the_label_into_the_same_place(self):
        sa = self.a_mount()
        ref = refs.put(self.src, FOLDER, svc=TR.Exploding(), find_engine=TR.Exploding)
        got = refs.local(ref, svc=TR.Exploding(), find_engine=TR.Exploding)
        self.assertEqual(got, SH.cache_home() / "runs" / "m" / "b" / "l" / "x.png")
        self.assertEqual(got.read_bytes(), b"picture-bytes")
        self.assertTrue((sa / "runs" / "m" / "b" / "l" / "x.png").is_file())   # the mount file untouched


class TestLocalStr(Base):
    def test_repo_relative_is_the_repo_file(self):
        repo = self.tmp / "repo"
        (repo / "runs" / "a").mkdir(parents=True)
        (repo / "runs" / "a" / "p.png").write_bytes(b"p")
        self.assertTrue(refs.is_ref("runs/a/p.png"))
        self.assertEqual(refs.local("runs/a/p.png", repo=repo), repo / "runs" / "a" / "p.png")
        with self.assertRaises(FileNotFoundError) as c:
            refs.local("runs/a/missing.png", repo=repo)
        self.assertIn("runs/a/missing.png", str(c.exception))

    def test_repo_relative_finds_the_workspace_itself(self):
        got = refs.local("components/gdrive-creator/gdrive_creator/refs.py")
        self.assertEqual(got.resolve(), Path(refs.__file__).resolve())

    def test_an_absolute_path_that_is_gone_is_unportable(self):
        gone = "/private/tmp/definitely-gone-ld79.png"
        self.assertFalse(refs.is_ref(gone))
        with self.assertRaises(refs.Unportable) as c:
            refs.local(gone)
        self.assertIn(gone, str(c.exception))
        self.assertIn("rule 4", str(c.exception))
        self.assertEqual(c.exception.path, gone)

    def test_an_absolute_path_that_exists_is_read_in_place(self):
        self.assertEqual(refs.local(str(self.src)), self.src)


class TestCache(Base):
    def test_the_cache_lasts_under_home(self):
        base = self.home / ".upright" / "cache" / "drive"
        tmp = tempfile.gettempdir()
        for p in (SH.cache_home(), R.cache_root()):
            self.assertTrue(str(p).startswith(str(base)), p)
            self.assertFalse(str(p).startswith(tmp), p)
        self.assertEqual(SH.cache_home(), base / R.SHARED_DRIVE)
        self.assertEqual(R.cache_root(), base)

    def test_drive_cache_wins(self):
        os.environ["DRIVE_CACHE"] = str(self.tmp / "dc")
        self.assertEqual(SH.cache_home(), self.tmp / "dc" / R.SHARED_DRIVE)
        self.assertEqual(R.cache_root(), self.tmp / "dc")

    def test_is_ref(self):
        self.assertTrue(refs.is_ref({"drive_id": None, "label": FOLDER + "/x.png"}))
        self.assertFalse(refs.is_ref({"drive_id": "abc"}))
        self.assertFalse(refs.is_ref(""))
        self.assertFalse(refs.is_ref(None))


if __name__ == "__main__":
    unittest.main()
