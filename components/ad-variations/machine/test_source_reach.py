#!/usr/bin/env python3
"""Stage 0 finds its source video by the run.json path, else this machine's Drive mount, else the Drive
file id; proven_to_format reads Shared Assets from the one shared mount helper (O9 (Drive by fileId)).

    /usr/bin/python3 components/ad-variations/machine/test_source_reach.py

No key, no network, ffmpeg never invoked. Every test runs under a fake HOME.
"""
import contextlib
import importlib
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "components" / "brandpath"))
import drive_index  # noqa: E402

sys.path.insert(0, str(HERE))
import measure  # noqa: E402
with contextlib.redirect_stderr(io.StringIO()):
    import proven_to_format as PTF  # noqa: E402

REAL_HOME = pathlib.Path.home()
FID = "AbC_123-xyz0"
MOUNT = pathlib.Path("Library", "CloudStorage", "GoogleDrive-tester@company.com",
                     "Shared drives", "Shared Assets")


class SourceReach(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name) / "home"
        self.home.mkdir()
        self.work = pathlib.Path(self.tmp.name) / "work"
        self.work.mkdir()
        for p in (mock.patch.object(pathlib.Path, "home", return_value=self.home),
                  mock.patch.dict(os.environ)):
            p.start()
            self.addCleanup(p.stop)
        os.environ.pop("GDRIVE_SA_KEY", None)
        # LD-26 (mount switch): a worker-spawned run of this suite inherits
        # DRIVE_MOUNT=off; these tests are a person's session, so drop it.
        os.environ.pop("DRIVE_MOUNT", None)
        self.addCleanup(self.tmp.cleanup)

    def mount_file(self, rel):
        f = self.home / MOUNT / rel
        f.parent.mkdir(parents=True)
        f.write_bytes(b"video")
        return f

    def never(self, *a, **k):
        self.fail("fetch called: " + repr(a))

    def test_file_id_from_drive_links(self):
        self.assertEqual(measure.file_id("https://drive.google.com/file/d/" + FID + "/view"), FID)
        self.assertEqual(measure.file_id("https://drive.google.com/open?id=" + FID), FID)
        self.assertIsNone(measure.file_id(None))
        self.assertIsNone(measure.file_id("source.mp4"))

    def test_run_json_path_wins(self):
        src = self.work / "here.mp4"
        src.write_bytes(b"video")
        tj = {"video": str(src), "video_url": "https://drive.google.com/file/d/" + FID + "/view"}
        self.assertEqual(measure.locate(tj, self.work, fetch=self.never), (src, "the path in run.json"))

    def test_mount_rerooted(self):
        want = self.mount_file("zz/v.mp4")
        tj = {"video": "~/Library/CloudStorage/GoogleDrive-someone@example.com/"
                       "Shared drives/Shared Assets/zz/v.mp4"}
        self.assertEqual(measure.locate(tj, self.work, fetch=self.never), (want, "this machine's Drive mount"))

    def test_drive_id_fetched_into_work(self):
        calls = []

        def fetch(fid, dest):
            calls.append((fid, dest))
            pathlib.Path(dest).write_bytes(b"video")
            return str(dest)

        tj = {"video": "/nowhere/source.mp4", "video_url": "https://drive.google.com/file/d/" + FID + "/view"}
        dest = self.work / "source.mp4"
        self.assertEqual(measure.locate(tj, self.work, fetch=fetch), (dest, "Drive by file id " + FID))
        self.assertEqual(calls, [(FID, dest)])
        self.assertTrue(dest.is_file())

    def test_no_key_no_mount_says_why(self):
        tj = {"video": "/nowhere/source.mp4", "video_url": "https://drive.google.com/file/d/" + FID + "/view"}
        path, why = measure.locate(tj, self.work)
        self.assertIsNone(path)
        self.assertIn("GDRIVE_SA_KEY", why)
        path, why = measure.locate({"video": "/nowhere/source.mp4"}, self.work)
        self.assertIsNone(path)
        self.assertIn("no Drive file id", why)

    def test_run_records_the_reason_without_ffmpeg_work(self):
        run_dir, td = self.work / "run", self.work / "teardown"
        run_dir.mkdir()
        td.mkdir()
        (td / "run.json").write_text(json.dumps({"video": "/nowhere/source.mp4"}))
        with mock.patch.object(measure.shutil, "which", return_value="/usr/bin/true"), \
                mock.patch.object(measure.subprocess, "run", side_effect=AssertionError("subprocess called")):
            measure.run(run_dir, td, echo=lambda *a: None)
        m = json.loads((run_dir / "measure.json").read_text())
        self.assertTrue(m["skipped"].startswith(
            "the source video named in the teardown's run.json is not reachable from this machine — "), m["skipped"])
        self.assertNotIn("video_from", m)

    def tearDown(self):
        if self._testMethodName == "test_proven_to_format_reads_the_shared_mount":
            with mock.patch.object(pathlib.Path, "home", return_value=REAL_HOME):
                self.reload_quietly()

    def test_proven_to_format_reads_the_shared_mount(self):
        self.mount_file("zz/v.mp4")
        self.reload_quietly()
        self.assertEqual(PTF.SA, drive_index.mount())
        self.assertTrue(PTF.SA.is_dir())

        empty = pathlib.Path(self.tmp.name) / "empty-home"
        empty.mkdir()
        err = io.StringIO()
        with mock.patch.object(pathlib.Path, "home", return_value=empty), contextlib.redirect_stderr(err):
            importlib.reload(PTF)
        self.assertFalse(PTF.SA.exists())
        self.assertIn("Shared Assets", err.getvalue())

        for f in ("proven_to_format.py", "measure.py"):
            text = (HERE / f).read_text()
            self.assertNotIn("CloudStorage", text, f)
            self.assertNotIn("GoogleDrive-", text, f)

    @staticmethod
    def reload_quietly():
        with contextlib.redirect_stderr(io.StringIO()):
            importlib.reload(PTF)


if __name__ == "__main__":
    unittest.main()
