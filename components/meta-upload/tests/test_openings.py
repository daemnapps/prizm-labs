"""A flexible video card says which opening each asset carries, and the concept its brief names (openings.py,
to_check.py, feed_video.py). The short ad name stays as it is. Every test files into its own scratch root, and no
test writes the brief register.

    /usr/bin/python3 components/meta-upload/tests/test_openings.py
"""
import json, os, shutil, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "naming"))
import openings as OP  # noqa: E402
import to_check as T  # noqa: E402
import feed_video as F  # noqa: E402
import concept as CN  # noqa: E402

AD = "acme_widget_brief-0001_batch-2026-11-18-a"
SAID = [{"id": "Opening 1 · Control", "text": "This one is 45 and this one is 70.", "take": "control"},
        {"id": "Opening 2 · The cream that lost", "text": "Every cream faded it, then it came back."},
        {"id": "Opening 3 · Same place", "text": "It came back in the same place."}]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.meta = self.tmp / "meta"
        self.env = mock.patch.dict(os.environ, {"META_CARDS_ROOT": str(self.meta), "NO_AD_WORDS": "1",
                                                "MADE_BY_TOOL_GATE_OFF": "all", "META_FILE_MASTER_COVERS_OFF": "1"})
        self.env.start()
        self.copy = mock.patch.object(T, "_copy", lambda s, d, c: shutil.copy2(s, d))
        self.copy.start()
        self.run = self.tmp / "edit-run"
        self.videos = []
        for v in ("control", "G01-H2", "G01-H3"):
            f = self.run / "renders" / f"{v}.mp4"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"video " + v.encode())
            self.videos.append(f)
        (self.run / "edit-map.json").write_text(json.dumps({"total": 30}))
        (self.run / "edit-map-G01-H2.json").write_text(json.dumps({"hook": "Opening 2 · The cream that lost"}))
        (self.run / "edit-map-G01-H3.json").write_text(json.dumps({"hook": "Opening 3 · Same place"}))

    def tearDown(self):
        self.copy.stop()
        self.env.stop()
        shutil.rmtree(self.tmp)

    def names(self):
        return [f"{AD}_asset-0{i}.mp4" for i in (1, 2, 3)]


class Labels(Base):
    def test_each_asset_is_labelled_from_the_edits_own_record(self):
        rows = OP.labels(self.videos, self.names(), None, SAID)
        self.assertEqual([r["asset"] for r in rows], ["asset-01", "asset-02", "asset-03"])
        self.assertEqual([r["version"] for r in rows], ["control", "G01-H2", "G01-H3"])
        self.assertEqual([r["opening"] for r in rows],
                         ["Opening 1 · Control", "Opening 2 · The cream that lost", "Opening 3 · Same place"])
        self.assertEqual(rows[1]["text"], "Every cream faded it, then it came back.")
        self.assertEqual({r["from"] for r in rows}, {"edit record"})

    def test_the_callers_own_label_wins(self):
        rows = OP.labels(self.videos, self.names(), [None, "Opening 3 · Same place", {"version": "cut-b"}], SAID)
        self.assertEqual(rows[1]["opening"], "Opening 3 · Same place")
        self.assertEqual(rows[1]["text"], "It came back in the same place.")
        self.assertEqual(rows[1]["from"], "caller")
        self.assertEqual(rows[2]["version"], "cut-b")
        self.assertIsNone(rows[2]["opening"])
        self.assertEqual(rows[0]["from"], "edit record")

    def test_an_opening_that_cannot_be_read_is_left_empty_never_guessed(self):
        loose = []
        for n in ("a", "b"):
            f = self.tmp / f"{n}.mp4"
            f.write_bytes(b"x")
            loose.append(f)
        rows = OP.labels(loose, self.names()[:2], None, SAID)
        self.assertEqual([r["opening"] for r in rows], [None, None])
        self.assertEqual([r["from"] for r in rows], ["file name", "file name"])
        (self.run / "edit-map-G01-H3.json").write_text("not json")
        self.assertIsNone(OP.labels(self.videos, self.names(), None, SAID)[2]["opening"])

    def test_one_master_alone_is_the_control(self):
        f = self.tmp / "master.mp4"
        f.write_bytes(b"x")
        row = OP.labels([f], self.names()[:1], None, SAID)[0]
        self.assertEqual((row["opening"], row["text"]), ("Opening 1 · Control", "This one is 45 and this one is 70."))

    def test_an_opening_numbered_the_same_finds_its_words(self):
        rows = OP.labels(self.videos[:2], self.names()[:2], [None, "Opening 2 · reworded"], SAID)
        self.assertEqual(rows[1]["text"], "Every cream faded it, then it came back.")


