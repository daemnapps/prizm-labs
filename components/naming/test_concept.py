"""concept.py: the concept a brief names and the opening each filed asset carries, on the brief's record.
No network, no model; every write goes to a scratch workspace.
Run: /usr/bin/python3 components/naming/test_concept.py"""
import json, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import names as N      # noqa: E402
import concept as C    # noqa: E402

PIECE = {"lane": "ai", "piece": {"title": "Two cheeks", "angle": "never-the-tool",
                                 "concept": {"name": "one face, two ages", "why": "the comparison is the proof"},
                                 "idea": "the cheek she treated looks younger than the one she did not"},
         "hooks": [{"id": "Opening 1 · Control", "text": "This cheek is 45 and this one is 70.", "take": "control"},
                   {"id": "Opening 2 · The cream that lost", "text": "Every cream faded it, then it came back."}]}


def brief_text(piece):
    return "# Two cheeks\n\nWords for people.\n\n```json\n" + json.dumps(piece, indent=1) + "\n```\n"


class Scratch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        ws = Path(self.tmp.name)
        (ws / "brands" / "testbrand" / "briefs").mkdir(parents=True)
        (ws / "brands" / "testbrand" / "briefs" / "briefs.json").write_text(json.dumps({"briefs": []}))
        self.deliverable = ws / "runs" / "video-writing" / "testbrand" / "two-cheeks" / "deliverable"
        self.deliverable.mkdir(parents=True)
        (self.deliverable / "5-brief.md").write_text(brief_text(PIECE))
        (ws / "components" / "image-teardown").mkdir(parents=True)
        self.reg = ws / "components" / "image-teardown" / "briefs.json"
        self.reg.write_text(json.dumps({"briefs": {"testbrand_widget_brief-0007": {
            "id": "testbrand_widget_brief-0007", "brief": "brief-0007", "type": "video-ai", "brand": "testbrand",
            "product": "widget", "avatar": "core-a", "run": "two-cheeks", "lane": "video-teardown", "declares": {},
            "ads": []}}}))
        self.ws = ws
        self._old = (N.WS, C.WS, N._ALIASES)
        N.WS = C.WS = ws
        N._ALIASES = None

    def tearDown(self):
        N.WS, C.WS, N._ALIASES = self._old
        self.tmp.cleanup()

    def entry(self):
        return json.loads(self.reg.read_text())["briefs"]["testbrand_widget_brief-0007"]


class FromBrief(Scratch):
    def test_reads_the_concept_the_idea_and_the_openings(self):
        got = C.from_brief(self.deliverable / "5-brief.md")
        self.assertEqual(got["concept"], "one face, two ages")
        self.assertEqual(got["concept_why"], "the comparison is the proof")
        self.assertEqual(got["idea"], "the cheek she treated looks younger than the one she did not")
        self.assertEqual([o["id"] for o in got["openings"]], ["Opening 1 · Control", "Opening 2 · The cream that lost"])
        self.assertEqual(got["openings"][0]["take"], "control")

    def test_a_concept_written_as_one_line_is_read_as_it_is(self):
        p = dict(PIECE, piece=dict(PIECE["piece"], concept="  the  mirror test "))
        f = self.deliverable / "5-brief.md"
        f.write_text(brief_text(p))
        self.assertEqual(C.from_brief(f)["concept"], "the mirror test")

    def test_a_brief_that_names_no_concept_gets_none(self):
        p = dict(PIECE, piece={"title": "Two cheeks"})
        f = self.deliverable / "5-brief.md"
        f.write_text(brief_text(p))
        self.assertIsNone(C.from_brief(f)["concept"])
        self.assertIsNone(C.from_brief(self.ws / "no-such-file.md")["concept"])
        (self.deliverable / "plain.md").write_text("# no block here\n")
        self.assertEqual(C.from_brief(self.deliverable / "plain.md")["openings"], [])


