#!/usr/bin/env python3
"""SI-56 (teardown working home): the working folder is runs/video-teardown/_work/,
named once (workdir.py); the board serves it; nothing in the machine builds the
old folder any more.

    /usr/bin/python3 tools/video-teardown/machine/test_si56_workdir.py

Stdlib only, no key, no network. Every tree is a temp folder; the real runs/
and the old in-machine folder are never touched.
"""
import contextlib, io, os, sys, tempfile, types, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import workdir                                              # noqa: E402
import chain                                                # noqa: E402
import file_run                                             # noqa: E402
import serve                                                # noqa: E402

OLD_DIR = "machine" + "/runs"        # split so this file is not a hit for its own search


def _ws(t):
    ws = Path(t).resolve()
    (ws / "brands").mkdir()
    (ws / "components").mkdir()
    return ws


class WhereItLives(unittest.TestCase):
    def test_root_system_run_dir_follow_the_workspace_and_create_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            ws = _ws(t)
            with mock.patch.dict(os.environ, {"AI_WORKSPACE": str(ws)}):
                self.assertEqual(workdir.workspace(), ws)
                self.assertEqual(workdir.root(), ws / "runs" / "video-teardown" / "_work")
                self.assertEqual(workdir.system(), ws / "runs" / "video-teardown" / "_system")
                self.assertEqual(workdir.run_dir("x"), workdir.root() / "x")
            self.assertFalse((ws / "runs").exists())
            # an explicit workspace wins over the variable
            other = ws / "elsewhere"
            self.assertEqual(workdir.root(other), other / "runs" / "video-teardown" / "_work")
            self.assertEqual(workdir.run_dir("y", other), other / "runs" / "video-teardown" / "_work" / "y")
            self.assertFalse(other.exists())

    def test_a_variable_without_brands_is_ignored(self):
        with tempfile.TemporaryDirectory() as t:
            with mock.patch.dict(os.environ, {"AI_WORKSPACE": t}):
                self.assertNotEqual(workdir.workspace(), Path(t).resolve())

    def test_legacy_entries(self):
        with tempfile.TemporaryDirectory() as t:
            old = Path(t) / "old"
            with mock.patch.object(workdir, "legacy", return_value=old):
                self.assertEqual(workdir.legacy_entries(), [])
                old.mkdir()
                (old / "b").mkdir()
                (old / "a.txt").write_text("x")
                self.assertEqual(workdir.legacy_entries(), [old / "a.txt", old / "b"])
        self.assertEqual(workdir.legacy(), HERE / "runs")


class RunsRoot(unittest.TestCase):
    def test_runs_root_is_the_working_folder_and_nags_once(self):
        with tempfile.TemporaryDirectory() as t:
            ws = Path(t).resolve()
            empty = ws / "no-old-folder"
            with mock.patch.object(chain, "WS", ws), \
                    mock.patch.object(chain.workdir, "legacy", return_value=empty):
                chain._LEGACY_NAGGED = False
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    d = chain.runs_root()
                self.assertEqual(d, workdir.root(ws))
                self.assertTrue(d.is_dir())
                self.assertEqual(err.getvalue(), "")          # nothing old: silent

            old = ws / "old"
            old.mkdir()
            (old / "left-behind.txt").write_text("x")
            with mock.patch.object(chain, "WS", ws), \
                    mock.patch.object(chain.workdir, "legacy", return_value=old):
                chain._LEGACY_NAGGED = False
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    a = chain.runs_root()
                    b = chain.runs_root()
                self.assertEqual(a, b)
                self.assertEqual(a, workdir.root(ws))          # never the old folder
                said = err.getvalue()
                self.assertEqual(said.count("move_runs.py --go"), 1, said)
                self.assertIn(OLD_DIR, said)
                self.assertEqual(len(said.strip().splitlines()), 1, said)
            chain._LEGACY_NAGGED = False


