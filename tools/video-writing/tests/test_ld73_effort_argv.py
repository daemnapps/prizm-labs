"""LD-73 (explicit effort): the 4cde writer's `claude -p` names its effort (2026-10-21).

A mini run's `claude -p` does not load the account's user settings, so without the flag it
wrote at the CLI's default effort. A fake `claude` first on PATH records the argv
writing_v2.claude_v2 actually starts; the teardown's _clean_env keeps PATH, so the fake is
the one found. No network, no spend, no real model.
"""
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TD = HERE.parents[1] / "video-teardown" / "machine"
sys.path.insert(0, str(HERE.parent / "machine"))
sys.path.insert(0, str(TD))
import writing_v2 as W    # noqa: E402

FAKE = """#!{python}
import json, sys
sys.stdin.read()
with open({record!r}, "w") as f:
    json.dump(sys.argv[1:], f)
print(json.dumps({{"result": "Scene one. She holds the tube up to the light.",
                  "usage": {{"input_tokens": 1, "output_tokens": 1}},
                  "total_cost_usd": 0, "is_error": False}}))
"""


class EffortReachesArgv(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.record = t / "argv.json"
        bin_dir = t / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "claude"
        fake.write_text(FAKE.format(python=sys.executable, record=str(self.record)))
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        self.run_dir = t / "run"
        (self.run_dir / "stages").mkdir(parents=True)
        (self.run_dir / "prompts").mkdir()
        (self.run_dir / "run.json").write_text(json.dumps({"brand": "brand-a", "stages": {}}))
        names = ("PATH", "CHAIN_EFFORT", "CLAUDE_CODE_OAUTH_TOKEN_CHAIN", "ANTHROPIC_API_KEY_CHAIN",
                 "VT_CLAUDE_TIMEOUT")
        self.prev = {k: os.environ.get(k) for k in names}
        os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
        os.environ.pop("CHAIN_EFFORT", None)
        # values that are not keys, so _clean_env never goes to the key file for one
        os.environ["CLAUDE_CODE_OAUTH_TOKEN_CHAIN"] = "not-a-token"
        os.environ["ANTHROPIC_API_KEY_CHAIN"] = "not-a-key"
        os.environ["VT_CLAUDE_TIMEOUT"] = "60"
        self.hand = W._HAND[0]
        W._HAND[0] = None
        W._CURRENT.clear()

    def tearDown(self):
        for k, v in self.prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        W._HAND[0] = self.hand
        W._CURRENT.clear()
        self.tmp.cleanup()

    def argv(self):
        out = self.run_dir / "stages" / "4cde-test.md"
        W.claude_v2("Write the scenes.", out, "opus")
        self.assertTrue(out.read_text().startswith("Scene one."), "the fake's answer was written")
        return json.loads(self.record.read_text())

    def test_clean_env_keeps_path(self):
        import run as R
        self.assertEqual(R._clean_env().get("PATH"), os.environ["PATH"])

    def test_effort_is_medium(self):
        a = self.argv()
        self.assertEqual(a[0], "-p")
        self.assertIn("--effort", a)
        self.assertEqual(a[a.index("--effort") + 1], "medium")
        self.assertEqual(a.count("--effort"), 1)

    def test_no_environment_knob(self):
        # the team 2026-10-21: "Don't add more variables" -- CHAIN_EFFORT does not move it
        os.environ["CHAIN_EFFORT"] = "max"
        a = self.argv()
        self.assertEqual(a[a.index("--effort") + 1], "medium")

    def test_nothing_else_changed(self):
        a = self.argv()
        i = a.index("--effort")
        rest = a[:i] + a[i + 2:]
        import run as R
        self.assertEqual(rest, ["-p", "--model", "opus", "--output-format", "json",
                                "--allowed-tools", "", "--append-system-prompt", R.PURE_TEXT])


if __name__ == "__main__":
    unittest.main()
