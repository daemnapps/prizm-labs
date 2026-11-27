#!/usr/bin/env python3
"""QB-9 (editor statics): statics.py reads the graphic-designer hand-offs from a fake Drive and editor's Done tells email_lead.
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

BRIEF = "<!-- prompt -->\n\n# DOCUMENT ONE\n\n# BRIEF · brand_a · FLEX™ Pro Vibrating Face Brush · The warehouse full of FLEX\n"


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


def handoff(files_back=(), approved="brand_a_flex-face-brush_brief-0296-approved.png", complete=True):
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


class Everything(object):
    """Every hand-off in a fixture is an approved brief, unless a test says otherwise."""
    def __contains__(self, k):
        return True


class Base(unittest.TestCase):
    def setUp(self):
        was, S.approved = S.approved, lambda role: Everything()
        self.addCleanup(setattr, S, "approved", was)
        self.out = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, str(self.out))


class Listing(Base):
    def test_complete_rows_and_incomplete_left_out(self):
        d = drive(brand_a={"brand_a_flex-face-brush_brief-0296": handoff(),
                          "brand_a_flex-face-brush_brief-0232": handoff(("a.png", "b.jpg", "notes.txt"),
                                                                       approved="brand_a_flex_brief-0232-approved.png")},
                  brand_b={"brand_b_brilliance-face-scrub_brief-0325": handoff(complete=False)})
        got = S.listing(d, self.out)
        self.assertIsNone(got["error"])
        rows = {r["key"]: r for r in got["rows"]}
        self.assertEqual(sorted(rows), ["brand_a_flex-face-brush_brief-0232", "brand_a_flex-face-brush_brief-0296"])
        self.assertEqual(got["incomplete"], [{"key": "brand_b_brilliance-face-scrub_brief-0325", "brand": "brand_b",
                                              "missing": ["BRIEF.md", "RUN.md", "run.json", "refs/"]}])
        r = rows["brand_a_flex-face-brush_brief-0296"]
        self.assertEqual((r["brand"], r["title"], r["returned_files"], r["returned_pictures"], r["done"]),
                         ("brand_a", "The warehouse full of FLEX", 0, 0, None))
        self.assertEqual(r["drive_url"], S.DRIVE_FOLDER % r["drive_id"])
        back = rows["brand_a_flex-face-brush_brief-0232"]
        self.assertEqual((back["returned_files"], back["returned_pictures"]), (3, 2))
        self.assertEqual(r["versions"], 1, "v1/ is the one version folder; refs/, 00-approved/ and returned/ are not")
        pic = self.out / "brand_a" / "brand_a_flex-face-brush_brief-0232" / "approved.png"
        self.assertEqual(pic.read_bytes(), b"PNG", "the -approved picture, never -approved-clean, by suffix")

    def test_versions_count_only_the_v_folders(self):
        h = handoff(("a.png",))
        for v in ("v2", "v3", "v10"):
            h["dirs"][v] = {"files": {}, "dirs": {}}
        h["dirs"]["v2-old"] = {"files": {}, "dirs": {}}
        got = S.listing(drive(brand_a={"brand_a_flex-face-brush_brief-0296": h}), self.out)
        self.assertEqual(got["rows"][0]["versions"], 4, "v1, v2, v3, v10; never v2-old")

    def test_when_each_piece_of_work_came_back(self):
        # 2026-11-06: a redo is finished by work newer than it, whoever made it; the list carries each work file's
        # Drive modifiedTime, oldest first, pictures only for a static (notes do not count)
        class Timed(FakeDrive):
            def files(self, fid):
                got = FakeDrive.files(self, fid)
                if fid.endswith("/returned"):
                    for f in got:
                        f["modifiedTime"] = {"b.png": "2026-11-07T02:00:00.000Z", "a.png": "2026-11-04T01:00:00.000Z",
                                             "notes.md": "2026-11-08T00:00:00.000Z"}[f["name"]]
                return got
        d = drive(brand_a={"brand_a_flex-face-brush_brief-0296": handoff(("a.png", "b.png", "notes.md"))})
        d.__class__ = Timed
        row = S.listing(d, self.out)["rows"][0]
        self.assertEqual(row["returned_work_at"], ["2026-11-04T01:00:00.000Z", "2026-11-07T02:00:00.000Z"])

    def test_the_brief_and_picture_are_fetched_once(self):
        d = drive(brand_a={"brand_a_flex-face-brush_brief-0296": handoff()})
        S.listing(d, self.out)
        n = len(d.gets)
        self.assertEqual(n, 3, "the brief, the picture and run.json (a revision says so there, 2026-11-19)")
        S.listing(d, self.out)
        self.assertEqual(len(d.gets), n, "the same Drive ids inside a day: nothing fetched again")
        S.listing(d, self.out, clock=lambda: 9e12)
        self.assertEqual(len(d.gets), n + 3, "after a day all three are fetched again")

    def test_a_revision_says_why_it_came_back(self):
        """email_lead, 2026-11-19: a static back for revision shows why at a glance; its run.json says state "revision"."""
        h = handoff()
        h["files"]["run.json"] = b'{"state": "revision", "next_action": "Correct $46 to $49; make a Christmas sister."}'
        d = drive(brand_a={"brand_a_flex-face-brush_brief-0297-holiday-revision": h, "brand_a_flex-face-brush_brief-0296": handoff()})
        rows = {r["key"]: r for r in S.listing(d, self.out)["rows"]}
        self.assertEqual(rows["brand_a_flex-face-brush_brief-0297-holiday-revision"]["revision"],
                         {"round": None, "why": "Correct $46 to $49; make a Christmas sister."})
        self.assertIsNone(rows["brand_a_flex-face-brush_brief-0296"]["revision"], "a first round is no revision")

    def test_a_revision_shows_the_approved_plate_from_refs(self):
        """email_lead, 2026-11-19: "por qué en el static no se ve la imagencita": a revision has no 00-approved/, its plate is in refs/."""
        h = handoff()
        del h["dirs"]["00-approved"]
        h["dirs"]["refs"]["files"]["03-approved-plate.png"] = b"PLATE"
        d = drive(brand_a={"brand_a_flex-face-brush_brief-0297-holiday-revision": h})
        row = S.listing(d, self.out)["rows"][0]
        self.assertTrue(row["picture"] and row["picture"].endswith("approved.png"), row["picture"])
        h2 = handoff(); del h2["dirs"]["00-approved"]
        h2["dirs"]["refs"]["files"].update({"01-product-sheet.png": b"P", "03-original-v1.jpg": b"O"})
        row2 = S.listing(drive(brand_b={"brand_b_idea_dec26-s6": h2}), self.out)["rows"][0]
        self.assertTrue(row2["picture"], "no approved plate: the picked original, never the product sheet")

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


class LastGoodList(Base):
    """2026-11-02, email_lead: a cold /data/statics took 137 s and editor read a missing Done as "already finished". `list`
    answers at once from the last good list (Done read fresh), and starts ONE background refresh when that list is
    older than STALE_S; `refresh` is the full Drive walk and keeps the result as the new last good list."""
    KEY = "brand_a_flex-face-brush_brief-0296"

    def setUp(self):
        super().setUp()
        self.spawned, self.now = [], [1000.0]

    def quick(self):
        return S.quick(self.out, clock=lambda: self.now[0], spawn=lambda out, role: self.spawned.append(role))

    def refresh(self, d):
        return S.refresh(d, self.out, clock=lambda: self.now[0])

    def test_no_list_yet_says_it_is_loading_and_starts_one_refresh(self):
        got = self.quick()
        self.assertEqual((got["rows"], got["refreshing"], got["error"]), ([], True, None))
        self.assertEqual(self.spawned, ["graphic-designer"])
        self.quick()
        self.assertEqual(len(self.spawned), 1, "one refresh at a time")

    def test_a_fresh_list_comes_back_at_once_with_done_read_now(self):
        self.refresh(drive(brand_a={self.KEY: handoff(("p1.png",))}))
        got = self.quick()
        self.assertEqual([r["key"] for r in got["rows"]], [self.KEY])
        self.assertFalse(got["refreshing"])
        self.assertEqual(self.spawned, [], "a fresh list starts no refresh")
        self.assertIsNone(got["rows"][0]["done"])
        (self.out / "brand_a" / self.KEY / "done.json").write_text(json.dumps({"by": "editor", "at": "2026-11-02T10:00:00Z"}))
        self.assertEqual(self.quick()["rows"][0]["done"]["by"], "editor", "Done is read from disk, never from the old list")

    def test_a_stale_list_still_comes_back_and_refreshes_behind(self):
        self.refresh(drive(brand_a={self.KEY: handoff(("p1.png",))}))
        self.now[0] += S.STALE_S + 1
        got = self.quick()
        self.assertEqual(len(got["rows"]), 1)
        self.assertTrue(got["refreshing"])
        self.assertEqual(self.spawned, ["graphic-designer"])

    def test_refresh_keeps_the_list_and_frees_the_lock(self):
        self.quick()                                         # takes the lock
        got = self.refresh(drive(brand_a={self.KEY: handoff(("p1.png",))}))
        self.assertEqual(len(got["rows"]), 1)
        self.assertFalse((self.out / S.LOCK).exists())
        self.assertEqual(len(self.quick()["rows"]), 1)

    def test_a_failed_refresh_never_replaces_the_last_good_list(self):
        self.refresh(drive(brand_a={self.KEY: handoff(("p1.png",))}))
        self.refresh(FakeDrive({}))                          # no root on Drive: an error
        got = self.quick()
        self.assertEqual(len(got["rows"]), 1)
        self.assertIn("graphic-designer", got["refresh_error"])

    def test_the_first_refresh_failing_is_said(self):
        self.refresh(FakeDrive({}))
        got = self.quick()
        self.assertEqual(got["rows"], [])
        self.assertIn("graphic-designer", got["error"])
        self.assertFalse(got["refreshing"])


class TheDone(Base):
    KEY = "brand_a_flex-face-brush_brief-0296"

    def run_done(self, d, **kw):
        filed, commits = [], []

        def file_request(**a):
            filed.append(a)
            return {"item": "rv-1", "route": "git", "path": str(self.out / "review.json")}
        said = S.done(d, self.KEY, "editor", self.out, file_request=file_request,
                      commit_paths=lambda paths, msg, repo: commits.append((paths, msg)), now="2026-10-29T21:00:00Z", **kw)
        return said, filed, commits

    def test_refused_with_nothing_back_and_nothing_written(self):
        d = drive(brand_a={self.KEY: handoff()})
        with self.assertRaises(S.Refused) as e:
            self.run_done(d)
        self.assertIn("returned/ has no pictures", str(e.exception))
        self.assertFalse((self.out / "brand_a" / self.KEY / "done.json").exists())

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

    def test_one_request_to_email_lead_only_then_done_json_and_one_commit(self):
        d = drive(brand_a={self.KEY: handoff(("a.png", "b.png", "c.txt"))})
        said, filed, commits = self.run_done(d)
        self.assertEqual(said, "Sent to email_lead: The warehouse full of FLEX, 3 files back.")
        self.assertEqual(len(filed), 1)
        f = filed[0]
        self.assertEqual((f["reviewers"], f["lane"], f["requested_by"], f["commit"]), (["email_lead"], "static-done", "editor", False))
        self.assertEqual(f["asset"]["warehouse"], "drive")
        self.assertIn(self.KEY, f["asset"]["title"])
        self.assertIn("3 files", f["asset"]["title"])
        rec = json.loads((self.out / "brand_a" / self.KEY / "done.json").read_text())
        self.assertEqual((rec["by"], rec["returned_files"], rec["returned_pictures"], rec["review"]["item"]), ("editor", 3, 2, "rv-1"))
        self.assertEqual(len(commits), 1)
        self.assertEqual([Path(p).name for p in commits[0][0]], ["done.json", "review.json"])
        listed = {r["key"]: r for r in S.listing(d, self.out)["rows"]}
        self.assertEqual(listed[self.KEY]["done"]["by"], "editor", "the list knows it was sent")

    def test_a_second_done_files_nothing(self):
        d = drive(brand_a={self.KEY: handoff(("a.png",))})
        self.run_done(d)
        said, filed, commits = self.run_done(d)
        self.assertTrue(said.startswith("Already sent to email_lead"))
        self.assertEqual((filed, commits), ([], []))

    def test_cli_refuses_a_bad_key_and_exits_2(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            self.assertEqual(S.main(["done", "../etc", "--by", "editor", "--out", str(self.out)], drive=FakeDrive({})), 2)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(S.main(["done", self.KEY, "--by", "editor", "--out", str(self.out)],
                                    drive=drive(brand_a={self.KEY: handoff()})), 2)
        self.assertIn("returned/ has no pictures", out.getvalue())


if __name__ == "__main__":
    unittest.main()
