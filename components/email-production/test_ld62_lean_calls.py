#!/usr/bin/env python3
"""LD-62 (lean model calls): every model call email-production makes runs lean —
from a fresh temp folder outside the repo, with --tools "", --strict-mcp-config,
--setting-sources "" and one explicit --effort — and the prompt it sends is
byte-identical to today's.

    python3 test_ld62_lean_calls.py

Offline: a fake `claude` first on PATH records its argv, cwd and stdin and
prints a minimal answer. No model call, no network, nothing written outside a
temp folder.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Run as a script, this folder is sys.path[0]; its runner, named `email` until LD-49
# (stdlib-name renames), answered `import email`: pin the standard library's package first, then put HERE back.
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != HERE]
import email.message  # noqa: E402,F401
import importlib.util  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
import unittest  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="ld62-lean-calls-")).resolve()
os.environ["AI_WORKSPACE"] = str(TMP / "ws")      # before anything imports paths.py

REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "components" / "run-kit"))
import lean_call                                     # noqa: E402
import section_email as SE                           # noqa: E402
from run_kit import model as M                       # noqa: E402

BRAND = "brand-a"
BIN = TMP / "bin"
LOG = TMP / "calls.jsonl"
REPLY = BIN / "reply.txt"        # what the fake answers
LIMIT = BIN / "limit"            # present: the fake is out of usage
SLEEP = BIN / "sleep"            # present: the fake hangs (a timeout)

FAKE = """#!{exe}
import json, os, sys, time
from pathlib import Path
BIN = Path({bin!r})
with open({log!r}, "a") as f:
    f.write(json.dumps({{"argv": sys.argv[1:], "cwd": os.getcwd(),
                        "stdin": sys.stdin.buffer.read().decode("utf-8")}}) + "\\n")
if (BIN / "sleep").exists():
    time.sleep(10)
if (BIN / "limit").exists():
    print("You've hit your usage limit")
    sys.exit(1)
