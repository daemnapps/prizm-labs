#!/usr/bin/env python3
"""LD-107 (retry failed only): a batch records what it built, held and failed; `--retry-failed` re-runs only the
emails the last run recorded as failed, and the retry log names only them. On Nov 3-4 the overnight runner retried
whole batches and finished emails were rewritten 7-8 times (email_lead's proposal card 7, 2026-11-04).

No model, no chain, no network.

    /usr/bin/python3 components/email-production/test_ld107_retry_failed.py
"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix="ld107-")).resolve()
os.environ["AI_WORKSPACE"] = str(TMP)            # before anything imports paths.py

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_month as M                              # noqa: E402

SLOTS = [{"id": i, "date": "2026-11-2%d" % n, "hour": 13, "local": True, "type": "sale-window",
          "segments": ["S"], "product": "none", "offer": "none", "occasion": "a recorded problem"}
         for n, i in enumerate(("nov-01", "nov-02", "nov-03", "nov-04"))]
MONTH = TMP / "month"


def month(record=None):
    MONTH.mkdir(exist_ok=True)
    (MONTH / "slots.json").write_text(json.dumps(SLOTS))
    (MONTH / "run.json").write_text(json.dumps({"brand": "zz"}))
    for f in ("last-run.json", "production.log"):
        if (MONTH / f).exists():
            (MONTH / f).unlink()
    if record is not None:
        (MONTH / "last-run.json").write_text(json.dumps(record))


def run(*extra, outcome=None):
    """run_month's main with the chain replaced; `outcome` maps label -> status the fake build returns."""
    outcome = outcome or {}
    asked = []

    def one_run(label, argv, brand, logf):
        asked.append(label)
        return label, outcome.get(label, "done"), "detail", 0.1
    out = io.StringIO()
    code = None
    with mock.patch.object(M, "one_run", one_run), mock.patch.object(M.brief, "chain_argv", return_value=["x"]), \
            mock.patch.object(M.brief, "label_prefix", return_value=""), \
            mock.patch.object(M.EE, "type_problem", return_value=None), \
            mock.patch.object(M, "DESIGN", False), \
            mock.patch.object(M.RD, "check", lambda s, b, a, label, **k: {"label": label, "slot": s["id"],
                                                                          "ready": True, "missing": [], "notes": []}), \
            mock.patch("reviewed_plan.reviewed", lambda _d, s: [dict(x, _review={"note": None, "edits": []}) for x in s]), \
            mock.patch.object(sys, "argv", ["run_month.py", str(MONTH), "--no-design", *extra]), redirect_stdout(out):
        try:
            M.main()
        except SystemExit as e:
            code = e.code
    return asked, out.getvalue(), code


class TheRunRecordsWhatFailed(unittest.TestCase):
    def test_a_batch_writes_the_labels_it_built_held_and_failed(self):
        month()
        run(outcome={"nov-02": "chain-fail", "nov-03": "held", "nov-04": "build-fail"})
        rec = json.loads((MONTH / "last-run.json").read_text())
        self.assertEqual(sorted(rec["failed"]), ["nov-02", "nov-04"])
        self.assertEqual(rec["held"], ["nov-03"])
        self.assertEqual(rec["built"], ["nov-01"])
        self.assertTrue(rec.get("at"))


class ARetryRunsOnlyTheFailed(unittest.TestCase):
    def test_retry_failed_reruns_only_the_failed_labels(self):
        month({"at": "2026-11-04T03:00:00", "built": ["nov-01"], "held": ["nov-03"], "failed": ["nov-02", "nov-04"]})
        asked, out, _ = run("--retry-failed")
        self.assertEqual(sorted(asked), ["nov-02", "nov-04"])

    def test_the_retry_log_names_only_the_failed(self):
        month({"at": "2026-11-04T03:00:00", "built": ["nov-01"], "held": ["nov-03"], "failed": ["nov-02"]})
        run("--retry-failed")
        log = (MONTH / "production.log").read_text()
        retry = [ln for ln in log.splitlines() if "retry" in ln]
        self.assertTrue(retry, log)
        self.assertIn("nov-02", retry[0])
        for other in ("nov-01", "nov-03", "nov-04"):
            self.assertNotIn(other, log)

    def test_a_retry_that_fails_again_is_recorded_for_the_next_retry(self):
        month({"at": "2026-11-04T03:00:00", "built": ["nov-01"], "held": [], "failed": ["nov-02", "nov-04"]})
        run("--retry-failed", outcome={"nov-04": "chain-fail"})
        rec = json.loads((MONTH / "last-run.json").read_text())
        self.assertEqual(rec["failed"], ["nov-04"])
        self.assertEqual(rec["retry_of"], "2026-11-04T03:00:00")

    def test_nothing_failed_means_nothing_runs(self):
        month({"at": "2026-11-04T03:00:00", "built": ["nov-01"], "held": [], "failed": []})
        asked, out, code = run("--retry-failed")
        self.assertEqual(asked, [])
        self.assertIn("nothing failed", out)
        self.assertIn(code, (0, None))

    def test_no_record_means_no_guess(self):
        month()
        asked, out, code = run("--retry-failed")
        self.assertEqual(asked, [])
        self.assertTrue(code and "last-run.json" in str(code), code)


if __name__ == "__main__":
    unittest.main(verbosity=1)
