"""SI-90 (Pillow test guard): the edit-map line's two Pillow-bound test files skip, named, on a machine without
Pillow instead of erroring at import — and with Pillow they run exactly as before."""
import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
RENDER_MAP = HERE / "test_render_map.py"
THUMBS = HERE / "test_thumbs.py"

# Runs in a fresh interpreter so this process's sys.modules stays clean. argv: <test file> <block_pil 0|1>.
CHILD = r"""
import importlib.util, io, json, sys, unittest
path, block = sys.argv[1], sys.argv[2] == "1"
if block:
    sys.modules["PIL"] = None          # makes `import PIL` raise ImportError even where Pillow is installed
spec = importlib.util.spec_from_file_location("si90_guard_target", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
suite = unittest.defaultTestLoader.loadTestsFromModule(mod)
res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
print(json.dumps({"run": res.testsRun, "skipped": len(res.skipped), "ok": res.wasSuccessful()}))
"""


def run_module(path, block_pil):
    p = subprocess.run([sys.executable, "-c", CHILD, str(path), "1" if block_pil else "0"],
                       capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise AssertionError(f"{path.name} did not load (exit {p.returncode}):\n{p.stderr}")
    return json.loads(p.stdout.strip().splitlines()[-1])


def have_pil():
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


class WithoutPillow(unittest.TestCase):
    def test_render_map_skips_without_pil(self):
        r = run_module(RENDER_MAP, True)
        self.assertEqual(r, {"run": 6, "skipped": 6, "ok": True})

    def test_thumbs_skips_without_pil(self):
        r = run_module(THUMBS, True)
        self.assertEqual(r, {"run": 3, "skipped": 3, "ok": True})


class WithPillow(unittest.TestCase):
    def test_runs_when_pil_is_there(self):
        if not have_pil():
            self.skipTest("Pillow not installed here — the with-Pillow half is checked on a machine that has it")
        for path, n in ((RENDER_MAP, 6), (THUMBS, 3)):
            r = run_module(path, False)
            self.assertEqual(r, {"run": n, "skipped": 0, "ok": True}, path.name)


class NothingElseMoved(unittest.TestCase):
    def test_no_assertion_was_touched(self):
        # counted at HEAD 42891c2551 with `grep -c self.assert`
        for path, n, cls in ((RENDER_MAP, 14, "Flatten"), (THUMBS, 5, "Placement")):
            src = path.read_text()
            self.assertEqual(sum("self.assert" in line for line in src.splitlines()), n, path.name)
            cases = [c for c in ast.parse(src).body if isinstance(c, ast.ClassDef)
                     and any(ast.unparse(b) == "unittest.TestCase" for b in c.bases)]
            self.assertEqual([c.name for c in cases], [cls], path.name)
            guards = [d for d in cases[0].decorator_list if isinstance(d, ast.Call)
                      and ast.unparse(d.func) == "unittest.skipUnless" and ast.unparse(d.args[0]) == "HAVE_PIL"]
            self.assertEqual(len(guards), 1, path.name)


if __name__ == "__main__":
    unittest.main()
