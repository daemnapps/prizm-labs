#!/usr/bin/env python3
"""PF-16c (Windows git hang): every git call the page server makes or passes down has a timeout; a call that does not
answer is killed with its children and said, never a hang.

    python3 components/page-features/kit/test_pf16c_git_timeout.py

    (a) a git that never answers (a fake `git` first on PATH, macOS/Linux): /data/home and /plain answer 200 within
        the timeout + 2 s and name the stuck command, /status carries it, one git per listing, none outlives it; a
        listing that answers clears the line
    (b) the stuck child is killed with its tree: on simulated Windows taskkill /T /F /PID ends the cmd\\git.exe shim
        and the real git.exe under it; git starts with stdin from NUL, close_fds and the no-window flag
    (c) on simulated Windows the listening socket and the git.lock handle are non-inheritable, and supervise's pipe is
        peeked at, never read
    (d) macOS unchanged: no creationflags, no taskkill, the child alone killed, the socket left as Python made it,
        the pipe read as before; run_cmd's own timeout ends a real stuck child

Stdlib only, Python 3.9. No network beyond 127.0.0.1; writes only in temp folders.
"""
import http.client
import http.server
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import server  # noqa: E402

TPL = "platform/views/viewers/_templates/"
PERSON = "tess"
PAGE = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n</head>\n<body><p>page</p></body>\n</html>\n'
STUCK = "git did not answer in 1 s: git hash-object -- %salpha.html" % TPL
FAKE_GIT = '#!/bin/sh\necho $$ >> "$PF16C_PIDS"\nexec sleep 60\n'


