"""The reason travels (logic layer W1, 2026-11-18). A front stage that decides something says what it chose and
why on the run's own trail, and the triage's reasons are kept beside the names it gives each layer. Before this,
only the names travelled: why a post was picked, why the product, why the awareness level, which route the
audience stage recommended, why a format was called that, why a swipe scene was dropped were each written down
once and read by no later stage.

No model, no network, no run folder outside a temp folder.

    /usr/bin/python3 -m unittest test_reasons_travel
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
_s = importlib.util.spec_from_file_location("td_run_reasons", HERE / "run.py")
R = importlib.util.module_from_spec(_s); _s.loader.exec_module(R)
import chain as C      # noqa: E402
import layers as L     # noqa: E402

TRIAGE = """LANE: ORGANIC
STYLE: studio-clean — flat even light, one seamless backdrop.
FORMAT: new:desk-demo — one presenter at a desk shows the thing working.
**STRUCTURE:** `problem-solution` · 0:00-0:04 the hook, 0:04-0:20 the problem
MADE: from-scratch - every picture is generated new
"""


def rows(st, decision=None):
    return [r for r in st.get("trail") or [] if decision is None or r["decision"] == decision]


class TheTrailRow(unittest.TestCase):
    def test_a_row_says_the_stage_the_decision_the_choice_the_reason_and_who_decided(self):
        st = {}
        self.assertTrue(R.trail_add(st, "1b", "Awareness level", "unaware", "the post never names the problem", "the audience stage"))
        r = st["trail"][0]
        self.assertEqual((r["stage"], r["decision"], r["choice"], r["why"], r["by"]),
                         ("teardown", "Awareness level", "unaware", "the post never names the problem", "the audience stage"))

    def test_stage_ids_are_filed_under_the_trails_own_stations(self):
        self.assertEqual([R.trail_station(s) for s in ("pick", "run setup", "0", "1b", "stage1c", "3", "4v2a", "writing")],
                         ["pick", "decide", "teardown", "teardown", "teardown", "writing", "writing", "writing"])

    def test_the_same_row_is_written_once_and_a_newer_answer_replaces_it(self):
        st = {}
        for _ in range(3):
            R.trail_add(st, "0", "The swipe's format", "meme", "a caption over one beat", "the triage")
        self.assertEqual(len(st["trail"]), 1)
        R.trail_add(st, "0", "The swipe's format", "meme", "the caption carries the joke", "the triage")
        self.assertEqual([r["why"] for r in st["trail"]], ["the caption carries the joke"])   # the newer answer replaces it

    def test_a_choice_with_no_reason_is_kept_and_the_gap_is_said(self):
        st = {}
        R.trail_add(st, "1b", "Who makes it (recommended)", "creator", None, "the audience stage")
        R.trail_add(st, "1b", "Who makes it (recommended)", "creator", "", "the audience stage")
        self.assertEqual([r["why"] for r in st["trail"]], ["no reason was written down"])

    def test_nothing_chosen_and_no_reason_writes_nothing(self):
        st = {}
        self.assertFalse(R.trail_add(st, "0", "The swipe's style", "", ""))
        self.assertNotIn("trail", st)

    def test_a_trail_that_cannot_be_written_never_stops_the_run(self):
        st = {}
        with mock.patch.object(R, "_trail", side_effect=RuntimeError("no trail here")), \
                mock.patch.object(R, "say", lambda *a, **k: None):
            self.assertFalse(R.trail_add(st, "0", "The swipe's style", "x", "y"))


class TheTriagesReasons(unittest.TestCase):
    def test_each_reason_is_read_off_the_line_its_name_is_read_from(self):
        self.assertEqual(L.parse(TRIAGE), {"format": "new:desk-demo", "style": "studio-clean",
                                           "structure": "problem-solution", "made": "from-scratch"})
        why = L.reasons(TRIAGE)
        self.assertEqual(why["format"], "one presenter at a desk shows the thing working.")
        self.assertEqual(why["style"], "flat even light, one seamless backdrop.")
        self.assertEqual(why["structure"], "0:00-0:04 the hook, 0:04-0:20 the problem")
        self.assertEqual(why["made"], "every picture is generated new")

    def test_a_line_with_only_a_name_has_no_reason(self):
        self.assertEqual(L.reasons("FORMAT: meme\nSTYLE: studio-clean\n"), {})

    def test_settle_keeps_the_reason_beside_the_name_as_from_keeps_who_named_it(self):
        st = {}
        active = {"format": [], "style": [{"id": "studio-clean"}], "structure": [{"id": "problem-solution"}]}
        with mock.patch.object(L, "active", lambda el: (active[el], "test")), \
                mock.patch.object(L, "aliases", lambda el: {}), mock.patch.object(L, "hand_tags", lambda key: {}), \
                mock.patch.object(L, "pending", lambda lay, key: []):
            lay = L.settle(st, L.parse(TRIAGE), None, L.reasons(TRIAGE))
        self.assertEqual(lay["format"], "new:desk-demo")
        self.assertEqual(lay["_why"]["format"], "one presenter at a desk shows the thing working.")
        self.assertEqual(lay["_from"]["format"], "triage")
        self.assertEqual(st["format_id"], "new:desk-demo")          # what it always set is still set

    def test_a_hand_tag_wins_and_its_reason_says_it_was_a_hand_tag(self):
        st = {}
        with mock.patch.object(L, "active", lambda el: ([{"id": "studio-clean"}, {"id": "talking-head"}], "test")), \
                mock.patch.object(L, "aliases", lambda el: {}), \
                mock.patch.object(L, "hand_tags", lambda key: {"format": "talking-head"}), \
                mock.patch.object(L, "pending", lambda lay, key: []):
            lay = L.settle(st, L.parse(TRIAGE), "ig:abc", L.reasons(TRIAGE))
        self.assertEqual((lay["format"], lay["_from"]["format"]), ("talking-head", "owner"))
        self.assertEqual(lay["_why"]["format"], L.HAND_TAG_WHY)
        self.assertNotIn("presenter at a desk", lay["_why"]["format"])   # the triage's reason was for its own read

    def test_a_re_read_with_no_reason_does_not_keep_the_older_reads_reason(self):
        st = {"layers": {"format": "meme", "_from": {"format": "triage"}, "_why": {"format": "an older reason"}}}
        with mock.patch.object(L, "active", lambda el: ([{"id": "studio-clean"}], "test")), \
                mock.patch.object(L, "aliases", lambda el: {}), mock.patch.object(L, "hand_tags", lambda key: {}), \
                mock.patch.object(L, "pending", lambda lay, key: []):
            lay = L.settle(st, {"format": "new:desk-demo"}, None, {})
        self.assertNotIn("format", lay.get("_why") or {})

    def test_settle_without_reasons_behaves_as_it_did(self):
        st = {}
        with mock.patch.object(L, "active", lambda el: ([{"id": "studio-clean"}], "test")), \
                mock.patch.object(L, "aliases", lambda el: {}), mock.patch.object(L, "hand_tags", lambda key: {}), \
                mock.patch.object(L, "pending", lambda lay, key: []):
            lay = L.settle(st, {"style": "studio-clean"}, None)
        self.assertEqual(lay, {"style": "studio-clean", "_from": {"style": "triage"}})

    def test_the_older_triage_read_still_gives_its_two_names_and_now_their_reasons_beside(self):
        self.assertEqual(C.style_format_from_triage(TRIAGE), {"style_id": "studio-clean", "format_id": "new:desk-demo"})
        self.assertEqual(L.style_format_why(TRIAGE), {"style": "flat even light, one seamless backdrop.",
                                                      "format": "one presenter at a desk shows the thing working."})
        self.assertEqual(L.style_format_why("LANE: ORGANIC\nSTYLE: studio-clean\n"), {})


class TheAudienceStagesCalls(unittest.TestCase):
    BODY = ("LEAD DESIRE: to stop hiding it\nAWARENESS: unaware\nAWARENESS MUST NOT: \"name the product\"\n"
            "AWARENESS WHY: the post never names a problem; it is watched for the joke\n"
            "ROUTE RECOMMENDED: creator\nROUTE WHY: one real person carries the whole piece\n")

    def test_the_awareness_reason_and_the_route_reason_are_kept_with_the_calls(self):
        ms = R.market_state_from(self.BODY)
        self.assertEqual(ms["awareness"], "unaware")
        self.assertEqual(ms["awareness_why"], "the post never names a problem; it is watched for the joke")
        self.assertEqual((ms["route_recommended"], ms["route_why"]), ("creator", "one real person carries the whole piece"))

    def test_a_level_declared_with_the_pick_says_so_before_the_stages_own_reason(self):
        ms = R.market_state_from(self.BODY)
        self.assertEqual(R.awareness_reason(ms), ms["awareness_why"])
        self.assertTrue(R.awareness_reason(ms, "unaware").startswith("declared with the pick"))
        self.assertIn(ms["awareness_why"], R.awareness_reason(ms, "unaware"))
        self.assertEqual(R.awareness_reason({}, ""), "")


class TheRunsOwnSetup(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.st = {"label": "t", "slug": "t", "stages": {}, "triage_lane": "ORGANIC"}
        plan = [dict(key=k, id=k.replace("stage", ""), name=k, engine="x", version="v1", prompt="")
                for k in ("stage0", "stage1", "stage1c", "stage1b", "stage2", "stage3", "stage5")]   # no route: stops before writing
        for obj, name, fake in (
                (R, "open_run", lambda *a, **k: (self.d, self.st)),
                (R, "save", lambda d, st: None), (R, "file_to_repo", lambda d: None),
                (R, "say", lambda *a, **k: None),
                (R, "run_stage", lambda d, st, s, extras, redo=False: True),
                (R.C, "stages", lambda *a, **k: plan), (R.C, "mirror_to_drive", lambda slug: None),
                (R.C, "route_for", lambda lane: dict(skip=[], why="", substitute={}))):
            p = mock.patch.object(obj, name, fake)
            p.start()
            self.addCleanup(p.stop)

    def test_the_picks_reason_comes_in_with_the_run_and_is_the_first_row(self):
        R.run_video(None, "t", "somebrand", extras={"picked_why": "sent 41 times per 1K views", "picked_by": "the feed's pick rule",
                                                    "post_url": "https://example.test/p/1"})
        self.assertEqual(self.st["pick"], {"why": "sent 41 times per 1K views", "by": "the feed's pick rule",
                                           "post": "https://example.test/p/1"})
        first = self.st["trail"][0]
        self.assertEqual((first["decision"], first["choice"], first["why"], first["by"]),
                         ("Which post to borrow", "https://example.test/p/1", "sent 41 times per 1K views", "the feed's pick rule"))

    def test_a_run_started_with_no_pick_reason_writes_no_pick_row(self):
        R.run_video(None, "t", "somebrand", extras={})
        self.assertNotIn("pick", self.st)
        self.assertEqual(rows(self.st, "Which post to borrow"), [])

    def test_a_product_named_on_the_run_says_it_was_named_there(self):
        R.run_video(None, "t", "somebrand", product="The-Thing", extras={})
        r = rows(self.st, "Which product")
        self.assertEqual((r[0]["choice"], r[0]["by"]), ("the-thing", "the run's command"))
        R.run_video(None, "t", "somebrand", product="The-Thing", extras={})     # a second pass adds nothing
        self.assertEqual(len(rows(self.st, "Which product")), 1)

    def test_a_door_that_chose_the_product_says_how(self):
        R.run_video(None, "t", "somebrand", product="the-thing",
                    extras={"product_why": "the feed desk's product map names it for this avatar"})
        self.assertEqual(rows(self.st, "Which product")[0]["why"], "the feed desk's product map names it for this avatar")


class ADroppedSwipeElement(unittest.TestCase):
    BODY = ("## ELEMENT LEDGER\n\n| # | Element | Status | How / why |\n|---|---|---|---|\n"
            "| 1 | the mirror shot | Carried | as the swipe has it |\n"
            "| 2 | the second friend | Dropped | one speaker carries both lines; a second face splits the product beat |\n"
            "| 3 | the price card | Adapted | our offer rides the swipe's ending |\n")

    def test_why_a_swipe_element_was_dropped_goes_on_the_trail(self):
        d = Path(tempfile.mkdtemp())
        (d / "run.json").write_text(json.dumps({"lane": "scratch"}))      # no swipe lines to count in this test
        st = {"stages": {"stage3": {}}}
        with mock.patch.object(R, "say", lambda *a, **k: None), mock.patch.object(R, "save", lambda d, st: None):
            R.structure_gate(d, st, "stage3", self.BODY)
        got = {r["choice"]: r for r in st["trail"]}
        self.assertEqual(sorted(got), ["Dropped"])                       # an adapted element is not a dropped scene
        self.assertIn("a second face splits the product beat", got["Dropped"]["why"])
        self.assertIn("the second friend", got["Dropped"]["decision"])
        self.assertEqual(got["Dropped"]["by"], "the injection")
        self.assertEqual(st["stages"]["stage3"]["status"], "done")        # a note, never a hold


class AReusedTeardown(unittest.TestCase):
    def test_the_layers_it_copies_in_go_on_this_runs_trail_with_their_reasons(self):
        tmp = Path(tempfile.mkdtemp())
        sd, d = tmp / "shared", tmp / "run"
        (sd / "stages").mkdir(parents=True)
        (d / "stages").mkdir(parents=True)
        (sd / "stages" / "0-triage.md").write_text(TRIAGE)
        (sd / "shared.json").write_text(json.dumps({
            "from_run": "an-earlier-run", "stages": {"stage0": {"status": "done", "out": "stages/0-triage.md"}},
            "run": {"layers": {"format": "new:desk-demo", "style": "studio-clean",
                               "_from": {"format": "triage", "style": "owner"},
                               "_why": {"format": "one presenter at a desk shows the thing working"}}}}))
        st = {"stages": {}}
        with mock.patch.object(R, "_v2_shared_dir", lambda st: sd), mock.patch.object(R, "_clone", lambda a, b: None):
            self.assertEqual(R._v2_reuse(d, st), ["stage0"])
        got = {r["decision"]: r for r in st["trail"]}
        self.assertEqual(got["The swipe's format"]["why"], "one presenter at a desk shows the thing working")
        self.assertEqual(got["The swipe's format"]["by"], "the triage, read once for this swipe")
        self.assertEqual(got["The swipe's style"]["by"], "a hand tag")
        self.assertEqual(got["The swipe's style"]["why"], "no reason was written down")


if __name__ == "__main__":
    unittest.main()
