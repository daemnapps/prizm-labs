"""The route lock (the owner, 2026-09-25, the four stations): writing starts only on
a route a person picked. No default "creator", and 1b may suggest a route but
never switch it — "it kept going and wrote for the wrong thing"."""
import importlib.util, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
_s = importlib.util.spec_from_file_location("td_run_lock", HERE / "run.py")
R = importlib.util.module_from_spec(_s); _s.loader.exec_module(R)

KEYS = ["stage0", "stage1", "stage1c", "stage1b", "stage2", "stage3", "stage4b", "stage5"]


def fake_plan(*_a, **_k):
    return [dict(key=k, id=k.replace("stage", ""), name=k, engine="x",
                 version="v1", prompt="") for k in KEYS]


class RouteDeclared(unittest.TestCase):
    def test_flag_wins(self):
        self.assertEqual(R.route_declared({"stages": {}}, "AI"), "ai")

    def test_nothing_picked_is_none(self):
        # the old silent default and 1b's recommendation both count for nothing
        st = {"stages": {}, "production_route": "creator",
              "market_state": {"route_recommended": "ai"}}
        self.assertIsNone(R.route_declared(st))

    def test_picked_on_an_earlier_pass_holds(self):
        st = {"stages": {}, "production_route": "ai", "route_chosen_by_hand": True}
        self.assertEqual(R.route_declared(st), "ai")

    def test_old_run_already_written_keeps_its_route(self):
        st = {"production_route": "creator", "route_chosen_by_hand": False,
              "stages": {"stage3": {"status": "done"}}}
        self.assertEqual(R.route_declared(st), "creator")

    def test_teardown_and_1b_alone_are_not_a_pick(self):
        st = {"production_route": "ai", "route_chosen_by_hand": False,
              "stages": {k: {"status": "done"} for k in
                         ("stage0", "stage1", "stage1c", "stage1b", "stage2")}}
        self.assertIsNone(R.route_declared(st))


class RunHolds(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.ran = []
        self.st = {"label": "t", "slug": "t", "stages": {}, "triage_lane": "ORGANIC"}
        R.open_run = lambda *a, **k: (self.d, self.st)
        R.save = lambda d, st: None
        R.file_to_repo = lambda d: None
        R.say = lambda *a, **k: None
        R.run_stage = lambda d, st, s, extras, redo=False: self.ran.append(s["key"]) or True
        R.C.stages = fake_plan
        R.C.mirror_to_drive = lambda slug: None
        R.C.route_for = lambda lane: dict(skip=[], why="", substitute={})

    def test_no_route_runs_the_teardown_and_holds_writing(self):
        ok = R.run_video(None, "t", "somebrand")
        self.assertTrue(ok)
        self.assertEqual(self.ran, ["stage0", "stage1", "stage1c", "stage2"])
        self.assertEqual(self.st["waiting_for"], "route")
        self.assertNotIn("production_route", self.st)

    def test_a_picked_route_writes(self):
        R.run_video(None, "t", "somebrand", route="ai", stop="5")
        self.assertEqual(self.ran, KEYS)
        self.assertEqual(self.st["production_route"], "ai")
        self.assertTrue(self.st["route_chosen_by_hand"])

    def test_frames_never_run(self):
        # the owner, 2026-09-30: "no more frames, only the brief and swipe file link"
        plan = fake_plan()
        plan.insert(-1, dict(key="stage6", id="6", name="frames", engine="frames",
                             version="v2", prompt=""))
        R.C.stages = lambda *a, **k: [dict(x) for x in plan]
        R.run_video(None, "t", "somebrand", route="creator", stop="5")
        self.assertNotIn("stage6", self.ran)


if __name__ == "__main__":
    unittest.main()
