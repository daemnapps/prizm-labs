#!/usr/bin/env python3
"""The mini's door into local-studio's upscale job (lab_entry.py), checked
without a model: lab-run's --name value pairs become `local.py upscale <input>
-o $OUT/<label>/<stem>-up<suffix> --scale N`, --dry_run yes prints that and
runs nothing, and refusals exit 2 before anything runs (LD-7 (four more doors)).
local.py is stubbed through `run`; the checkout is a temp folder.

    /usr/bin/python3 components/local-studio/test_lab_entry.py
"""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lab_entry as E                # noqa: E402

PICTURE = "runs/image-production/testbrand/ip-01/hero.png"


def quiet(fn, *a, **kw):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        got = fn(*a, **kw)
    return got, out.getvalue()


class Door(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.repo = self.tmp / "repo"
        (self.repo / PICTURE).parent.mkdir(parents=True)
        (self.repo / PICTURE).write_text("x")
        self.out = self.tmp / "lab-out" / "mini-1"
        self.env = {"BRAND": "testbrand", "OUT": str(self.out), "PATH": "/usr/bin", "KEEP": "me"}
        self.calls = []

    def tearDown(self):
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    def stub(self, rc=0):
        def run(cmd, env=None):
            self.calls.append((cmd, env))
            return rc
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

    def upscale(self, label, scale):
        return [sys.executable, str(HERE / "local.py"), "upscale", str(self.repo / PICTURE),
                "-o", str(self.out / label / "hero-up.png"), "--scale", scale]


class Upscale(Door):
    def test_maps_to_local_py_upscale(self):
        rc, text = self.door(["--input", PICTURE, "--label", "up-01", "--scale", "4", "--dry_run", "no"])
        self.assertEqual(rc, 0, text)
        self.assertEqual(len(self.calls), 1)
        cmd, env = self.calls[0]
        self.assertEqual(cmd, self.upscale("up-01", "4"))
        self.assertTrue((self.out / "up-01").is_dir(), "the output folder is made for -o")
        self.assertEqual(env["KEEP"], "me")

    def test_scale_defaults_to_2_and_dry_run_to_no(self):
        rc, text = self.door(["--input", PICTURE, "--label", "up-02"])
        self.assertEqual(rc, 0, text)
        self.assertEqual(self.calls[0][0], self.upscale("up-02", "2"))

    def test_nothing_passed_for_the_model_dir_or_engine(self):
        self.door(["--input", PICTURE, "--label", "up-03"])
        cmd = self.calls[0][0]
        for flag in ("--engine", "--esrgan-model", "--softness", "--brand", "--dry-run"):
            self.assertNotIn(flag, cmd)

    def test_child_exit_code_is_returned(self):
        rc, _ = self.door(["--input", PICTURE, "--label", "up-04"], run=self.stub(rc=6))
        self.assertEqual(rc, 6)

    def test_hyphenated_dry_run_reads_as_underscored(self):
        rc, text = self.door(["--input", PICTURE, "--label", "up-05", "--dry-run", "yes"])
        self.assertEqual(rc, 0, text)
        self.assertEqual(self.calls, [])


class DryRun(Door):
    def test_dry_run_yes_prints_the_command_and_runs_nothing(self):
        for i, yes in enumerate(("yes", "true", "1", "YES")):
            label = f"dry-{i}"
            rc, text = self.door(["--input", PICTURE, "--label", label, "--scale", "4", "--dry_run", yes])
            self.assertEqual(rc, 0, text)
            self.assertEqual(self.calls, [], "a dry run runs nothing")
            self.assertIn(" ".join(self.upscale(label, "4")), text)
            self.assertFalse(self.out.exists(), "a dry run makes nothing")


class Refusals(Door):
    def test_engine_is_refused(self):
        self.refused(["--input", PICTURE, "--label", "x", "--engine", "seedvr2"],
                     "--engine is refused by this door")
        self.refused(["--input", PICTURE, "--label", "x", "--engine", "esrgan"],
                     "--engine is refused by this door")

    def test_everything_else_is_refused(self):
        for name in ("--esrgan_model", "--softness", "--output", "--o", "--model", "--brand"):
            self.refused(["--input", PICTURE, "--label", "x", name, "v"], "unknown argument(s)")

    def test_input_outside_the_checkout_is_refused(self):
        self.refused(["--input", "/etc/hosts", "--label", "x"], "outside this checkout")
        self.refused(["--input", "../outside.png", "--label", "x"], "'..' part")
        outside = self.tmp / "outside.png"
        outside.write_text("x")
        self.refused(["--input", str(outside), "--label", "x"], "outside this checkout")

    def test_input_missing_not_there_or_a_folder(self):
        self.refused(["--label", "x"], "--input is required")
        self.refused(["--input", "runs/none.png", "--label", "x"], "is not there")
        self.refused(["--input", "runs", "--label", "x"], "is not a file")

    def test_scale_is_2_or_4(self):
        for bad in ("3", "8", "two", "0"):
            self.refused(["--input", PICTURE, "--label", "x", "--scale", bad], "2 or 4")

    def test_dry_run_must_say_yes_or_no(self):
        self.refused(["--input", PICTURE, "--label", "x", "--dry_run", "maybe"], "say yes or no")

    def test_value_that_would_read_as_a_flag(self):
        self.refused(["--input", PICTURE, "--label", "--engine"], "would read as a flag")

    def test_missing_out(self):
        self.refused(["--input", PICTURE, "--label", "x"], "$OUT", env={"BRAND": "testbrand"})

    def test_label_missing_malformed_or_taken(self):
        self.refused(["--input", PICTURE], "--label")
        self.refused(["--input", PICTURE, "--label", "../up"], "plain name")
        (self.out / "taken").mkdir(parents=True)
        rc, text = self.door(["--input", PICTURE, "--label", "taken"])
        self.assertEqual(rc, 2, text)
        self.assertIn("already exists", text)
        self.assertEqual(self.calls, [])

    def test_not_in_pairs_or_twice(self):
        self.refused(["--input"], "pairs")
        self.refused(["--label", "a", "--label", "b"], "given twice")


class RealFile(unittest.TestCase):
    def test_shebang_is_the_minis_python(self):
        self.assertEqual((HERE / "lab_entry.py").read_text().splitlines()[0], "#!/usr/bin/python3")

    def test_real_door_refuses_without_out_and_runs_nothing(self):
        env = {k: v for k, v in os.environ.items() if k not in ("BRAND", "OUT")}
        r = subprocess.run([sys.executable, str(HERE / "lab_entry.py"), "--label", "x"],
                           env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("$OUT", r.stdout)


if __name__ == "__main__":
    unittest.main()
