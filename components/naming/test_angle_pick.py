"""angle_pick + the one brief record (the owner 2026-10-12: the angle is derived from the brief and
kept in its notes). No network: the model call goes through a fake runner, and every write goes to
a scratch workspace. Run: /usr/bin/python3 components/naming/test_angle_pick.py"""
import json, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import names as N          # noqa: E402
import angle_pick as AP    # noqa: E402

BRIEF = """# brief-0901 · A song ad

Verse: I blamed the tool for years.
Bridge: It was never the tool you blamed, it was what was under it.
"""
ANGLES = {"angles": [
    {"id": "never-the-tool", "name": "Never the tool", "avatar": "core-a", "status": "active",
     "what": "He blames the tool; the real cause is underneath."},
    {"id": "gift-idea", "name": "A gift", "avatar": "core-a", "status": "active", "what": "Someone buys it for him."},
    {"id": "a-format", "name": "Grid", "avatar": "core-a", "status": "active", "what": "four cells", "misfiled": "format"},
    {"id": "other-person", "name": "Other", "avatar": "core-b", "status": "active", "what": "for someone else"},
    {"id": "unsigned-one", "name": "Draft", "avatar": "core-a", "status": "draft", "what": "not signed"},
]}


class Scratch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        ws = Path(self.tmp.name)
        (ws / "brands" / "testbrand" / "strategy").mkdir(parents=True)
        (ws / "brands" / "testbrand" / "strategy" / "angles.json").write_text(json.dumps(ANGLES))
        (ws / "brands" / "testbrand" / "briefs").mkdir(parents=True)
        (ws / "brands" / "testbrand" / "briefs" / "briefs.json").write_text(json.dumps({"briefs": []}))
        run = ws / "runs" / "video-production" / "testbrand" / "song-run"
        run.mkdir(parents=True)
        (run / "EDITOR-BRIEF.md").write_text(BRIEF)
        (ws / "tools" / "image-teardown").mkdir(parents=True)
        self.reg = ws / "tools" / "image-teardown" / "briefs.json"
        self.reg.write_text(json.dumps({"briefs": {"testbrand_widget_brief-0901": {
            "id": "testbrand_widget_brief-0901", "brief": "brief-0901", "type": "video-ai", "brand": "testbrand",
            "product": "widget", "avatar": "core-a", "run": "runs/video-production/testbrand/song-run",
            "brief_file": "runs/video-production/testbrand/song-run/EDITOR-BRIEF.md", "declares": {}}}}))
        (ws / "components" / "models").mkdir(parents=True)
        (ws / "components" / "models" / "models.json").write_text(json.dumps({"models": [
            {"id": "claude-sonnet-5", "aliases": ["sonnet"], "status": "approved", "modality": ["text"]}]}))
        self.ws = ws
        self._old = (N.WS, AP.WS, N._ALIASES)
        N.WS = AP.WS = ws
        N._ALIASES = None

    def tearDown(self):
        N.WS, AP.WS, N._ALIASES = self._old
        self.tmp.cleanup()

    def runner(self, answer):
        seen = {}

        def r(prompt, model):
            seen["prompt"], seen["model"] = prompt, model
            return 0, json.dumps(answer), ""
        r.seen = seen
        return r


class TestBank(Scratch):
    def test_every_avatar_gets_every_active_angle(self):
        # angles are the brand's, not an avatar's (the owner, 28 Oct 2026): another avatar's angle stays in the bank
        rows, scope = AP.bank("testbrand", "core-a")
        self.assertEqual({a["id"] for a in rows}, {"never-the-tool", "gift-idea", "other-person"})
        self.assertEqual(scope, "")

    def test_unknown_avatar_gets_whole_active_bank(self):
        rows, _ = AP.bank("testbrand", "nobody")
        self.assertEqual({a["id"] for a in rows}, {"never-the-tool", "gift-idea", "other-person"})


