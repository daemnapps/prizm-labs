#!/usr/bin/env python3
"""SI-196 (key checks report-only) — declared test for checks.py.

Every case builds a FIXTURE TREE in a temp dir — a fake env.template, a fake
job_env.py and fake components/ — and runs `checks.py --root <tree>` as its
own process (sys.executable) under a temp HOME. Fake NAMES only: no fixture,
assertion or comment holds a key value, and nothing here reads a real
dotfile, the Keychain or the real job_env.py.

  (1) TEMPLATE vs SCOPE — an uncovered credential name is reported with
      env.template:line; a covered one (exact or by prefix) is not; a lock /
      timeout setting is skipped; job_env failing to import says "check 1 not
      run" and check 2 still runs.
  (2) KEYS ON A COMMAND LINE — an argv leak is found with path:line (direct
      read, via a local name, via .format); a key handed over in env= is not
      flagged, nor a value passed through another call first; tests and
      archive/ are not scanned; an unparseable file is counted as skipped.
  (G-A2) exit 0 in every case: findings, none, broken job_env, bad flag.

Run: cd components/keys && python3 test_checks.py
"""
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKS = HERE / "checks.py"

TEMPLATE = """\
# fake template — NAMES ONLY
FAKE_COVERED_KEY
    what      a covered credential.
FAKE_UNCOVERED_TOKEN
    what      a credential job_env does not hold back.
FAKE_PERSON_TOKEN_{PERSON}
    what      covered by prefix.
FAKE_JOB_LOCK
FAKE_JOB_LOCK_WAIT
FAKE_JOB_TIMEOUT
FAKE_PROSE_KEY               a NAME with prose after it is not a bare line
"""

JOB_ENV = """\
VENDOR_KEYS = frozenset({"FAKE_COVERED_KEY"})
VENDOR_KEY_PREFIXES = ("FAKE_PERSON_TOKEN_",)


def is_vendor_key(name):
    if name in VENDOR_KEYS:
        return True
    return any(name.startswith(p) and len(name) > len(p)
               for p in VENDOR_KEY_PREFIXES)
"""

LEAKY = """\
import os
import subprocess
from subprocess import run as spawn


def leak_direct():
    subprocess.run(["curl", "-H", f"auth: {os.environ['FAKE_COVERED_KEY']}"])  # LEAK-1


def leak_via_name():
    tok = os.getenv("FAKE_UNCOVERED_TOKEN")
    cmd = ["curl", "-F"]
    cmd.append("api_token=" + tok)
    spawn(cmd)  # LEAK-2


def leak_via_format(keys):
    os.system("curl https://example.invalid/?k={k}".format(k=keys.key("FAKE_COVERED_KEY")))  # LEAK-3


def safe_env():
    tok = os.environ.get("FAKE_COVERED_KEY")
    subprocess.run(["curl", "https://example.invalid"], env={"FAKE_COVERED_KEY": tok})  # SAFE-1


def safe_transformed(for_psql):
    safe, child = for_psql(os.environ["FAKE_DB_URL"])
    subprocess.run(["psql", safe, "-c", "select 1"], env=child)  # SAFE-2


def safe_setting():
    subprocess.run(["sleep", os.environ.get("FAKE_JOB_TIMEOUT", "1")])  # SAFE-3
"""

TEST_LEAK = """\
import os
import subprocess
subprocess.run(["curl", os.environ["FAKE_COVERED_KEY"]])
"""


def line_of(text, marker):
    for n, line in enumerate(text.splitlines(), 1):
        if marker in line:
            return n
    raise AssertionError("marker not in fixture: " + marker)


def section(out, n):
    """The text of check n's section, header to the next blank line."""
    start = out.index("== Check %d" % n)
    end = out.find("\n\n", start)
    return out[start:] if end < 0 else out[start:end]


class Fixture:
    def __init__(self, job_env=JOB_ENV, leaky=LEAKY, extra=True):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir()
        mw = self.root / "platform" / "workers" / "mini-worker"
        mw.mkdir(parents=True)
        (mw / "env.template").write_text(TEMPLATE)
        if job_env is not None:
            (mw / "job_env.py").write_text(job_env)
        comp = self.root / "components" / "fake"
        comp.mkdir(parents=True)
        if leaky is not None:
            (comp / "leaky.py").write_text(leaky)
        if extra:
            (comp / "test_leaky.py").write_text(TEST_LEAK)
            (comp / "archive").mkdir()
            (comp / "archive" / "old.py").write_text(TEST_LEAK)
            (comp / "broken.py").write_text("def broken(:\n")

    def run(self, *args):
        env = {"PATH": os.environ.get("PATH", ""), "HOME": str(self.home),
               "LANG": "C.UTF-8", "PYTHONIOENCODING": "utf-8"}
        argv = [sys.executable, str(CHECKS)] + (list(args) if args else
                                                ["--root", str(self.root)])
        p = subprocess.run(argv, capture_output=True, text=True, env=env,
                           cwd=str(self.home), timeout=120)
        return p.returncode, p.stdout, p.stderr

    def close(self):
        self.tmp.cleanup()


