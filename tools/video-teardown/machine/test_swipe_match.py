"""Swipe match (the owner, 2026-09-24): production refuses a brief that was not
checked against its swipe, was held, or was edited after the check."""
import importlib.util, json, os, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location("swipe_match", HERE / "swipe_match.py")
SM = importlib.util.module_from_spec(_s); _s.loader.exec_module(SM)

BRIEF = 'intro\n```json\n' + json.dumps({"cast": [{"id": "A", "bank_id": "NEW"}], "scenes": [
    {"id": "S1", "looks": {"A": "NEW"}, "first_frame": {"camera": "handheld selfie at arm's length"}},
    {"id": "S2", "first_frame": {"camera": "square on, chest height"}}]}) + '\n```\n'
SHOTS = {"shots": [
    {"swipe": "0:00", "swipe_has": "outside · creator · handheld selfie", "brief_scenes": ["S1"], "keeps": True, "changed": []},
    {"swipe": "0:05", "swipe_has": "office · doctor · selfie", "brief_scenes": ["S2"], "keeps": True, "changed": []}],
    "added": [], "verdict": "KEEPS"}


class SwipeMatch(unittest.TestCase):
    def setUp(self):
        os.environ.pop("DAEMN_STRUCTURE_APPROVALS", None)
        self.d = Path(tempfile.mkdtemp()); (self.d / "stages").mkdir()
        (self.d / "stages" / "1-teardown.md").write_text("### 1. record")
        (self.d / "stages" / "5-brief.md").write_text(BRIEF)
        self.verdict = json.loads(json.dumps(SHOTS))
        SM.ask_judge = lambda t, b, v=None: (json.loads(json.dumps(self.verdict)), "swipe-match-v1-damon.md")

    def brief(self):
        return (self.d / "stages" / "5-brief.md").read_text()

    def test_never_checked_is_refused(self):
        self.assertIsNone(SM.stamp_of(BRIEF))

    def test_selfie_turned_composed_is_held_by_the_machine_not_the_judge(self):
        passed, open_ = SM.check(self.d)
        self.assertFalse(passed)
        self.assertEqual([f["brief_scenes"] for f in open_], [["S2"]])
        self.assertEqual(SM.stamp_of(self.brief()), "HELD")

    def test_approval_by_number_passes_the_same_findings(self):
        SM.check(self.d)
        SM.ask_judge = lambda t, b, v=None: self.fail("the judge must not be asked again")
        os.environ["DAEMN_STRUCTURE_APPROVALS"] = "M1"
        passed, _ = SM.check(self.d)
        self.assertTrue(passed)
        self.assertEqual(SM.stamp_of(self.brief()), "PASSED")

    def test_binding_the_cast_keeps_the_pass_but_an_edit_goes_stale(self):
        os.environ["DAEMN_STRUCTURE_APPROVALS"] = "all"
        SM.check(self.d)
        bound = self.brief().replace('"bank_id": "NEW"', '"bank_id": "someone"').replace('{"A": "NEW"}', '{"A": "look-1"}')
        self.assertEqual(SM.stamp_of(bound), "PASSED")
        edited = self.brief().replace("chest height", "waist height")
        self.assertEqual(SM.stamp_of(edited), "STALE")

    def test_damon_must_read_the_brief_and_an_edit_needs_his_read_again(self):
        os.environ["DAEMN_STRUCTURE_APPROVALS"] = "all"
        SM.check(self.d)
        self.assertIsNone(SM.read_of(self.brief()))
        SM.approve_read(self.d / "stages" / "5-brief.md")
        self.assertEqual(SM.read_of(self.brief()), "APPROVED")
        self.assertEqual(SM.stamp_of(self.brief()), "PASSED")
        SM.check(self.d)  # a re-check keeps his read on the same brief
        self.assertEqual(SM.read_of(self.brief()), "APPROVED")
        self.assertEqual(SM.read_of(self.brief().replace("chest height", "waist height")), "STALE")

    def test_an_expansion_beat_inside_the_swipes_world_passes_one_outside_is_held(self):
        self.verdict["shots"][1]["swipe_has"] = "office · doctor · close-up"
        self.verdict["added"] = [{"brief_scene": "S3", "what": "she holds the tube, selfie outside", "place": "the sidewalk", "in_world": True}]
        passed, _ = SM.check(self.d)
        self.assertTrue(passed)
        self.verdict["added"].append({"brief_scene": "S4", "what": "a kitchen", "place": "new: a kitchen", "in_world": False})
        (self.d / "swipe-match.json").unlink()
        passed, open_ = SM.check(self.d)
        self.assertFalse(passed)
        self.assertEqual(open_[0]["brief_scenes"], ["S4"])

    def tearDown(self):
        os.environ.pop("DAEMN_STRUCTURE_APPROVALS", None)


if __name__ == "__main__":
    unittest.main()
