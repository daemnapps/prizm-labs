#!/usr/bin/env python3
"""LD-11 (stills by Drive API): when the mount is absent or refuses a photos
folder, `all_stills` reads the same folder through the Drive API by file id —
O9 (Drive by fileId) — so the mini's launchd worker needs no Full Disk Access.

    python3 tests/test_stills_by_api.py

What a caller sees: mount absent → the stills come from the API, sorted by
name, cached under the temp dir, one stderr line saying so; the mount
refusing the first pool/folder → the API is asked for that same label; the
API failing → today's answer (no stills, the warn line); no GDRIVE_SA_KEY →
the API is never called; the mount, when it reads, wins and the API is never
called.

No key, no network, no Drive: gdrive-creator's own engine driven through its
`svc` seam with a fake Drive, a stand-in `googleapiclient.http`, the temp dir
and the mount both temp folders.
"""
import contextlib
import errno
import io
import os
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

LANE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LANE / "tools"))
sys.path.insert(0, str(LANE))

import paths as P                     # noqa: E402
import chain as C                     # noqa: E402
import swipe_home                     # noqa: E402  (put on the path by chain)

sys.path.insert(0, str(P.REPO / "components" / "gdrive-creator"))
from gdrive_creator import engine as E   # noqa: E402  imports nothing from Google

FOLDER = E.FOLDER_MIME
DEADLOCK = (errno.EDEADLK, "Resource deadlock avoided")
_REAL_IS_DIR = Path.is_dir
SWIPE = "zz-swipe"
BLOCK = {"file": "01_x.md"}


# ---- the Google client, stood in ----------------------------------------------
class MediaIoBaseDownload(object):
    """Writes the fake request's bytes in one chunk."""

    def __init__(self, fh, req):
        self.fh, self.req = fh, req

    def next_chunk(self, num_retries=0):
        self.fh.write(self.req.data)
        return None, True


def google_stub():
    gac = types.ModuleType("googleapiclient")
    gac.__path__ = []
    http = types.ModuleType("googleapiclient.http")
    http.MediaIoBaseDownload = MediaIoBaseDownload
    gac.http = http
    return {"googleapiclient": gac, "googleapiclient.http": http}


# ---- the fake Drive --------------------------------------------------------------
class Req(object):
    def __init__(self, result=None, data=b""):
        self.result, self.data = result, data

    def execute(self):
        return self.result


class Drive(object):
    """`Shared Assets` holding the given label → {file name: bytes} folders."""

    def __init__(self, folders, broken=False):
        self.broken = broken
        self.calls = []
        self.children = {}                  # parent id -> [{id, name, mimeType}]
        self.bytes = {}                     # file id -> bytes
        ids = {"Shared Assets": "d-sa"}
        n = [0]

        def nid():
            n[0] += 1
            return "id%d" % n[0]
        for label, files in folders.items():
            parts = label.split("/")
            for i in range(1, len(parts)):
                key = "/".join(parts[:i + 1])
                if key not in ids:
                    ids[key] = nid()
                    self.children.setdefault(ids["/".join(parts[:i])], []).append(
                        {"id": ids[key], "name": parts[i], "mimeType": FOLDER})
            for name, data in files.items():
                fid = nid()
                self.bytes[fid] = data
                self.children.setdefault(ids[label], []).append(
                    {"id": fid, "name": name, "mimeType": "image/jpeg"})

    def _call(self, what, kw):
        self.calls.append((what, kw))
        if self.broken:
            raise RuntimeError("HttpError 500 (fake)")

    def drives(self):
        d = self

        class Drives(object):
            def list(self, **kw):
                d._call("drives.list", kw)
                return Req({"drives": [{"id": "d-sa", "name": "Shared Assets"}]})
        return Drives()

    def files(self):
        d = self

        class Files(object):
            def list(self, **kw):
                d._call("files.list", kw)
                parent = re.search(r"'([^']+)' in parents", kw["q"]).group(1)
                rows = d.children.get(parent, [])
                if f"mimeType = '{FOLDER}'" in kw["q"]:
                    rows = [r for r in rows if r["mimeType"] == FOLDER]
                return Req({"files": list(rows)})

            def get_media(self, **kw):
                d._call("files.get_media", kw)
                return Req(data=d.bytes[kw["fileId"]])
        return Files()

    def downloads(self):
        return [kw["fileId"] for c, kw in self.calls if c == "files.get_media"]


