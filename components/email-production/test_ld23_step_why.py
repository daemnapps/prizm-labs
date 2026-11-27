#!/usr/bin/env python3
"""LD-23 (step failure says why): a failed design or Klaviyo-build step logs
its error's own line — never a 300-character tail of google-auth's Python 3.9
FutureWarning — and the step's whole stderr is kept in the run folder
(`design/design-step.err`, `klaviyo/build-step.err`).

    python3 test_ld23_step_why.py

Offline: why() is fed CompletedProcess objects; the one_run case replaces
run_month's subprocess.run with a fake. Everything lands in a temp workspace.
"""
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix="ld23-step-why-")).resolve()
os.environ["AI_WORKSPACE"] = str(TMP)            # before anything imports paths.py

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_month as M                              # noqa: E402

BRAND = "testbrand"
LABEL = "ld23-send"

WARNING = (
    "/Library/Python/3.9/site-packages/google/auth/__init__.py:54: FutureWarning: You are using a Python "
    "version 3.9 past its end of life. Google will update google-auth with critical bug fixes only until "
    "2025-10-04. Please upgrade your Python version, and then update google-auth.\n"
    "  warnings.warn(eol_message.format(\"3.9\"), FutureWarning)\n")
TRACEBACK = (
    "Traceback (most recent call last):\n"
    "  File \"design/line.py\", line 210, in <module>\n"
    "    main()\n"
    "  File \"design/line.py\", line 188, in main\n"
    "    hero = layout[\"hero\"]\n"
    "KeyError: 'hero'\n")
FAILED = WARNING + TRACEBACK + WARNING.replace("__init__.py:54", "_default.py:91")


def proc(stderr, stdout="", code=1):
    return subprocess.CompletedProcess(["x"], code, stdout, stderr)


def setUpModule():
    look = TMP / "brands" / BRAND / "email-sms" / "design-system.json"
    look.parent.mkdir(parents=True, exist_ok=True)
    look.write_text("{}")


class WhyNamesTheError(unittest.TestCase):
    def test_traceback_between_warnings_gives_the_error_line(self):
        self.assertEqual(M.why(proc(FAILED)), "KeyError: 'hero'")

    def test_only_warnings_gives_the_last_warning_line(self):
        second = WARNING.replace("google-auth.", "google-auth, second.")
        got = M.why(proc(WARNING + second))
        self.assertTrue(got)
        self.assertEqual(got, second.splitlines()[0].strip()[:300])
        self.assertIn("FutureWarning:", got)

    def test_plain_last_line_without_traceback(self):
        self.assertEqual(M.why(proc(WARNING + "no email.json in the run folder\n")),
                         "no email.json in the run folder")

    def test_stdout_when_stderr_empty(self):
        self.assertEqual(M.why(proc("", stdout="building\nlayout refused: no hero slot\n")),
                         "layout refused: no hero slot")

    def test_never_empty(self):
        self.assertTrue(M.why(proc("", stdout="", code=2)))

    def test_cut_at_300(self):
        self.assertEqual(len(M.why(proc("ValueError: " + "x" * 1000 + "\n"))), 300)

    def test_last_of_chained_tracebacks(self):
        chained = TRACEBACK + "\nDuring handling of the above exception, another exception occurred:\n\n" \
            + TRACEBACK.replace("KeyError: 'hero'", "RuntimeError: no layout for the hero")
        self.assertEqual(M.why(proc(chained)), "RuntimeError: no layout for the hero")

    def test_err_file_keeps_the_whole_text(self):
        err = TMP / "runs" / "why-unit" / "design" / "design-step.err"
        self.assertEqual(M.why(proc(FAILED), err), "KeyError: 'hero'")
        self.assertEqual(err.read_text(), FAILED)


class OneRunLogsWhy(unittest.TestCase):
    def test_failed_design_and_build_log_the_error_and_keep_stderr(self):
        run = TMP / "runs" / "email-production" / BRAND / LABEL
        (run / "design").mkdir(parents=True, exist_ok=True)
        (run / "design" / "email.json").write_text("{}")    # the build and gaps steps run
        build_failed = WARNING + TRACEBACK.replace("KeyError: 'hero'", "FileNotFoundError: slices/1.png")

        def fake(argv, **kw):
            step = argv[1] if len(argv) > 1 else ""
            if step == "design/line.py":
                return subprocess.CompletedProcess(argv, 1, "", FAILED)
            if step == "design/build.py":
                return subprocess.CompletedProcess(argv, 1, "", build_failed)
            return subprocess.CompletedProcess(argv, 0, "ok\n", "")

        logf = io.StringIO()
        with mock.patch.object(M.subprocess, "run", fake), \
                mock.patch.object(M, "have_picture_key", lambda: False), \
                mock.patch.object(M, "NO_IMAGES", True), \
                mock.patch.object(M, "DESIGN", True), \
                mock.patch.object(M, "PUSH", False), \
                mock.patch("sys.stdout", io.StringIO()):
            label, status, _, _ = M.one_run(LABEL, ["python3", "email_line.py", LABEL], BRAND, logf)
        log = logf.getvalue()
        self.assertEqual((label, status), (LABEL, "done"))
        self.assertIn("(design step failed: KeyError: 'hero')", log)
        self.assertIn("(Klaviyo build failed: FileNotFoundError: slices/1.png)", log)
        self.assertNotIn("google-auth", log)
        self.assertEqual((run / "design" / "design-step.err").read_text(), FAILED)
        self.assertEqual((run / "klaviyo" / "build-step.err").read_text(), build_failed)


if __name__ == "__main__":
    unittest.main()
