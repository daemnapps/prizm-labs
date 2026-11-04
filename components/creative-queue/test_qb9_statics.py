#!/usr/bin/env python3
"""QB-9 (the team statics): statics.py reads the graphic-designer hand-offs from a fake Drive and the team's Done tells the team.
Offline: no key, no network, no git; file_request and the commit are stand-ins that record what they were handed.

    /usr/bin/python3 components/creative-queue/test_qb9_statics.py
"""
import contextlib
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

BRIEF = "<!-- prompt -->\n\n# DOCUMENT ONE\n\n# BRIEF · BRAND-A · NOVA™ Pro Vibrating Face Brush · The warehouse full of NOVA\n"


class FakeDrive(object):
    """A tree of folders {name: {"files": {name: bytes}, "dirs": {...}}}; ids are the path. get() counts its calls."""

    def __init__(self, tree):
        self.tree, self.gets = tree, []

    def _node(self, fid):
        n = {"dirs": self.tree}
        for part in fid.split("/") if fid else []:
            n = n["dirs"].get(part)
            if n is None:
                return None
        return n

    def folder(self, parts):
        fid = "/".join(parts)
        return fid if self._node(fid) is not None else None

    def subfolders(self, fid):
        return [{"id": fid + "/" + k, "name": k} for k in sorted(self._node(fid)["dirs"])]

    def files(self, fid):
        return [{"id": fid + "/" + k, "name": k} for k in sorted(self._node(fid).get("files") or {})]

    def get(self, file_id, dest):
        self.gets.append(file_id)
        folder, _, name = file_id.rpartition("/")
        Path(dest).write_bytes(self._node(folder)["files"][name])
        return str(dest)


def handoff(files_back=(), approved="brand_a_nova-face-brush_brief-0296-approved.png", complete=True):
    top = {"BRIEF.md": BRIEF.encode(), "RUN.md": b"r", "run.json": b"{}", "HANDOFF.md": b"h"}
    dirs = {"00-approved": {"files": {approved: b"PNG", approved.replace("-approved", "-approved-clean"): b"CLEAN",
                                      "swipe.jpg": b"S"}, "dirs": {}},
            "refs": {"files": {"a.png": b"a"}, "dirs": {}}, "v1": {"files": {"x.png": b"x"}, "dirs": {}}}
    if files_back:
        dirs["returned"] = {"files": {n: b"1" for n in files_back}, "dirs": {}}
    if not complete:
        top = {"HANDOFF.md": b"h"}
        del dirs["refs"]
    return {"files": top, "dirs": dirs}


def drive(**brands):
    return FakeDrive({"runs": {"dirs": {"handoffs": {"dirs": {"graphic-designer": {"dirs": {
        b: {"dirs": keys} for b, keys in brands.items()}}}}}}})


class Base(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, str(self.out))


class Listing(Base):
    def test_complete_rows_and_incomplete_left_out(self):
        d = drive(brand_a={"brand_a_nova-face-brush_brief-0296": handoff(),
                          "brand_a_nova-face-brush_brief-0232": handoff(("a.png", "b.jpg", "notes.txt"),
                                                                       approved="brand_a_nova_brief-0232-approved.png")},
                  brand_b={"brand_b_brilliance-face-scrub_brief-0325": handoff(complete=False)})
        got = S.listing(d, self.out)
        self.assertIsNone(got["error"])
        rows = {r["key"]: r for r in got["rows"]}
        self.assertEqual(sorted(rows), ["brand_a_nova-face-brush_brief-0232", "brand_a_nova-face-brush_brief-0296"])
        self.assertEqual(got["incomplete"], [{"key": "brand_b_brilliance-face-scrub_brief-0325", "brand": "brand-b",
                                              "missing": ["BRIEF.md", "RUN.md", "run.json", "refs/"]}])
        r = rows["brand_a_nova-face-brush_brief-0296"]
        self.assertEqual((r["brand"], r["title"], r["returned_files"], r["returned_pictures"], r["done"]),
                         ("brand-a", "The warehouse full of NOVA", 0, 0, None))
        self.assertEqual(r["drive_url"], S.DRIVE_FOLDER % r["drive_id"])
        back = rows["brand_a_nova-face-brush_brief-0232"]
        self.assertEqual((back["returned_files"], back["returned_pictures"]), (3, 2))
        pic = self.out / "brand-a" / "brand_a_nova-face-brush_brief-0232" / "approved.png"
        self.assertEqual(pic.read_bytes(), b"PNG", "the -approved picture, never -approved-clean, by suffix")

    def test_the_brief_and_picture_are_fetched_once(self):
        d = drive(brand_a={"brand_a_nova-face-brush_brief-0296": handoff()})
        S.listing(d, self.out)
        n = len(d.gets)
        self.assertEqual(n, 2)
        S.listing(d, self.out)
        self.assertEqual(len(d.gets), n, "the same Drive ids inside a day: nothing fetched again")
        S.listing(d, self.out, clock=lambda: 9e12)
        self.assertEqual(len(d.gets), n + 2, "after a day both are fetched again")

    def test_no_root_on_drive_is_said(self):
        got = S.listing(FakeDrive({}), self.out)
        self.assertEqual(got["rows"], [])
        self.assertIn("graphic-designer", got["error"])

    def test_no_drive_here_still_prints_json(self):
        buf = io.StringIO()

        class NoDrive(object):
            def __init__(self):
                raise RuntimeError("no GDRIVE_SA_KEY")
        real = S.Drive
        S.Drive = NoDrive
        try:
            with contextlib.redirect_stdout(buf):
                code = S.main(["list", "--out", str(self.out)])
        finally:
            S.Drive = real
        self.assertEqual(code, 0)
        got = json.loads(buf.getvalue())
        self.assertEqual(got["rows"], [])
        self.assertEqual(got["error"], S.NO_DRIVE, "the page gets plain words (QC 2026-10-29)")
        self.assertIn("no GDRIVE_SA_KEY", got["detail"], "the reason stays, for whoever debugs it")