def photos(pool, folder):
    return swipe_home.label(pool, SWIPE, folder, "01_x", "photos")


def _refuse_under(root, real):
    def method(self, *args, **kwargs):
        if str(self).startswith(str(root)):
            raise OSError(*DEADLOCK)
        return real(self, *args, **kwargs)
    return method


class Base(unittest.TestCase):

    def setUp(self):
        self._said, self._api = set(C._SAID), dict(C._API)
        C._SAID.clear()
        C._API.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.temp = Path(self.tmp.name) / "temp"
        self.temp.mkdir()
        self.mount = Path(self.tmp.name) / "mount"
        self.mount.mkdir()
        self.err = io.StringIO()
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        for p in (mock.patch.object(tempfile, "tempdir", str(self.temp)),
                  mock.patch.object(swipe_home, "MOUNT", return_value=self.mount),
                  mock.patch.dict(sys.modules, google_stub()),
                  contextlib.redirect_stderr(self.err)):
            self.stack.enter_context(p)

    def tearDown(self):
        C._SAID.clear()
        C._SAID.update(self._said)
        C._API.clear()
        C._API.update(self._api)

    def api(self, drive):
        """The process's one Drive client is this fake."""
        C._API.update(engine=E, svc=drive)

    def cache(self, pool, folder):
        return self.temp / "image-teardown-stills" / pool / SWIPE / folder / "01_x"

    def lines(self):
        return self.err.getvalue().splitlines()


class MountAbsent(Base):

    def test_stills_come_from_the_api_sorted_and_cached(self):
        drive = Drive({photos("organic", "posts"): {
            "02.jpg": b"two", "01.jpg": b"one", "notes.txt": b"x", "03.PNG": b"three"}})
        self.api(drive)
        with mock.patch.object(P, "DRIVE_MOUNTED", False):
            got = C.all_stills(BLOCK, SWIPE)
        where = self.cache("organic", "posts")
        self.assertEqual(got, [where / "01.jpg", where / "02.jpg", where / "03.PNG"])
        self.assertEqual([p.read_bytes() for p in got], [b"one", b"two", b"three"])
        self.assertEqual(sorted(p.name for p in where.iterdir()),
                         ["01.jpg", "02.jpg", "03.PNG"])   # no .txt, no .part left
        api_lines = [ln for ln in self.lines() if "Drive API" in ln]
        self.assertEqual(len(api_lines), 1, self.lines())
        self.assertIn(photos("organic", "posts"), api_lines[0])
        # every download asked the shared drive the right way
        for c, kw in drive.calls:
            if c == "files.get_media":
                self.assertTrue(kw["supportsAllDrives"])

    def test_a_still_already_cached_is_not_fetched_again(self):
        drive = Drive({photos("organic", "posts"): {"01.jpg": b"one", "02.jpg": b"two"}})
        self.api(drive)
        with mock.patch.object(P, "DRIVE_MOUNTED", False):
            first = C.all_stills(BLOCK, SWIPE)
            self.assertEqual(len(drive.downloads()), 2)
            second = C.all_stills(BLOCK, SWIPE)
        self.assertEqual(first, second)
        self.assertEqual(len(drive.downloads()), 2)

    def test_the_first_folder_in_todays_order_with_stills_wins(self):
        drive = Drive({photos("paid", "angles"): {"a.jpg": b"paid"},
                       photos("organic", "posts"): {"b.jpg": b"organic"}})
        self.api(drive)
        with mock.patch.object(P, "DRIVE_MOUNTED", False):
            got = C.all_stills(BLOCK, SWIPE)
        self.assertEqual(got, [self.cache("paid", "angles") / "a.jpg"])

    def test_api_raising_is_todays_empty_answer(self):
        self.api(Drive({photos("organic", "posts"): {"01.jpg": b"one"}}, broken=True))
        with mock.patch.object(P, "DRIVE_MOUNTED", False):
            got = C.all_stills(BLOCK, SWIPE)
        self.assertEqual(got, [])
        self.assertEqual(self.lines(), [P.NO_MOUNT_NOTE])


