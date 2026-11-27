#!/usr/bin/env python3
"""setup.sh --check names every piece local.py needs, and exits 0 only when all are there (SI-134).

    python3 components/local-studio/test_setup_check.py

No network. setup.sh (and components/3d/setup.sh) are copied into a temp tree
<tmp>/components/{local-studio,3d} with <tmp>/brands beside it; only --check is ever run,
never --install or --fetch. The Hugging Face cache and PATH point into the temp tree.
"""
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SETUP = HERE / "setup.sh"
SETUP_3D = HERE.parent / "3d" / "setup.sh"
SAM2 = "sam2/sam2.1_hiera_small.pt"
LS = "components/local-studio"
DEMUCS = ["f7e0c4bc-ba3fe64a.th", "d12395a8-e57c48e6.th", "92cfc3b6-ef3bcb9c.th", "04573f0d-f3cf25b2.th"]
MLX_HF = ["mflux-community/flux2-klein-4b-mflux-q4", "mlx-community/whisper-large-v3-turbo",
          "mlx-community/Kokoro-82M-bf16", "prince-canuma/Kokoro-82M"]
SHARED_HF = ["ZhengPeng7/BiRefNet", "ZhengPeng7/BiRefNet_lite", "microsoft/TRELLIS.2-4B",
             "microsoft/TRELLIS-image-large", "camenduru/dinov3-vitl16-pretrain-lvd1689m"]


def hf_dir(repo):
    return "models--" + repo.replace("/", "--")


class SetupCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / LS
        self.root.mkdir(parents=True)
        (self.tmp / "components" / "3d").mkdir(parents=True)
        (self.tmp / "brands").mkdir()
        shutil.copy(SETUP, self.root / "setup.sh")
        shutil.copy(SETUP_3D, self.tmp / "components" / "3d" / "setup.sh")
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        # The shared models/venvs folders (LD-52 (venvs outside repo)) point into the temp tree too, so a real
        # one on this machine (the mini has ~/.upright/models/local-studio) never masks a piece the test removed.
        self.env = {**os.environ, "HF_HUB_CACHE": str(self.tmp / "hf"),
                    "UPRIGHT_MODELS": str(self.tmp / "upright" / "models"),
                    "UPRIGHT_VENVS": str(self.tmp / "upright" / "venvs"),
                    "PATH": f"{self.bin}:/usr/bin:/bin:/usr/sbin:/sbin"}
        for k in ("LOCAL_STUDIO_FALLBACK", "REALESRGAN_DIR", "HF_HOME"):
            self.env.pop(k, None)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def check(self, *args, **env):
        p = subprocess.run(["bash", str(self.root / "setup.sh"), *args], cwd=str(self.tmp), env={**self.env, **env},
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)
        return p.returncode, p.stdout

    def stub(self, rel, kind="file", executable=False, base=None):
        path = (base or self.tmp) / rel
        if kind == "dir":
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("")
            if executable:      # an empty executable runs as an empty shell script: exit 0, prints nothing
                path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def stub_hf(self, cache, repo):
        self.stub(f"{hf_dir(repo)}/refs/main", base=cache)

    def stub_all(self):
        for t in ("git", "uv", "ffmpeg", "blender"):
            self.stub(f"bin/{t}", executable=True)
        self.stub(f"{LS}/.venv/bin/python", executable=True)
        self.stub(f"{LS}/.venv-mlx/bin/python", executable=True)
        self.stub(f"{LS}/src/ltx-2-mlx/.venv/bin/ltx-2-mlx", executable=True)
        self.stub(f"{LS}/models/rife-ncnn-vulkan-20221029-macos/rife-ncnn-vulkan", executable=True)
        self.stub(f"{LS}/models/realesrgan", "dir")
        self.stub(f"{LS}/models/{SAM2}")
        self.stub(f"{LS}/models/depth-pro/depth_pro.pt")
        for f in DEMUCS:
            self.stub(f"{LS}/models/torch/hub/checkpoints/{f}")
        self.stub(f"{LS}/models/seedvr2-3b/seedvr2_ema_3b_fp16.safetensors")
        for r in MLX_HF:
            self.stub_hf(self.root / "models/hf/hub", r)
        for r in SHARED_HF:
            self.stub_hf(self.tmp / "hf", r)
        self.stub("components/3d/trellis-mac/TRELLIS.2/trellis2/pipelines/trellis2_image_to_3d.py")
        self.stub("components/3d/trellis-mac/.venv/bin/python", executable=True)

    def test_nothing_installed_names_the_missing_pieces(self):
        code, out = self.check("--check")
        self.assertNotEqual(code, 0, out)
        for name in (".venv-mlx", f"{LS}/.venv", "models", "src/ltx-2-mlx", "realesrgan", "rife", SAM2,
                     "depth_pro.pt", DEMUCS[0], "seedvr2-3b", "flux2-klein", "BiRefNet", "trellis-mac/.venv"):
            self.assertIn(name, out)
        self.assertNotIn("present " + LS, out)
        self.assertNotIn("fallback ", out)

    def test_default_is_check(self):
        code, out = self.check()
        self.assertNotEqual(code, 0, out)
        self.assertIn(f"missing {LS}/.venv-mlx", out)

    def test_everything_stubbed_exits_zero(self):
        self.stub_all()
        code, out = self.check("--check")
        self.assertEqual(code, 0, out)
        self.assertNotIn("missing", out)
        self.assertIn(f"present {LS}/models/realesrgan", out)
        self.assertIn(f"present {LS}/models/{SAM2}", out)

    def test_shared_models_folder_is_used_when_it_exists(self):
        # LD-52: a shared models folder that exists is where the check looks — the copy beside the component
        # no longer counts; one that is absent leaves the component's models/ in charge (the test above).
        self.stub_all()
        shared = self.tmp / "upright" / "models" / "local-studio"
        shared.mkdir(parents=True)
        code, out = self.check("--check")
        self.assertEqual(code, 1, out)
        self.assertIn("realesrgan", out)
        self.assertNotIn(f"present {LS}/models/realesrgan", out)
        self.stub("realesrgan", "dir", base=shared)
        code, out = self.check("--check")
        self.assertNotIn("missing upright/models/local-studio/realesrgan", out)

    def test_no_3d_leaves_the_3d_pieces_out(self):
        self.stub_all()
        shutil.rmtree(self.tmp / "components/3d/trellis-mac")
        code, out = self.check("--check")
        self.assertEqual(code, 1, out)
        self.assertIn("missing components/3d/trellis-mac", out)
        code, out = self.check("--check", "--no-3d")
        self.assertEqual(code, 0, out)
        self.assertNotIn("trellis", out)

    def test_one_missing_piece_fails(self):
        self.stub_all()
        (self.root / "models/realesrgan").rmdir()
        code, out = self.check("--check")
        self.assertEqual(code, 1, out)
        self.assertIn(f"missing {LS}/models/realesrgan", out)

    def test_an_incomplete_venv_is_missing(self):
        self.stub_all()
        py = self.root / ".venv/bin/python"
        py.write_text("#!/bin/sh\necho kornia\n")
        code, out = self.check("--check")
        self.assertEqual(code, 1, out)
        self.assertIn(f"missing {LS}/.venv (incomplete: kornia)", out)

    def test_realesrgan_is_found_where_the_environment_names_it(self):
        self.stub_all()
        (self.root / "models/realesrgan").rmdir()
        self.stub("elsewhere/realesrgan", "dir")
        code, out = self.check("--check", REALESRGAN_DIR=str(self.tmp / "elsewhere/realesrgan"))
        self.assertEqual(code, 0, out)
        self.assertIn("present elsewhere/realesrgan", out)

    def test_the_fallback_folder_is_used_only_for_what_is_missing_here(self):
        self.stub_all()
        shutil.rmtree(self.root / ".venv-mlx")
        (self.root / f"models/{SAM2}").unlink()
        fb = self.tmp / "old-tools"
        self.stub("local/.venv-mlx/bin/python", executable=True, base=fb)
        self.stub(f"av/models/{SAM2}", base=fb)
        code, out = self.check("--check")
        self.assertEqual(code, 1, out)
        code, out = self.check("--check", LOCAL_STUDIO_FALLBACK=str(fb))
        self.assertEqual(code, 0, out)
        self.assertIn("fallback old-tools/local/.venv-mlx", out)
        self.assertIn(f"fallback old-tools/av/models/{SAM2}", out)
        self.assertIn(f"present {LS}/.venv", out)

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
