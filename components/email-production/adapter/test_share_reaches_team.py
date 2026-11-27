"""ask.share pushes a Done past an unrelated uncommitted file, and says plainly when it could not (editor, 2026-11-11: her
Done stayed on her Mac behind a dirty index.json, and nothing told her it had not reached the team). Real git, in a
temporary folder: a bare "team" repo and two clones. No network.

    python3 adapter/test_share_reaches_team.py
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ask  # noqa: E402


def git(cwd, *a):
    r = subprocess.run(["git"] + list(a), cwd=str(cwd), capture_output=True, text=True)
    if r.returncode:
        raise AssertionError("git %s: %s" % (" ".join(a), r.stderr))
    return r.stdout.strip()


def clone(team, path):
    git(team.parent, "clone", "-q", str(team), str(path))
    git(path, "config", "user.email", "t@example.com")
    git(path, "config", "user.name", "T")
    git(path, "config", "pull.rebase", "false")
    return path


class ShareReachesTeam(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.team = root / "team.git"
        git(root, "init", "-q", "--bare", "-b", "main", str(self.team))
        seed = clone(self.team, root / "seed")
        (seed / "run").mkdir()
        for n in ("done.json", "index.json", "other.json"):
            (seed / "run" / n).write_text("{}\n")
        git(seed, "add", ".")
        git(seed, "commit", "-qm", "seed")
        git(seed, "push", "-q", "origin", "HEAD:main")
        self.editor = clone(self.team, root / "editor")
        self.mate = clone(self.team, root / "mate")
        self._repo = ask.REPO
        ask.REPO = self.editor

    def tearDown(self):
        ask.REPO = self._repo
        self.tmp.cleanup()

    def team_has(self, text):
        return text in git(self.team, "log", "--format=%s", "main")

    def teammate_pushes(self, name):
        (self.mate / "run" / name).write_text('{"mate": 1}\n')
        git(self.mate, "commit", "-qam", "mate")
        git(self.mate, "push", "-q", "origin", "HEAD:main")

    def test_done_reaches_the_team_past_an_unrelated_dirty_file(self):
        self.teammate_pushes("other.json")         # the team moved on, so a pull is needed
        (self.editor / "run" / "index.json").write_text('{"rewritten": "on this Mac"}\n')
        (self.editor / "run" / "done.json").write_text('{"done": true}\n')
        self.assertEqual(ask.share(["run/done.json"], "editor: done"), "shared")
        self.assertTrue(self.team_has("editor: done"))
        self.assertIn("rewritten", (self.editor / "run" / "index.json").read_text())   # her file untouched

    def test_a_done_that_cannot_reach_the_team_says_so_plainly(self):
        self.teammate_pushes("index.json")         # the team changed the very file left dirty here
        (self.editor / "run" / "index.json").write_text('{"rewritten": "on this Mac"}\n')
        (self.editor / "run" / "done.json").write_text('{"done": true}\n')
        r = ask.share(["run/done.json"], "editor: done")
        self.assertTrue(r.startswith("NOT on the team page yet: your change is saved only on this Mac"), r)
        self.assertFalse(self.team_has("editor: done"))
        self.assertEqual(git(self.editor, "status", "--porcelain", "--", "run/done.json"), "")   # committed, kept
        self.assertIn("rewritten", (self.editor / "run" / "index.json").read_text())


if __name__ == "__main__":
    unittest.main()