class MountRefuses(Base):

    def test_a_refused_first_folder_is_asked_of_the_api_by_its_label(self):
        drive = Drive({photos("paid", "blocks"): {"b.jpg": b"bee", "a.jpg": b"ay"}})
        self.api(drive)
        asked = []
        real = E.folder_by_path

        def spy(label, svc=None):
            asked.append(label)
            return real(label, svc=svc)
        bad = self.mount / "swipe/paid" / SWIPE / "blocks"
        with mock.patch.object(P, "DRIVE_MOUNTED", True), \
                mock.patch.object(Path, "is_dir", _refuse_under(bad, _REAL_IS_DIR)), \
                mock.patch.object(E, "folder_by_path", spy):
            got = C.all_stills(BLOCK, SWIPE)
        self.assertEqual(asked, [photos("paid", "blocks")])
        where = self.cache("paid", "blocks")
        self.assertEqual(got, [where / "a.jpg", where / "b.jpg"])
        self.assertEqual([p.read_bytes() for p in got], [b"ay", b"bee"])
        self.assertEqual(len(self.lines()), 1, self.lines())
        self.assertIn("Drive API", self.lines()[0])
        self.assertNotIn("warn", self.lines()[0])

    def test_api_raising_keeps_the_warn_line_and_no_stills(self):
        drive = Drive({photos("paid", "blocks"): {"a.jpg": b"ay"}}, broken=True)
        self.api(drive)
        with mock.patch.object(P, "DRIVE_MOUNTED", True), \
                mock.patch.object(Path, "is_dir", _refuse_under(self.mount, _REAL_IS_DIR)):
            got = C.all_stills(BLOCK, SWIPE)
        self.assertEqual(got, [])
        self.assertTrue(drive.calls)                      # the API was tried
        lines = self.lines()
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("warn  stills unreadable in " + photos("paid", "blocks"), lines[0])
        self.assertIn("(and 5 more)", lines[0])
        self.assertIn("EDEADLK (Resource deadlock avoided)", lines[0])
        self.assertEqual(list(self.temp.rglob("*.jpg")), [])   # nothing cached


class NoKey(Base):

    def test_no_key_never_calls_the_api(self):
        env = {k: v for k, v in os.environ.items() if k != "GDRIVE_SA_KEY"}
        env["KEYS_NO_FALLBACK"] = "1"               # LD-47 step 1.6: this machine's real key file never counts in a test
        built = mock.Mock(side_effect=AssertionError("service() must not be built"))
        walked = mock.Mock(side_effect=AssertionError("folder_by_path must not be called"))
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(E, "_KEY_LOOKUP", None), \
                mock.patch.object(E, "service", built), \
                mock.patch.object(E, "folder_by_path", walked), \
                mock.patch.object(P, "DRIVE_MOUNTED", False):
            got = C.all_stills(BLOCK, SWIPE)
            refused = C.all_stills(BLOCK, SWIPE)    # and the answer is remembered
        self.assertEqual(got, [])
        self.assertEqual(refused, [])
        built.assert_not_called()
        walked.assert_not_called()
        self.assertEqual(C._API.get("svc"), None)
        self.assertEqual(self.lines(), [P.NO_MOUNT_NOTE])


class MountWins(Base):

    def test_a_readable_mount_is_read_and_the_api_is_never_called(self):
        d = self.mount / "swipe/organic" / SWIPE / "posts/01_x/photos"
        d.mkdir(parents=True)
        for n in ("b.jpg", "a.png", "c.txt"):
            (d / n).write_bytes(b"m")
        drive = Drive({photos("paid", "blocks"): {"x.jpg": b"api"}})
        self.api(drive)
        with mock.patch.object(P, "DRIVE_MOUNTED", True):
            got = C.all_stills(BLOCK, SWIPE)
        self.assertEqual(got, [d / "a.png", d / "b.jpg"])
        self.assertEqual(drive.calls, [])
        self.assertEqual(self.lines(), [])


if __name__ == "__main__":
    unittest.main()
