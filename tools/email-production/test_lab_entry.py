#!/usr/bin/env python3
"""The mini's door (lab_entry.py), checked without a model, a network or a
real month: lab-run's --name value pairs become a words-only run_month.py
call, and what the run made lands in $OUT minus prompt dumps (ready.md G1;
EP-1 (email writer mini door), EP-2 (month in the repo)).

    /usr/bin/python3 tools/email-production/test_lab_entry.py
"""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lab_entry as E                # noqa: E402

BRAND = "testbrand"
MONTH = "calendar-2099-11"


def quiet(fn, *a, **kw):
    """Run fn, return (result_or_SystemExit, printed text)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        try:
            got = fn(*a, **kw)
        except SystemExit as e:
            got = e
    return got, out.getvalue()


def args(only=""):
    return E.argparse.Namespace(month=MONTH, only=only, dry_run="no")


class Argv(unittest.TestCase):
    def test_words_only_only_when_given_never_push(self):
        got = E.month_argv(args(), Path("/m"))
        self.assertEqual(got, [str(E.HERE / "run_month.py"), "/m", "--no-images", "--concurrency", "2"])
        self.assertNotIn("--only", got)
        got = E.month_argv(args("nov-01,nov-02"), Path("/m"))
        self.assertIn("--no-images", got)
        self.assertEqual(got[got.index("--only") + 1], "nov-01,nov-02")
        self.assertNotIn("--push", got)

    def test_the_mini_writes_two_emails_at_once(self):
        got = E.month_argv(args("nov-01"), Path("/m"))
        self.assertEqual(got[got.index("--concurrency") + 1], "2")

    def test_child_env_points_at_this_checkout_and_drops_the_picture_key(self):
        env = {"PATH": "/usr/bin", "OPENAI_API_KEY": "not-a-key"}
        got = E.child_env(env, Path("/repo"))
        self.assertEqual(got["AI_WORKSPACE"], "/repo")
        self.assertNotIn("OPENAI_API_KEY", got)
        self.assertEqual(got["PATH"], "/usr/bin")
        self.assertIn("OPENAI_API_KEY", env)            # the caller's env is untouched

    def test_month_dir(self):
        self.assertEqual(E.month_dir(Path("/r"), MONTH, BRAND),
                         Path("/r/runs/marketing-calendar") / BRAND / "2099-11")


class Door(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.keep_repo = E.REPO
        E.REPO = self.tmp / "repo"
        self.month = E.month_dir(E.REPO, MONTH, BRAND)
        self.month.mkdir(parents=True)
        for n in E.MONTH_FILES:
            (self.month / n).write_text("{}")
        self.runs = E.REPO / "runs" / "email-production" / BRAND
        self.out = self.tmp / "lab-out" / "mini-1"
        self.out.mkdir(parents=True)
        self.env = {"BRAND": BRAND, "OUT": str(self.out), "OPENAI_API_KEY": "not-a-key"}
        self.calls = []

    def tearDown(self):
        E.REPO = self.keep_repo
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    def never(self, cmd, env=None):
        self.calls.append(cmd)
        return 0

    def door(self, *extra, env=None, run=None):
        return quiet(E.main, ["--month", MONTH, *extra],
                     self.env if env is None else env, run or self.never)

    def test_missing_out_or_brand_exits(self):
        for env in ({"BRAND": BRAND}, {"OUT": str(self.out)}):
            got, text = self.door(env=env)
            self.assertIsInstance(got, SystemExit)
            self.assertIn("$BRAND and $OUT", str(got.code))
        self.assertEqual(self.calls, [])

    def test_a_month_without_its_review_is_refused(self):
        (self.month / "review.json").unlink()
        got, text = self.door()
        self.assertEqual(got, 2)
        self.assertIn("review.json", text)
        self.assertEqual(self.calls, [])

    def test_dry_run_runs_nothing_and_writes_nothing(self):
        for word in ("yes", "true", "1", "YES"):
            got, text = self.door("--dry_run", word)
            self.assertEqual(got, 0, text)
            self.assertIn("--no-images", text)
            for n in E.MONTH_FILES:
                self.assertIn(n, text)
        self.assertEqual(self.calls, [])
        self.assertEqual(list(self.out.iterdir()), [])
        self.assertFalse((E.REPO / "runs" / "email-production").exists())

    def test_a_real_run_carries_new_and_changed_files_but_no_prompt_dumps(self):
        old = self.runs / "oct-01" / "email.md"
        kept = self.runs / "oct-02" / "email.md"
        for f in (old, kept):
            f.parent.mkdir(parents=True)
            f.write_text("committed")
            os.utime(str(f), (1_000_000_000, 1_000_000_000))
        seen = {}

        def made(cmd, env=None):                        # run_month.py, stubbed
            seen["cmd"], seen["env"] = cmd, env
            (self.runs / "x").mkdir(parents=True)
            (self.runs / "x" / "a.md").write_text("words")
            (self.runs / "x" / "b--sent.md").write_text("brand context")
            old.write_text("rewritten")
            return 3

        got, text = self.door("--only", "nov-01", run=made)
        self.assertEqual(got, 3, text)
        self.assertEqual(seen["cmd"][0], sys.executable)
        self.assertEqual(seen["cmd"][1:], E.month_argv(args("nov-01"), self.month))
        self.assertEqual(seen["env"]["AI_WORKSPACE"], str(E.REPO))
        self.assertNotIn("OPENAI_API_KEY", seen["env"])
        carried = sorted(str(p.relative_to(self.out)) for p in self.out.rglob("*") if p.is_file())
        self.assertEqual(carried, ["oct-01/email.md", "x/a.md"])
        self.assertEqual((self.out / "oct-01" / "email.md").read_text(), "rewritten")

    def test_dry_run_word_parses(self):
        got, text = self.door("--dry_run", "yes")
        self.assertEqual(got, 0, text)
        self.assertIn("dry run", text)
        got, text = self.door("--dry_run", "no", run=lambda cmd, env=None: 0)
        self.assertEqual(got, 0, text)
        self.assertNotIn("dry run", text)


if __name__ == "__main__":
    unittest.main()