class TestPick(Scratch):
    def test_picks_from_bank_with_a_quote_from_the_brief(self):
        r = self.runner({"state": "picked", "angle": "never-the-tool",
                         "quote": "It was never the tool you blamed", "why": "The turn says the tool was not the cause."})
        res = AP.pick("testbrand", "brief-0901", "widget", runner=r)
        self.assertEqual(res["angle"], "never-the-tool")
        self.assertIn('"It was never the tool you blamed"', res["angle_why"])
        self.assertEqual(r.seen["model"], "claude-sonnet-5")
        self.assertIn("INVENTED-EXAMPLE GUARD", r.seen["prompt"].split("## Your job")[0])
        self.assertNotIn("a-format", r.seen["prompt"])      # a misfiled row never reaches the bank
        self.assertNotIn("unsigned-one", r.seen["prompt"])

    def test_coined_angle_is_refused(self):
        r = self.runner({"state": "picked", "angle": "brand-new-angle", "quote": "I blamed the tool", "why": "x"})
        with self.assertRaises(AP.NoPick):
            AP.pick("testbrand", "brief-0901", "widget", runner=r)

    def test_quote_not_in_brief_is_refused(self):
        r = self.runner({"state": "picked", "angle": "gift-idea", "quote": "words nobody wrote here", "why": "x"})
        with self.assertRaises(AP.NoPick):
            AP.pick("testbrand", "brief-0901", "widget", runner=r)

    def test_no_fit_is_an_answer(self):
        r = self.runner({"state": "no-fit", "angle": None, "quote": "I blamed the tool for years", "why": "No claim fits."})
        res = AP.pick("testbrand", "brief-0901", "widget", runner=r)
        self.assertEqual((res["state"], res["angle"]), ("no-fit", None))

    def test_declared_angle_needs_no_model(self):
        reg = json.loads(self.reg.read_text())
        reg["briefs"]["testbrand_widget_brief-0901"]["declares"] = {"angle": "gift-idea"}
        self.reg.write_text(json.dumps(reg))

        def boom(p, m):
            raise AssertionError("no model call for a declared angle")
        res = AP.pick("testbrand", "brief-0901", "widget", runner=boom)
        self.assertEqual((res["state"], res["angle"]), ("declared", "gift-idea"))


class TestRunningAdSets(Scratch):
    """the owner, 2026-10-27: new ads go into the ad sets already running unless he signs a new one — so the
    angle is picked from the angles whose ad set is open (meta-upload ad_sets.py, faked here)."""
    def open_only(self, *ids):
        mu = self.ws / "components" / "meta-upload"
        mu.mkdir(parents=True, exist_ok=True)
        (mu / "ad_sets.py").write_text(
            f"def open_angles(brand, avatar, angles, runs_root=None):\n    return [a for a in angles if a in {list(ids)!r}]\n")

    def declare(self, angle):
        reg = json.loads(self.reg.read_text())
        reg["briefs"]["testbrand_widget_brief-0901"]["declares"] = {"angle": angle}
        self.reg.write_text(json.dumps(reg))

    def test_only_angles_with_a_running_ad_set_reach_the_bank(self):
        self.open_only("gift-idea")
        r = self.runner({"state": "picked", "angle": "gift-idea", "quote": "I blamed the tool", "why": "x"})
        AP.pick("testbrand", "brief-0901", "widget", runner=r)
        self.assertNotIn("never-the-tool", r.seen["prompt"])
        self.assertIn("with an ad set already running", r.seen["prompt"])

    def test_an_avatar_with_none_running_keeps_the_whole_bank(self):
        self.open_only()
        r = self.runner({"state": "picked", "angle": "gift-idea", "quote": "I blamed the tool", "why": "x"})
        AP.pick("testbrand", "brief-0901", "widget", runner=r)
        self.assertIn("never-the-tool", r.seen["prompt"])

    def test_a_declared_angle_in_squashed_spelling_is_kept(self):
        self.declare("giftidea")

        def boom(p, m):
            raise AssertionError("no model call for a declared angle")
        res = AP.pick("testbrand", "brief-0901", "widget", runner=boom)
        self.assertEqual((res["state"], res["angle"]), ("declared", "gift-idea"))

    def test_a_declared_angle_with_no_running_ad_set_is_picked_again(self):
        self.open_only("never-the-tool")
        self.declare("gift-idea")
        r = self.runner({"state": "picked", "angle": "never-the-tool",
                         "quote": "It was never the tool you blamed", "why": "x"})
        res = AP.pick("testbrand", "brief-0901", "widget", runner=r)
        self.assertEqual((res["state"], res["angle"]), ("picked", "never-the-tool"))

    def test_a_picture_brief_is_found_in_its_teardown_run(self):
        out = self.ws / "tools" / "image-teardown" / "runs" / "pic-run" / "out"
        out.mkdir(parents=True)
        (out / "06-brief.md").write_text(BRIEF)
        self.assertEqual(AP.brief_file({"brand": "testbrand", "run": "pic-run"}), out / "06-brief.md")


