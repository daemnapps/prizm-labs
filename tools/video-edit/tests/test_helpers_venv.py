"""LD-52 (venvs outside repo): the helpers venv is looked for in the shared venvs folder first
(run-kit paths.venv, named by requirements-helpers.txt), then beside the component, else a loud
HelperMissing naming both places and the setup command. No venv is built; stdlib only."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import helpers  # noqa: E402


def fake_python(venv: Path) -> Path:
    p = venv / "bin" / "python"
    p.parent.mkdir(parents=True)
    p.write_text("")
    return p


class HelpersVenvLookup(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.saved_env = os.environ.get("COMPANY_VENVS")
        os.environ["COMPANY_VENVS"] = str(self.tmp / "venvs")
        self.saved_local = helpers.LOCAL_VENV
        helpers.LOCAL_VENV = self.tmp / "beside" / ".venv"

    def tearDown(self):
        helpers.LOCAL_VENV = self.saved_local
        if self.saved_env is None:
            os.environ.pop("COMPANY_VENVS", None)
        else:
            os.environ["COMPANY_VENVS"] = self.saved_env
        shutil.rmtree(self.tmp)

    def test_shared_venv_is_named_by_the_requirements_file(self):
        self.assertTrue(helpers.shared_venv().name.startswith("video-edit-"))
        self.assertEqual(helpers.shared_venv().parent, self.tmp / "venvs")

    def test_setting_wins_over_beside(self):
        shared = fake_python(helpers.shared_venv())
        fake_python(helpers.LOCAL_VENV)
        self.assertEqual(helpers.python(), shared)

    def test_beside_when_no_shared(self):
        beside = fake_python(helpers.LOCAL_VENV)
        self.assertEqual(helpers.python(), beside)

    def test_loud_when_neither(self):
        self.assertIsNone(helpers.python())
        with self.assertRaises(helpers.HelperMissing) as e:
            helpers.call("faces.py")
        msg = str(e.exception)
        self.assertIn(str(helpers.shared_venv()), msg)
        self.assertIn(str(helpers.LOCAL_VENV), msg)
        self.assertIn("helpers.py setup", msg)


if __name__ == "__main__":
    unittest.main()
