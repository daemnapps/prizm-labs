#!/usr/bin/env python3
"""SI-56 (teardown working home): every reader outside the machine is repointed
in the same commit — finished text through run_kit.index (the filed shelves),
live runs through video-teardown's workdir.py, loaded by file.

    /usr/bin/python3 tools/video-teardown/machine/test_si56_readers.py

Stdlib only, no key, no network. The behaviour checks build a temp runs/ tree;
the real runs/ is never read for an answer and never written.
"""
import contextlib, importlib.util, io, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import workdir                                              # noqa: E402
import culture_json as CJ                                   # noqa: E402

OUTSIDE = [
    "tools/copywriter/library/build_library.py",
    "tools/copywriter/machine/batch_status.py",
    "tools/copywriter/machine/ads_to_copy.sh",
    "components/swipe-organic/profile.py",
    "components/swipe-organic/desk.py",
    "components/swipe-organic/briefs.py",
    "components/swipe-paid/profile.py",
    "components/meta-upload/winner_briefs_page.py",
    "components/research-gatherer/research_gatherer/culture_map.py",
    "components/ad-variations/machine/proven_to_format.py",
    "tools/video-production/machine/pipeline.py",
    "tools/video-production/machine/elements_check.py",
    "platform/workers/mini-worker/teardown_run.py",
    "tools/video-teardown/machine/briefs_page.py",
    "tools/video-teardown/machine/culture_json.py",
]
LOADS_WORKDIR = [
    "tools/copywriter/machine/batch_status.py",
    "components/swipe-organic/desk.py",
    "components/swipe-organic/briefs.py",
    "components/ad-variations/machine/proven_to_format.py",
    "tools/video-production/machine/pipeline.py",
    "tools/video-production/machine/elements_check.py",
    "platform/workers/mini-worker/teardown_run.py",
    "components/meta-upload/winner_briefs_page.py",
    "components/swipe-organic/profile.py",
    "components/swipe-paid/profile.py",
]
READS_INDEX = [
    "tools/copywriter/library/build_library.py",
    "components/swipe-organic/profile.py",
    "components/swipe-paid/profile.py",
    "components/meta-upload/winner_briefs_page.py",
]
# split so this file is not a hit for its own search
BANNED = ("video-teardown/" + "machine/runs", '"machine" / ' + '"runs"', '"machine", ' + '"runs"',
          'TD / ' + '"runs"', 'TEARDOWN / ' + '"runs"')

ROW = "| 0:01 | v | ON SCREEN | A: hello there |\n"


def _text(rel):
    return (REPO / rel).read_text(encoding="utf-8")


class Repointed(unittest.TestCase):
    def test_no_reader_builds_the_old_folder(self):
        hits = [f"{rel}: {b}" for rel in OUTSIDE for b in BANNED if b in _text(rel)]
        self.assertEqual(hits, [])

    def test_live_readers_load_workdir_by_file(self):
        for rel in LOADS_WORKDIR:
            text = _text(rel)
            self.assertIn("workdir.py", text, rel)
            self.assertIn("spec_from_file_location", text, rel)

    def test_finished_text_readers_use_the_index(self):
        for rel in READS_INDEX:
            self.assertIn("run_kit", _text(rel), rel)


def _tree(t):
    runs = Path(t) / "runs"
    td = runs / "video-teardown" / "zz-brand" / "zz-run" / "stages"
    td.mkdir(parents=True)
    (td / "1-teardown.md").write_text(ROW)
    vw = runs / "video-writing" / "zz-brand" / "zz-run" / "stages"
    vw.mkdir(parents=True)
    (vw / "1b-audience.md").write_text("AVATAR: zz-avatar\n")
    live = runs / "video-teardown" / "_work" / "zz-live" / "stages"
    live.mkdir(parents=True)
    (live / "1-teardown.md").write_text(ROW)
    return runs


def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(mod)
    return mod


class CopyLibrary(unittest.TestCase):
    def test_teardowns_come_from_the_filed_shelf_never_the_working_folder(self):
        mod = _load("tools/copywriter/library/build_library.py", "_si56_copy_library")
        with tempfile.TemporaryDirectory() as t:
            runs = _tree(t)
            mod.rows[:] = []
            with contextlib.redirect_stdout(io.StringIO()):
                mod.teardowns(runs_root=runs)
            got = list(mod.rows)
        self.assertTrue(got)
        self.assertTrue(any(r["tags"]["run"] == "zz-run" and r["audience"].get("avatar") == "zz-avatar"
                            for r in got), got)
        self.assertFalse(any(r["tags"]["run"] == "zz-live" for r in got), got)
        for r in got:
            self.assertTrue(r["path"].startswith("runs/video-teardown/zz-brand/zz-run/"), r["path"])

    def test_no_filed_runs_is_zero_not_a_crash(self):
        mod = _load("tools/copywriter/library/build_library.py", "_si56_copy_library_empty")
        with tempfile.TemporaryDirectory() as t:
            mod.rows[:] = []
            with contextlib.redirect_stdout(io.StringIO()):
                mod.teardowns(runs_root=Path(t) / "runs")
            self.assertEqual(mod.rows, [])


class CultureReads(unittest.TestCase):
    def test_two_roots_and_work_is_not_a_brand(self):
        rg = str(REPO / "components" / "research-gatherer")
        if rg not in sys.path:
            sys.path.append(rg)
        from research_gatherer import culture_map as CM
        self.assertEqual(CM.RUN_ROOTS, (("runs", "video-teardown"), ("runs", "video-writing")))
        with tempfile.TemporaryDirectory() as t:
            runs = Path(t) / "runs"
            self.assertIsNone(CJ._brand(runs / "video-teardown" / "_work" / "x", {}))
            self.assertEqual(CJ._brand(runs / "video-teardown" / "zz-brand" / "x", {}), "zz-brand")


class MiniWorker(unittest.TestCase):
    def test_the_job_done_check_reads_the_working_folder(self):
        mw = str(REPO / "platform" / "workers" / "mini-worker")
        if mw not in sys.path:
            sys.path.insert(0, mw)
        import teardown_run
        self.assertEqual(teardown_run.RUNS_ROOT,
                         teardown_run.WS / "runs" / "video-teardown" / "_work")
        self.assertEqual(teardown_run.RUNS_ROOT, workdir.root(teardown_run.WS))


if __name__ == "__main__":
    unittest.main()
