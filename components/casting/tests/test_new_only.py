"""New only: an old person, set or product picture is refused by name; new names, unapproved rows and runs in flight pass."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent))
from casting import new_only as NO                                     # noqa: E402

B = "testbrand"


class Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.ws = Path(self.t.name)
        (self.ws / "components").mkdir(); (self.ws / "brands").mkdir()
        bank = self.ws / "runs/ai-elements" / B
        kit = bank / "products/brush-face"
        (kit / "model").mkdir(parents=True); (kit / "sources").mkdir()
        (kit / "kit.json").write_text(json.dumps({"aliases": ["brush"], "shown": {"refs": ["sources/turntable-000.png"]}}))
        (kit / "sources/turntable-000.png").write_bytes(b"x")
        (kit / "model/sheet/current").mkdir(parents=True)
        (kit / "model/sheet/current/front.png").write_bytes(b"x")
        (kit / "model/sheet/current/back.png").write_bytes(b"x")
        self.rows = {"in_flight": ["old-run"],
                     "people": {"old-guy": {"why": "marked Remove", "status": "approved"},
                                "maybe-guy": {"why": "not decided", "status": "draft"}},
                     "sets": {"old-room": {"why": "made before the rebuild", "status": "approved"}},
                     "pictures": {"store": {"match": "http*", "why": "store photo", "status": "approved"},
                                  "kit-packshot": {"match": "*/products/*/sources/*_packshot_*", "why": "old", "status": "approved"}}}
        NO.path_of(B, self.ws).write_text(json.dumps(self.rows))

    def tearDown(self):
        self.t.cleanup()


class Refused(Base):
    def test_old_person_refused_by_name(self):
        with self.assertRaises(SystemExit) as e:
            NO.refuse_person(B, "old-guy", ws=self.ws)
        self.assertIn("old-guy", str(e.exception))

    def test_old_person_picture_refused(self):
        p = self.ws / "runs/ai-elements" / B / "casting/old-guy/sheets/headshot.jpg"
        with self.assertRaises(SystemExit):
            NO.refuse_pictures([p], ws=self.ws)

    def test_old_set_picture_refused(self):
        self.assertTrue(NO.old_picture("runs/ai-elements/%s/sets/old-room/plates/wide.png" % B, ws=self.ws))

    def test_store_photo_and_old_packshot_refused(self):
        self.assertTrue(NO.old_picture("https://cdn.example/x.jpg", B, ws=self.ws))
        self.assertTrue(NO.old_picture("runs/ai-elements/%s/products/brush-face/sources/b_brush_packshot_front.jpg" % B, ws=self.ws))

    def test_a_new_run_cannot_borrow_the_old_person(self):
        self.assertTrue(NO.old_person(B, "old-guy", "brand-new-run", ws=self.ws))


class Passed(Base):
    def test_new_name_passes(self):
        self.assertIsNone(NO.old_person(B, "made-for-this-piece", ws=self.ws))

    def test_draft_row_refuses_nothing(self):
        self.assertIsNone(NO.old_person(B, "maybe-guy", ws=self.ws))

    def test_run_in_flight_finishes(self):
        self.assertIsNone(NO.old_person(B, "old-guy", "old-run", ws=self.ws))
        self.assertIsNone(NO.old_picture("runs/ai-elements/%s/casting/old-guy/master.jpg" % B, run="old-run", ws=self.ws))

    def test_turntable_view_passes(self):
        self.assertIsNone(NO.old_picture("runs/ai-elements/%s/products/brush-face/sources/turntable-000.png" % B, ws=self.ws))

    def test_no_list_refuses_nothing(self):
        self.assertIsNone(NO.old_person("no-such-brand", "anyone", ws=self.ws))

    def test_run_of_reads_the_label(self):
        self.assertEqual(NO.run_of("/x/runs/video-production/b/label-1/media/a.png"), "label-1")
        self.assertIsNone(NO.run_of("/x/runs/ai-elements/b/casting/a/master.jpg"))


class Fresh(Base):
    def test_product_comes_from_the_kit_by_any_name(self):
        for name in ("brush", "brush-face"):
            got, _ = NO.fresh_product(B, name, self.ws)
            self.assertEqual(got.parent.name + "/" + got.name, "current/front.png")

    def test_the_sheet_views_say_their_side(self):
        got = NO.sheet_views(B, "brush", self.ws)
        self.assertEqual([p.name for p, _ in got], ["front.png", "back.png"])
        self.assertIn("BACK", got[1][1])

    def test_no_repoint_until_approved(self):
        for r in self.rows["pictures"].values():
            r["status"] = "draft"
        NO.path_of(B, self.ws).write_text(json.dumps(self.rows))
        self.assertIsNone(NO.fresh_product(B, "brush", self.ws)[0])

    def test_approve_turns_a_draft_on(self):
        self.assertEqual(NO.approve(B, ws=self.ws), 1)
        self.assertTrue(NO.old_person(B, "maybe-guy", ws=self.ws))

    def test_keep_drops_the_out_person(self):
        self.assertEqual(NO.keep(B, [{"id": "old-guy"}, {"id": "new-guy"}], ws=self.ws), [{"id": "new-guy"}])


if __name__ == "__main__":
    unittest.main()