class FilingGuard(unittest.TestCase):
    def test_the_guard_reads_a_fixed_path(self):
        src = (HERE / "file_run.py").read_text(encoding="utf-8")
        self.assertIn("workdir.root(C.WS)", src)
        self.assertNotIn('(MACHINE / "runs")', src)

    def test_a_temp_run_is_never_filed_and_a_real_one_is(self):
        with tempfile.TemporaryDirectory() as t:
            ws = Path(t).resolve()
            scratch = ws / "scratch" / "r1"
            scratch.mkdir(parents=True)
            calls = []

            def fake_file_run(run_dir, repo=None):
                calls.append(Path(run_dir))
                return ws / "runs" / "video-teardown" / "b" / "r1", ["x.md"], []

            stub_index = types.ModuleType("brief_index")
            stub_index.build = lambda *a, **k: None
            env = {k: v for k, v in os.environ.items() if k != file_run.OFF_ENV}
            with mock.patch.dict(os.environ, env, clear=True), \
                    mock.patch.dict(sys.modules, {"brief_index": stub_index}), \
                    mock.patch.object(file_run, "file_run", fake_file_run), \
                    mock.patch.object(file_run.C, "WS", ws), \
                    mock.patch.object(file_run.C, "runs_root", lambda: scratch.parent):
                # fires: a run outside the fixed working folder (even when
                # runs_root is patched to point at it) is never filed
                self.assertIsNone(file_run.file_after_run(scratch))
                self.assertEqual(calls, [])
                # releases: a run in the working folder is filed
                real = workdir.run_dir("r1", ws)
                real.mkdir(parents=True)
                note = file_run.file_after_run(real)
                self.assertIsNotNone(note)
                self.assertEqual(calls, [real])


class BoardServer(unittest.TestCase):
    def setUp(self):
        self.h = serve.NoCache.__new__(serve.NoCache)
        self.h.directory = str(serve.HERE)

    def test_runs_urls_map_to_the_working_folder(self):
        self.assertEqual(self.h.translate_path("/runs/s1/x.mp4"),
                         str(workdir.root() / "s1" / "x.mp4"))
        self.assertEqual(self.h.translate_path("/runs/s1/x.mp4?t=3#f"),
                         str(workdir.root() / "s1" / "x.mp4"))
        self.assertEqual(self.h.translate_path("/runs/s%201/x.mp4"),
                         str(workdir.root() / "s 1" / "x.mp4"))

    def test_climbing_out_goes_nowhere(self):
        for url in ("/runs/../chain.py", "/runs/../../machine/chain.py", "/runs/%2e%2e/chain.py"):
            p = self.h.translate_path(url)
            self.assertFalse(Path(p).exists(), (url, p))
            self.assertFalse(p.startswith(str(serve.HERE) + os.sep), (url, p))

    def test_everything_else_is_the_machine_folder(self):
        self.assertEqual(self.h.translate_path("/board.html"), str(serve.HERE / "board.html"))


class NothingBuildsTheOldFolder(unittest.TestCase):
    BANNED = ('HERE / "runs"', 'MACHINE / "runs"', 'parent / "runs"', "C.MACHINE / m", OLD_DIR)
    SCRIPTS = ("general_run.sh", "overnight.sh", "rerun-all.sh", "resume.sh", "run-remaining.sh")

    def test_machine_python(self):
        skip = {"workdir.py", "move_runs.py"}
        hits = []
        for f in sorted(HERE.glob("*.py")):
            if f.name in skip or f.name.startswith("test_"):
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            hits += [f"{f.name}: {b}" for b in self.BANNED if b in text]
        self.assertEqual(hits, [])

    def test_shell_scripts_ask_workdir(self):
        for name in self.SCRIPTS:
            text = (HERE / name).read_text(encoding="utf-8")
            self.assertNotIn("runs/", text, name)
            self.assertIn("RUNS=\"$(python3 -c 'import workdir", text, name)

    def test_creators_json_lives_in_system(self):
        for name in ("tracker.py", "sourcing.py"):
            self.assertIn("workdir.system()", (HERE / name).read_text(encoding="utf-8"), name)
        self.assertIn("workdir.system(", (HERE / "simplify.py").read_text(encoding="utf-8"))
        self.assertTrue((REPO / "runs" / "video-teardown" / "_system" / "creators.json").is_file())
        self.assertFalse((HERE / "creators.json").exists())

    def test_the_ignore_file(self):
        lines = (REPO / "runs" / "video-teardown" / ".gitignore").read_text().splitlines()
        self.assertEqual(lines, ["_work/", "_system/briefs.html", "_system/prompts.html"])

    def test_the_mirror_path_did_not_move(self):
        self.assertTrue("/".join(chain.RUNS_SUBPATH).endswith("video-teardown/" + OLD_DIR))


if __name__ == "__main__":
    unittest.main()
