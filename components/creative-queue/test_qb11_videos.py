#!/usr/bin/env python3
"""QB-11 (creator view): statics.py --role video-editor reads creator's hand-offs from a fake Drive and his Done tells email_lead.
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
from test_qb9_statics import Everything, FakeDrive  # noqa: E402

VIDEO_BRIEF = "<!-- prompt -->\n\n# Entanglement, 45 s with the pitch — song ad cut\n\n## Sources (all existing)\n"
KEY = "brand_a_flex-face-brush_brief-0274"


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
        "brand_a": {"dirs": keys}}}}}}}})


class Base(unittest.TestCase):
    def setUp(self):
        was, S.approved = S.approved, lambda role: Everything()
        self.addCleanup(setattr, S, "approved", was)
        self.out = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, str(self.out))


class DamonsOwnForm(Base):
    def test_a_video_hand_off_with_only_handoff_md_is_ahmeds_work(self):
        """owner handed brand_b Body Scrub 0324 and 0325 to creator on 2026-11-03 as folders with one handoff.md and the
        files it names, not the four parts; creator works from them, so for the video editor that folder is complete and
        its handoff.md heading is the title (email_lead, 2026-11-11). A statics folder keeps the four-part rule (test_qb9)."""
        own = {"files": {"handoff.md": b"# brand_b_brilliance-body-scrub_brief-0324\n\n| `brief-0324` | x | `briefs/brief-0324/brief.md` | 23 |\n"},
               "dirs": {"briefs": {"files": {}, "dirs": {"brief-0324": {"files": {"brief.md": b"# Kitchen To The Lab\n\nbody\n"}, "dirs": {}}}}}}
        d = FakeDrive({"runs": {"dirs": {"handoffs": {"dirs": {"video-editor": {"dirs": {"brand_b": {"dirs": {
            "brand_b_brilliance-body-scrub_brief-0324": own, "brand_b_brilliance-body-scrub_brief-0399": {"files": {}, "dirs": {}}}}}}}}}}})
        got = S.listing(d, self.out, role="video-editor")
        rows = {r["key"]: r for r in got["rows"]}
        self.assertEqual(list(rows), ["brand_b_brilliance-body-scrub_brief-0324"])
        self.assertEqual((rows["brand_b_brilliance-body-scrub_brief-0324"]["title"], rows["brand_b_brilliance-body-scrub_brief-0324"]["form"]),
                         ("Kitchen To The Lab", "handoff.md"))
        self.assertEqual([g["key"] for g in got["incomplete"]], ["brand_b_brilliance-body-scrub_brief-0399"], "an empty folder is still incomplete")

    def test_the_hand_off_day_is_read_from_handoff_md(self):
        p = self.out / "BRIEF.md"
        p.write_text("# k\n\n*Video editor hand-off · brand_b · 2026-11-02 · handoff/1*\n")
        self.assertEqual(S._handed(p), "2026-11-02", "work in returned/ from before this day is not the editor's (0325)")


class Read(Base):
    def test_rows_titles_and_no_returned_folder_is_empty(self):
        d = drive(**{KEY: video(), "brand_a_flex-face-brush_brief-0075": video(("cut.mp4", "notes.txt")),
                     "brand_a_flex-face-brush_brief-0076": video(complete=False)})
        before = copy.deepcopy(d.tree)
        got = S.listing(d, self.out, role="video-editor")
        rows = {r["key"]: r for r in got["rows"]}
        self.assertEqual(sorted(rows), ["brand_a_flex-face-brush_brief-0075", KEY])
        self.assertEqual([g["key"] for g in got["incomplete"]], ["brand_a_flex-face-brush_brief-0076"])
        r = rows[KEY]
        self.assertEqual((r["title"], r["returned_files"], r["returned_work"], r["returned_id"], r["picture"]),
                         ("Entanglement, 45 s with the pitch — song ad cut", 0, 0, None, None))
        self.assertEqual((rows["brand_a_flex-face-brush_brief-0075"]["returned_files"],
                          rows["brand_a_flex-face-brush_brief-0075"]["returned_work"]), (2, 1),
                         "every file is counted as back, only a video as work: a note is not a cut (2026-11-12, 0324's CHECK-NOTES.md)")
        self.assertEqual(d.tree, before, "nothing is created on Drive: no returned/ folder appears")
        self.assertEqual(d.gets, [x for k in sorted(rows) for x in ("runs/handoffs/video-editor/brand_a/%s/BRIEF.md" % k,
                                                                     "runs/handoffs/video-editor/brand_a/%s/run.json" % k)],
                         "only the briefs and their run.json (a revision says so there, 2026-11-19) are fetched: no picture for video")

    def test_cuts_in_returned_subfolders_count_and_set_aside_ones_do_not(self):
        """email_lead, 2026-11-12: the queue missed creator's 0274, 0324 and 0325 because he saved them in returned/control/ and
        returned/variations/; a superseded-review/ folder holds cuts put aside, not his delivery."""
        v = video(("README.md", "CHECK-NOTES.md"))
        v["dirs"]["returned"]["dirs"] = {
            "control": {"files": {KEY + "-control.mp4": b"1"}, "dirs": {}},
            "variations": {"files": {KEY + "-v1.mp4": b"1", KEY + "-v2.mp4": b"1"}, "dirs": {}},
            "superseded-review": {"files": {KEY + "-control-v5.mp4": b"1"}, "dirs": {}}}
        r = S.listing(drive(**{KEY: v}), self.out, role="video-editor")["rows"][0]
        self.assertEqual((r["returned_files"], r["returned_work"]), (5, 3), "two notes + three cuts; the set-aside cut is not counted")

    def test_an_idea_with_no_brief_number_is_not_the_editors(self):
        """2026-11-25: a folder named by its production id (idea-33) reached the board before it had a brief number and was
        asked about; it is neither a row nor an incomplete hand-off. A numbered empty folder still is incomplete."""
        got = S.listing(drive(**{KEY: video(), "brand_a_flex-face-brush_idea-15": video(),
                                 "brand_a_flex-face-brush_idea-33": video(complete=False),
                                 "brand_a_flex-face-brush_brief-0076": video(complete=False)}), self.out, role="video-editor")
        self.assertEqual([r["key"] for r in got["rows"]], [KEY])
        self.assertEqual([g["key"] for g in got["incomplete"]], ["brand_a_flex-face-brush_brief-0076"])

    def test_only_a_brief_the_owner_approved_is_the_editors(self):
        """2026-11-25: a brief not approved is neither a row nor an incomplete hand-off; a cut already back stays."""
        S.approved = lambda role: {KEY}
        got = S.listing(drive(**{KEY: video(), "brand_a_flex-face-brush_brief-0075": video(),
                                 "brand_a_flex-face-brush_brief-0076": video(complete=False),
                                 "brand_a_flex-face-brush_brief-0077": video(("cut.mp4",))}), self.out, role="video-editor")
        self.assertEqual({r["key"] for r in got["rows"]}, {KEY, "brand_a_flex-face-brush_brief-0077"})
        self.assertEqual(got["incomplete"], [])

    def test_the_default_role_still_reads_graphic_designer(self):
        got = S.listing(drive(**{KEY: video()}), self.out)
        self.assertEqual(got["rows"], [])
        self.assertIn("graphic-designer", got["error"])

    def test_titles(self):
        self.assertEqual(S.title_of("# DOCUMENT ONE\n\n# BRIEF · brand_a · FLEX · The warehouse\n", "k"), "The warehouse")
        self.assertEqual(S.title_of("# DOCUMENT ONE — THE BRIEF\n# The fight × pastor barber\n", "k"), "The fight × pastor barber")
        self.assertEqual(S.title_of("no heading here", "k"), "k")


class TheDone(Base):
    def run_done(self, d):
        filed, commits = [], []

        def file_request(**a):
            filed.append(a)
            return {"item": "rv-9", "route": "git", "path": str(self.out / "review.json")}
        said = S.done(d, KEY, "creator", self.out, file_request=file_request, now="2026-10-29T22:00:00Z",
                      commit_paths=lambda paths, msg, repo: commits.append((paths, msg)), role="video-editor")
        return said, filed, commits

    def test_refused_with_no_returned_folder_and_with_an_empty_one(self):
        for d in (drive(**{KEY: video()}), drive(**{KEY: video(())})):
            with self.assertRaises(S.Refused) as e:
                self.run_done(d)
            self.assertEqual(str(e.exception), "Not sent: returned/ is empty. Put your finished cut there first.")
            self.assertFalse((self.out / "brand_a" / KEY / "done.json").exists())

    def test_one_request_to_email_lead_on_the_video_lane(self):
        said, filed, commits = self.run_done(drive(**{KEY: video(("cut-45.mp4", "cut-45.srt"))}))
        self.assertEqual(said, "Sent to email_lead: Entanglement, 45 s with the pitch — song ad cut, 2 files back.")
        self.assertEqual(len(filed), 1)
        f = filed[0]
        self.assertEqual((f["reviewers"], f["lane"], f["type"], f["requested_by"]), (["email_lead"], "video-done", "video", "creator"))
        self.assertIn("finished the video for brief", f["notes"])
        rec = json.loads((self.out / "brand_a" / KEY / "done.json").read_text())
        self.assertEqual((rec["role"], rec["by"], rec["returned_files"]), ("video-editor", "creator", 2))
        self.assertEqual(len(commits), 1)
        self.assertTrue(commits[0][1].startswith("videos: %s done by creator, 2 files back (QB-11 (creator view))" % KEY))

    def test_cli_role_and_a_bad_role(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = S.main(["done", KEY, "--role", "video-editor", "--by", "creator", "--out", str(self.out)],
                          drive=drive(**{KEY: video()}))
        self.assertEqual((code, out.getvalue().strip()), (2, "Not sent: returned/ is empty. Put your finished cut there first."))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(S.main(["list", "--role", "copywriter"], drive=drive()), 1)
        # 2026-11-02: `refresh` is the Drive walk, `list` answers at once from what it kept (never a walk itself)
        self.assertEqual(S.main(["refresh", "--role", "video-editor", "--out", str(self.out)], drive=drive(**{KEY: video()})), 0)
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
                self.assertEqual(S.main(["done", KEY, "--role", "video-editor", "--by", "creator", "--out", str(self.out)]), 1)
            self.assertEqual(out.getvalue().strip().splitlines()[-1], "Not sent: %s." % S.NO_DRIVE, "the kit shows the last line")
        finally:
            S.Drive = real

    def test_the_default_cache_folders(self):
        self.assertEqual(S.out_of("graphic-designer"), S.OUT)
        self.assertEqual(S.out_of("video-editor").relative_to(S.REPO).as_posix(), "runs/creative-queue/videos")


class ProductionStage(Base):
    def test_a_production_packet_is_ahmeds_too(self):
        """email_lead, 2026-11-19: owner handed 0334 "The Inch" out under handoffs/video-producer/ (BRIEF.md + START.md); the
        queue read only video-editor/ and showed his register's stale "brief to approve". The production folder is
        read as creator's too; a key in both folders is the video-editor one."""
        prod = {"files": {"BRIEF.md": b"# 0334 \xc2\xb7 The Inch\n", "START.md": b"s", "HANDOFF.json": b"{}"}, "dirs": {"returned": {"files": {}, "dirs": {}}}}
        d = FakeDrive({"runs": {"dirs": {"handoffs": {"dirs": {
            "video-editor": {"dirs": {"brand_a": {"dirs": {"brand_a_flex-face-brush_brief-0075": video()}}}},
            "video-producer": {"dirs": {"brand_a": {"dirs": {"brand_a_flex-face-brush_brief-0334": prod,
                                                             "brand_a_flex-face-brush_brief-0075": prod,
                                                             "brand_b-yai-a1v3": {"files": {"hand.md": b"h"}, "dirs": {}}}}}}}}}}})
        got = S.listing(d, self.out, role="video-editor")
        rows = {r["key"]: r for r in got["rows"]}
        self.assertEqual(set(rows), {"brand_a_flex-face-brush_brief-0075", "brand_a_flex-face-brush_brief-0334"})
        self.assertEqual((rows["brand_a_flex-face-brush_brief-0334"]["form"], rows["brand_a_flex-face-brush_brief-0334"].get("stage_role")),
                         ("START.md", "video-producer"))
        self.assertIsNone(rows["brand_a_flex-face-brush_brief-0075"].get("stage_role"), "the video-editor folder wins")
        self.assertEqual(got["incomplete"], [], "a writing continuation in the production folder is not listed")


