#!/usr/bin/env python3
"""QB-11 (the team view): statics.py --role video-editor reads the team's hand-offs from a fake Drive and his Done tells the team.
The graphic-designer default is unchanged (test_qb9_statics.py). Offline: no key, no network, no git.

    /usr/bin/python3 components/creative-queue/test_qb11_videos.py
"""
import contextlib
import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
import statics as S  # noqa: E402
from test_qb9_statics import FakeDrive  # noqa: E402

VIDEO_BRIEF = "<!-- prompt -->\n\n# Entanglement, 45 s with the pitch — song ad cut\n\n## Sources (all existing)\n"
KEY = "brand_a_widget-face-brush_brief-0274"


def video(back=None, complete=True):
    """A video-editor hand-off: no 00-approved/, and no returned/ at all unless `back` names files."""
    top = {"BRIEF.md": VIDEO_BRIEF.encode(), "RUN.md": b"r", "run.json": b"{}"}
    dirs = {"refs": {"files": {"a.mp4": b"a"}, "dirs": {}}}
    if back is not None:
        dirs["returned"] = {"files": {n: b"1" for n in back}, "dirs": {}}
    if not complete:
        top, dirs = {}, {}
    return {"files": top, "dirs": dirs}


def drive(**keys):
    return FakeDrive({"runs": {"dirs": {"handoffs": {"dirs": {"video-editor": {"dirs": {
        "brand-a": {"dirs": keys}}}}}}}})


class Base(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, str(self.out))


class Read(Base):
    def test_rows_titles_and_no_returned_folder_is_empty(self):
        d = drive(**{KEY: video(), "brand_a_widget-face-brush_brief-0075": video(("cut.mp4", "notes.txt")),
                     "brand_a_widget-face-brush_brief-0076": video(complete=False)})
        before = copy.deepcopy(d.tree)
        got = S.listing(d, self.out, role="video-editor")
        rows = {r["key"]: r for r in got["rows"]}
        self.assertEqual(sorted(rows), ["brand_a_widget-face-brush_brief-0075", KEY])
        self.assertEqual([g["key"] for g in got["incomplete"]], ["brand_a_widget-face-brush_brief-0076"])
        r = rows[KEY]
        self.assertEqual((r["title"], r["returned_files"], r["returned_work"], r["returned_id"], r["picture"]),
                         ("Entanglement, 45 s with the pitch — song ad cut", 0, 0, None, None))
        self.assertEqual((rows["brand_a_widget-face-brush_brief-0075"]["returned_files"],
                          rows["brand_a_widget-face-brush_brief-0075"]["returned_work"]), (2, 2), "any file counts for video")
        self.assertEqual(d.tree, before, "nothing is created on Drive: no returned/ folder appears")
        self.assertEqual(d.gets, ["runs/handoffs/video-editor/brand-a/%s/BRIEF.md" % k for k in sorted(rows)],
                         "only the briefs are fetched: no picture for video")

    def test_the_default_role_still_reads_graphic_designer(self):
        got = S.listing(drive(**{KEY: video()}), self.out)
        self.assertEqual(got["rows"], [])
        self.assertIn("graphic-designer", got["error"])

    def test_titles(self):
        self.assertEqual(S.title_of("# DOCUMENT ONE\n\n# BRIEF · BRAND-A · WIDGET · The warehouse\n", "k"), "The warehouse")
        self.assertEqual(S.title_of("# DOCUMENT ONE — THE BRIEF\n# The fight × pastor barber\n", "k"), "The fight × pastor barber")
        self.assertEqual(S.title_of("no heading here", "k"), "k")


class TheDone(Base):
    def run_done(self, d):
        filed, commits = [], []

        def file_request(**a):
            filed.append(a)
            return {"item": "rv-9", "route": "git", "path": str(self.out / "review.json")}
        said = S.done(d, KEY, "editor", self.out, file_request=file_request, now="2026-10-29T22:00:00Z",
                      commit_paths=lambda paths, msg, repo: commits.append((paths, msg)), role="video-editor")
        return said, filed, commits

    def test_refused_with_no_returned_folder_and_with_an_empty_one(self):
        for d in (drive(**{KEY: video()}), drive(**{KEY: video(())})):
            with self.assertRaises(S.Refused) as e:
                self.run_done(d)
            self.assertEqual(str(e.exception), "Not sent: returned/ is empty. Put your finished cut there first.")
            self.assertFalse((self.out / "brand-a" / KEY / "done.json").exists())

    def test_one_request_to_pm_on_the_video_lane(self):
        said, filed, commits = self.run_done(drive(**{KEY: video(("cut-45.mp4", "cut-45.srt"))}))
        self.assertEqual(said, "Sent to the team: Entanglement, 45 s with the pitch — song ad cut, 2 files back.")
        self.assertEqual(len(filed), 1)
        f = filed[0]
        self.assertEqual((f["reviewers"], f["lane"], f["type"], f["requested_by"]), (["pm"], "video-done", "video", "editor"))
        self.assertIn("finished the video for brief", f["notes"])
        rec = json.loads((self.out / "brand-a" / KEY / "done.json").read_text())
        self.assertEqual((rec["role"], rec["by"], rec["returned_files"]), ("video-editor", "the team", 2))
        self.assertEqual(len(commits), 1)
        self.assertTrue(commits[0][1].startswith("videos: %s done by the team, 2 files back (QB-11 (the team view))" % KEY))

    def test_cli_role_and_a_bad_role(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = S.main(["done", KEY, "--role", "video-editor", "--by", "editor", "--out", str(self.out)],
                          drive=drive(**{KEY: video()}))
        self.assertEqual((code, out.getvalue().strip()), (2, "Not sent: returned/ is empty. Put your finished cut there first."))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(S.main(["list", "--role", "copywriter"], drive=drive()), 1)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            S.main(["list", "--role", "video-editor", "--out", str(self.out)], drive=drive(**{KEY: video()}))
        self.assertEqual([r["key"] for r in json.loads(out.getvalue())["rows"]], [KEY])

    def test_no_drive_here_is_said_in_plain_words(self):
        """gdrive-creator exits (SystemExit) with no key or no package; the list still prints JSON and Done says why."""
        class Exits(object):
            def __init__(self):
                raise SystemExit("No GDRIVE_SA_KEY yet — put the service-account key in the environment")
        real = S.Drive
        S.Drive = Exits
        try:
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(S.main(["list", "--role", "video-editor", "--out", str(self.out)]), 0)
            got = json.loads(out.getvalue())
            self.assertEqual((got["rows"], got["error"]), ([], S.NO_DRIVE))
            self.assertIn("GDRIVE_SA_KEY", got["detail"])
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(S.main(["done", KEY, "--role", "video-editor", "--by", "editor", "--out", str(self.out)]), 1)
            self.assertEqual(out.getvalue().strip().splitlines()[-1], "Not sent: %s." % S.NO_DRIVE, "the kit shows the last line")
        finally:
            S.Drive = real

    def test_the_default_cache_folders(self):
        self.assertEqual(S.out_of("graphic-designer"), S.OUT)
        self.assertEqual(S.out_of("video-editor").relative_to(S.REPO).as_posix(), "runs/creative-queue/videos")


if __name__ == "__main__":
    unittest.main()
