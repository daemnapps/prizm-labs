#!/usr/bin/env python3
"""The mini's door into the Ad Desk read (lab_entry.py), checked without the
warehouse or Meta: lab-run's --name value pairs become `analyze.py <brand>`
then `desk_page.py <brand> --out`, the report lands in $OUT/<label>/, and the
door never runs decide.py or act.py (LD-7 (four more doors)). Both children are
stubbed through `run`; the checkout is a temp folder.

    /usr/bin/python3 components/media-buying/machine/test_lab_entry.py
"""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lab_entry as E                # noqa: E402

BRAND = "testbrand"
ALLOWED = ("analyze.py", "desk_page.py")


def quiet(fn, *a, **kw):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        got = fn(*a, **kw)
    return got, out.getvalue()


class Door(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.out = self.tmp / "lab-out" / "mini-1"
        self.env = {"BRAND": BRAND, "OUT": str(self.out), "PATH": "/usr/bin", "KEEP": "me"}
        self.calls = []

    def tearDown(self):
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    def stub(self, rc=None, writes=True):
        """The children, stubbed: analyze.py writes the report where analyze.py would."""
        rc = rc or {}

        def run(cmd, env=None):
            self.calls.append((cmd, env))
            script = Path(cmd[1]).name
            if script == "analyze.py" and writes:
                asof = cmd[cmd.index("--asof") + 1] if "--asof" in cmd else \
                    str(date.today() - timedelta(days=1))
                made = self.repo / "runs" / "media-buying" / cmd[2] / asof
                made.mkdir(parents=True)
                (made / "report.json").write_text('{"asof": "%s"}' % asof)
                (made / "REPORT.md").write_text("# report")
            if script == "desk_page.py":
                Path(cmd[cmd.index("--out") + 1]).write_text("<html>")
            return rc.get(script, 0)
        return run

    def door(self, argv, env=None, run=None):
        return quiet(E.main, argv, self.env if env is None else env,
                     run=run or self.stub(), repo=self.repo)

    def refused(self, argv, says, env=None):
        rc, text = self.door(argv, env=env)
        self.assertEqual(rc, 2, text)
        self.assertIn(says, text)
        self.assertEqual(self.calls, [], "nothing may run on a refusal")
        self.assertFalse(self.out.exists(), "$OUT is not even made on a refusal")
        return text


class TwoCommands(Door):
    def test_analyze_then_desk_page_with_the_brand_positional(self):
        rc, text = self.door(["--asof", "2026-10-16", "--label", "desk-01"])
        self.assertEqual(rc, 0, text)
        dest = self.out / "desk-01"
        self.assertEqual([c for c, _ in self.calls], [
            [sys.executable, str(HERE / "analyze.py"), BRAND, "--asof", "2026-10-16"],
            [sys.executable, str(HERE / "desk_page.py"), BRAND, "--out", str(dest / "desk.html")],
        ])
        self.assertEqual((dest / "report.json").read_text(), '{"asof": "2026-10-16"}')
        self.assertEqual((dest / "REPORT.md").read_text(), "# report")
        self.assertTrue((dest / "desk.html").is_file())
        self.assertEqual(self.calls[0][1]["KEEP"], "me")

    def test_no_asof_leaves_it_to_analyze_and_reads_yesterday(self):
        rc, text = self.door(["--label", "desk-02"])
        self.assertEqual(rc, 0, text)
        self.assertEqual(self.calls[0][0], [sys.executable, str(HERE / "analyze.py"), BRAND])
        yesterday = str(date.today() - timedelta(days=1))
        self.assertIn(yesterday, (self.out / "desk-02" / "report.json").read_text())

    def test_analyze_failing_stops_before_the_page(self):
        rc, text = self.door(["--label", "desk-03"], run=self.stub(rc={"analyze.py": 4}, writes=False))
        self.assertEqual(rc, 4, text)
        self.assertEqual([Path(c[1]).name for c, _ in self.calls], ["analyze.py"])
        self.assertIn("desk_page.py not run", text)

    def test_page_exit_code_is_returned(self):
        rc, _ = self.door(["--label", "desk-04"], run=self.stub(rc={"desk_page.py": 3}))
        self.assertEqual(rc, 3)

    def test_missing_report_is_said_and_fails(self):
        rc, text = self.door(["--label", "desk-05"], run=self.stub(writes=False))
        self.assertEqual(rc, 1, text)
        self.assertIn("report.json, REPORT.md not found", text)


class Refusals(Door):
    def test_missing_brand_or_out_exits_2(self):
        self.refused(["--label", "x"], "$BRAND", env={"OUT": str(self.out)})
        self.refused(["--label", "x"], "$OUT", env={"BRAND": BRAND})
        self.refused(["--label", "x"], "$BRAND and $OUT", env={})

    def test_decide_and_act_never_run(self):
        attempts = [
            ["--decide", "F1"], ["--act", "F1"], ["--label", "act"], ["--label", "decide"],
            ["--label", "act-1"], ["--label", "decide.py"], ["--asof", "act.py"],
            ["--label", "x", "--act_go", "yes"], ["components/media-buying/machine/act.py"],
            ["--label", "ACT"], ["--Decide", "1"],
        ]
        for argv in attempts:
            self.calls = []
            text = self.refused(argv, "this door reads the desk only")
            self.assertTrue("act" in text or "decide" in text, text)

    def test_words_that_merely_contain_act_are_not_refused_for_it(self):
        rc, text = self.door(["--label", "exact-1"])
        self.assertEqual(rc, 0, text)

    def test_every_command_is_analyze_or_desk_page(self):
        self.door(["--asof", "2026-10-01", "--label", "ok"])
        self.assertEqual(len(self.calls), 2)
        for cmd, _ in self.calls:
            self.assertIn(Path(cmd[1]).name, ALLOWED)
            for token in cmd:
                self.assertNotIn("decide.py", token)
                self.assertNotIn("act.py", Path(token).name)

    def test_unknown_arguments(self):
        self.refused(["--label", "x", "--model", "m"], "unknown argument(s) --model")
        self.refused(["--label", "x", "--out", "/tmp/y"], "unknown argument(s) --out")
        self.refused(["--brand", "other", "--label", "x"], "$BRAND comes from lab-run")

    def test_not_in_pairs_or_twice(self):
        self.refused(["--label"], "pairs")
        self.refused(["label", "x"], "is not a --name")
        self.refused(["--label", "a", "--label", "b"], "given twice")

    def test_asof_must_be_a_real_date(self):
        for bad in ("20261001", "2026-10-1", "yesterday", "2026-13-01", "2026-02-30"):
            self.refused(["--asof", bad, "--label", "x"], "--asof")

    def test_label_missing_malformed_or_taken(self):
        self.refused(["--asof", "2026-10-01"], "--label")
        self.refused(["--label", "../up"], "plain name")
        (self.out / "taken").mkdir(parents=True)
        rc, text = self.door(["--label", "taken"])
        self.assertEqual(rc, 2, text)
        self.assertIn("already exists", text)
        self.assertEqual(self.calls, [])

    def test_bad_brand(self):
        self.refused(["--label", "x"], "plain name", env={"BRAND": "../other", "OUT": str(self.out)})


class RealFile(unittest.TestCase):
    def test_shebang_is_the_minis_python(self):
        self.assertEqual((HERE / "lab_entry.py").read_text().splitlines()[0], "#!/usr/bin/python3")

    def test_real_door_refuses_without_brand_and_runs_nothing(self):
        env = {k: v for k, v in os.environ.items() if k not in ("BRAND", "OUT")}
        r = subprocess.run([sys.executable, str(HERE / "lab_entry.py"), "--label", "x"],
                           env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("$BRAND", r.stdout)


if __name__ == "__main__":
    unittest.main()