class Writing(Base):
    def test_a_writing_continuation_is_a_row_with_its_hold(self):
        """email_lead, 2026-11-19: owner's six Grandma Yai jobs for creator are writing continuations (START.md + HANDOFF.json,
        no brief yet); show them, marked as writing, and say which one is held."""
        import json as J
        def pack(key, status):
            return {"files": {"START.md": b"# x\n", "HANDOFF.json": J.dumps({"packet_kind": "writing-continuation", "title": key + " \u00b7 finish writing",
                    "stage": "video-writing", "stopped": [{"stage": "stage5", "status": status}]}).encode()}, "dirs": {"returned": {"files": {}, "dirs": {}}}}
        d = FakeDrive({"runs": {"dirs": {"handoffs": {"dirs": {"video-editor": {"dirs": {}},
            "video-producer": {"dirs": {"brand_b": {"dirs": {"brand_b-yai-a1v3": pack("brand_b-yai-a1v3", "error"),
                                                              "brand_b-yai-a3v2": pack("brand_b-yai-a3v2", "held")}}}}}}}}})
        rows = {r["key"]: r for r in S.listing(d, self.out, role="video-editor")["rows"]}
        self.assertEqual(rows["brand_b-yai-a1v3"]["form"], "writing")
        self.assertEqual(rows["brand_b-yai-a1v3"]["title"], "brand_b-yai-a1v3 \u00b7 finish writing")
        self.assertEqual((rows["brand_b-yai-a1v3"]["writing"]["held"], rows["brand_b-yai-a3v2"]["writing"]["held"]), (False, True))


if __name__ == "__main__":
    unittest.main()
