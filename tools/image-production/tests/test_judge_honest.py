#!/usr/bin/env python3
"""SI-147 (image engine honest): a picture passes only when the judge answered
every test it was asked, a missing judge key is a hold, and the hand-run plate
builder reads only the overall verdict.

    python3 tools/image-production/tests/test_judge_honest.py

Stdlib `unittest`, Python 3.9. **No network, no model, no key** — every judge
is a stub caller, and the one real caller used (`google_caller`) is handed an
empty key so it stops before it builds a request. The two `build.py` files are
read by path and only their `passed()` is compiled: importing them whole would
run their `paths.py`, which discovers the Drive mount and (image-teardown)
carries lab files over at import time. Nothing is written outside `tempfile`.
"""
import ast
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENTS = HERE.parent.parent
sys.path.append(str(HERE.parent))                  # APPEND — never insert at 0
from image_production import judge as J            # noqa: E402

TESTS = ["The first thing is true. It is checked.",
         "The second thing is true. It is checked too."]
ENTRY = {"vendor_model": "stub", "key": "GEMINI_API_KEY"}

BUILDS = {
    "image-production": COMPONENTS / "image-production" / "static" / "tools" / "build.py",
    "image-teardown": COMPONENTS / "image-teardown" / "tools" / "build.py",
}


def saying(reply):
    """A stub judge that answers with `reply` (a dict, sent as JSON)."""
    def caller(prompt, img_path, entry):
        return json.dumps(reply)
    return caller


def passed_from(path):
    """`passed()` out of a build.py, compiled from the file on disk — the
    function as written there, without running the module's imports."""
    tree = ast.parse(path.read_text(), str(path))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "passed")
    ns = {"re": re}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), ns)
    return ns["passed"]


class TestJudgeAnswersEveryTest(unittest.TestCase):
    def seen(self, caller):
        return J.seen("picture.png", TESTS, ENTRY, caller=caller)

    def test_an_empty_reply_is_a_reject(self):
        fails, _raw = self.seen(saying({}))
        self.assertTrue(fails, "a {} reply answered nothing and must not pass")
        self.assertTrue(any("judge answered 0 of 2 tests" in f for f in fails), fails)

    def test_one_answer_of_two_is_a_reject_naming_test_2(self):
        fails, _raw = self.seen(saying({"results": [
            {"test": 1, "verdict": "PASS", "evidence": "seen"}]}))
        self.assertEqual(len(fails), 1, fails)
        self.assertIn("judge answered 1 of 2 tests", fails[0])
        self.assertIn("test 2 ", fails[0])
        self.assertIn("The second thing is true", fails[0])
        self.assertNotIn("test 1 ", fails[0])

    def test_two_of_two_pass_is_a_pass(self):
        fails, raw = self.seen(saying({"results": [
            {"test": 1, "verdict": "PASS", "evidence": "seen"},
            {"test": 2, "verdict": "PASS", "evidence": "seen"}]}))
        self.assertEqual(fails, [])
        self.assertIn('"results"', raw)

    def test_a_non_list_results_is_a_reject(self):
        fails, _raw = self.seen(saying({"results": {"test": 1, "verdict": "PASS"}}))
        self.assertIn("judge returned no list of results", fails)
        self.assertEqual(sum("was asked and not answered" in f for f in fails), 2, fails)

    def test_a_failed_test_still_names_its_reason(self):
        fails, _raw = self.seen(saying({"results": [
            {"test": 1, "verdict": "FAIL", "evidence": "a rival logo"},
            {"test": 2, "verdict": "PASS", "evidence": "seen"}]}))
        self.assertEqual(fails, ["The first thing is true — a rival logo"])


class TestJudgeThatDidNotRun(unittest.TestCase):
    def test_a_caller_raising_systemexit_is_a_reject_not_an_exit(self):
        def no_key(prompt, img_path, entry):
            raise SystemExit("no GEMINI_API_KEY on this machine")
        fails, raw = J.seen("picture.png", TESTS, ENTRY, caller=no_key)
        self.assertEqual(raw, "")
        self.assertEqual(len(fails), 1, fails)
        self.assertTrue(fails[0].startswith("judge did not run: SystemExit: "), fails)
        self.assertIn("no GEMINI_API_KEY", fails[0])

    def test_the_real_caller_with_no_key_is_a_reject(self):
        """The live door: `google_caller` exits before any request when the
        key is missing. That exit now comes back as a hold."""
        def door(prompt, img_path, entry):
            return J.google_caller(prompt, img_path, entry, transport=self.fail, key="")
        fails, _raw = J.seen("picture.png", TESTS, ENTRY, caller=door)
        self.assertEqual(len(fails), 1, fails)
        self.assertIn("judge did not run: SystemExit", fails[0])

    def fail(self, *a):
        raise AssertionError("no request may be sent without a key")


PLATE_CHECK = """# Judge the plates

## plate-a

**Verdict:** FAIL

- `PASS` — plate is a real image — 1080x1920
- `FAIL` — the headline band is empty — text found in it

**What the next generation must change:** clear the band

## plate-b

**Verdict:** PASS

- `PASS` — plate is a real image — 1080x1920
- `PASS` — the headline band is empty — flat
"""


class TestBuildReadsTheVerdictLine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="judge-honest-")
        self.run_dir = Path(self.tmp.name)
        (self.run_dir / "out").mkdir()
        (self.run_dir / "out" / "08-plate-check.md").write_text(PLATE_CHECK)

    def tearDown(self):
        self.tmp.cleanup()

    def test_both_build_files_read_only_the_overall_verdict(self):
        for name, path in BUILDS.items():
            with self.subTest(build=name):
                passed = passed_from(path)
                self.assertFalse(passed(self.run_dir, "plate-a"),
                                 f"{name}: an overall FAIL with a PASS row must not pass")
                self.assertTrue(passed(self.run_dir, "plate-b"),
                                f"{name}: an overall PASS must pass")
                self.assertFalse(passed(self.run_dir, "plate-c"),
                                 f"{name}: a plate with no block must not pass")


if __name__ == "__main__":
    unittest.main(verbosity=2)