sys.stdout.write((BIN / "reply.txt").read_text() if (BIN / "reply.txt").exists() else "OK")
"""

LEAN = ["--tools", "", "--strict-mcp-config", "--setting-sources", ""]
EFFORTS = ((None, "medium"), ("max", "medium"), ("turbo", "medium"))   # no knob: CHAIN_EFFORT never moves it


def load(rel, name):
    """By file, under a distinct name (the runner's old name `email` collided with the stdlib package)."""
    spec = importlib.util.spec_from_file_location(name, HERE / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


EM = load("email_line.py", "email_production_email_ld62")
CL = load("pull/classify.py", "email_production_classify_ld62")
PR = load("design/promises.py", "email_production_promises_ld62")


def setUpModule():
    BIN.mkdir(parents=True, exist_ok=True)
    fake = BIN / "claude"
    fake.write_text(FAKE.format(exe=sys.executable, bin=str(BIN), log=str(LOG)))
    fake.chmod(0o755)
    os.environ["PATH"] = str(BIN) + os.pathsep + os.environ.get("PATH", "")


def calls():
    if not LOG.exists():
        return []
    return [json.loads(x) for x in LOG.read_text().splitlines() if x.strip()]


class Lean(unittest.TestCase):

    def setUp(self):
        for f in (LOG, REPLY, LIMIT, SLEEP):
            if f.exists():
                f.unlink()
        self.env = {k: os.environ.get(k) for k in ("CHAIN_EFFORT", "DAEMN_HAND_DIR")}
        os.environ.pop("CHAIN_EFFORT", None)
        os.environ.pop("DAEMN_HAND_DIR", None)

    def tearDown(self):
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def one_call(self):
        got = calls()
        self.assertEqual(len(got), 1, got)
        LOG.unlink()
        return got[0]

    def assert_lean(self, call, today, effort):
        argv = call["argv"]
        self.assertEqual(argv[:len(today)], today, "today's argv is kept, in order")
        self.assertEqual(argv[len(today):], LEAN + ["--effort", effort], "only the lean flags are added")
        for flag, val in (("--tools", ""), ("--setting-sources", ""), ("--effort", effort)):
            self.assertEqual(argv[argv.index(flag) + 1], val, flag)
        self.assertIn("--strict-mcp-config", argv)
        self.assertEqual(argv.count("--effort"), 1)
        self.assertNotIn("--system-prompt", argv)
        self.assertNotIn("--bare", argv)
        cwd = Path(call["cwd"]).resolve()
        self.assertNotEqual(cwd, REPO.resolve())
        self.assertNotIn(REPO.resolve(), cwd.parents, "the call runs outside the repo")
        self.assertFalse(cwd.exists(), "the temp folder is removed after the call")

    def each_effort(self, drive, today, sent):
        for value, want in EFFORTS:
            with self.subTest(CHAIN_EFFORT=value):
                if value is None:
                    os.environ.pop("CHAIN_EFFORT", None)
                else:
                    os.environ["CHAIN_EFFORT"] = value
                expect = drive()
                call = self.one_call()
                self.assert_lean(call, today, want)
                self.assertEqual(call["stdin"], sent if expect is None else expect, "the prompt is byte-identical")

    # ---------------------------------------------------------------- the sites

    def test_email_claude(self):
        prompt = "Write the email.\n  {keep} the spacing \n\n"
        self.each_effort(lambda: self.assertEqual(EM.claude(prompt, "model-x", label="3"), "OK"),
                         ["-p", "--model", "model-x", "--output-format", "text"],
                         prompt + "\n\nReturn only the deliverable. No tools, no preamble.")

    def test_section_email_8s(self):
        REPLY.write_text("```SECTIONS\n[]\n```\n")
        fmt = SE.FORMATS["_default"]
        out = TMP / "run-8s" / "deliverable"
        out.mkdir(parents=True, exist_ok=True)

        def drive():
            got = SE.run_8s({"headline": "A line"}, fmt, SE.resolved_format(fmt, []),
                            "(none on file)", out)
            self.assertEqual(got, [])
            return (out / "stage8s--prompt-sent.md").read_text()
        self.each_effort(drive, ["-p", "--model", SE.SECTIONS_MODEL, "--output-format", "text"], None)

    def test_classify_claude(self):
        REPLY.write_text("[]")
        prompt = "Tag these.\n--- EMAIL 1\nsubject: x\n"
        self.each_effort(lambda: self.assertEqual(CL.claude(prompt, "model-y"), "[]"),
                         ["-p", "--model", "model-y", "--output-format", "text"], prompt)

    def test_design_runner_through_run_kit_call(self):
        prompt = "Lay it out.\n{json}\n"
        self.each_effort(
            lambda: self.assertEqual(M.call(prompt, "model-z", label="design1-x",
                                            runner=lean_call.design_runner(M)), "OK"),
            ["-p", "--model", "model-z", "--output-format", "text", "--append-system-prompt", M.PURE_TEXT],
            prompt)

    def test_design_promise_check_runs_lean(self):
        """A real design-line site (design/promises.py check), reaching lean_call by file."""
        REPLY.write_text('{"promises": []}')
        run = TMP / "runs" / BRAND / "send-1"
        (run / "design").mkdir(parents=True, exist_ok=True)
        spec = {"brand": BRAND, "sections": [{"s": "hero", "title": "A line"}]}

        def drive():
            got = PR.check(run, spec, {"job": "x"}, {"headline": "A line"})
            self.assertEqual(got["promises"], [])
            return (run / "design" / "design3--prompt.md").read_text()
        p = None
        for value, want in EFFORTS:
            with self.subTest(CHAIN_EFFORT=value):
                if value is None:
                    os.environ.pop("CHAIN_EFFORT", None)
                else:
                    os.environ["CHAIN_EFFORT"] = value
                p = drive()
                call = self.one_call()
                model, _ = M.pick("checks", len(p))
                self.assert_lean(call, ["-p", "--model", model, "--output-format", "text",
                                        "--append-system-prompt", M.PURE_TEXT], want)
                self.assertEqual(call["stdin"], p)
        self.assertIs(PR.lean(), lean_call, "one lean_call module for the whole process")

    # ---------------------------------------------------------------- failures

    def test_usage_limit_email_claude(self):
        LIMIT.write_text("on")
        with self.assertRaises(SystemExit) as e:
            EM.claude("p", "model-x", label="3")
        self.assertTrue(str(e.exception.code).startswith("USAGE LIMIT — stage"), e.exception.code)
        self.assertFalse(Path(self.one_call()["cwd"]).exists())

    def test_usage_limit_run_kit_call(self):
        LIMIT.write_text("on")
        with self.assertRaises(M.UsageLimit):
            M.call("p", "model-z", label="design2-x", runner=lean_call.design_runner(M))
        self.assertFalse(Path(self.one_call()["cwd"]).exists())

    def test_timeout_propagates_and_cleans_up(self):
        SLEEP.write_text("on")
        with self.assertRaises(subprocess.TimeoutExpired):
            lean_call.runner(M, timeout=1)("p", "model-z")
        self.assertFalse(Path(self.one_call()["cwd"]).exists())

    def test_session_hand_takes_no_runner(self):
        hand = TMP / "hand"
        os.environ["DAEMN_HAND_DIR"] = str(hand)
        self.assertIsNone(lean_call.design_runner(M))
        with self.assertRaises(M.StageFailed):
            M.call("p", "model-z", label="design1-x", runner=lean_call.design_runner(M))
        self.assertEqual(calls(), [], "the fake claude is never called under the session hand")
        self.assertTrue(list(hand.glob("*.prompt.md")), "the prompt is left for the session hand")

    def test_existing_effort_is_kept_alone(self):
        os.environ["CHAIN_EFFORT"] = "max"
        lean_call.run(["claude", "-p", "--effort", "low"], input="p", capture_output=True, text=True)
        argv = self.one_call()["argv"]
        self.assertEqual(argv.count("--effort"), 1)
        self.assertEqual(argv[argv.index("--effort") + 1], "low")
        self.assertEqual(argv, ["-p", "--effort", "low"] + LEAN)

    def test_effort_is_runkit_medium(self):
        # the team 2026-10-21: email runs at the chains' one level, medium, with no knob
        for value in ("low", "xhigh", "Max", "", "hi gh"):
            os.environ["CHAIN_EFFORT"] = value
            self.assertEqual(lean_call.effort(), "medium", value)
        from run_kit import claude_flags
        self.assertEqual(lean_call.effort(), claude_flags.EFFORT)


if __name__ == "__main__":
    unittest.main()
