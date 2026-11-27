"""What ran (run_kit/ran.py), recorded in the credential door: off changes nothing; on, one line per call.

    python3 test_what_ran.py

No network, no model, no real login: a stand-in `claude` on PATH answers, the door's credentials and Codex are
replaced for the test, and the daily log goes to a temp folder.
"""
import importlib.util
import json
import os
import shutil
import stat
import sys
import tempfile
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_kit import claude_door, model, ran       # noqa: E402
from run_kit.stage import Chain                    # noqa: E402

STEPS = [{"key": "stage1", "name": "Read", "tier": "reads", "label": "record"}]
ME = str(Path(__file__).resolve().relative_to(ran.repo()))


def ok(reply="fine"):
    return lambda p, m: (0, reply, "")


class Switch:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        self.old, ran.RECORD = ran.RECORD, self.value

    def __exit__(self, *_):
        ran.RECORD = self.old


def fake_claude(folder, body):
    folder.mkdir(parents=True, exist_ok=True)
    f = folder / "claude"
    f.write_text("#!/bin/sh\ncat >/dev/null\n" + body + "\n")
    f.chmod(f.stat().st_mode | stat.S_IEXEC)


class WhatRan(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.run = self.tmp / "run"
        self.saved = {k: os.environ.get(k) for k in ("PATH", "DAEMN_HAND_DIR", "HAND_DIR", "DAEMN_HAND_FIRST")}
        for k in ("DAEMN_HAND_DIR", "HAND_DIR", "DAEMN_HAND_FIRST"):
            os.environ.pop(k, None)
        self.old_root, ran.LOG_ROOT = ran.LOG_ROOT, self.tmp / "daily"
        self.old_creds, self.old_codex = claude_door.credentials, claude_door.codex
        claude_door.credentials = lambda: [("the test login", {})]
        claude_door.codex = lambda *a, **k: None
        self.use_bin("echo answer")

    def tearDown(self):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        ran.LOG_ROOT = self.old_root
        claude_door.credentials, claude_door.codex = self.old_creds, self.old_codex
        shutil.rmtree(self.tmp, ignore_errors=True)

    def use_bin(self, body):
        b = self.tmp / ("bin-%d" % abs(hash(body)))
        fake_claude(b, body)
        os.environ["PATH"] = str(b) + ":" + (self.saved["PATH"] or "")

    def daily(self):
        out = []
        for f in sorted((self.tmp / "daily").rglob("*.jsonl")):
            out += ran.rows(f)
        return out

    # --- off ------------------------------------------------------------------------------------------------

    def test_ships_off(self):
        self.assertFalse(ran.RECORD, "the switch ships off; turning it on is its own commit")

    def test_off_writes_nothing_anywhere(self):
        with Switch(False):
            self.assertEqual(model.call("x", "m", runner=ok(), run_dir=self.run), "fine")
            self.assertEqual(claude_door.run(["--model", "m"], "x").stdout.strip(), "answer")
            self.assertEqual(model.call("x", "m", run_dir=self.run, tries=1), "answer")
        self.assertFalse((self.run / ran.FILE).exists())
        self.assertEqual(self.daily(), [])

    # --- the door -------------------------------------------------------------------------------------------

    def test_door_writes_one_line_to_the_daily_log(self):
        with Switch(True):
            r = claude_door.run(["--model", "claude-sonnet-5-5", "--output-format", "text"], "secret customer line")
        self.assertEqual(r.stdout.strip(), "answer")
        rows = self.daily()
        self.assertEqual(len(rows), 1)
        x = rows[0]
        self.assertEqual((x["route"], x["model_asked"], x["outcome"]), ("door", "claude-sonnet-5-5", "done"))
        self.assertEqual(x["effort"], "medium")
        self.assertEqual(x["answered_by"], "the test login")
        self.assertEqual(x["caller"], ME)
        self.assertEqual(x["prompt_sha256_12"], ran.fingerprint("secret customer line"))
        self.assertNotIn("secret customer line", json.dumps(rows), "never the prompt's text")

    def test_door_names_the_default_model_when_the_caller_named_none(self):
        with Switch(True):
            claude_door.run(["--output-format", "text"], "x")
        self.assertEqual(self.daily()[0]["model_asked"], claude_door._flags().model())

    def test_door_failure_is_recorded_and_the_result_returned_unchanged(self):
        self.use_bin("echo 'bad request' >&2; exit 1")
        with Switch(True):
            r = claude_door.run(["--model", "m"], "x")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.daily()[0]["outcome"], "failed")

    def test_door_loaded_by_path_shares_the_one_switch(self):
        spec = importlib.util.spec_from_file_location("door_by_path", HERE / "run_kit" / "claude_door.py")
        d = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(d)
        self.assertIs(d._ran(), ran)

    # --- model.call -----------------------------------------------------------------------------------------

    def test_model_call_through_the_door_writes_one_line_in_the_run_folder(self):
        with Switch(True):
            self.assertEqual(model.call("p", "claude-opus-5", label="stage1", run_dir=self.run, tier="designs",
                                        why="designs", prompt_file="stage1-read-v1-x.md", tries=1), "answer")
        rows = ran.rows(self.run)
        self.assertEqual(len(rows), 1, "the door's line only, never a second from model.call")
        x = rows[0]
        self.assertEqual((x["route"], x["step"], x["tier"], x["prompt_file"]), ("door", "stage1", "designs", "stage1-read-v1-x.md"))
        self.assertEqual(x["model_asked"], "claude-opus-5")
        self.assertEqual(self.daily(), [], "a known run folder keeps the line out of the daily log")

    def test_model_call_with_its_own_runner_writes_its_own_line(self):
        with Switch(True):
            model.call("p", "claude-sonnet-5-5", label="stage1", runner=ok("answer"), run_dir=self.run, tier="checks")
        x = ran.rows(self.run)[0]
        self.assertEqual((x["route"], x["outcome"], x["answered_by"], x["tier"]), ("model.call", "done", "the caller's runner", "checks"))
        self.assertEqual(x["chars_out"], len("answer"))

    def test_model_call_without_a_run_folder_goes_to_the_daily_log(self):
        with Switch(True):
            model.call("p", "m", label="s", runner=ok())
        rows = self.daily()
        self.assertEqual([(r["route"], r["step"]) for r in rows], [("model.call", "s")])
        self.assertEqual(rows[0]["caller"], ME)

    def test_failure_and_usage_limit_are_recorded_and_still_raised(self):
        with Switch(True):
            with self.assertRaises(model.StageFailed):
                model.call("x", "m", runner=lambda p, m: (1, "", "bad request"), run_dir=self.run, wait=0)
            with self.assertRaises(model.UsageLimit):
                model.call("x", "m", runner=lambda p, m: (1, "", "usage limit reached"), run_dir=self.run)
        self.assertEqual([r["outcome"] for r in ran.rows(self.run)], ["failed", "usage_limit"])

    def test_context_does_not_leak_into_the_next_call(self):
        with Switch(True):
            with self.assertRaises(model.StageFailed):
                model.call("x", "m", label="first", runner=lambda p, m: (1, "", "bad"), run_dir=self.run, wait=0)
            claude_door.run(["--model", "m"], "y")
        self.assertEqual(len(ran.rows(self.run)), 1)
        self.assertNotIn("step", self.daily()[0], "the next door call carries no leftover step")

    def test_a_record_that_cannot_be_written_never_breaks_the_step(self):
        blocker = self.tmp / "not-a-folder"
        blocker.write_text("a file where the run folder should be")
        with Switch(True):
            self.assertEqual(model.call("x", "m", runner=ok(), run_dir=blocker / "run"), "fine")
            self.assertEqual(model.call("x", "m", run_dir=blocker / "run", tries=1), "answer")

    def test_side_by_side_calls_each_get_a_whole_line(self):
        with Switch(True):
            ts = [threading.Thread(target=model.call, args=("p%d" % i, "m"),
                                   kwargs={"label": "s%d" % i, "runner": ok(), "run_dir": self.run})
                  for i in range(12)]
            [t.start() for t in ts]
            [t.join() for t in ts]
        self.assertEqual(sorted(r["step"] for r in ran.rows(self.run)), sorted("s%d" % i for i in range(12)))

    def test_chain_passes_its_run_folder_tier_and_prompt(self):
        pr = self.tmp / "prompts"
        pr.mkdir()
        (pr / "stage1-read-v1-x.md").write_text("Read this: {source}")
        with Switch(True):
            Chain("tool", "brand", "label", self.run, pr, STEPS, echo=lambda *_: None, runner=ok()).run("stage1", source="s")
        x = ran.rows(self.run)[0]
        self.assertEqual((x["step"], x["tier"], x["prompt_file"]), ("stage1", "reads", "stage1-read-v1-x.md"))


if __name__ == "__main__":
    unittest.main()
