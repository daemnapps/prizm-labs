#!/usr/bin/env python3
"""LD-95 (posts off-clone): mini_run.publish_one commits and pushes ONE file from a
throwaway worktree of origin/main, never in the caller's clone. Checked against a
temp-dir fixture — a bare origin.git, the caller's `clone` and an `other` clone that
pushes — with the module's own git runner (real git, the machine's global and system
config shut out), so no real repo, remote or network is touched.

    /usr/bin/python3 components/run-kit/test_ld95_publish_off_clone.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mini_run as M      # noqa: E402
import mini_debug as D    # noqa: E402

ISOLATED = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0",
            "GIT_MERGE_AUTOEDIT": "no"}
REL = "team/threads/x/001-a.md"
BODY = "# a post\nask: why?\n"
MSG = "mini-debug: alice opens x/001"
NOW = datetime(2026, 10, 23, 14, 30, 0, tzinfo=timezone.utc)


def git_bytes(repo, *args):
    p = subprocess.run(["git"] + list(args), cwd=str(repo), capture_output=True)
    if p.returncode != 0:
        raise AssertionError("git {0}: {1}".format(" ".join(args), p.stderr.decode()))
    return p.stdout


def sh(repo, *args):
    return git_bytes(repo, *args).decode()


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def publish_dirs():
    return {p for p in os.listdir(tempfile.gettempdir()) if p.startswith("run-kit-publish-")}


class Base(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ, ISOLATED)
        env.start()
        self.addCleanup(env.stop)
        self.tmp = Path(tempfile.mkdtemp(prefix="ld95-"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.origin = self.tmp / "origin.git"
        sh(self.tmp, "init", "--bare", "-q", "-b", "main", str(self.origin))
        seed = self.tmp / "seed"
        sh(self.tmp, "init", "-q", "-b", "main", str(seed))
        write(seed / "team/dispatch-grants.json", json.dumps({"components": []}))
        write(seed / "team/people/alice/identity.json", json.dumps(
            {"person": "alice", "emails": [{"address": "alice@example.com"}]}))
        write(seed / "team/people/dayu/identity.json", json.dumps(
            {"person": "dayu", "emails": [{"address": "dayu@example.com"}]}))
        write(seed / "tracked.txt", "tracked\n")
        self.ident(seed, "seed")
        sh(seed, "add", "-A")
        sh(seed, "commit", "-q", "-m", "seed")
        sh(seed, "remote", "add", "origin", str(self.origin))
        sh(seed, "push", "-q", "origin", "main")
        self.clone = self.clone_as("alice", "clone")
        self.other = self.clone_as("dayu", "other")
        self.out = []
        self.dirs_before = publish_dirs()

    def ident(self, repo, person):
        sh(repo, "config", "user.email", person + "@example.com")
        sh(repo, "config", "user.name", person)
        sh(repo, "config", "commit.gpgsign", "false")

    def clone_as(self, person, name):
        path = self.tmp / name
        sh(self.tmp, "clone", "-q", str(self.origin), str(path))
        self.ident(path, person)
        return path

    def other_pushes(self, name="other.txt"):
        sh(self.other, "pull", "-q", "--no-rebase", "origin", "main")
        write(self.other / name, "from the other clone\n")
        sh(self.other, "add", "--", name)
        sh(self.other, "commit", "-q", "-m", "other: " + name, "--", name)
        sh(self.other, "push", "-q", "origin", "main")

    def make_dirty(self):
        write(self.clone / "staged.txt", "staged, not ours\n")
        sh(self.clone, "add", "--", "staged.txt")
        write(self.clone / "tracked.txt", "edited, not staged\n")

    def snapshot(self):
        c = self.clone
        return {"head": sh(c, "rev-parse", "HEAD"),
                "status": git_bytes(c, "status", "--porcelain=v1", "-z"),
                "staged": sh(c, "rev-parse", ":staged.txt"),
                "dirty": (c / "tracked.txt").read_bytes(),
                "worktrees": sh(c, "worktree", "list", "--porcelain")}

    def worktree_paths(self):
        return [l for l in sh(self.clone, "worktree", "list", "--porcelain").splitlines()
                if l.startswith("worktree ")]

    def publish(self, git=M.git_run, **kw):
        return M.publish_one(self.clone, git, REL, BODY, MSG, self.out.append, **kw)

    def on_origin(self, rel):
        p = subprocess.run(["git", "--git-dir", str(self.origin), "show", "main:" + rel], capture_output=True)
        return p.stdout.decode() if p.returncode == 0 else None

    def assert_clone_untouched(self, before):
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.clone / ".git/MERGE_HEAD").exists())
        self.assertFalse((self.clone / REL).exists())
        self.assertFalse((self.clone / "team/threads").exists())
        self.assertEqual(publish_dirs(), self.dirs_before)


class TestPublishOffClone(Base):
    def test_a_moved_origin_and_a_dirty_clone_are_left_untouched(self):
        self.other_pushes()
        self.make_dirty()
        before = self.snapshot()
        self.assertEqual(self.publish(), 0, "\n".join(self.out))
        self.assertEqual(self.on_origin(REL), BODY)
        self.assertEqual(self.on_origin("other.txt"), "from the other clone\n")
        self.assert_clone_untouched(before)
        log = sh(self.clone, "log", "--format=%s", "origin/main").splitlines()
        self.assertEqual(log[:2], [MSG, "other: other.txt"])
        self.assertEqual(sh(self.clone, "show", "--name-only", "--format=", "origin/main").split(), [REL])

    def test_b_a_push_always_refused_returns_1_and_leaves_nothing(self):
        hook = self.origin / "hooks/pre-receive"
        write(hook, "#!/bin/sh\necho 'declined by the fixture' >&2\nexit 1\n")
        hook.chmod(0o755)
        self.make_dirty()
        before = self.snapshot()
        slept = []
        self.assertEqual(self.publish(sleep=slept.append), 1, "\n".join(self.out))
        self.assertEqual(slept, [M.PUBLISH_PAUSE_S] * (M.PUBLISH_ATTEMPTS - 1))
        self.assertIsNone(self.on_origin(REL))
        self.assert_clone_untouched(before)
        refusal = [l for l in self.out if l.startswith("not published: ")]
        self.assertEqual(len(refusal), 1, self.out)
        self.assertIn("pre-receive hook declined", refusal[0])
        self.assertIn("run the same command again", "\n".join(self.out))

    def test_c_a_push_racing_another_lands_after_the_in_worktree_rebase(self):
        calls = []

        def racing(args, cwd):
            calls.append((list(args), Path(cwd)))
            if args[0] == "push" and [a for a, _ in calls].count(list(args)) == 1:
                self.other_pushes("raced.txt")
            return M.git_run(args, cwd)

        self.make_dirty()
        before = self.snapshot()
        self.assertEqual(self.publish(git=racing, sleep=lambda _: None), 0, "\n".join(self.out))
        self.assertEqual(self.on_origin(REL), BODY)
        self.assertEqual(self.on_origin("raced.txt"), "from the other clone\n")
        self.assertEqual([a[0] for a, _ in calls].count("push"), 2)
        rebases = [cwd for a, cwd in calls if a[0] == "rebase"]
        self.assertEqual(len(rebases), 1)
        self.assertNotEqual(rebases[0].resolve(), self.clone.resolve())
        for args, cwd in calls:    # nothing but fetch and the worktree bookkeeping runs in the clone
            if cwd.resolve() == self.clone.resolve():
                self.assertIn(args[0], ("fetch", "worktree", "merge-base"), args)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(publish_dirs(), self.dirs_before)

    def test_d_open_no_push_still_commits_in_the_clone(self):
        before = sh(self.clone, "rev-parse", "HEAD").strip()
        wt = self.worktree_paths()
        out = []
        code = D.main(["open", "--slug", "np", "--ask", "why?", "--no-push"], repo=self.clone,
                      git=M.git_run, now=NOW, say=out.append, env={}, host="alices-mbp")
        self.assertEqual(code, 0, "\n".join(out))
        rel = "team/threads/dayu/20261023T1430Z-alice-np/001-alice.md"
        self.assertTrue((self.clone / rel).is_file())
        self.assertEqual(sh(self.clone, "rev-parse", "HEAD~1").strip(), before)
        self.assertEqual(sh(self.clone, "show", "--name-only", "--format=", "HEAD").split(), [rel])
        self.assertIsNone(self.on_origin(rel))
        self.assertEqual(self.worktree_paths(), wt)
        self.assertIn("--no-push: not pushed — `git push origin main` sends it", out)

    def test_push_never_pulls_in_the_clone(self):
        calls = []

        def refused(args, cwd):
            calls.append(list(args))
            return (1, "", "! [rejected] main -> main (fetch first)") if args[0] == "push" else (0, "", "")
        self.assertFalse(M.push(self.clone, refused, self.out.append))
        self.assertEqual([c[0] for c in calls], ["push"])
        self.assertIn("push refused — nothing pulled or merged in this clone", "\n".join(self.out))


if __name__ == "__main__":
    unittest.main()
