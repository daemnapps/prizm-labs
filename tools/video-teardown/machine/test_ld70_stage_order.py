"""LD-70 (teardown stage order), 2026-10-21: a teardown stage that ran beside another and was marked stale by it
is redone before anything after it starts, and a stage never runs beside one whose output it reads.
Found by vt-real-brand-b-2 ("2 Spec STOPPED — 'stage stage1c has not run yet'"). Spends nothing."""
import importlib.util, os, sys, tempfile, threading, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_sp = importlib.util.spec_from_file_location("run", HERE / "run.py")
R = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(R)

KEYS = ["stage0", "stage1", "stage1k", "stage1c", "stage1b", "stage2", "stage3"]
WAIT = 10   # seconds: an Event that never fires fails the test instead of hanging it


class PartnerOrder(unittest.TestCase):
    """run_video with stage1 beside stage0, the finishing order forced by Events."""

    def run_loop(self, partner_first):
        d = Path(tempfile.mkdtemp())
        st = {"label": "t", "slug": "t", "stages": {}, "triage_lane": "ORGANIC", "video": str(d / "v.mp4")}
        ran, refused = [], []
        partner_done, left_done = threading.Event(), threading.Event()
        lock = threading.Lock()
        plan = lambda *a, **k: [dict(key=k_, id=k_.replace("stage", ""), name=k_, engine="x", version="v1",
                                     prompt="", vars={}) for k_ in KEYS]

        def fake_run_stage(d, st, s, e, redo=False):
            key = s["key"]
            with lock:
                ran.append((key, threading.current_thread().name))
            # what outputs_so_far hands on: a reader of an earlier stage that is not "done" stops (chain.py:1198);
            # stage1, the partner, reads nothing stage0 writes
            order = st.get("_order") or []
            for before in order[:order.index(key)] if key != "stage1" else []:
                if (st["stages"].get(before) or {}).get("status") != "done":
                    refused.append((key, before))
                    return False
            if key == "stage1" and not partner_first and not left_done.wait(WAIT):
                raise AssertionError("stage0 never finished")
            if key == "stage0" and partner_first and not partner_done.wait(WAIT):
                raise AssertionError("stage1 never finished")
            with lock:
                rec = st["stages"].get(key, {})
                st["stages"][key] = {"status": "done", "name": s["name"], "_hash": "new"}
                # a copy of run_stage's invalidation (run.py, "REDOING A STAGE REDOES WHAT DEPENDS ON IT")
                if rec.get("_hash") != "new" and key in order:
                    for later in order[order.index(key) + 1:]:
                        r2 = st["stages"].get(later)
                        if r2 and r2.get("status") == "done":
                            r2["status"] = "stale"; r2["stale_because"] = f"{key} changed"
            if key == "stage1":
                partner_done.set()
            if key == "stage0":
                left_done.set()
            return True

        with mock.patch.dict(os.environ, {"VT_WRITING": "v1"}), \
                mock.patch.object(R, "open_run", lambda *a, **k: (d, st)), \
                mock.patch.object(R, "save", lambda d, st: None), \
                mock.patch.object(R, "file_to_repo", lambda d: None), \
                mock.patch.object(R, "say", lambda *a, **k: None), \
                mock.patch.object(R, "real_video", lambda p: True), \
                mock.patch.object(R, "research_prefetch", lambda d, st: None), \
                mock.patch.object(R, "run_stage", fake_run_stage), \
                mock.patch.object(R.C, "stages", plan), \
                mock.patch.object(R.C, "mirror_to_drive", lambda slug: None), \
                mock.patch.object(R.C, "route_for", lambda lane: dict(skip=[], why="", substitute={})):
            R.run_video(None, "t", "brand-a", route="creator", stop="3")
        return ran, refused, st

    def test_a_partner_that_finished_first_is_redone_before_the_next_stage(self):
        ran, refused, st = self.run_loop(partner_first=True)
        self.assertEqual(refused, [])
        ones = [i for i, (k, _) in enumerate(ran) if k == "stage1"]
        self.assertEqual(len(ones), 2, ran)
        self.assertIn("-beside-", ran[ones[0]][1])
        self.assertEqual(ran[ones[1]][1], "MainThread")
        self.assertLess(ones[1], [k for k, _ in ran].index("stage1k"))
        self.assertEqual(sorted({k for k, _ in ran}), sorted(KEYS))   # every stage after it is reached
        self.assertTrue(all(st["stages"][k]["status"] == "done" for k in KEYS))

    def test_a_partner_that_finished_last_runs_once(self):
        ran, refused, st = self.run_loop(partner_first=False)
        self.assertEqual(refused, [])
        self.assertEqual([k for k, _ in ran].count("stage1"), 1)
        self.assertEqual(sorted(k for k, _ in ran), sorted(KEYS))
        self.assertTrue(all(st["stages"][k]["status"] == "done" for k in KEYS))


class NeverBesideWhatItReads(unittest.TestCase):
    def side(self, plan):
        d = Path(tempfile.mkdtemp())
        st = {"stages": {}, "video": str(d / "v.mp4")}
        with mock.patch.object(R, "real_video", lambda p: True), \
                mock.patch.object(R, "say", lambda *a, **k: None), \
                mock.patch.object(R, "run_stage", lambda d, st, s, e, redo=False: True), \
                mock.patch.object(R, "SIDE_BY_SIDE", {"stage0": "stage1"}):
            side = R._side_start(d, st, plan[0], plan, {}, False, set(), set())
            if side:
                side[1]()
        return side

    def test_a_right_side_that_reads_the_left_is_refused(self):
        for src in ("@stage0", "@stage0*", "@stage0#pick"):
            plan = [dict(key="stage0", id="0", name="Triage", vars={}),
                    dict(key="stage1", id="1", name="Teardown", vars={"x": src})]
            self.assertIsNone(self.side(plan), src)

    def test_a_read_of_another_stage_does_not_refuse(self):
        plan = [dict(key="stage0", id="0", name="Triage", vars={}),
                dict(key="stage1", id="1", name="Teardown", vars={"x": "@stage00", "y": "=creator"})]
        self.assertEqual(self.side(plan)[0], "stage1")

    def test_the_real_config_pair_still_runs_beside(self):
        # the plan from the real chain config (chain.stages, machine-local prompts and config; no brand folder read)
        plan = [s for s in R.C.stages("brand-a", "", "creator", "ORGANIC") if s["key"] in ("stage0", "stage1")]
        self.assertEqual([s["key"] for s in plan], ["stage0", "stage1"])
        self.assertFalse(any(str(v).startswith("@stage0") for v in plan[1]["vars"].values()))
        self.assertEqual(self.side(plan)[0], "stage1")


if __name__ == "__main__":
    unittest.main()