class TheDone(Base):
    KEY = "brand_a_nova-face-brush_brief-0296"

    def run_done(self, d, **kw):
        filed, commits = [], []

        def file_request(**a):
            filed.append(a)
            return {"item": "rv-1", "route": "git", "path": str(self.out / "review.json")}
        said = S.done(d, self.KEY, "designer", self.out, file_request=file_request,
                      commit_paths=lambda paths, msg, repo: commits.append((paths, msg)), now="2026-10-29T21:00:00Z", **kw)
        return said, filed, commits

    def test_refused_with_nothing_back_and_nothing_written(self):
        d = drive(brand_a={self.KEY: handoff()})
        with self.assertRaises(S.Refused) as e:
            self.run_done(d)
        self.assertIn("returned/ has no pictures", str(e.exception))
        self.assertFalse((self.out / "brand-a" / self.KEY / "done.json").exists())

    def test_refused_when_only_non_pictures_came_back(self):
        d = drive(brand_a={self.KEY: handoff(("notes.txt",))})
        with self.assertRaises(S.Refused):
            self.run_done(d)

    def test_refused_when_incomplete_or_missing(self):
        with self.assertRaises(S.Refused) as e:
            self.run_done(drive(brand_a={self.KEY: handoff(("a.png",), complete=False)}))
        self.assertIn("incomplete", str(e.exception))
        with self.assertRaises(S.Refused) as e:
            self.run_done(drive(brand_a={}))
        self.assertIn("no hand-off", str(e.exception))

    def test_one_request_to_pm_only_then_done_json_and_one_commit(self):
        d = drive(brand_a={self.KEY: handoff(("a.png", "b.png", "c.txt"))})
        said, filed, commits = self.run_done(d)
        self.assertEqual(said, "Sent to the team: The warehouse full of NOVA, 3 files back.")
        self.assertEqual(len(filed), 1)
        f = filed[0]
        self.assertEqual((f["reviewers"], f["lane"], f["requested_by"], f["commit"]), (["pm"], "static-done", "designer", False))
        self.assertEqual(f["asset"]["warehouse"], "drive")
        self.assertIn(self.KEY, f["asset"]["title"])
        self.assertIn("3 files", f["asset"]["title"])
        rec = json.loads((self.out / "brand-a" / self.KEY / "done.json").read_text())
        self.assertEqual((rec["by"], rec["returned_files"], rec["returned_pictures"], rec["review"]["item"]), ("the team", 3, 2, "rv-1"))
        self.assertEqual(len(commits), 1)
        self.assertEqual([Path(p).name for p in commits[0][0]], ["done.json", "review.json"])
        listed = {r["key"]: r for r in S.listing(d, self.out)["rows"]}
        self.assertEqual(listed[self.KEY]["done"]["by"], "the team", "the list knows it was sent")

    def test_a_second_done_files_nothing(self):
        d = drive(brand_a={self.KEY: handoff(("a.png",))})
        self.run_done(d)
        said, filed, commits = self.run_done(d)
        self.assertTrue(said.startswith("Already sent to the team"))
        self.assertEqual((filed, commits), ([], []))

    def test_cli_refuses_a_bad_key_and_exits_2(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            self.assertEqual(S.main(["done", "../etc", "--by", "designer", "--out", str(self.out)], drive=FakeDrive({})), 2)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(S.main(["done", self.KEY, "--by", "designer", "--out", str(self.out)],
                                    drive=drive(brand_a={self.KEY: handoff()})), 2)
        self.assertIn("returned/ has no pictures", out.getvalue())


if __name__ == "__main__":
    unittest.main()
