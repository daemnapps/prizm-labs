"""The Wan door, offline: the call it would make, the framing line, the rulebook refusals. No network, no spend."""
import importlib.util
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sp = importlib.util.spec_from_file_location("wan_door", HERE / "wan.py")
W = importlib.util.module_from_spec(sp)
sp.loader.exec_module(W)


class WanDoor(unittest.TestCase):
    def test_dry_run_sends_the_house_settings(self):
        with redirect_stdout(io.StringIO()):
            r = W.motion("She turns to the window.", "/x/still.png", "/x/out.mp4", seconds=5, dry_run=True)
        self.assertEqual(r["model"], "wan-3.0")
        self.assertIn("Image 1 is the first frame", r["prompt"])
        self.assertIn(W.HOLD, r["prompt"])

    def test_credits_follow_the_cli_estimate(self):
        self.assertEqual(W.credits("480p", 5), 5.0)
        self.assertEqual(W.credits("720p", 5), 8.75)

    def test_rulebook_refuses_a_bad_call(self):
        with self.assertRaises(SystemExit):
            W.motion("x", "/x/still.png", "/x/out.mp4", seconds=5, resolution="240p", dry_run=True)


if __name__ == "__main__":
    unittest.main()
