#!/usr/bin/env python3
"""SI-55 (organic pages home), swipe-organic#20: the creator-profiles page is
written to runs/swipe-organic/_system/ at the repo root, ignored there, and no
longer beside the code. No key, no network; never runs main() or a browser.

    /usr/bin/python3 components/swipe-organic/test_pages_home.py
"""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SRC = HERE / "profile.py"

# Never `import profile` — that name is a stdlib module.
_spec = importlib.util.spec_from_file_location("profile_si55", SRC)
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)


class PagesHome(unittest.TestCase):
    def test_the_page_goes_to_runs_system(self):
        env = {k: v for k, v in os.environ.items() if k != "AI_WORKSPACE"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(P.pages_dir(), REPO / "runs" / "swipe-organic" / "_system")
        self.assertTrue((REPO / "components").is_dir() and (REPO / "brands").is_dir())

    def test_ai_workspace_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "components").mkdir()
            (ws / "brands").mkdir()
            with mock.patch.dict(os.environ, {"AI_WORKSPACE": str(ws)}):
                got = P.pages_dir()
            self.assertEqual(got, ws / "runs" / "swipe-organic" / "_system")
            self.assertFalse((ws / "runs").exists())  # pages_dir() never makes the folder

    def test_no_page_beside_the_code(self):
        self.assertNotIn('(HERE / "organic-profiles.html")', SRC.read_text(encoding="utf-8"))

    def test_the_page_is_ignored(self):
        lines = (REPO / "runs" / "swipe-organic" / ".gitignore").read_text(
            encoding="utf-8").splitlines()
        self.assertIn("_system/organic-profiles.html", lines)

    def test_templates_stay(self):
        for name in ("desk.html", "sounds.html"):
            self.assertTrue((HERE / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
