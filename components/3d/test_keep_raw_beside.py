#!/usr/bin/env python3
"""--keep-raw writes the raw mesh beside the .glb, never inside the component folder (SI-178 (raw mesh beside glb), 3d#10).

    cd components/3d && python3 test_keep_raw_beside.py

No network. make3d.py is never run and torch is never imported: its `raw_path`
function is lifted out of the source by AST and executed alone, with only `os`.
"""
import ast
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MAKE3D = os.path.join(HERE, "make3d.py")


def _tree():
    with open(MAKE3D) as f:
        return ast.parse(f.read())


def _raw_path():
    fn = [n for n in _tree().body if isinstance(n, ast.FunctionDef) and n.name == "raw_path"]
    assert len(fn) == 1, "make3d.py defines no top-level raw_path"
    mod = ast.Module(body=fn, type_ignores=[])
    ns = {"os": os}
    exec(compile(mod, MAKE3D, "exec"), ns)
    return ns["raw_path"]


def _here_raw_joins(tree):
    """Every join(...) call that takes the name HERE and a string naming "raw".

    Read from the AST, so comments never count and a string only counts as a
    join argument — never the help text or a docstring (I-102 (test convention))."""
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
        if name != "join":
            continue
        here = any(isinstance(a, ast.Name) and a.id == "HERE" for a in node.args)
        raw = any(isinstance(a, ast.Constant) and isinstance(a.value, str) and "raw" in a.value
                  for a in node.args)
        if here and raw:
            hits.append(node.lineno)
    return hits


class KeepRawBeside(unittest.TestCase):
    def test_raw_path_is_beside_the_glb(self):
        raw_path = _raw_path()
        self.assertEqual(raw_path("/x/y/chair.glb"), "/x/y/chair_raw.npz")
        p = raw_path("/x/runs/3d/demo/racket.glb")
        self.assertEqual(os.path.dirname(p), "/x/runs/3d/demo")
        self.assertNotIn("components/3d", p)

    def test_no_join_of_here_with_raw(self):
        # fires on the old shape …
        old = 'import os\nHERE = "h"\nraw = os.path.join(HERE, "raw")\n'
        self.assertEqual(_here_raw_joins(ast.parse(old)), [3])
        # … and releases on make3d.py as it is now
        self.assertEqual(_here_raw_joins(_tree()), [], "make3d.py still joins HERE with raw")

    def test_gitignore_drops_raw_keeps_logs(self):
        with open(os.path.join(HERE, ".gitignore")) as f:
            lines = [ln.strip() for ln in f.read().splitlines()]
        self.assertNotIn("raw/", lines)
        self.assertIn("logs/", lines)


if __name__ == "__main__":
    unittest.main()
