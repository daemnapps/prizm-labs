import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

REPO = Path(os.environ.get("PRIZM_TEST_REPO", Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(REPO / "components/run-kit/run_kit"))
import text_executor as T


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"PRIZM_TEXT_EXECUTOR": "session",
            "PRIZM_TEXT_REQUESTS": self.temp.name, "PRIZM_TEXT_WAIT": "0",
            "PRIZM_TEXT_AUTHOR": "test-assistant"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def request(self, text="prompt", **kw):
        with self.assertRaises(T.Pending):
            T.call(text, "stage", **kw)
        return next(self.root.glob("*/request.json"))

    def test_session_calls_no_process_and_preserves_answer(self):
        with patch.object(T.subprocess, "run", side_effect=AssertionError("provider called")):
            request = self.request()
            T.answer(request, "written by the current assistant", "Codex")
            self.assertEqual(T.call("prompt", "stage"), "written by the current assistant")
            receipt = json.loads(request.with_name("receipt.json").read_text())
            self.assertEqual(receipt["author"], "Codex")

    def test_prompt_change_does_not_reuse_answer(self):
        request = self.request()
        T.answer(request, "old answer", "Claude")
        with self.assertRaises(T.Pending):
            T.call("changed prompt", "stage")

    def test_image_change_does_not_reuse_answer(self):
        img = self.root / "test.png"
        img.write_bytes(b"one")
        request = self.request(image=img)
        T.answer(request, "old image answer", "Codex")
        img.write_bytes(b"two")
        with self.assertRaises(T.Pending):
            T.call("prompt", "stage", image=img)

    def test_empty_invalid_json_and_foreign_receipts_refused(self):
        request = self.request(as_json=True)
        for text in ("", "not JSON"):
            with self.assertRaises(ValueError):
                T.answer(request, text, "test")
        T.answer(request, '{"ok":true}', "test")
        af = request.with_name("answer.json")
        value = json.loads(af.read_text()); value["request_id"] = "foreign"
        af.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            T.call("prompt", "stage", as_json=True)

    def test_command_protocol_and_resume(self):
        adapter = self.root / "adapter.py"
        adapter.write_text("import sys,json\nr=json.load(sys.stdin)\nprint('answer to '+r['prompt'])\n")
        with patch.dict(os.environ, {"PRIZM_TEXT_EXECUTOR": "command",
            "PRIZM_TEXT_COMMAND": json.dumps([sys.executable, str(adapter)])}):
            self.assertEqual(T.call("prompt", "stage"), "answer to prompt")
            adapter.unlink()
            self.assertEqual(T.call("prompt", "stage"), "answer to prompt")

    def test_command_failure_never_falls_back(self):
        with patch.dict(os.environ, {"PRIZM_TEXT_EXECUTOR": "command",
            "PRIZM_TEXT_COMMAND": json.dumps([sys.executable, "-c", "raise SystemExit(2)"])}):
            with self.assertRaisesRegex(RuntimeError, "no provider fallback"):
                T.call("prompt", "stage")
        self.assertFalse(list(self.root.glob("*/answer.json")))

    def test_concurrent_command_consumers_only_execute_once(self):
        from concurrent.futures import ThreadPoolExecutor
        count = self.root / "calls.txt"
        adapter = self.root / "count.py"
        adapter.write_text("import time,sys\nfrom pathlib import Path\n"
                           "p=Path(sys.argv[1])\np.write_text(p.read_text()+'x' if p.exists() else 'x')\n"
                           "time.sleep(.05)\nprint('one answer')\n")
        with patch.dict(os.environ, {"PRIZM_TEXT_EXECUTOR": "command",
            "PRIZM_TEXT_COMMAND": json.dumps([sys.executable,str(adapter),str(count)])}):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: T.call("same", "stage"), range(2)))
        self.assertEqual(results, ["one answer", "one answer"])
        self.assertEqual(count.read_text(), "x")

    def test_unknown_executor_rejected(self):
        with patch.dict(os.environ, {"PRIZM_TEXT_EXECUTOR": "typo"}):
            with self.assertRaises(ValueError): T.call("prompt", "stage")

    def function(self, file, name, globals_):
        tree = ast.parse((REPO / file).read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
        namespace = dict(TEXT=T, os=os, Path=Path, **globals_)
        exec(compile(ast.Module(body=[fn], type_ignores=[]), file, "exec"), namespace)
        return namespace[name]

    def test_all_integrations_select_session_before_legacy(self):
        # Execute the real function bodies with legacy/network calls made fatal.
        bad = lambda *a, **k: self.fail("Legacy provider called")
        cases = [
            ("tools/video-teardown/machine/run.py", "claude", ("prompt", self.root/"out.md"),
             {"PURE_TEXT":"", "CHATTER":(), "subprocess":subprocess, "_cli_model":bad}),
            ("tools/copywriter/machine/copy.py", "claude", ("prompt", "legacy-model"), {}),
            ("components/run-kit/run_kit/model.py", "call", ("prompt", "legacy-model"), {"PURE_TEXT":""}),
            ("components/quality-checks/marketing_chain_checks/viewer.py", "ask", ("prompt",),
             {"USED":set(), "_json":json.loads, "_claude_cli":bad}),
            ("components/quality-checks/marketing_chain_checks/viewer.py", "_ask_image", ("prompt", self.root/"image.png"),
             {"USED":set(), "_json":json.loads, "_hand":bad}),
        ]
        (self.root/"image.png").write_bytes(b"image")
        for file, name, args, globals_ in cases:
            with self.subTest(file=file, name=name):
                fn = self.function(file, name, globals_)
                with self.assertRaises(T.Pending): fn(*args)
                pending = [p for p in self.root.glob("*/request.json") if not p.with_name("answer.json").exists()]
                for p in pending:
                    as_json = json.loads(p.read_text())["as_json"]
                    T.answer(p, '{"ok":true}' if as_json else "Document content", "Codex")
                fn(*args)


if __name__ == "__main__":
    unittest.main()
