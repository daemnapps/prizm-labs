#!/usr/bin/env python3
"""
test_si57_pages_home.py — SI-57 (production pages home), held in place.

    python3 machine/test_si57_pages_home.py

  · the style board renders to runs/video-production/_system/, not beside the code
  · the pipeline view renders to runs/video-production/_system/ (parsed, never imported)
  · both pages are ignored there, the old tracked copies are gone, and the
    old machine/runs/ folder is ignored at the root
  · machine/storyboard.html is the storyboard tool's source page and stays

Standard library only. No network, no key, nothing written outside a temp dir.
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import os
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
VP = HERE.parent


def _repo():
    for d in [HERE, *HERE.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    raise FileNotFoundError(f"no workspace found upward of {HERE}")


REPO = _repo()


class PagesHome(unittest.TestCase):

    def test_style_board_renders_under_runs(self):
        old = os.environ.get("AI_WORKSPACE")
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            (ws / "brands").mkdir()
            (ws / "components").mkdir()
            os.environ["AI_WORKSPACE"] = str(ws)
            try:
                spec = importlib.util.spec_from_file_location(
                    "_si57_render_board", VP / "styles" / "render_board.py")
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
            finally:
                if old is None:
                    os.environ.pop("AI_WORKSPACE", None)
                else:
                    os.environ["AI_WORKSPACE"] = old
            self.assertEqual(
                mod.out_path(),
                ws / "runs" / "video-production" / "_system" / "style-board.html")
            src = inspect.getsource(mod.main)
            self.assertIn("out_path()", src)
            self.assertNotIn('HERE / "style-board.html"', src)

    def test_pipeline_page_renders_under_runs(self):
        text = (HERE / "pipeline.py").read_text()
        tree = ast.parse(text)
        assigns = [n for n in tree.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == "OUT" for t in n.targets)]
        self.assertEqual(len(assigns), 1, "one module-level OUT assignment")
        # ast.walk is breadth-first; read the `/` chain's constants in source order.
        consts = sorted(
            (n for n in ast.walk(assigns[0].value)
             if isinstance(n, ast.Constant) and isinstance(n.value, str)),
            key=lambda n: (n.lineno, n.col_offset))
        self.assertEqual([n.value for n in consts],
                         ["runs", "video-production", "_system", "pipeline.html"])
        self.assertNotIn("machine/pipeline.html", text)
        self.assertIn("OUT.parent.mkdir(parents=True, exist_ok=True)", text)

    def test_pages_are_ignored_and_gone(self):
        lines = (REPO / "runs" / "video-production" / ".gitignore").read_text().splitlines()
        self.assertIn("_system/style-board.html", lines)
        self.assertIn("_system/pipeline.html", lines)
        root = (REPO / ".gitignore").read_text().splitlines()
        self.assertIn("tools/video-production/machine/runs/", root)
        self.assertFalse((VP / "styles" / "style-board.html").exists())
        self.assertFalse((VP / "machine" / "pipeline.html").exists())

    def test_storyboard_source_stays(self):
        self.assertTrue((HERE / "storyboard.html").exists())
        self.assertIn('HERE / "storyboard.html"', (HERE / "storyboard.py").read_text())


if __name__ == "__main__":
    unittest.main()
