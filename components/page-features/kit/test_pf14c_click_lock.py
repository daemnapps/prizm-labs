#!/usr/bin/env python3
"""PF-14c (click lock): two clicks in the same second both save and both say so, over a real private copy.

    python3 components/page-features/kit/test_pf14c_click_lock.py

The cause, reproduced 2026-10-29: the page list behind /, /plain and /data/home ran `git status --porcelain` in the
copy outside the server's git lock, and its index refresh held index.lock while a click's `git commit` ran. Every
test here builds PF-14 (page server)'s fixture (a temp HOME, bare origin, the person's clone, `on`), with a cq stub
that appends each click's decision to ONE shared decisions file, as creative-queue's cq.py does. Git runs for real.
"""
import json
import os
import subprocess
import sys
import threading
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import server  # noqa: E402
import test_pf14_page_server as T  # noqa: E402  PF-14 (page server)'s fixture and helpers

DECISIONS = "runs/queue-shadow/decisions/tess/2026-10-29.jsonl"
CQ_STUB = r'''import json, os, subprocess, sys
a = sys.argv[1:]
if a[1] == "nope":
    print("cq stub: no such item", file=sys.stderr)
    sys.exit(2)
f = os.path.join("runs", "queue-shadow", "decisions", "tess", "2026-10-29.jsonl")
os.makedirs(os.path.dirname(f), exist_ok=True)
with open(f, "a") as fh:
    fh.write(json.dumps({"id": a[1], "argv": a}) + "\n")
print("decision: " + f)
run = lambda *x: subprocess.run(["git"] + list(x), capture_output=True, text=True)
for step in (("add", "--", f), ("commit", "-q", "-m", "cq stub: " + a[1], "--", f), ("push", "-q")):
    p = run(*step)
    if p.returncode:
        print("git %s failed: %s" % (step[0], p.stderr.strip()), file=sys.stderr)
        sys.exit(1)
print("commit: ok")
'''
HOLDER = r'''import os, sys
fd = os.open(sys.argv[1], os.O_CREAT | os.O_EXCL | os.O_WRONLY)
print("held", flush=True)
sys.stdin.read()
os.close(fd)
os.unlink(sys.argv[1])
'''


# PF-14 (page server)'s setUp, tearDown and helpers, never its tests
Fixture = type("Fixture", (unittest.TestCase,),
               {k: v for k, v in vars(T.PageServerTest).items() if not k.startswith("test")})


