"""The Higgsfield command line is found wherever a machine installed it, and a refusal names the real cause (2026-11-11)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from image_production import providers as PV  # noqa: E402


class Found(unittest.TestCase):
    def test_env_override(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "higgsfield"
            f.write_text("")
            with mock.patch.dict(os.environ, {"HIGGSFIELD_BIN": str(f)}):
                self.assertEqual(PV._HfShell().which(), str(f))

    def test_usual_places_when_path_is_bare(self):
        with tempfile.TemporaryDirectory() as d:
            b = Path(d) / "v22" / "bin"
            b.mkdir(parents=True)
            (b / "higgsfield").write_text("")
            with mock.patch.dict(os.environ, {"PATH": "/usr/bin:/bin", "HIGGSFIELD_BIN": ""}), \
                 mock.patch.object(PV, "HF_PLACES", (str(Path(d) / "*" / "bin"),)), \
                 mock.patch("shutil.which", lambda n: None):
                self.assertEqual(PV._HfShell().which(), str(b / "higgsfield"))

    def test_not_signed_in_says_so_not_setup(self):
        class Hf:
            def which(self):
                return "/x/higgsfield"

            def run(self, argv, timeout=60):
                return 1, "", "not logged in"
        with self.assertRaises(PV.ProviderError) as e:
            PV.higgsfield_ready(Hf())
        self.assertIn("not signed in", str(e.exception))
        self.assertIn("No API key", str(e.exception))


if __name__ == "__main__":
    unittest.main()