class OnTheCard(Base):
    def file(self, **kw):
        return F.file_master("acme", "none", "widget", "batch-2026-11-18-a", self.videos, root=str(self.meta), **kw)[0]

    def test_a_video_card_lists_the_opening_of_every_asset_and_the_name_stays_short(self):
        p = self.file()
        card = json.loads((p["target"] / "card.json").read_text())
        self.assertEqual(card["ad_name"], "acme_widget_none_batch-2026-11-18-a")
        self.assertEqual([o["file"] for o in card["openings"]], card["media"])
        self.assertEqual([o["opening"] for o in card["openings"]],
                         [None, "Opening 2 · The cream that lost", "Opening 3 · Same place"])
        self.assertNotIn("concept", card)                       # no brief, so no concept is claimed

    def test_the_callers_labels_reach_the_card(self):
        p = self.file(openings=["Opening 1 · Control", "Opening 2 · x", "Opening 3 · y"])
        self.assertEqual([o["from"] for o in p["card"]["openings"]], ["caller"] * 3)

    def test_the_briefs_concept_rides_on_the_card(self):
        with mock.patch.object(T, "brief_facts", lambda *a, **k: {"product": "widget", "concept": "one face, two ages"}):
            p = self.file()
        self.assertEqual(p["card"]["concept"], "one face, two ages")

    def test_a_picture_card_has_no_openings(self):
        pic = self.tmp / "a.png"
        pic.write_bytes(b"png")
        p = T.to_check("acme", "image", "flexible", [pic], {}, [], product="widget", brief="none",
                       batch="batch-2026-11-18-a", root=str(self.meta))
        self.assertNotIn("openings", p["card"])

    def test_a_trial_filing_never_writes_the_brief_register(self):
        with mock.patch.object(CN, "file_assets") as wrote, mock.patch.object(CN, "auto") as read:
            self.file()
            self.file(dry_run=True)
        wrote.assert_not_called()
        read.assert_not_called()

    def test_a_label_that_fails_never_stops_the_filing(self):
        with mock.patch.object(OP, "labels", side_effect=RuntimeError("boom")):
            p = self.file()
        self.assertEqual(p["state"], "filed")
        self.assertNotIn("openings", p["card"])


class OnTheRecord(Base):
    def test_a_real_filing_writes_the_rows_and_the_concept_onto_the_briefs_record(self):
        card = {"brief_id": "brief-0001", "product": "widget", "ad_name": AD,
                "openings": [{"asset": "asset-01", "opening": "Opening 1 · Control"}]}
        with mock.patch.object(CN, "file_assets") as wrote:
            T.record_openings("acme", card)
        wrote.assert_called_once_with("acme", "brief-0001", "widget", AD, card["openings"])
        with mock.patch.object(CN, "auto") as read:
            T.read_concept("acme", "brief-0001", "widget")
            T.read_concept("acme", "none", "widget")
        read.assert_called_once_with("acme", "brief-0001", "widget")   # read before the card is planned

    def test_a_card_with_no_brief_writes_nothing_and_a_failure_is_said_not_raised(self):
        with mock.patch.object(CN, "file_assets") as wrote:
            T.record_openings("acme", {"brief_id": None, "ad_name": AD, "openings": [{"asset": "asset-01"}]})
        wrote.assert_not_called()
        with mock.patch.object(CN, "file_assets", side_effect=RuntimeError("boom")):
            T.record_openings("acme", {"brief_id": "brief-0001", "ad_name": AD, "openings": [{"asset": "asset-01"}]})
        with mock.patch.object(CN, "auto", side_effect=RuntimeError("boom")):
            T.read_concept("acme", "brief-0001", "widget")                         # no raise


if __name__ == "__main__":
    unittest.main()
