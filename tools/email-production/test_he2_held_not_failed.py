#!/usr/bin/env python3
"""HE-2 (held not failed): a month run where an email is held at the delivery
gate reads "done · N built, M held, K failed" and exits 0 unless K > 0.

    python3 test_he2_held_not_failed.py

No chain and no simple_email run: run_month's subprocess.run is replaced by a
fake that plays each email's part. Everything lands in a temp workspace.
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix="he2-held-not-failed-")).resolve()
os.environ["AI_WORKSPACE"] = str(TMP)            # before anything imports paths.py

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_month as M                              # noqa: E402

BRAND = "testbrand"
HELD_OUT = "HELD — not sent to Klaviyo:\n  product fact UNSUPPORTED: “x” — the files say: y"


def check_json(label):
    return TMP / "runs" / "email-production" / BRAND / label / "deliverable" / "check.json"


def write_held(label):
    f = check_json(label)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"delivery": {"result": "HELD", "problems": ["x"]}}))


def fake(plays):
    """subprocess.run stand-in: the chain always succeeds; the build does what
    `plays[label]` says."""
    def run(argv, **kw):
        if argv[1] != "simple_email.py":
            return subprocess.CompletedProcess(argv, 0, "chain ok\n", "")
        label = Path(argv[2]).name
        play = plays[label]
        if play == "built":
            return subprocess.CompletedProcess(argv, 0, "email: preview.html\n", "")
        if play == "held":
            write_held(label)
            return subprocess.CompletedProcess(argv, 1, "", HELD_OUT)
        if play == "stale-held-crash":
            return subprocess.CompletedProcess(argv, 1, "", "Traceback (most recent call last):\n  boom\n" + HELD_OUT)
        return subprocess.CompletedProcess(argv, 1, "", "Traceback (most recent call last):\n  boom")
    return run


def produce(plays):
    jobs = [(label, ["python3", "email.py", label]) for label in plays]
    out, logf = io.StringIO(), io.StringIO()
    with mock.patch.object(M.subprocess, "run", fake(plays)), contextlib.redirect_stdout(out):
        code = M.produce(jobs, BRAND, logf, 2)
    return code, out.getvalue(), logf.getvalue()


class HeldIsNotFailed(unittest.TestCase):
    def test_one_built_one_held_exits_0(self):
        code, out, log = produce({"a-built": "built", "b-held": "held"})
        self.assertEqual(code, 0, out)
        self.assertIn("done · 1 built, 1 held, 0 failed", out)
        self.assertIn("held (waiting on a ruling): b-held", out)
        self.assertNotIn("failed:", out)
        self.assertIn("HELD  b-held", log)
        self.assertIn("product fact UNSUPPORTED", log)
        self.assertIn("=== done: 1 built, 1 held, 0 failed, 0 skipped ===", log)

    def test_a_crash_is_still_a_failure(self):
        code, out, _ = produce({"a2-built": "built", "b2-held": "held", "c2-crash": "crash"})
        self.assertEqual(code, 1, out)
        self.assertIn("1 built, 1 held, 1 failed", out)
        self.assertIn("failed: c2-crash", out)

    def test_a_stale_held_never_relabels_a_crash(self):
        write_held("d3-stale")
        old = time.time() - 3600
        os.utime(check_json("d3-stale"), (old, old))
        code, out, _ = produce({"d3-stale": "stale-held-crash"})
        self.assertEqual(code, 1, out)
        self.assertIn("0 built, 0 held, 1 failed", out)
        self.assertIn("failed: d3-stale", out)


if __name__ == "__main__":
    unittest.main()