class Record(Scratch):
    def test_writes_the_concept_once_with_where_it_was_read(self):
        res = C.record("testbrand", "brief-0007", "widget")
        self.assertTrue(res["wrote"])
        e = self.entry()
        self.assertEqual(e["concept"], "one face, two ages")
        self.assertEqual(e["concept_from"], "runs/video-writing/testbrand/two-cheeks/deliverable/5-brief.md")
        self.assertEqual(e["concept_why"], "the comparison is the proof")
        # set once: a later change on the brief does not move the record unless asked
        p = dict(PIECE, piece=dict(PIECE["piece"], concept="something else"))
        (self.deliverable / "5-brief.md").write_text(brief_text(p))
        again = C.record("testbrand", "brief-0007", "widget")
        self.assertFalse(again["wrote"])
        self.assertEqual(self.entry()["concept"], "one face, two ages")
        self.assertTrue(C.record("testbrand", "brief-0007", "widget", again=True)["wrote"])
        self.assertEqual(self.entry()["concept"], "something else")

    def test_no_concept_on_the_brief_leaves_the_record_alone(self):
        before = self.reg.read_text()
        (self.deliverable / "5-brief.md").write_text(brief_text(dict(PIECE, piece={"title": "x"})))
        res = C.record("testbrand", "brief-0007", "widget")
        self.assertFalse(res["wrote"])
        self.assertIsNone(res["concept"])
        self.assertEqual(res["why"], "the brief names no concept")
        self.assertEqual(self.reg.read_text(), before)

    def test_an_unknown_brief_is_said_not_raised(self):
        res = C.record("testbrand", "brief-0999", "widget")
        self.assertIsNone(res["key"])
        self.assertFalse(res["wrote"])

    def test_the_one_brief_record_carries_the_concept(self):
        C.record("testbrand", "brief-0007", "widget")
        self.assertEqual(N.brief_record("testbrand", "brief-0007", "widget")["concept"], "one face, two ages")

    def test_the_hook_never_raises_and_can_be_switched_off(self):
        import os
        said = []
        self.assertEqual(C.auto("testbrand", "brief-0007", "widget", say=said.append), "one face, two ages")
        self.assertIn("one face, two ages", said[0])
        self.assertIsNone(C.auto("testbrand", "brief-0999", "widget", say=said.append))
        os.environ[C.OFF_ENV] = "off"
        try:
            self.assertIsNone(C.auto("testbrand", "brief-0007", "widget", say=said.append))
        finally:
            del os.environ[C.OFF_ENV]


class FileAssets(Scratch):
    ROWS = [{"asset": "asset-01", "version": "control", "opening": "Opening 1 · Control", "text": "This cheek is 45.",
             "from": "edit record"},
            {"asset": "asset-02", "version": "h2", "opening": "Opening 2 · The cream that lost", "text": None,
             "from": "edit record"}]

    def test_writes_each_assets_opening_under_the_ad_name(self):
        ad = "testbrand_widget_brief-0007_batch-2026-11-18-a"
        self.assertTrue(C.file_assets("testbrand", "brief-0007", "widget", ad, self.ROWS))
        got = self.entry()["openings"][ad]
        self.assertEqual(got[0], {"asset": "asset-01", "version": "control", "opening": "Opening 1 · Control",
                                  "text": "This cheek is 45."})
        self.assertEqual(got[1], {"asset": "asset-02", "version": "h2", "opening": "Opening 2 · The cream that lost"})
        # the same rows again change nothing; a second ad of the brief sits beside the first
        self.assertFalse(C.file_assets("testbrand", "brief-0007", "widget", ad, self.ROWS))
        self.assertTrue(C.file_assets("testbrand", "brief-0007", "widget", ad.replace("-a", "-b"), self.ROWS[:1]))
        self.assertEqual(sorted(self.entry()["openings"]), [ad, ad.replace("-a", "-b")])

    def test_nothing_to_write_writes_nothing(self):
        before = self.reg.read_text()
        self.assertFalse(C.file_assets("testbrand", "brief-0007", "widget", "x", []))
        self.assertFalse(C.file_assets("testbrand", "brief-0999", "widget", "x", self.ROWS))
        self.assertEqual(self.reg.read_text(), before)


if __name__ == "__main__":
    unittest.main()