class TestChecks(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        self.code, self.out, self.err = self.fx.run()

    def tearDown(self):
        self.fx.close()

    def test_exit_zero_with_findings(self):
        self.assertEqual(self.code, 0, self.err)
        self.assertIn("REPORT-ONLY", self.out)

    def test_check1_uncovered_credential_reported_with_line(self):
        c1 = section(self.out, 1)
        self.assertIn("1 finding(s)", c1)
        want = "platform/workers/mini-worker/env.template:%d  FAKE_UNCOVERED_TOKEN" % (
            line_of(TEMPLATE, "FAKE_UNCOVERED_TOKEN"))
        self.assertIn(want, c1)

    def test_check1_covered_names_not_reported(self):
        c1 = section(self.out, 1)
        self.assertNotIn("FAKE_COVERED_KEY", c1)
        self.assertNotIn("FAKE_PERSON_TOKEN_", c1)

    def test_check1_settings_skipped(self):
        c1 = section(self.out, 1)
        for name in ("FAKE_JOB_LOCK", "FAKE_JOB_TIMEOUT", "FAKE_PROSE_KEY"):
            self.assertNotIn(name, c1)

    def test_check2_leaks_found_with_path_line_and_name(self):
        c2 = section(self.out, 2)
        self.assertIn("3 finding(s)", c2)
        for marker, name in (("LEAK-1", "FAKE_COVERED_KEY"),
                             ("LEAK-2", "FAKE_UNCOVERED_TOKEN"),
                             ("LEAK-3", "FAKE_COVERED_KEY")):
            self.assertIn("components/fake/leaky.py:%d  %s"
                          % (line_of(LEAKY, marker), name), c2)

    def test_check2_safe_calls_not_flagged(self):
        c2 = section(self.out, 2)
        for marker in ("SAFE-1", "SAFE-2", "SAFE-3"):
            self.assertNotIn("leaky.py:%d " % line_of(LEAKY, marker), c2)
        self.assertNotIn("FAKE_DB_URL", c2)

    def test_check2_skips_tests_archive_and_counts_unparseable(self):
        self.assertNotIn("test_leaky.py", self.out)
        self.assertNotIn("archive/old.py", self.out)
        self.assertIn("did not parse", self.out)
        self.assertIn("components/fake/broken.py", self.out)


class TestEdges(unittest.TestCase):
    def test_clean_tree_says_none_and_exits_zero(self):
        fx = Fixture(leaky=textwrap.dedent("""\
            import subprocess
            subprocess.run(["true"])
            """), extra=False)
        try:
            (fx.root / "platform/workers/mini-worker/env.template").write_text(
                "FAKE_COVERED_KEY\nFAKE_JOB_LOCK\n")
            code, out, err = fx.run()
        finally:
            fx.close()
        self.assertEqual(code, 0, err)
        self.assertIn("none", section(out, 1))
        self.assertIn("0 finding(s)", section(out, 1))
        self.assertIn("none", section(out, 2))
        self.assertIn("0 finding(s)", section(out, 2))

    def test_job_env_import_fails_check1_not_run_check2_runs(self):
        fx = Fixture(job_env="raise RuntimeError('fake import failure')\n", extra=False)
        try:
            code, out, err = fx.run()
        finally:
            fx.close()
        self.assertEqual(code, 0, err)
        self.assertIn("check 1 not run", out)
        self.assertNotIn("FAKE_UNCOVERED_TOKEN", section(out, 1))
        c2 = section(out, 2)
        self.assertIn("leaky.py:%d  FAKE_COVERED_KEY" % line_of(LEAKY, "LEAK-1"), c2)
        self.assertIn("suffix rules only", c2)

    def test_job_env_missing_check1_not_run(self):
        fx = Fixture(job_env=None, extra=False)
        try:
            code, out, err = fx.run()
        finally:
            fx.close()
        self.assertEqual(code, 0, err)
        self.assertIn("check 1 not run", out)

    def test_bad_flag_still_exits_zero(self):
        fx = Fixture(extra=False)
        try:
            code, out, err = fx.run("--no-such-flag")
        finally:
            fx.close()
        self.assertEqual(code, 0, err)
        self.assertIn("nothing checked", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