def write(root, rel, text):
    p = os.path.join(str(root), rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@unittest.skipIf(os.name == "nt", "the fake git is a shell script")
class StuckGit(unittest.TestCase):
    """(a) against a PageServer on a temp root whose git never answers."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="pf16c-")).resolve()
        self.addCleanup(shutil.rmtree, str(self.root), True)
        subprocess.run(["git", "init", "-q", str(self.root)], capture_output=True)
        write(self.root, TPL + "alpha.features.json", json.dumps({"owner": PERSON}))
        write(self.root, TPL + "alpha.html", PAGE)
        write(self.root, "platform/views/viewers/tess/alpha.html", PAGE)
        write(self.root, "platform/views/viewers/tess/drafts/alpha--try.html", PAGE)
        self.state = self.root.parent / (self.root.name + "-state")
        self.state.mkdir()
        self.addCleanup(shutil.rmtree, str(self.state), True)
        bin_ = self.state / "bin"
        bin_.mkdir()
        git = bin_ / "git"
        git.write_text(FAKE_GIT)
        git.chmod(git.stat().st_mode | stat.S_IXUSR)
        self.pids = self.state / "pids"
        env = mock.patch.dict(os.environ, {"PATH": "%s%s%s" % (bin_, os.pathsep, os.environ.get("PATH", "")),
                                           "PF16C_PIDS": str(self.pids)})
        env.start()
        self.addCleanup(env.stop)
        self.srv = server.PageServer(self.state, self.root, PERSON, act_person=PERSON, git_timeout=1)
        httpd = server.Server(("127.0.0.1", 0), self.srv.handler())
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        self.port = httpd.server_address[1]

    def req(self, path):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        t = time.time()
        try:
            c.request("GET", path, headers={"Host": "127.0.0.1:%d" % self.port})
            r = c.getresponse()
            return r.status, r.read().decode("utf-8"), time.time() - t
        finally:
            c.close()

    def git_pids(self):
        return [int(x) for x in self.pids.read_text().split()] if self.pids.exists() else []

    def assert_none_left(self, n):
        pids = self.git_pids()
        self.assertEqual(len(pids), n, "one git per listing: the later calls of a stuck listing fail at once")
        for pid in pids:
            self.assertFalse(alive(pid), "git pid %d outlived its request" % pid)

    def test_a_data_home_answers_and_names_the_stuck_command(self):
        code, body, took = self.req(server.DATA_HOME)
        self.assertEqual(code, 200, body[:300])
        self.assertLess(took, 1 + 2, "answered within the timeout + 2 s")
        d = json.loads(body)
        self.assertEqual(d["status"]["git"], STUCK)
        self.assertIn(STUCK, d["status_line"])
        self.assertIsNone(d["pages_error"], "the page list still answers, git's parts unknown")
        live = d["pages"]["families"][0]["live"]
        self.assertEqual(live["path"], "platform/views/viewers/tess/alpha.html")
        self.assertEqual(live["save"], "unknown (%s)" % STUCK)
        self.assert_none_left(1)
        code, body, _ = self.req("/status")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["server"]["git"], STUCK, "/status carries it")

    def test_b_plain_answers_and_shows_it_as_a_line(self):
        code, body, took = self.req(server.PLAIN)
        self.assertEqual(code, 200, body[:300])
        self.assertLess(took, 1 + 2)
        self.assertIn(STUCK, body)
        self.assertIn('href="/v/tess/alpha.html"', body, "the pages are still listed")
        self.assert_none_left(1)

    def test_c_a_listing_that_answers_clears_the_line(self):
        self.req(server.DATA_HOME)
        self.srv.git_call = lambda argv, cwd, timeout: (0, "", "")
        code, body, _ = self.req(server.DATA_HOME)
        self.assertEqual(code, 200)
        self.assertIsNone(json.loads(body)["status"]["git"])
        self.assertNotIn("did not answer", self.srv.status_line())


class FakeProc(object):
    """One process of a fake tree: communicate() waits until it is dead; kill() ends it alone, as TerminateProcess."""

    def __init__(self, pid, children=()):
        self.pid, self.children, self.dead, self.returncode = pid, list(children), threading.Event(), None

    def communicate(self, timeout=None):
        if not self.dead.wait(timeout):
            raise subprocess.TimeoutExpired("git", timeout)
        return "", ""

    def kill(self):
        self.returncode = -9
        self.dead.set()

    def tree(self):
        yield self
        for c in self.children:
            yield from c.tree()


class Tree(object):
    """popen + taskkill over one shim (cmd\\git.exe) and its real git.exe."""

    def __init__(self):
        self.real = FakeProc(101)
        self.shim = FakeProc(100, [self.real])
        self.kw, self.taskkills = None, []

    def popen(self, argv, **kw):
        self.kw = kw
        return self.shim

    def taskkill(self, argv, **kw):
        self.taskkills.append(argv)
        pid = int(argv[argv.index("/PID") + 1])
        for p in self.shim.tree():
            if p.pid == pid:
                for q in p.tree():
                    q.kill()

    def call(self, platform):
        t = time.time()
        got = server.call(["git", "hash-object", "--", "x.html"], "/nowhere", 0.3, platform=platform,
                          popen=self.popen, kill=lambda p, plat: server.kill_tree(p, plat, run=self.taskkill))
        return got, time.time() - t


class Children(unittest.TestCase):
    """(b) and (d): how git starts and how a stuck one ends."""

    def test_b_windows_kills_the_whole_tree(self):
        tree = Tree()
        got, took = tree.call("win32")
        self.assertIsNone(got, "a call that did not answer")
        self.assertLess(took, 0.3 + 2)
        self.assertEqual(tree.taskkills, [["taskkill", "/T", "/F", "/PID", "100"]])
        self.assertTrue(tree.shim.dead.is_set() and tree.real.dead.is_set(), "the shim and the real git.exe")
        self.assertIs(tree.kw["stdin"], subprocess.DEVNULL)
        self.assertTrue(tree.kw["close_fds"])
        self.assertEqual(tree.kw["creationflags"], 0x08000000, "CREATE_NO_WINDOW")

    def test_d_macos_kills_the_child_alone(self):
        tree = Tree()
        got, _ = tree.call("darwin")
        self.assertIsNone(got)
        self.assertEqual(tree.taskkills, [], "no taskkill on macOS")
        self.assertTrue(tree.shim.dead.is_set())
        self.assertNotIn("creationflags", tree.kw)
        self.assertIs(tree.kw["stdin"], subprocess.DEVNULL)

    def test_b_the_runner_says_it_once_and_waits_once(self):
        calls = []

        def stuck(argv, cwd, timeout):
            calls.append(argv)
            return None
        git = server.GitRunner(7, stuck)
        line = "git did not answer in 7 s: git hash-object -- a.html"
        self.assertEqual(git(["git", "hash-object", "--", "a.html"], "/r"), (1, "", line))
        self.assertEqual(git(["git", "status", "--porcelain"], "/r"), (1, "", line))
        self.assertEqual(len(calls), 1, "the second call never starts git")
        self.assertEqual(git.stuck, line)
        ok = server.GitRunner(7, lambda argv, cwd, timeout: (0, "abc\n", ""))
        self.assertEqual(ok(["git", "x"], "/r"), (0, "abc\n", ""))
        self.assertIsNone(ok.stuck)

    def test_d_run_cmd_ends_a_real_stuck_child(self):
        t = time.time()
        code, out = server.run_cmd([sys.executable, "-c", "import time; time.sleep(30)"], timeout=1)
        self.assertLess(time.time() - t, 1 + 2 + 0.5)
        self.assertEqual(code, 1)
        self.assertIn("did not answer in 1 s", out)

    def test_d_the_copy_s_git_has_the_timeout(self):
        self.assertIs(server.Copy("/x").runner, server.git_cmd)
        with mock.patch.object(server, "run_cmd", return_value=(0, "")) as rc:
            server.git_cmd(["git", "status"])
        rc.assert_called_once_with(["git", "status"], None, server.GIT_TIMEOUT)


class Handles(unittest.TestCase):
    """(c) and (d): what `run` owns is never a child's."""

    def bound(self):
        class Made(server.Server):
            def server_bind(self):
                self.socket.set_inheritable(True)        # as if something had made it inheritable
                server.Server.server_bind(self)
        httpd = Made(("127.0.0.1", 0), http.server.BaseHTTPRequestHandler)
        self.addCleanup(httpd.server_close)
        return httpd.socket.get_inheritable()

    def test_c_windows_socket_is_not_inheritable(self):
        with mock.patch.object(server, "windows", lambda platform=None: True):
            self.assertFalse(self.bound())

    def test_d_macos_socket_left_as_made(self):
        with mock.patch.object(server, "windows", lambda platform=None: False):
            self.assertTrue(self.bound(), "nothing changes on macOS")

    def test_c_windows_lock_handle_is_not_inheritable(self):
        state = tempfile.mkdtemp(prefix="pf16c-lock-")
        self.addCleanup(shutil.rmtree, state, True)
        real = open

        def opened(*a, **k):
            fh = real(*a, **k)
            os.set_inheritable(fh.fileno(), True)
            return fh
        with mock.patch.object(server, "windows", lambda platform=None: True), \
                mock.patch.object(server, "open", opened, create=True):
            with server.StateLock(state) as lock:
                self.assertFalse(os.get_inheritable(lock.fh.fileno()))

    def test_c_windows_peeks_at_the_pipe_never_reads(self):
        peeks = []

        def peek():
            peeks.append(1)
            if len(peeks) == 3:
                raise BrokenPipeError(109, "the pipe has been ended")
            return 0, 0
        stream = mock.Mock()
        stream.buffer.read.side_effect = AssertionError("a pending read locks the pipe for every child")
        server.watch_parent(stream, platform="win32", peek=peek, sleep=lambda s: None)
        self.assertEqual(len(peeks), 3, "returns when the pipe breaks")
        stream.buffer.read.assert_not_called()

    def test_d_macos_reads_the_pipe(self):
        stream = mock.Mock()
        server.watch_parent(stream, platform="darwin", peek=mock.Mock(side_effect=AssertionError))
        stream.buffer.read.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
