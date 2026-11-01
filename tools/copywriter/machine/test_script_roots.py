#!/usr/bin/env python3
"""batch.sh and ads_to_copy.sh find the workspace through run-kit's paths.repo()
(SI-68 (copywriter script roots)). No key, no network, no model, no real brand."""
import os, re, subprocess, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SCRIPTS = ("batch.sh", "ads_to_copy.sh")


def env(ws=None):
    e = {k: v for k, v in os.environ.items() if k != "AI_WORKSPACE"}
    if ws is not None:
        e["AI_WORKSPACE"] = str(ws)
    return e


def root_lines(script):
    text = (HERE / script).read_text()
    return "\n".join(l for l in text.splitlines() if re.match(r"^(HERE|WS)=", l))


def print_ws(script, ws=None):
    return subprocess.run(["bash", "-c", root_lines(script) + '\necho "$WS"', str(HERE / script)],
                          cwd=tempfile.gettempdir(), env=env(ws),
                          capture_output=True, text=True, timeout=30)


class ScriptRoots(unittest.TestCase):
    def test_no_home_folder_literal(self):
        for s in SCRIPTS:
            self.assertNotIn("Projects/workspace", (HERE / s).read_text(), s)

    def test_teardown_and_copy_paths_hang_off_ws(self):
        text = (HERE / "ads_to_copy.sh").read_text()
        self.assertIn('VT="$WS/tools/video-teardown/machine"', text)
        self.assertIn('CP="$WS/tools/copywriter"', text)

    def test_root_lines_find_this_checkout_from_anywhere(self):
        for s in SCRIPTS:
            self.assertEqual(len(root_lines(s).splitlines()), 2, s)
            r = print_ws(s)
            self.assertEqual(r.returncode, 0, s + ": " + r.stderr)
            self.assertEqual(Path(r.stdout.strip()).resolve(), REPO.resolve(), s)

    def test_ai_workspace_still_wins(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "brands").mkdir()
            (Path(d) / "components").mkdir()
            r = print_ws("ads_to_copy.sh", ws=d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(Path(r.stdout.strip()).resolve(), Path(d).resolve())

    def test_batch_refuses_an_unknown_brand_naming_the_checkout(self):
        r = subprocess.run(["bash", str(HERE / "batch.sh"), "zz-test-brand",
                            "brands/zz-test-brand/products/x.md"],
                           cwd=HERE.parent, env=env(), capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("no brands/zz-test-brand under " + str(REPO.resolve()), r.stderr)


if __name__ == "__main__":
    unittest.main()