class ClickLockTest(Fixture):
    def setUp(self):
        with mock.patch.dict(T.FILES, {"components/creative-queue/cq.py": CQ_STUB}):
            Fixture.setUp(self)
        self.on()
        self.lock = server.StateLock(self.state)
        self.syncer = server.Sync(server.Copy(self.copy), self.lock)
        self.srv = server.PageServer(self.state, self.copy, T.PERSON, act_person=T.PERSON, sync=self.syncer,
                                     lock=self.lock)
        self.port = self.up(self.srv)

    # ------------------------------------------------------------------ helpers
    def click(self, item):
        code, text = self.req(self.port, "/act", "POST", referer="/v/tess/alpha.html", token=self.srv.token,
                              body={"family": "alpha", "n": 5, "item": item, "field": "who", "value": "editor"})
        return code, json.loads(text)

    def lines(self):
        p = self.state / "clicks.jsonl"
        return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []

    def at_head(self):
        """The decisions file as the copy's HEAD has it ("" before any commit carries it)."""
        p = subprocess.run(["git", "-C", str(self.copy), "show", "HEAD:" + DECISIONS], capture_output=True, text=True)
        return p.stdout if p.returncode == 0 else ""

    def on_disk(self):
        return (self.copy / DECISIONS).read_text()

    def gitdir(self):
        return T.git("-C", str(self.copy), "rev-parse", "--absolute-git-dir").strip()

    # ------------------------------------------------------------------ (a) 2, then 5, at once
    def test_a_two_then_five_clicks_at_once_all_save_commit_and_say_ok(self):
        seen = 0
        for k in (2, 5):
            out, done = {}, threading.Event()

            def press(i):
                out[i] = self.click("a%d-%d" % (k, i))

            def home():                                  # the page list's git, the cause, running alongside
                while not done.is_set():
                    self.req(self.port, "/data/home")

            hs = [threading.Thread(target=home) for _ in range(2)]
            ts = [threading.Thread(target=press, args=(i,)) for i in range(k)]
            for t in hs + ts:
                t.start()
            for t in ts:
                t.join()
            done.set()
            for t in hs:
                t.join()
            for i in range(k):
                code, res = out[i]
                self.assertEqual((code, res["ok"]), (200, True), res)
                self.assertNotIn("pending", res)
                item = '"id": "a%d-%d"' % (k, i)
                self.assertIn(item, self.on_disk())
                self.assertIn(item, self.at_head(), "every record in a commit")
                self.assertIn(item, T.git("show", "main:" + DECISIONS, cwd=str(self.origin)), "and pushed")
            new = self.lines()[seen:]
            seen += len(new)
            self.assertEqual(len(new), k, "one click line each")
            self.assertEqual([server.click_word(c) for c in new], ["ok"] * k)
            self.assertTrue(all(c["ok"] and "pending" not in c for c in new), new)
        self.assertEqual(T.git("-C", str(self.copy), "status", "--porcelain", "--", DECISIONS), "")
        self.assertEqual(self.srv.pending, {})

    # ------------------------------------------------------------------ (b) the cause: the page list takes no lock
    def test_b_the_page_list_never_writes_the_copys_index(self):
        index = os.path.join(self.gitdir(), "index")
        readme = str(self.copy / "README.md")
        t = time.time() + 5
        os.utime(readme, (t, t))                         # stat-dirty: a refreshing git status rewrites the index
        with open(index, "rb") as fh:
            before = fh.read()
        for route in ("/data/home", "/plain", "/"):
            self.assertEqual(self.req(self.port, route)[0], 200, route)
        with open(index, "rb") as fh:
            self.assertEqual(fh.read(), before, "the page list's git status left the index (and its lock) alone")
        self.assertEqual(server.reading_env()["GIT_OPTIONAL_LOCKS"], "0")
        env = dict(os.environ)
        env.pop("GIT_OPTIONAL_LOCKS", None)
        subprocess.run(["git", "-C", str(self.copy), "status", "--porcelain"], env=env, capture_output=True)
        with open(index, "rb") as fh:
            self.assertNotEqual(fh.read(), before, "control: a plain git status does write it, under index.lock")

    # ------------------------------------------------------------------ (c) a lock another process holds
    def test_c_an_index_lock_another_process_holds_is_saved_pending_and_the_next_sync_commits_it(self):
        lock = os.path.join(self.gitdir(), "index.lock")
        p = subprocess.Popen([sys.executable, "-c", HOLDER, lock], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             universal_newlines=True)
        try:
            self.assertEqual(p.stdout.readline().strip(), "held")
            code, res = self.click("c1")
        finally:
            p.stdin.close()
            p.wait(10)
            p.stdout.close()
        self.assertEqual((code, res["ok"]), (200, True), res)
        self.assertIn("index.lock", res["pending"])
        self.assertIn("saved — commit pending (", res["said"])
        self.assertIn('"id": "c1"', self.on_disk(), "the record was written")
        self.assertNotIn('"id": "c1"', self.at_head(), "but not committed yet")
        (c,) = self.lines()
        self.assertEqual(server.click_word(c), "saved — commit pending")
        self.assertTrue(c["ok"])
        self.assertIn("saved — commit pending (", c["said"])
        self.assertIn("index.lock", c["pending"])
        self.assertNotIn("failed</span>", self.srv.index_html(), "never 'failed'")
        self.assertIn("saved — commit pending", self.srv.index_html())
        self.assertEqual(sorted(json.loads((self.state / "pending.json").read_text())), [DECISIONS])
        self.assertFalse(os.path.exists(lock), "the holder let go")
        rec = self.syncer.once()
        self.assertTrue(rec["ok"], rec)
        self.assertIn("committed 1 file clicks had saved", rec["said"])
        self.assertIn('"id": "c1"', self.at_head(), "the next sync's commit carries it")
        self.assertIn('"id": "c1"', T.git("show", "main:" + DECISIONS, cwd=str(self.origin)), "and pushes it")
        self.assertEqual(T.git("-C", str(self.copy), "status", "--porcelain", "--", DECISIONS), "")
        self.assertEqual(json.loads((self.state / "pending.json").read_text()), {})
        self.assertEqual(self.syncer.once()["said"], "up to date", "nothing left to commit")

    def test_c_a_later_click_that_carries_the_pending_file_empties_the_list(self):
        lock = os.path.join(self.gitdir(), "index.lock")
        p = subprocess.Popen([sys.executable, "-c", HOLDER, lock], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             universal_newlines=True)
        try:
            p.stdout.readline()
            self.assertIn("pending", self.click("e1")[1])
        finally:
            p.stdin.close()
            p.wait(10)
            p.stdout.close()
        code, res = self.click("e2")                     # its commit of the shared file carries e1's line too
        self.assertEqual((code, res["ok"]), (200, True), res)
        self.assertNotIn("pending", res)
        self.assertIn('"id": "e1"', self.at_head())
        commits = T.git("-C", str(self.copy), "rev-list", "--count", "HEAD").strip()
        rec = self.syncer.once()
        self.assertTrue(rec["ok"], rec)
        self.assertEqual(T.git("-C", str(self.copy), "rev-list", "--count", "HEAD").strip(), commits, "no empty commit")
        self.assertEqual(self.srv.pending, {})

    # ------------------------------------------------------------------ (d) nothing written: failed, as before
    def test_d_a_click_that_wrote_nothing_still_says_failed(self):
        code, res = self.click("nope")
        self.assertEqual((code, res["ok"]), (200, False), res)
        self.assertNotIn("pending", res)
        (c,) = self.lines()
        self.assertEqual(server.click_word(c), "failed")
        self.assertFalse(c["ok"])
        self.assertIn("failed</span>", self.srv.index_html())
        self.assertEqual(self.srv.pending, {})
        self.assertFalse((self.state / "pending.json").exists())

    # ------------------------------------------------------------------ the why
    def test_e_the_why_is_the_line_that_names_the_lock(self):
        out = "decision: x\ngit add failed: fatal: Unable to create '/r/.git/worktrees/repo/index.lock': File exists.\n" \
              "Another git process seems to be running in this repository"
        self.assertTrue(server.commit_why(out).startswith("git add failed: fatal: Unable to create"))
        self.assertEqual(server.commit_why("one\ntwo\n"), "two")
        self.assertEqual(server.commit_why(""), "no message")


if __name__ == "__main__":
    unittest.main()
