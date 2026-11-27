"""Stage hand-offs: the producer pack, the checker and the pull door, on a made-up workspace. No network."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import stage_handoff as SH  # noqa: E402
import check as CK  # noqa: E402
import pack as PK  # noqa: E402
import pull as PL  # noqa: E402

KEY = "acme_widget_brief-0901"


def workspace(accepted=True, route="ai"):
    root = Path(tempfile.mkdtemp())
    (root / "components" / "image-teardown").mkdir(parents=True)
    (root / "components" / "image-teardown" / "briefs.json").write_text(json.dumps({"briefs": {
        KEY: {"type": "video-ai", "brand": "acme", "run": "swipe-1", "title": "The Widget Ad"}}}))
    run = root / "runs" / "video-writing" / "acme" / "swipe-1"
    (run / "deliverable").mkdir(parents=True)
    (run / "stages").mkdir()
    (run / "deliverable" / "5-brief.md").write_text("# The Widget Ad\n\n" + "scene line\n" * 400)
    (run / "stages" / "4f-audit.md").write_text("audit")
    (run / "run.json").write_text(json.dumps({"ran_by": "strategist-a", "production_route": route, "format_id": "fmt-a",
                                              "writing_acceptance": {"accepted": accepted, "source_sha256": "x"}}))
    tear = root / "runs" / "video-teardown" / "acme" / "swipe-1"
    (tear / "stages").mkdir(parents=True)
    (tear / "framemap").mkdir()
    (tear / "stages" / "1-teardown.md").write_text("beat\n" * 200)
    (tear / "stages" / "2-spec.md").write_text("spec\n" * 200)
    (tear / "framemap" / "FRAME-MAP.md").write_text("frame\n" * 100)
    return root


class ProducerHandoff(unittest.TestCase):
    def setUp(self):
        self.root = workspace()
        self.addCleanup(shutil.rmtree, str(self.root))

    def test_pack_files_what_the_stage_declares(self):
        out, rec = PK.build("0901", drive=False, root=self.root)
        self.assertIn("VIDEO-DELIVERY.md", rec["files"])
        self.assertIn("one distinct thumbnail", (out / "BRIEF.md").read_text())
        self.assertEqual(out, self.root / "runs/handoffs/video-producer/acme" / KEY)
        for need in SH.stage("video-production")["receives"]["files"]:
            if not need["path"].startswith("refs/"):
                self.assertTrue((out / need["path"]).is_file(), need["path"])
        man = json.loads((out / "HANDOFF.json").read_text())
        self.assertEqual((man["stage"], man["role"], man["brief"]), ("video-production", "video-producer", "brief-0901"))
        self.assertIn(man["activate"]["say"], (out / "START.md").read_text())
        self.assertEqual(man["next"]["role"], "video-editor")
        self.assertNotIn(str(self.root), json.dumps(man["sources"]))      # repo paths and Drive labels only

    def test_check_names_only_what_is_missing(self):
        out, _ = PK.build("0901", drive=False, root=self.root)
        r = CK.check(out, SH.stage("video-production"), drive=False, root=self.root)
        fails = [c["check"] for c in r["checks"] if not c["ok"]]
        self.assertEqual(fails, ["The swipe's first frame (refs/swipe-poster.jpg)"])   # no swipe video in this test

    def test_a_removed_brief_fails_the_check(self):
        out, _ = PK.build("0901", drive=False, root=self.root)
        (out / "BRIEF.md").unlink()
        r = CK.check(out, SH.stage("video-production"), drive=False, root=self.root)
        self.assertTrue(any("BRIEF.md" in c["check"] and not c["ok"] for c in r["checks"]))

    def test_a_studio_number_clash_fails(self):
        out, rec = PK.build("0901", drive=False, root=self.root)
        rec["studio"] = {"production": "E9", "brief_key": "acme_widget_brief-0999"}
        (out / "HANDOFF.json").write_text(json.dumps(rec))
        r = CK.check(out, SH.stage("video-production"), drive=False, root=self.root)
        bad = [c for c in r["checks"] if "Studio production" in c["check"]]
        self.assertEqual(len(bad), 1)
        self.assertFalse(bad[0]["ok"])

    def test_refuses_unaccepted_writing_and_other_routes(self):
        for kw in ({"accepted": False}, {"route": "creator"}):
            root = workspace(**kw)
            self.addCleanup(shutil.rmtree, str(root))
            with self.assertRaises(SystemExit) as e:
                PK.build("0901", drive=False, root=root)
            self.assertIn("REFUSED", str(e.exception))
            self.assertFalse((root / "runs" / "handoffs").exists())

    def test_pull_lists_and_opens_for_the_role(self):
        PK.build("0901", drive=False, root=self.root)
        rows = PL.waiting("video-producer", root=self.root, drive=False)
        self.assertEqual([(r["number"], r["state"], r["title"]) for r in rows], [("0901", "open", "The Widget Ad")])
        o = PL.opening("901", "video-producer", root=self.root)
        self.assertIn("components/video-production/machine/run.py start", o["run"])
        self.assertTrue(o["start"].startswith("# The Widget Ad"))

    def test_moved_on_once_the_editor_hand_off_is_filed(self):
        PK.build("0901", drive=False, root=self.root)
        (self.root / "runs/handoffs/video-editor/acme" / KEY).mkdir(parents=True)
        self.assertEqual(PL.waiting("video-producer", root=self.root, drive=False)[0]["state"], "moved on")


class WritingHandoff(unittest.TestCase):
    def setUp(self):
        self.root = workspace()
        self.addCleanup(shutil.rmtree, str(self.root))
        w = self.root / "runs/video-teardown/_work/swipe-2"
        (w / "stages").mkdir(parents=True)
        (w / "run.json").write_text(json.dumps({"brand": "acme", "production_route": "ai", "stages": {}} ) + " " * 300)
        (w / "stages" / "1-teardown.md").write_text("beat\n" * 200)
        (w / "stages" / "2-spec.md").write_text("spec\n" * 200)
        self.work = w

    def test_teardown_run_goes_whole_to_the_writing(self):
        out, rec = PK.build_writing("swipe-2", drive=False, root=self.root)
        self.assertEqual(out, self.root / "runs/handoffs/creative-strategist/acme/swipe-2")
        self.assertEqual(rec["stage"], "video-writing")
        self.assertIn("components/video-writing/machine/run.py swipe-2", rec["activate"]["run"])
        r = CK.check(out, SH.stage("video-writing"), drive=False, root=self.root)
        self.assertEqual([c["check"] for c in r["checks"] if not c["ok"]], [])

    def test_open_puts_the_teardown_where_the_writing_reads_it(self):
        out, _ = PK.build_writing("swipe-2", drive=False, root=self.root)
        shutil.rmtree(str(self.work))                                  # another machine: no working run there
        o = PL.opening("swipe-2", "creative-strategist", root=self.root)
        self.assertEqual(o["placed"], "runs/video-teardown/_work/swipe-2")
        self.assertTrue((self.work / "stages" / "2-spec.md").is_file())
        (self.work / "stages" / "2-spec.md").write_text("theirs")
        PL.opening("swipe-2", "creative-strategist", root=self.root)  # never over a run already there
        self.assertEqual((self.work / "stages" / "2-spec.md").read_text(), "theirs")

    def test_refuses_a_teardown_not_finished_or_already_written(self):
        (self.work / "stages" / "2-spec.md").unlink()
        with self.assertRaises(SystemExit):
            PK.build_writing("swipe-2", drive=False, root=self.root)
        (self.work / "stages" / "2-spec.md").write_text("spec")
        (self.work / "stages" / "3-injection.md").write_text("written")
        with self.assertRaises(SystemExit):
            PK.build_writing("swipe-2", drive=False, root=self.root)

    def test_pull_shows_the_stage_it_is_for(self):
        PK.build_writing("swipe-2", drive=False, root=self.root)
        rows = PL.waiting("creative-strategist", root=self.root, drive=False)
        self.assertEqual([(r["key"], r["stage"], r["state"]) for r in rows], [("swipe-2", "video-writing", "open")])


class RolesAreData(unittest.TestCase):
    def test_every_stage_role_is_in_roles_json(self):
        rs = SH.roles()
        for s in SH.chain("video")["stages"]:
            self.assertIn(s["role"], rs, s["id"])

    def test_roles_are_jobs_not_people(self):
        people = {h for v in SH.roles().values() for h in v["holders"]}
        for s in SH.chain("video")["stages"]:
            self.assertNotIn(s["role"], people)

    def test_the_chain_is_the_four_components(self):
        st = SH.chain("video")["stages"]
        self.assertEqual([s["id"] for s in st], ["video-teardown", "video-writing", "video-production", "video-edit"])
        for s in st:
            self.assertTrue((SH.repo() / s["component"]).is_dir(), s["component"])
            self.assertIn("components/%s/" % s["id"], s["activates"]["run"])
        self.assertEqual([s["next"] for s in st], ["video-writing", "video-production", "video-edit", None])

    def test_editor_stage_keeps_its_own_checker(self):
        self.assertEqual(SH.stage("video-edit")["receives"]["checker"], "components/video-edit/handoff_check.py")
        self.assertTrue((SH.repo() / "components/video-edit/handoff_check.py").is_file())


if __name__ == "__main__":
    unittest.main()
