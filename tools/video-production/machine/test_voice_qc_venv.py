"""SI-94 (late-night run-breakers): the voice check finds the helpers venv at
video-edit's components home, not its old lab path."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import make_voice  # noqa: E402


class VoiceQcVenv(unittest.TestCase):
    def test_helpers_python_is_at_components_home(self):
        self.assertEqual(make_voice._helpers_python(Path("/ws")),
                         Path("/ws/tools/video-edit/.venv/bin/python"))

    def test_old_lab_path_is_gone(self):
        self.assertNotIn("the team notes", (HERE / "make_voice.py").read_text())


if __name__ == "__main__":
    unittest.main()
