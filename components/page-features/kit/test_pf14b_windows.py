#!/usr/bin/env python3
"""PF-14b (Windows page server): kit/server.py's Windows form, tested on the mini with the platform forced to win32 —
the Task Scheduler task it makes and ends, its folder under LOCALAPPDATA, supervise's restart loop, and the msvcrt lock.

    python3 components/page-features/kit/test_pf14b_windows.py

schtasks goes to a recorder that answers like schtasks; git runs for real on temp folders (PF-14 (page server)'s
fixture, imported from test_pf14_page_server). Nothing here has run on Windows: the first real `on` there is the
acceptance check.
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import server  # noqa: E402
import test_pf14_page_server as pf14  # noqa: E402  the fixture's helpers only; its tests run in their own file

PERSON, EMAIL = pf14.PERSON, pf14.EMAIL
QUERY = ["schtasks", "/Query", "/TN", "UprightPageServer", "/FO", "LIST"]
END = ["schtasks", "/End", "/TN", "UprightPageServer"]
DELETE = ["schtasks", "/Delete", "/TN", "UprightPageServer", "/F"]
RUN = ["schtasks", "/Run", "/TN", "UprightPageServer"]
LIST = ("\r\nFolder: \\\r\nHostName:      creator-PC\r\nTaskName:      \\UprightPageServer\r\n"
        "Next Run Time: N/A\r\nStatus:        %s\r\nLogon Mode:    Interactive only\r\n")
NO_TASK = "ERROR: The system cannot find the file specified.\r\n"


class Schtasks(object):
    """Records every argv; answers schtasks like it would, runs git for real."""

    def __init__(self, create=(0, "SUCCESS: The scheduled task \"UprightPageServer\" has successfully been created.")):
        self.calls, self.installed, self.running, self.create = [], False, False, create

    def __call__(self, argv):
        self.calls.append(list(argv))
        if argv[0] == "schtasks":
            verb = argv[1]
            if verb == "/Query":
                return (0, LIST % ("Running" if self.running else "Ready")) if self.installed else (1, NO_TASK)
            if verb == "/Create":
                self.installed = self.installed or self.create[0] == 0
                return self.create
            if verb == "/Run":
                self.running = self.installed
                return (0, "SUCCESS: Attempted to run") if self.installed else (1, NO_TASK)
            if verb == "/End":
                was, self.running = self.running, False
                return (0, "SUCCESS: terminated") if was else (1, NO_TASK if not self.installed else
                                                              "ERROR: The task is not running.")
            if verb == "/Delete":
                was, self.installed, self.running = self.installed, False, False
                return (0, "SUCCESS: deleted") if was else (1, NO_TASK)
        if argv[0] == "git":
            return server.run_cmd(argv)
        raise AssertionError("unexpected command %r" % (argv,))

    def tasks(self):
        return [c for c in self.calls if c[0] == "schtasks"]


class WindowsPageServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pf14b-")).resolve()
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.local = self.tmp / "AppData-Local"
        env = {"HOME": str(self.home), "LOCALAPPDATA": str(self.local), "GIT_CONFIG_NOSYSTEM": "1",
               "GIT_AUTHOR_NAME": "Tess", "GIT_AUTHOR_EMAIL": EMAIL, "GIT_COMMITTER_NAME": "Tess",
               "GIT_COMMITTER_EMAIL": EMAIL}
        self.env = mock.patch.dict(os.environ, env)
        self.env.start()
        os.environ.pop(server.SELF_ENV, None)
        os.environ.pop("AI_WORKSPACE", None)
        origin, seed = self.tmp / "origin.git", self.tmp / "seed"
        pf14.git("init", "-q", "--bare", str(origin))
        pf14.git("symbolic-ref", "HEAD", "refs/heads/main", cwd=str(origin))
        pf14.git("init", "-q", str(seed))
        pf14.git("checkout", "-q", "-b", "main", cwd=str(seed))
        for rel, text in pf14.FILES.items():
            pf14.write(seed, rel, text)
        pf14.git("add", "-A", cwd=str(seed))
        pf14.git("commit", "-q", "-m", "seed", cwd=str(seed))
        pf14.git("remote", "add", "origin", str(origin), cwd=str(seed))
        pf14.git("push", "-q", "origin", "main", cwd=str(seed))
        self.clone = self.tmp / "clone"
        pf14.git("clone", "-q", str(origin), str(self.clone))
        pf14.git("config", "user.email", EMAIL, cwd=str(self.clone))
        self.rec = Schtasks()
        self.state = self.local / "upright-page-server" / PERSON
        self.copy = self.state / "repo"

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    def main(self, *argv, **kw):
        out = io.StringIO()
        kw.setdefault("wait", lambda port, person: True)
        kw.setdefault("platform", "win32")
        with contextlib.redirect_stdout(out):
            code = server.main(list(argv), repo=self.clone, runner=kw.pop("runner", self.rec), **kw)
        return code, out.getvalue()

    def create_argv(self):
        return ["schtasks", "/Create", "/SC", "ONLOGON", "/TN", "UprightPageServer", "/TR",
                '"%s" "%s" supervise' % (sys.executable, self.copy / server.SELF), "/RL", "LIMITED", "/F"]

    # ------------------------------------------------------------------ (a) on: /Create, then /Run
    def test_a_on_creates_the_logon_task_with_quoted_paths_then_runs_it(self):
        opened = []
        with mock.patch.object(server.os, "startfile", opened.append, create=True):
            code, out = self.main("on")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.rec.tasks(), [QUERY, self.create_argv(), RUN])
        self.assertTrue((self.copy / ".git").is_file(), "the private copy is a worktree under LOCALAPPDATA")
        cfg = json.loads((self.state / "config.json").read_text())
        self.assertEqual((cfg["person"], cfg["repo"]), (PERSON, str(self.clone)))
        url = "http://127.0.0.1:%d/" % cfg["port"]
        self.assertEqual(opened, [url], "os.startfile opens the index")
        self.assertIn("on: tess's pages at %s" % url, out)
        self.assertFalse((self.home / "Library").exists(), "no LaunchAgent, no ~/Library/Caches on Windows")
        with open(str(self.state / "config.json"), "rb") as fh:
            self.assertNotIn(b"\r\n", fh.read(), "text files are written with \\n")
        code, out = self.main("on", "--no-open")
        self.assertEqual(code, 0, out)
        self.assertIn("already on", out)
        self.assertEqual([c for c in self.rec.tasks() if c[1] == "/Create"], [self.create_argv()], "never twice")

    def test_a_on_says_so_when_task_scheduler_refuses(self):
        self.rec.create = (1, "ERROR: Access is denied.\r\n")
        code, out = self.main("on", "--no-open")
        self.assertEqual(code, 1, out)
        self.assertIn("failed: schtasks would not take the background task: ERROR: Access is denied.", out)
        self.assertNotIn(RUN, self.rec.tasks())

    # ------------------------------------------------------------------ (b) off and remove
    def test_b_off_ends_and_deletes_the_task_and_keeps_the_copy(self):
        self.main("on", "--no-open")
        before = len(self.rec.calls)
        code, out = self.main("off")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.rec.calls[before:], [END, DELETE], "/End, /Delete, nothing else")
        self.assertTrue((self.state / "stop").is_file(), "a supervise /End leaves alive ends itself")
        self.assertTrue((self.copy / ".git").is_file(), "off keeps the private copy")
        self.assertIn("will not start at login", out)
        code, out = self.main("on", "--no-open")
        self.assertEqual(code, 0, out)
        self.assertFalse((self.state / "stop").exists(), "on clears the stop file before /Run")
        before = len(self.rec.calls)
        code, out = self.main("restart", "--no-open")
        self.assertEqual(code, 0, out)
        self.assertEqual([c[1] for c in self.rec.tasks()[-5:]], ["/End", "/Delete", "/Query", "/Create", "/Run"])

    def test_b_off_with_no_task_is_still_off(self):
        code, out = self.main("off")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.rec.tasks(), [END, QUERY, DELETE, QUERY])

    def test_b_off_from_its_own_page_is_refused(self):
        self.main("on", "--no-open")
        before = len(self.rec.calls)
        with mock.patch.dict(os.environ, {server.SELF_ENV: "1"}):
            code, out = self.main("off")
        self.assertEqual(code, 2, out)
        self.assertEqual(self.rec.calls[before:], [])

    def test_b_remove_ends_deletes_removes_the_worktree_and_the_folder(self):
        self.main("on", "--no-open")
        other = self.state.parent / "other-person"
        other.mkdir()
        (other / "keep.txt").write_text("keep")
        before = len(self.rec.calls)
        code, out = self.main("remove")
        self.assertEqual(code, 0, out)
        calls = self.rec.calls[before:]
        self.assertEqual([c for c in calls if c[0] == "schtasks"], [END, DELETE])
        self.assertIn(["git", "-C", str(self.clone), "worktree", "remove", "--force", str(self.copy)], calls)
        self.assertLess(calls.index(DELETE), calls.index(["git", "-C", str(self.clone), "worktree", "remove",
                                                           "--force", str(self.copy)]))
        self.assertFalse(self.state.exists())
        self.assertNotIn(str(self.copy), pf14.git("worktree", "list", "--porcelain", cwd=str(self.clone)))
        self.assertEqual((other / "keep.txt").read_text(), "keep", "its own folder, nothing else")

    # ------------------------------------------------------------------ (c) status from /Query /FO LIST
    def test_c_status_reads_the_query_list(self):
        for said, out, loaded, installed in (("Running", LIST % "Running", True, True),
                                             ("Ready", LIST % "Ready", False, True),
                                             (None, NO_TASK, False, False)):
            agent = server.WinAgent(runner=lambda argv, o=out, i=installed: (0 if i else 1, o))
            self.assertEqual(agent.status(), {"loaded": loaded, "pid": None, "installed": installed, "said": said})
        self.assertEqual(server.task_status(LIST % "Running"), "Running")
        self.main("on", "--no-open")
        self.rec.running = False
        code, out = self.main("status")
        self.assertEqual(code, 0, out)
        self.assertIn("page server: off (port", out, "a task that is Ready, not Running, is off")
        self.assertEqual(self.rec.tasks()[-1], QUERY)

    # ------------------------------------------------------------------ (d) supervise
    def fake(self, lives):
        """(spawn, sleep, clock, spawned): children that live lives[i] seconds each (None = until stopped)."""
        t, spawned = [0.0], []

        class Child(object):
            def __init__(self, life):
                self.life, self.born, self.returncode, self.stdin_closed = life, t[0], None, False
                self.stdin = self

            def poll(self):
                if self.returncode is None and self.life is not None and t[0] - self.born >= self.life:
                    self.returncode = 1
                return self.returncode

            def close(self):
                self.stdin_closed = True
                self.returncode = 0

            def wait(self, timeout=None):
                return self.returncode

            def terminate(self):
                self.returncode = -1

        def spawn():
            c = Child(lives[len(spawned)])
            spawned.append(c)
            return c

        def sleep(s):
            t[0] += s
        return spawn, sleep, lambda: t[0], spawned

    def test_d_supervise_restarts_backs_off_and_stops_on_the_stop_file(self):
        self.state.mkdir(parents=True)
        lives = [0, 0, 0, 0, 30, 0, None]
        spawn, sleep, clock, spawned = self.fake(lives)

        def sleep_and_stop(s):
            sleep(s)
            if len(spawned) == len(lives) and clock() > 200:
                (self.state / "stop").write_text("off\n")
        notes = []
        delays = server.supervise(self.state, spawn, sleep_and_stop, clock, notes.append)
        self.assertEqual(delays, [1, 2, 4, 8, 1, 1], "1 s, doubling on repeated fast exits, 1 s after a long run")
        self.assertEqual(len(spawned), 7)
        self.assertTrue(spawned[-1].stdin_closed, "the stop file closes the running child's stdin")
        self.assertIn("stop file: ending run", notes[-1])

    def test_d_backoff_caps_at_60_s_and_a_stop_file_first_spawns_nothing(self):
        self.state.mkdir(parents=True)
        spawn, sleep, clock, spawned = self.fake([0] * 9 + [None])

        def sleep_and_stop(s):
            sleep(s)
            if len(spawned) == 10:
                (self.state / "stop").write_text("off\n")
        delays = server.supervise(self.state, spawn, sleep_and_stop, clock, lambda s: None)
        self.assertEqual(delays, [1, 2, 4, 8, 16, 32, 60, 60, 60])
        spawned[:] = []
        self.assertEqual(server.supervise(self.state, spawn, sleep, clock, lambda s: None), [])
        self.assertEqual(spawned, [])

    def test_d_a_real_child_ends_when_its_stdin_closes(self):
        self.state.mkdir(parents=True)
        child = subprocess.Popen([sys.executable, "-c", "import sys; sys.stdin.buffer.read()"],
                                 stdin=subprocess.PIPE)
        try:
            server.end_child(child, timeout=20)
            self.assertEqual(child.returncode, 0, "EOF on stdin, not terminate()")
        finally:
            if child.poll() is None:
                child.kill()

    def test_d_supervise_without_a_config_is_refused(self):
        self.state.mkdir(parents=True)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = server.main(["supervise", "--state", str(self.state)])
        self.assertEqual(code, 2, out.getvalue())
        self.assertIn("has no config.json", out.getvalue())

    # ------------------------------------------------------------------ (e) the folder
    def test_e_caches_on_win32_uses_localappdata(self):
        self.assertEqual(server.caches(platform="win32", env={"LOCALAPPDATA": str(self.local)}),
                         self.local / "upright-page-server")
        self.assertEqual(server.caches(home=self.home, platform="win32", env={}),
                         self.home / "AppData" / "Local" / "upright-page-server")
        self.assertEqual(server.caches(home=self.home, platform="darwin", env={"LOCALAPPDATA": str(self.local)}),
                         self.home / "Library" / "Caches" / "upright-page-server", "macOS unchanged")
        self.assertEqual(server.state_of(PERSON, platform="win32"), self.state)

    # ------------------------------------------------------------------ (f) anything else is refused
    def test_f_linux_is_refused_naming_what_is_supported(self):
        for verb in ("on", "off", "status", "restart", "remove"):
            code, out = self.main(verb, platform="linux")
            self.assertEqual(code, 2, verb)
            self.assertIn("runs on macOS (a LaunchAgent) and Windows (a Task Scheduler task) only; this machine is "
                          "linux", out)
            self.assertNotIn("PF-14b", out)
        self.assertEqual(self.rec.calls, [])
        self.assertFalse(self.state.exists())

    # ------------------------------------------------------------------ (g) the lock without fcntl
    def test_g_state_lock_uses_msvcrt_where_there_is_no_fcntl(self):
        self.state.mkdir(parents=True)
        seen = []

        class Msvcrt(object):
            LK_LOCK, LK_UNLCK = 1, 0
            tries = [OSError(36, "Resource deadlock avoided")]

            def locking(self, fd, mode, n):
                if mode == self.LK_LOCK and self.tries:
                    raise self.tries.pop()
                seen.append((mode, n))
        with mock.patch.object(server, "fcntl", None), mock.patch.object(server, "msvcrt", Msvcrt()):
            with server.StateLock(self.state) as lock:
                self.assertEqual(lock.fh.tell(), 0, "locks byte 0, whatever the file holds")
        self.assertEqual(seen, [(1, 1), (0, 1)], "waits past LK_LOCK's 10 s give-up, then unlocks")
        self.assertTrue((self.state / "git.lock").is_file())


if __name__ == "__main__":
    unittest.main()
