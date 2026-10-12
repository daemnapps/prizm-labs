#!/usr/bin/env python3
"""setup.sh --check names every piece local.py needs, and exits 0 only when all are there (SI-134).

    python3 components/local-studio/test_setup_check.py

No network. setup.sh is copied into a temp tree <tmp>/components/local-studio with
<tmp>/brands beside it; only --check is ever run, never --install or --fetch.
"""
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

SETUP = Path(__file__).resolve().parent / "setup.sh"
SAM2 = "sam2/sam2.1_hiera_small.pt"


class SetupCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "components" / "local-studio"
        self.root.mkdir(parents=True)
        (self.tmp / "brands").mkdir()
        shutil.copy(SETUP, self.root / "setup.sh")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def check(self, *args):
        p = subprocess.run(["bash", str(self.root / "setup.sh"), *args], cwd=str(self.tmp),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=30)
        return p.returncode, p.stdout

    def stub(self, rel, kind="dir", executable=False):
        path = self.tmp / rel
        if kind == "dir":
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("")
            if executable:
                path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def stub_all(self, sam2_under="tools/av/models"):
        self.stub("components/local-studio/.venv-mlx/bin/python", "file", executable=True)
        self.stub("components/local-studio/models")
        self.stub("components/local-studio/src/ltx-2-mlx")
        self.stub("tools/av/bin/rife-ncnn-vulkan-20221029-macos")
        self.stub("tools/av/bin/realesrgan", "file", executable=True)
        self.stub(sam2_under + "/" + SAM2, "file")

    def test_nothing_installed_names_the_missing_pieces(self):
        code, out = self.check("--check")
        self.assertNotEqual(code, 0, out)
        for name in (".venv-mlx", "models", "tools/av", "src/ltx-2-mlx", "realesrgan", "rife", SAM2):
            self.assertIn(name, out)
        self.assertNotIn("present ", out)

    def test_default_is_check(self):
        code, out = self.check()
        self.assertNotEqual(code, 0, out)
        self.assertIn("missing components/local-studio/.venv-mlx/bin/python", out)

    def test_everything_stubbed_exits_zero(self):
        self.stub_all()
        code, out = self.check("--check")
        self.assertEqual(code, 0, out)
        self.assertNotIn("missing", out)
        self.assertIn("present tools/av/bin/realesrgan", out)
        self.assertIn("present tools/av/models/" + SAM2, out)

    def test_sam2_in_the_component_models_is_enough(self):
        self.stub_all(sam2_under="components/local-studio/models")
        code, out = self.check("--check")
        self.assertEqual(code, 0, out)
        self.assertIn("present components/local-studio/models/" + SAM2, out)

    def test_one_missing_piece_fails(self):
        self.stub_all()
        (self.tmp / "tools/av/bin/realesrgan").unlink()
        code, out = self.check("--check")
        self.assertEqual(code, 1, out)
        self.assertIn("missing tools/av/bin/realesrgan", out)

    def test_realesrgan_is_found_in_the_components_own_models(self):
        self.stub_all()
        (self.tmp / "tools/av/bin/realesrgan").unlink()
        self.stub("components/local-studio/models/realesrgan")
        code, out = self.check("--check")
        self.assertEqual(code, 0, out)
        self.assertIn("present components/local-studio/models/realesrgan", out)

    def test_realesrgan_is_found_where_the_environment_names_it(self):
        self.stub_all()
        (self.tmp / "tools/av/bin/realesrgan").unlink()
        self.stub("elsewhere/realesrgan")
        p = subprocess.run(["bash", str(self.root / "setup.sh"), "--check"], cwd=str(self.tmp),
                           env={**os.environ, "REALESRGAN_DIR": str(self.tmp / "elsewhere/realesrgan")},
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("present elsewhere/realesrgan", p.stdout)

    def test_unknown_argument_refused(self):
        code, out = self.check("--bogus")
        self.assertEqual(code, 2, out)

    def test_no_repo_root_refused(self):
        shutil.rmtree(self.tmp / "brands")
        code, out = self.check("--check")
        self.assertEqual(code, 2, out)
        self.assertIn("components/ and brands/", out)


if __name__ == "__main__":
    unittest.main()
