#!/usr/bin/env python3
"""PF-14 (page server): kit/server.py — the agent it installs, its private copy, its sync, its one server for all of a
person's pages, and that the person's own working folder is never touched.

    python3 components/page-features/kit/test_pf14_page_server.py

Each test builds a temp HOME, a temp bare origin, a seed checkout that moves origin, and the person's clone (left
dirty on purpose: a modified file, a staged file, an untracked file). launchctl and `open` go to a recorder that
answers like launchctl; git runs for real on those temp folders. No network beyond 127.0.0.1.
"""
import contextlib
import http.client
import io
import json
import os
import plistlib
import shutil
import socket
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
import serve  # noqa: E402
import server  # noqa: E402

PERSON, EMAIL = "tess", "tess@example.com"


def free_port(ports=range(18740, 18800)):
    """PF-16 (fixed port): tess's record port — one free on this machine now, outside the real 8740–8749 and the
    ephemeral range a test's port-0 server is given."""
    for p in ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    raise AssertionError("no free port from %d to %d for the fixture" % (ports[0], ports[-1]))


PORT = free_port()
PAGE = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n</head>\n<body><p>page</p></body>\n</html>\n'
TPL = "platform/views/viewers/_templates/"
CQ_STUB = r'''import os, subprocess, sys
a = sys.argv[1:]
f = os.path.join("runs", "queue-shadow", a[1] + ".txt")
os.makedirs(os.path.dirname(f), exist_ok=True)
open(f, "w").write(" ".join(a) + "\n")
run = lambda *x: subprocess.run(["git"] + list(x), capture_output=True, text=True)
run("add", "--", f)
run("commit", "-q", "-m", "cq stub: " + a[1], "--", f)
p = run("push", "-q")
print("stub push: %s" % ("ok" if p.returncode == 0 else p.stderr.strip()))
sys.exit(p.returncode)
'''
FILES = {
    "brands/.keep": "",
    "components/.keep": "",
    "README.md": "readme\n",
    "team/people/tess/identity.json": json.dumps({"emails": [{"address": EMAIL}], "page_server_port": PORT}),
    server.SELF: "# stub: the real one is on origin/main once PF-14 merges\n",
    TPL + "alpha.sources.json": json.dumps({"x": {"argv": ["components/alpha/fail.py"]}}),
    TPL + "alpha.actions.json": json.dumps({"direct": {"5": {"run": "cq", "verb": "set", "fields": ["who"]}}}),
    TPL + "beta.sources.json": json.dumps({"y": {"argv": ["components/beta/ok.py"]}}),
    TPL + "gamma.sources.json": json.dumps({"z": {"argv": ["components/gamma/ok.py"], "keys": ["PF14_NO_SUCH_KEY"]}}),
    TPL + "alpha.features.json": json.dumps({"owner": PERSON}),
    TPL + "beta.features.json": json.dumps({"owner": PERSON}),
    TPL + "alpha.html": PAGE,
    TPL + "beta.html": PAGE,
    "components/alpha/fail.py": "import sys\nprint('alpha broke', file=sys.stderr)\nsys.exit(3)\n",
    "components/beta/ok.py": "print('[{\"ok\": 1}]')\n",
    "components/gamma/ok.py": "open('gamma-ran', 'w').write('x')\nprint('[]')\n",
    "components/creative-queue/cq.py": CQ_STUB,
    "platform/views/viewers/tess/alpha.html": PAGE,
    "platform/views/viewers/tess/drafts/beta--try.html": PAGE,
}


def git(*args, cwd=None):
    p = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True)
    if p.returncode:
        raise AssertionError("git %s: %s" % (" ".join(args), p.stderr))
    return p.stdout


def write(root, rel, text):
    p = os.path.join(str(root), rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)


class Launchctl(object):
    """Records every argv; answers launchctl and open like they would, runs git for real."""

    def __init__(self):
        self.calls, self.loaded = [], False

    def __call__(self, argv):
        self.calls.append(list(argv))
        if argv[0] == "launchctl":
            if argv[1] == "bootstrap":
                self.loaded = True
                return 0, ""
            if argv[1] == "bootout":
                was, self.loaded = self.loaded, False
                return (0, "") if was else (3, "Boot-out failed: 3: No such process")
            if argv[1] == "print":
                return (0, "state = running\n\tpid = 4242\n") if self.loaded else (113, "Could not find service")
        if argv[0] == "open":
            return 0, ""
        return server.run_cmd(argv)

    def made(self, word):
        return [c for c in self.calls if c[0] == word]


class PageServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pf14-")).resolve()
        self.home = self.tmp / "home"
        self.home.mkdir()
        env = {"HOME": str(self.home), "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "Tess",
               "GIT_AUTHOR_EMAIL": EMAIL, "GIT_COMMITTER_NAME": "Tess", "GIT_COMMITTER_EMAIL": EMAIL}
        self.env = mock.patch.dict(os.environ, env)
        self.env.start()
        os.environ.pop(server.SELF_ENV, None)
        os.environ.pop("AI_WORKSPACE", None)
        self.origin = self.tmp / "origin.git"
        git("init", "-q", "--bare", str(self.origin))
        git("symbolic-ref", "HEAD", "refs/heads/main", cwd=str(self.origin))
        self.seed = self.tmp / "seed"
        git("init", "-q", str(self.seed))
        git("checkout", "-q", "-b", "main", cwd=str(self.seed))
        for rel, text in FILES.items():
            write(self.seed, rel, text)
        git("add", "-A", cwd=str(self.seed))
        git("commit", "-q", "-m", "seed", cwd=str(self.seed))
        git("remote", "add", "origin", str(self.origin), cwd=str(self.seed))
        git("push", "-q", "origin", "main", cwd=str(self.seed))
        git("branch", "-q", "--set-upstream-to=origin/main", cwd=str(self.seed))
        self.clone = self.tmp / "clone"
        git("clone", "-q", str(self.origin), str(self.clone))
        git("config", "user.email", EMAIL, cwd=str(self.clone))
        write(self.clone, "README.md", "my own edit, not committed\n")
        write(self.clone, "staged.txt", "staged, not committed\n")
        git("add", "staged.txt", cwd=str(self.clone))
        write(self.clone, "notes.txt", "untracked\n")
        self.rec = Launchctl()
        self.state = self.home / "Library" / "Caches" / "upright-page-server" / PERSON
        self.copy = self.state / "repo"
        self.plist = self.home / "Library" / "LaunchAgents" / "com.upright.page-server.plist"
        self.servers = []

    def tearDown(self):
        for s in self.servers:
            s.shutdown()
            s.server_close()
        self.env.stop()
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    # ------------------------------------------------------------------ helpers
    def main(self, *argv, **kw):
        out = io.StringIO()
        kw.setdefault("wait", lambda port, person: True)
        with contextlib.redirect_stdout(out):
            code = server.main(list(argv), repo=self.clone, runner=self.rec, **kw)
        return code, out.getvalue()

    def on(self):
        code, out = self.main("on", "--no-open")
        self.assertEqual(code, 0, out)
        return out

    def snap(self):
        """The person's clone, byte for byte where git keeps its state: HEAD, the index, status, the files."""
        g = self.clone / ".git"
        with open(str(g / "HEAD"), "rb") as fh:
            head = fh.read()
        with open(str(g / "index"), "rb") as fh:
            index = fh.read()
        files = {}
        for rel in ("README.md", "staged.txt", "notes.txt"):
            with open(str(self.clone / rel), "rb") as fh:
                files[rel] = fh.read()
        return (head, index, git("rev-parse", "HEAD", cwd=str(self.clone)),
                git("--no-optional-locks", "status", "--porcelain", cwd=str(self.clone)), files)

    def move_origin(self, rel, text):
        write(self.seed, rel, text)
        git("pull", "-q", "--no-rebase", cwd=str(self.seed))
        git("add", "-A", cwd=str(self.seed))
        git("commit", "-q", "-m", "move " + rel, cwd=str(self.seed))
        git("push", "-q", "origin", "main", cwd=str(self.seed))
        return git("rev-parse", "HEAD", cwd=str(self.seed)).strip()

    def origin_main(self):
        return git("rev-parse", "main", cwd=str(self.origin)).strip()

    def local_commit(self, rel):
        write(self.copy, rel, "made in the copy\n")
        git("-C", str(self.copy), "add", "--", rel)
        git("-C", str(self.copy), "commit", "-q", "-m", "local " + rel, "--", rel)
        return git("-C", str(self.copy), "rev-parse", "HEAD").strip()

    def sync(self):
        return server.Sync(server.Copy(self.copy), server.StateLock(self.state))

    def up(self, srv):
        httpd = server.Server(("127.0.0.1", 0), srv.handler())
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.servers.append(httpd)
        return httpd.server_address[1]

    def req(self, port, path, method="GET", referer=None, body=None, token=None):
        h = {"Host": "127.0.0.1:%d" % port}
        if referer:
            h["Referer"] = "http://127.0.0.1:%d%s" % (port, referer)
        if method == "POST":
            h.update({"Origin": "http://127.0.0.1:%d" % port, "X-Kit-Token": token or "",
                      "Content-Type": "application/json"})
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
        try:
            c.request(method, path, body=json.dumps(body) if body is not None else None, headers=h)
            r = c.getresponse()
            return r.status, r.read().decode()
        finally:
            c.close()

    # ------------------------------------------------------------------ (a) on: the plist and bootstrap
    def test_a_on_writes_the_plist_and_bootstraps_gui_uid(self):
        code, out = self.main("on")
        self.assertEqual(code, 0, out)
        with open(str(self.plist), "rb") as fh:
            pl = plistlib.load(fh)
        self.assertEqual(pl, {
            "Label": "com.upright.page-server",
            "ProgramArguments": ["/usr/bin/python3", str(self.copy / server.SELF), "run"],
            "RunAtLoad": True, "KeepAlive": True,
            "StandardOutPath": str(self.state / "server.log"), "StandardErrorPath": str(self.state / "server.log"),
            "WorkingDirectory": str(self.copy)})
        self.assertEqual(self.rec.made("launchctl")[-1],
                         ["launchctl", "bootstrap", "gui/%d" % os.getuid(), str(self.plist)])
        cfg = json.loads((self.state / "config.json").read_text())
        self.assertEqual((cfg["person"], cfg["repo"]), (PERSON, str(self.clone)))
        self.assertEqual(cfg["port"], PORT, "PF-16 (fixed port): the record's port, no range")
        url = "http://127.0.0.1:%d/" % cfg["port"]
        self.assertEqual(self.rec.made("open"), [["open", url]])
        self.assertIn(url, out)
        code, out = self.main("on", "--no-open")
        self.assertEqual(code, 0, out)
        self.assertIn("already on", out)
        self.assertEqual(len([c for c in self.rec.made("launchctl") if c[1] == "bootstrap"]), 1, "never twice")
        code, out = self.main("restart", "--no-open")
        self.assertEqual(code, 0, out)
        self.assertEqual([c[1] for c in self.rec.made("launchctl") if c[1] != "print"][-3:],
                         ["bootstrap", "bootout", "bootstrap"])
        self.assertEqual(json.loads((self.state / "config.json").read_text())["port"], cfg["port"],
                         "a restart keeps the address")

    def test_a_on_refuses_who_are_you_and_a_main_without_the_server(self):
        git("config", "user.email", "nobody@example.com", cwd=str(self.clone))
        code, out = self.main("on", "--no-open")
        self.assertEqual(code, 2, out)
        self.assertIn("who are you?", out)
        self.assertFalse(self.plist.exists())
        git("config", "user.email", EMAIL, cwd=str(self.clone))
        git("rm", "-q", server.SELF, cwd=str(self.seed))
        git("commit", "-q", "-m", "no server", cwd=str(self.seed))
        git("push", "-q", "origin", "main", cwd=str(self.seed))
        code, out = self.main("on", "--no-open")
        self.assertEqual(code, 2, out)
        self.assertIn("PF-14 (page server)", out)
        self.assertEqual(self.rec.made("launchctl"), [c for c in self.rec.made("launchctl") if c[1] == "print"])

    # ------------------------------------------------------------------ (b) not macOS or Windows (PF-14b)
    def test_b_an_unsupported_platform_is_refused_naming_what_is(self):
        for verb in ("on", "off", "status", "restart", "remove"):
            code, out = self.main(verb, platform="linux")
            self.assertEqual(code, 2, verb)
            self.assertIn("runs on macOS (a LaunchAgent) and Windows (a Task Scheduler task) only", out)
        self.assertEqual(self.rec.calls, [])
        self.assertFalse(self.plist.exists())
        self.assertFalse(self.state.exists())

    # ------------------------------------------------------------------ (c) THE KEY TEST: the working folder
    def test_c_the_persons_working_folder_is_never_touched(self):
        before = self.snap()
        self.on()
        self.assertTrue((self.copy / ".git").is_file(), "the private copy is a worktree")
        common = git("-C", str(self.copy), "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
        self.assertEqual(os.path.realpath(common), os.path.realpath(str(self.clone / ".git")))
        self.assertEqual(git("-C", str(self.copy), "rev-parse", "HEAD").strip(), self.origin_main())
        self.assertEqual(git("-C", str(self.copy), "status", "--porcelain"), "", "the copy has none of my edits")
        tip = self.move_origin("components/beta/new.txt", "moved\n")
        rec = self.sync().once()
        self.assertTrue(rec["ok"], rec)
        self.assertEqual(git("-C", str(self.copy), "rev-parse", "HEAD").strip(), tip)
        code, out = self.main("off")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.snap(), before, "HEAD, index, status and files of my clone are byte-identical")
        in_clone = [c for c in self.rec.calls if c[:3] == ["git", "-C", str(self.clone)]]
        self.assertEqual(sorted(set(c[3] for c in in_clone)), ["fetch", "worktree"], in_clone)
        self.assertFalse(any(c[0] == "git" and "-C" not in c for c in self.rec.calls), self.rec.calls)

    # ------------------------------------------------------------------ (d) sync
    def test_d_sync_fast_forwards_rebases_pushes_and_keeps_a_refused_push(self):
        self.on()
        sync = self.sync()
        tip = self.move_origin("a.txt", "1\n")
        rec = sync.once()
        self.assertEqual((rec["ok"], rec["said"]), (True, "pulled"))
        self.assertEqual(git("-C", str(self.copy), "rev-parse", "HEAD").strip(), tip)
        self.local_commit("mine.txt")
        tip = self.move_origin("b.txt", "2\n")
        rec = sync.once()
        self.assertEqual((rec["ok"], rec["said"], rec["ahead"]), (True, "pushed", 0), rec)
        head = git("-C", str(self.copy), "rev-parse", "HEAD").strip()
        self.assertEqual(self.origin_main(), head, "pushed")
        self.assertEqual(git("-C", str(self.copy), "rev-parse", "HEAD^").strip(), tip, "rebased onto origin")
        hook = self.origin / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\necho 'fatal: could not read Username: terminal prompts disabled' >&2\nexit 1\n")
        hook.chmod(0o755)
        kept = self.local_commit("kept.txt")
        rec = sync.once()
        self.assertFalse(rec["ok"])
        self.assertEqual(rec["ahead"], 1)
        self.assertEqual(git("-C", str(self.copy), "rev-parse", "HEAD").strip(), kept, "the commit is kept")
        srv = server.PageServer(self.state, self.copy, PERSON, sync=sync)
        self.assertIn("1 not pushed", srv.status_line())
        self.assertIn("say 'push my page server' to your Claude", srv.status_line())
        code, out = self.main("status")
        self.assertEqual(code, 0, out)
        self.assertIn("1 not pushed", out)
        code, out = self.main("push")
        self.assertEqual(code, 1, out)
        hook.unlink()
        code, out = self.main("push")
        self.assertEqual(code, 0, out)
        self.assertIn("pushed", out)
        self.assertEqual(self.origin_main(), git("-C", str(self.copy), "rev-parse", "HEAD").strip())

    def test_d_a_direct_click_commits_in_the_copy_and_is_pushed(self):
        before = self.snap()
        self.on()
        lock = server.StateLock(self.state)
        sync = server.Sync(server.Copy(self.copy), lock)
        srv = server.PageServer(self.state, self.copy, PERSON, act_person=PERSON, sync=sync, lock=lock)
        port = self.up(srv)
        code, text = self.req(port, "/act", "POST", referer="/v/tess/alpha.html", token=srv.token,
                              body={"family": "alpha", "n": 5, "item": "x1", "field": "who", "value": "editor"})
        res = json.loads(text)
        self.assertEqual((code, res["ok"]), (200, True), res)
        self.assertIn("stub push: ok", res["said"], "the button's own push works from the detached copy")
        self.assertEqual(git("show", "main:runs/queue-shadow/x1.txt", cwd=str(self.origin)),
                         "set x1 who editor --by tess\n")
        self.assertEqual(sync.copy.ahead(), 0)
        clicks = [json.loads(x) for x in (self.state / "clicks.jsonl").read_text().splitlines()]
        self.assertEqual(len(clicks), 1)
        self.assertEqual((clicks[0]["page"], clicks[0]["n"], clicks[0]["ok"]), ("tess/alpha.html", 5, True))
        self.assertEqual(sorted(clicks[0]), ["at", "n", "ok", "page", "said"])
        code, text = self.req(port, "/act", "POST", referer="/v/tess/alpha.html", token=srv.token,
                              body={"family": "alpha", "n": 26, "item": "x1"})
        self.assertEqual(code, 403)
        self.assertEqual(len((self.state / "clicks.jsonl").read_text().splitlines()), 2, "every /act result")
        code, text = self.req(port, "/act", "POST", token="wrong", body={"family": "alpha", "n": 5})
        self.assertEqual(code, 403)
        self.assertEqual(len((self.state / "clicks.jsonl").read_text().splitlines()), 2, "no token, no click")
        code, text = self.req(port, "/")
        self.assertIn("tess/alpha.html", text)
        self.assertIn("Recent clicks", text)
        self.assertEqual(self.snap(), before)

    # ------------------------------------------------------------------ (e) a pull that changed the kit
    def test_e_a_pull_touching_the_kit_ends_runs_loop(self):
        self.on()
        sync = self.sync()
        self.move_origin("components/beta/other.txt", "x\n")
        sync.once()
        self.assertFalse(sync.restart.is_set(), "a change outside the kit keeps serving")
        self.move_origin("components/page-features/kit/serve.py", "# new kit\n")
        srv = server.PageServer(self.state, self.copy, PERSON, sync=sync)
        stop = threading.Event()
        t = threading.Thread(target=srv.loop, args=(stop, 0.05), daemon=True)
        t.start()
        t.join(20)
        self.assertFalse(t.is_alive())
        self.assertTrue(stop.is_set() and sync.restart.is_set())
        self.assertIn("restarting on the new code", sync.last["said"])
        self.assertTrue((self.state / "state.json").is_file())

    # ------------------------------------------------------------------ (f) one server, all pages
    def test_f_index_pages_and_a_down_family(self):
        srv = server.PageServer(self.tmp / "st", self.seed, PERSON, act_person=PERSON)
        (self.tmp / "st").mkdir()
        port = self.up(srv)
        code, text = self.req(port, "/")
        self.assertEqual(code, 200, text)
        live, draft = text.find('href="/v/tess/alpha.html"'), text.find('href="/v/tess/drafts/beta--try.html"')
        self.assertTrue(0 < live < draft, "live pages first, then drafts")
        self.assertIn("every family up", text)
        code, text = self.req(port, "/v/tess/drafts/beta--try.html")
        self.assertEqual(code, 200)
        self.assertIn('<head>\n<meta name="kit-token" content="%s">' % srv.token, text)
        code, text = self.req(port, "/data/x", referer="/v/tess/alpha.html")
        self.assertEqual(code, 502)
        self.assertTrue(text.startswith("down:") and "alpha broke" in text, text)
        code, text = self.req(port, "/data/y", referer="/v/tess/drafts/beta--try.html")
        self.assertEqual((code, json.loads(text)), (200, [{"ok": 1}]))
        code, text = self.req(port, "/data/y")
        self.assertEqual(code, 200, "a name only one family declares answers without a Referer")
        code, text = self.req(port, "/data/x", referer="/v/tess/drafts/beta--try.html")
        self.assertEqual(code, 404, "a route answers for the asking page's family only")
        code, text = self.req(port, "/data/z")
        self.assertEqual(code, 502)
        self.assertIn("down: needs PF14_NO_SUCH_KEY", text)
        self.assertFalse((self.seed / "gamma-ran").exists(), "a missing key runs nothing")
        code, text = self.req(port, "/")
        self.assertIn("down: alpha (down:", text)
        self.assertIn("alpha broke", text)
        self.assertNotIn("beta (down", text)
        code, text = self.req(port, "/v/tess/alpha.html")
        self.assertEqual(code, 200)
        self.assertIn('data-page-server="down"', text)
        self.assertNotIn('data-page-server="down"', self.req(port, "/v/tess/drafts/beta--try.html")[1])
        st = json.loads(self.req(port, "/status")[1])
        self.assertEqual(sorted(st["server"]["down"]), ["alpha", "gamma"])
        self.assertIn("behind", st)
        code, _ = self.req(port, "/v/../../team/people/tess/identity.json")
        self.assertEqual(code, 404)
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        c.request("GET", "/", headers={"Host": "evil.example:%d" % port})
        self.assertEqual(c.getresponse().status, 403, "a foreign Host is refused on the index too")
        c.close()

    # ------------------------------------------------------------------ (g) off and remove: only their own
    def test_g_off_and_remove_delete_only_their_own(self):
        before = self.snap()
        self.on()
        agents = self.plist.parent
        (agents / "com.other.thing.plist").write_text("other")
        other_state = self.state.parent / "other-person"
        other_state.mkdir()
        (other_state / "keep.txt").write_text("keep")
        (self.home / "Library" / "Caches" / "other").mkdir()
        with mock.patch.dict(os.environ, {server.SELF_ENV: "1"}):
            code, out = self.main("off")
        self.assertEqual(code, 2, "refuses to switch off the page you are using")
        self.assertTrue(self.plist.exists())
        code, out = self.main("off")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.rec.made("launchctl")[-1],
                         ["launchctl", "bootout", "gui/%d/com.upright.page-server" % os.getuid()])
        self.assertFalse(self.plist.exists())
        self.assertEqual(sorted(p.name for p in agents.iterdir()), ["com.other.thing.plist"])
        self.assertTrue(self.copy.is_dir(), "off keeps the private copy")
        self.local_commit("unpushed.txt")
        code, out = self.main("remove")
        self.assertEqual(code, 2, out)
        self.assertIn("1 not pushed", out)
        self.assertTrue(self.state.is_dir())
        code, out = self.main("remove", "--force")
        self.assertEqual(code, 0, out)
        self.assertFalse(self.state.exists())
        self.assertNotIn(str(self.copy), git("worktree", "list", "--porcelain", cwd=str(self.clone)))
        self.assertEqual((other_state / "keep.txt").read_text(), "keep")
        self.assertTrue((self.home / "Library" / "Caches" / "other").is_dir())
        self.assertEqual(sorted(p.name for p in agents.iterdir()), ["com.other.thing.plist"])
        self.assertEqual(self.snap(), before)

    # ------------------------------------------------------------------ (h) serve.py <page> as before
    def test_h_serve_py_still_serves_one_page(self):
        p = subprocess.run([sys.executable, os.path.join(HERE, "test_serve.py")], capture_output=True, text=True,
                           timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        page = os.path.join(serve.ROOT, serve.TEMPLATES, "content-queue.html")
        proc = subprocess.Popen([sys.executable, os.path.join(HERE, "serve.py"), page, "--port", str(port)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                try:
                    code, _ = self.req(port, "/status")
                    break
                except OSError:
                    time.sleep(0.1)
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            c.request("GET", "/", headers={"Host": "127.0.0.1:%d" % port})
            r = c.getresponse()
            self.assertEqual((r.status, r.getheader("Location")), (302, "/p/_templates/content-queue.html"))
            c.close()
            code, text = self.req(port, "/p/_templates/content-queue.html")
            self.assertEqual(code, 200)
            self.assertEqual(text.count('<meta name="kit-token"'), 1)
        finally:
            proc.terminate()
            proc.wait(10)


if __name__ == "__main__":
    unittest.main()
