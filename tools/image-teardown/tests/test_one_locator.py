#!/usr/bin/env python3
"""SI-108 (teardown one locator): the image board finds the workspace through
run-kit's paths.repo(), and reads the video board's template from THIS clone,
not from one person's home folder; tools/paths.py's `_repo` is run-kit's walk.

    python3 tests/test_one_locator.py

No key, no network. The clone is a temp folder that is not
the workspace: nothing is written under the real runs/ or brands/.
"""
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

LANE = Path(__file__).resolve().parent.parent
RUN_KIT = LANE.parent.parent / "components" / "run-kit"
sys.path.insert(0, str(LANE / "tools"))
sys.path.append(str(RUN_KIT))

import paths as P                     # noqa: E402
from run_kit import paths as RK       # noqa: E402


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class BoardInAnotherClone(unittest.TestCase):
    """build_ui.py copied into a clone that is not at the workspace."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.clone = Path(self.tmp.name).resolve() / "elsewhere"
        (self.clone / "brands").mkdir(parents=True)
        lane = self.clone / "tools" / "image-teardown"
        lane.mkdir(parents=True)
        shutil.copy(LANE / "build_ui.py", lane / "build_ui.py")
        shutil.copytree(RUN_KIT / "run_kit", self.clone / "components" / "run-kit" / "run_kit",
                        ignore=shutil.ignore_patterns("__pycache__"))
        self.stub = self.clone / "tools" / "video-teardown" / "machine" / "board.py"
        self.stub.parent.mkdir(parents=True)
        self.stub.write_text('TEMPLATE = r"""<html>stub board</html>"""\n')
        env = {k: v for k, v in os.environ.items() if k != "AI_WORKSPACE"}
        self.env = unittest.mock.patch.dict(os.environ, env, clear=True)
        self.env.start()
        self.path = unittest.mock.patch.object(sys, "path", list(sys.path))
        self.path.start()
        self.ui = _load(lane / "build_ui.py", "build_ui_si108")

    def tearDown(self):
        self.path.stop()
        self.env.stop()
        self.tmp.cleanup()

    def test_clone_is_not_the_home_default(self):
        default = Path(os.environ.get("AI_WORKSPACE") or ".").resolve()
        self.assertFalse(str(self.clone).startswith(str(default)))

    def test_video_board_resolves_inside_the_clone(self):
        self.assertEqual(self.ui.VIDEO_BOARD, self.stub)
        self.assertTrue(self.ui.VIDEO_BOARD.is_relative_to(self.clone))

    def test_the_board_reads_the_clones_template(self):
        self.assertIn("stub board", self.ui.VIDEO_BOARD.read_text())

    def test_run_kit_appended_never_ahead(self):
        self.assertEqual(sys.path[-1], str(self.clone / "components" / "run-kit"))


class NoHomeFolder(unittest.TestCase):
    def test_build_ui_source_has_no_path_home(self):
        self.assertNotIn("Path.home()", (LANE / "build_ui.py").read_text())


class ToolsPathsIsRunKitsWalk(unittest.TestCase):
    def test_repo_is_run_kits_repo(self):
        self.assertEqual(P.REPO, RK.repo(P.LANE))

    def test_repo_wrapper_delegates(self):
        with unittest.mock.patch.object(RK, "repo", return_value=Path("/x/ws")) as m:
            self.assertEqual(P._repo(P.LANE), Path("/x/ws"))
        m.assert_called_once_with(P.LANE)


if __name__ == "__main__":
    unittest.main()
