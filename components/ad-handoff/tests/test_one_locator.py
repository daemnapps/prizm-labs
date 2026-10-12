#!/usr/bin/env python3
"""ad-handoff finds the workspace through run-kit's paths.repo(), and only there.

    /usr/bin/python3 components/ad-handoff/tests/test_one_locator.py

SI-69 (handoff locator), ad-handoff#10 (second repo walk), triage page 12:
the gate carried its own copy of the walk, without the AI_WORKSPACE override.
Now `repo` IS run-kit's, and no workspace still stops with the gate's own words.
Offline: no key, no network, no Drive.
"""
import importlib.util, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

COMP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(COMP))
import handoff as H  # noqa: E402

sys.path.append(str(COMP.parent / "run-kit"))
from run_kit import paths as RK  # noqa: E402

SOURCE = COMP / "handoff.py"
STOP = "no workspace root above this file"
_n = [0]


def fresh(env_ws):
    """handoff.py executed again under a fresh module name, with AI_WORKSPACE
    set to env_ws (or removed when None); the caller's value is restored."""
    before = os.environ.get("AI_WORKSPACE")
    if env_ws is None:
        os.environ.pop("AI_WORKSPACE", None)
    else:
        os.environ["AI_WORKSPACE"] = str(env_ws)
    try:
        _n[0] += 1
        spec = importlib.util.spec_from_file_location(f"handoff_fresh_{_n[0]}", SOURCE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if before is None:
            os.environ.pop("AI_WORKSPACE", None)
        else:
            os.environ["AI_WORKSPACE"] = before


class OneLocator(unittest.TestCase):

    def test_repo_is_run_kits(self):
        self.assertIs(H.repo, RK.repo)

    def test_no_second_walk(self):
        self.assertNotIn("def repo(", SOURCE.read_text())

    @unittest.skipIf(os.environ.get("AI_WORKSPACE"), "AI_WORKSPACE is set in this shell")
    def test_ws_is_this_checkout(self):
        self.assertEqual((fresh(None).WS / "components" / "ad-handoff").resolve(), COMP)

    def test_ai_workspace_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "brands").mkdir()
            (Path(tmp) / "components").mkdir()
            self.assertEqual(Path(fresh(tmp).WS).resolve(), Path(tmp).resolve())

    def test_no_workspace_keeps_the_gates_words(self):
        with tempfile.TemporaryDirectory() as tmp:
            comps = Path(tmp) / "components"
            (comps / "ad-handoff").mkdir(parents=True)
            copy = comps / "ad-handoff" / "handoff.py"
            shutil.copy2(SOURCE, copy)
            shutil.copytree(COMP.parent / "run-kit", comps / "run-kit",
                            ignore=shutil.ignore_patterns("__pycache__"))
            env = {k: v for k, v in os.environ.items() if k != "AI_WORKSPACE"}
            r = subprocess.run([sys.executable, str(copy), "--help"], env=env,
                               capture_output=True, text=True, timeout=30)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn(STOP, r.stderr)


if __name__ == "__main__":
    unittest.main()
