#!/usr/bin/env python3
"""SI-66 (video workspace root): the workspace is found, never ~/Projects.

pipeline.py, briefs.py and plan_from_brief.py take WS from run-kit's
paths.repo() (AI_WORKSPACE when it holds brands/, else this checkout), and
sound.py loads the `keys` helper module from this checkout. From a worktree
the old literals read another checkout's code and data.

No key is read (keys.py's module level is imports and constants only), no
network. Run: /usr/bin/python3 tools/video-production/machine/test_workspace_root.py
"""
import ast
import importlib.util
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1].parent
FILES = ("pipeline.py", "briefs.py", "plan_from_brief.py", "sound.py")
LITERAL = re.compile(r'Projects[/]workspace|"Projects"\s*/\s*"workspace"')   # [/] so this line is not itself a hit


def load(name):
    """Import HERE/<name>.py fresh, under a name of its own."""
    spec = importlib.util.spec_from_file_location("vp_" + name, HERE / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def code_lines(p):
    """Every source line that is not a comment and not inside a docstring
    (as components/run-kit/test_workspace_paths.py reads them)."""
    src = p.read_text(errors="ignore")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    doc = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
           and isinstance(node.value.value, str):
            doc.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    out = []
    for n, line in enumerate(src.splitlines(), 1):
        if n in doc or line.lstrip().startswith("#"):
            continue
        out.append((n, line))
    return out


class WorkspaceRoot(unittest.TestCase):

    def setUp(self):
        self._path = list(sys.path)

    def tearDown(self):
        sys.path[:] = self._path

    def test_no_home_folder_literal(self):
        for f in FILES:
            lines = code_lines(HERE / f)
            self.assertTrue(lines, f + " did not parse, so nothing was checked")
            hits = ["%s:%d: %s" % (f, n, line.strip()) for n, line in lines if LITERAL.search(line)]
            self.assertEqual(hits, [], "a home-folder workspace literal is back")

    @unittest.skipIf(os.environ.get("AI_WORKSPACE"), "AI_WORKSPACE is set; repo() honours it")
    def test_each_finds_this_checkout(self):
        for name in ("pipeline", "briefs", "plan_from_brief"):
            self.assertEqual(Path(load(name).WS).resolve(), REPO.resolve(), name)

    def test_ai_workspace_still_wins(self):
        old = os.environ.get("AI_WORKSPACE")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "brands").mkdir()
            (Path(tmp) / "components").mkdir()
            os.environ["AI_WORKSPACE"] = tmp
            try:
                self.assertEqual(Path(load("briefs").WS).resolve(), Path(tmp).resolve())
            finally:
                if old is None:
                    os.environ.pop("AI_WORKSPACE", None)
                else:
                    os.environ["AI_WORKSPACE"] = old

    def test_sound_loads_the_key_helper_from_this_checkout(self):
        sys.modules.pop("keys", None)
        load("sound")
        self.assertEqual(Path(sys.modules["keys"].__file__).resolve(),
                         (REPO / "tools" / "video-teardown" / "machine" / "keys.py").resolve())


if __name__ == "__main__":
    unittest.main()
