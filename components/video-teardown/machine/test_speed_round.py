"""The 2026-10-21 speed round (video-system sync W30, W31): research pulled once a run, teardown
stages side by side, the run record safe while they do. Spends nothing."""
import importlib.util, json, os, sys, tempfile, threading, time, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_sp = importlib.util.spec_from_file_location("run", HERE / "run.py")
R = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(R)


class ResearchOnce(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.st = {"brand": "b", "audience": {"_avatar": "a"}, "slug": "x"}
        self.calls = []
        fake = type(sys)("research")
        fake.inputs = lambda st: self.calls.append(1) or {"research": "# Research\n\nrows"}
        p = mock.patch.dict(sys.modules, {"research": fake})
        p.start(); self.addCleanup(p.stop)
        for name in ("say",):
            q = mock.patch.object(R, name, lambda *a, **k: None); q.start(); self.addCleanup(q.stop)

    def test_every_pass_reads_one_pull(self):
        self.assertEqual(R.research_inputs(self.d, self.st)["research"], "# Research\n\nrows")
        R.research_inputs(self.d, self.st)
        R.research_inputs(self.d, self.st)
        self.assertEqual(len(self.calls), 1)
        self.assertTrue((self.d / "research" / "inputs.json").is_file())

    def test_a_new_audience_pulls_again(self):
        R.research_inputs(self.d, self.st)
        R.research_inputs(self.d, dict(self.st, audience={"_avatar": "other"}))
        self.assertEqual(len(self.calls), 2)

    def test_the_background_pull_is_waited_for_and_read(self):
        R.research_prefetch(self.d, self.st)
        R.research_inputs(self.d, self.st)
        self.assertEqual(len(self.calls), 1)

    def test_a_failure_from_another_process_is_pulled_again(self):
        (self.d / "research").mkdir()
        (self.d / "research" / "inputs.json").write_text(json.dumps(
            {"key": R._research_key(self.st), "at": time.time(), "ok": False, "pid": -1, "inputs": {}}))
        R.research_inputs(self.d, self.st)
        self.assertEqual(len(self.calls), 1)


class SaveIsSafe(unittest.TestCase):
    def test_two_threads_changing_and_saving(self):
        d = Path(tempfile.mkdtemp())
        st = {"stages": {}}
        def work(tag):
            for i in range(300):
                st["stages"][f"{tag}{i}"] = {"status": "done", "i": i}
                R.save(d, st)
        ts = [threading.Thread(target=work, args=(t,)) for t in "ab"]
        [t.start() for t in ts]; [t.join() for t in ts]
        R.save(d, st)
        self.assertEqual(len(json.loads((d / "run.json").read_text())["stages"]), 600)


class SideBySide(unittest.TestCase):
    def test_the_partner_runs_beside_and_is_joined(self):
        d = Path(tempfile.mkdtemp())
        st = {"stages": {}, "video": str(d / "v.mp4")}
        plan = [dict(key="stage0", id="0", name="Triage"), dict(key="stage1", id="1", name="Teardown")]
        seen = []
        with mock.patch.object(R, "real_video", lambda p: True), \
                mock.patch.object(R, "say", lambda *a, **k: None), \
                mock.patch.object(R, "run_stage", lambda d, st, s, e, redo=False: seen.append(
                    (s["key"], threading.current_thread().name)) or True):
            side = R._side_start(d, st, plan[0], plan, {}, False, set(), set())
            self.assertEqual(side[0], "stage1")
            self.assertTrue(side[1]())
        self.assertEqual(seen, [("stage1", "stage1-beside-stage0")])

    def test_never_on_a_still_or_a_finished_partner(self):
        d = Path(tempfile.mkdtemp())
        plan = [dict(key="stage0", id="0", name="Triage"), dict(key="stage1", id="1", name="Teardown")]
        with mock.patch.object(R, "real_video", lambda p: False):
            self.assertIsNone(R._side_start(d, {"stages": {}, "video": "x.jpg"}, plan[0], plan, {}, False, set(), set()))
        with mock.patch.object(R, "real_video", lambda p: True):
            st = {"stages": {"stage1": {"status": "done"}}, "video": "v.mp4"}
            self.assertIsNone(R._side_start(d, st, plan[0], plan, {}, False, set(), set()))
            self.assertIsNone(R._side_start(d, {"stages": {}, "video": "v.mp4"}, plan[0], plan, {}, False, {"stage1"}, set()))


class TheLoop(unittest.TestCase):
    """run_video runs every stage once, partners beside their stage, on a real video (W31)."""

    def test_every_stage_once_and_the_partners_beside(self):
        keys = ["stage0", "stage1", "stage1k", "stage1c", "stage1b", "stage2", "stage3"]
        d = Path(tempfile.mkdtemp())
        st = {"label": "t", "slug": "t", "stages": {}, "triage_lane": "ORGANIC", "video": str(d / "v.mp4")}
        ran = []
        plan = lambda *a, **k: [dict(key=k_, id=k_.replace("stage", ""), name=k_, engine="x", version="v1",
                                     prompt="") for k_ in keys]
        with mock.patch.dict(os.environ, {"VT_WRITING": "v1"}),                 mock.patch.object(R, "open_run", lambda *a, **k: (d, st)),                 mock.patch.object(R, "save", lambda d, st: None),                 mock.patch.object(R, "file_to_repo", lambda d: None),                 mock.patch.object(R, "say", lambda *a, **k: None),                 mock.patch.object(R, "real_video", lambda p: True),                 mock.patch.object(R, "research_prefetch", lambda d, st: None),                 mock.patch.object(R, "run_stage", lambda d, st, s, e, redo=False: ran.append(
                    (s["key"], threading.current_thread().name)) or True),                 mock.patch.object(R.C, "stages", plan),                 mock.patch.object(R.C, "mirror_to_drive", lambda slug: None),                 mock.patch.object(R.C, "route_for", lambda lane: dict(skip=[], why="", substitute={})):
            R.run_video(None, "t", "somebrand", route="creator", stop="3")
        self.assertEqual(sorted(k for k, _ in ran), sorted(keys))
        beside = {k for k, th in ran if "-beside-" in th}
        self.assertEqual(beside, {"stage1"})
        # 2 (spec) goes stale when 1b (audience) finishes after it starts: never beside it (yai-turmeric-watch)
        self.assertNotIn("stage2", beside)
        # 1c (doctrine) reads 1k (culture): never beside it, or 1k marks it stale mid-run (yai-scrub-ads-1021)
        self.assertNotIn("stage1c", beside)


if __name__ == "__main__":
    unittest.main()