class TestRecordAndRead(Scratch):
    def test_record_then_every_reader_sees_it(self):
        r = self.runner({"state": "picked", "angle": "never-the-tool",
                         "quote": "It was never the tool you blamed", "why": "The turn names the real cause."})
        AP.record("testbrand", AP.pick("testbrand", "brief-0901", "widget", runner=r))
        e = json.loads(self.reg.read_text())["briefs"]["testbrand_widget_brief-0901"]
        self.assertEqual((e["angle"], e["angle_state"]), ("never-the-tool", "picked"))
        note = (self.ws / e["brief_file"]).read_text()
        self.assertEqual(note.count(AP.NOTE_TAG), 1)
        self.assertIn("`never-the-tool`", note)
        # the one reader: no brands header → the register's angle
        self.assertEqual(N.brief_angle("testbrand", "brief-0901", "widget")["angle_from"], "register")
        self.assertEqual(N.brief_record("testbrand", "brief-0901", "widget")["avatar"], "core-a")
        # proposal for the brands/ header, under runs/, never in brands/
        props = list((self.ws / "runs" / "brands-proposals" / "testbrand").glob("*/briefs/brief-angles.json"))
        self.assertEqual(len(props), 1)
        self.assertEqual(json.loads((self.ws / "brands/testbrand/briefs/briefs.json").read_text()), {"briefs": []})
        # recording twice keeps one NOTES line
        AP.record("testbrand", AP.pick("testbrand", "brief-0901", "widget", runner=r))
        self.assertEqual((self.ws / e["brief_file"]).read_text().count(AP.NOTE_TAG), 1)

    def test_header_angle_wins_over_register(self):
        reg = json.loads(self.reg.read_text())
        reg["briefs"]["testbrand_widget_brief-0901"]["angle"] = "gift-idea"
        self.reg.write_text(json.dumps(reg))
        (self.ws / "brands/testbrand/briefs/briefs.json").write_text(json.dumps({"briefs": [
            {"brief": "brief-0901", "product": "widget", "count": N.PER_PRODUCT, "angle": "never-the-tool"}]}))
        self.assertEqual(N.brief_angle("testbrand", "brief-0901", "widget"),
                         {"angle": "never-the-tool", "angle_why": None, "angle_from": "header"})
        # a header with no angle falls back to the register's
        (self.ws / "brands/testbrand/briefs/briefs.json").write_text(json.dumps({"briefs": [
            {"brief": "brief-0901", "product": "widget", "count": N.PER_PRODUCT}]}))
        self.assertEqual(N.brief_header("testbrand", "brief-0901", "widget")["angle"], "gift-idea")

    def test_auto_is_off_by_env_and_never_raises(self):
        import os
        os.environ[AP.OFF_ENV] = "off"
        try:
            self.assertIsNone(AP.auto("testbrand", "brief-0901", "widget", say=lambda *_: None))
        finally:
            del os.environ[AP.OFF_ENV]
        self.assertIsNone(AP.auto("testbrand", "brief-9999", "widget", say=lambda *_: None))


if __name__ == "__main__":
    unittest.main()
