#!/usr/bin/env python3
"""SI-63 (email interpreter pin): run_month.py and brief.py start their
children on the interpreter they run on (sys.executable), never whichever
python3 is first on PATH.

    python3 test_interpreter_pin.py

No network, no model, no key. The workspace is a temp folder (AI_WORKSPACE,
set before paths.py is imported); subprocess.run is replaced by a recorder.
"""
import ast
import io
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = Path(tempfile.mkdtemp(prefix="email-production-interpreter-pin-")) / "ws"
(WS / "brands" / "zz-test-brand" / "email-sms" / "sends").mkdir(parents=True)
(WS / "components").mkdir()
(WS / "runs").mkdir()
os.environ["AI_WORKSPACE"] = str(WS)            # before anything imports paths.py

sys.path.insert(0, str(HERE))
import brief  # noqa: E402
import run_month  # noqa: E402


class InterpreterPin(unittest.TestCase):
    def test_chain_argv_starts_with_this_interpreter(self):
        argv = brief.chain_argv({"id": "sep-01", "type": "house-special",
                                 "source": "old-email.md"}, "zz-test-brand")
        self.assertEqual(argv[0], sys.executable)
        self.assertEqual(argv[1], "email.py")

    def test_the_build_step_starts_with_this_interpreter(self):
        calls = []

        def recorder(argv, **kw):
            calls.append(list(argv))
            return types.SimpleNamespace(returncode=0, stdout="built\n", stderr="")

        saved = (run_month.subprocess.run, run_month.NO_IMAGES, run_month.PUSH)
        run_month.subprocess.run = recorder
        run_month.NO_IMAGES = True
        run_month.PUSH = False
        try:
            out = run_month.one_run("sep-01", ["chain-argv"], "zz-test-brand",
                                    io.StringIO())
        finally:
            run_month.subprocess.run, run_month.NO_IMAGES, run_month.PUSH = saved
        self.assertEqual(out[1], "done")
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1][:2], [sys.executable, "simple_email.py"])

    def test_no_bare_python3_list_left(self):
        for name in ("run_month.py", "brief.py"):
            tree = ast.parse((HERE / name).read_text(), filename=name)
            for node in ast.walk(tree):
                if isinstance(node, ast.List) and node.elts:
                    first = node.elts[0]
                    self.assertFalse(
                        isinstance(first, ast.Constant) and first.value == "python3",
                        f'{name}:{node.lineno} starts a list with a bare "python3"')


if __name__ == "__main__":
    unittest.main()
