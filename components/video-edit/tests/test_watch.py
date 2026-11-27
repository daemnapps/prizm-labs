"""The watch (step 4b): the house judge's verdict on a finished cut — no network, the judge is stubbed."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "machine"))
import watch as W  # noqa: E402

HAVE_FFMPEG = bool(shutil.which("ffmpeg"))


def _clip(folder: Path) -> Path:
    mp4 = folder / "control.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=gray:s=180x320:d=1",
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "1", "-shortest", str(mp4)], check=True)
    return mp4


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg is needed to make the test cut")
class Watch(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.mp4 = _clip(self.tmp)
        self.calls = []

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def asker(self, answer):
        def ask(prompt, video):
            self.calls.append((prompt, video))
            return json.dumps(answer), "stub-judge"
        return ask

    def test_a_clean_cut_passes_and_is_remembered(self):
        good = self.asker({"score": 8.5, "pass": True, "problems": [], "stop_power": 7})
        r = W.watch(self.mp4, "control", None, asker=good)
        self.assertTrue(r["pass"])
        self.assertEqual(r["by"], "stub-judge")
        self.assertTrue((self.tmp / "control.watch.json").exists())
        again = W.watch(self.mp4, "control", None, asker=good)
        self.assertTrue(again["remembered"])
        self.assertEqual(len(self.calls), 1, "the same cut is never watched twice")

    def test_a_problem_fails_the_cut(self):
        r = W.watch(self.mp4, "control", None, asker=self.asker(
            {"score": 8, "pass": False, "problems": [{"check": 1, "at": "3", "what": "the product label is garbled"}]}))
        self.assertFalse(r["pass"])
        self.assertEqual(r["problems"][0]["check"], 1)

    def test_a_low_score_fails_even_when_the_judge_says_pass(self):
        r = W.watch(self.mp4, "control", None, asker=self.asker({"score": 5, "pass": True, "problems": []}))
        self.assertFalse(r["pass"])

    def test_an_unanswered_judge_never_passes(self):
        def down(prompt, video):
            raise RuntimeError("HTTP 503")
        r = W.watch(self.mp4, "control", None, asker=down)
        self.assertFalse(r["pass"])
        self.assertFalse(r["answered"])
        self.assertFalse((self.tmp / "control.watch.json").exists(), "a cut nobody watched is not remembered as watched")

    def test_an_unreadable_answer_never_passes(self):
        r = W.watch(self.mp4, "control", None, asker=lambda p, v: ("not json", "stub-judge"))
        self.assertFalse(r["pass"])

    def test_the_script_lines_reach_the_prompt(self):
        lines = self.tmp / "lines.json"
        lines.write_text(json.dumps({"S1": "My neck was a mess.", "S2": "Then this."}))
        W.watch(self.mp4, "hook-a", lines, asker=self.asker({"score": 9, "pass": True, "problems": []}))
        prompt = self.calls[0][0]
        self.assertIn("My neck was a mess.", prompt)
        self.assertIn("This is version: hook-a", prompt)
        self.assertNotIn("{lines}", prompt)

    def test_the_model_comes_from_the_house(self):
        house = json.loads(W.HOUSE.read_text())["behind"]
        self.assertEqual(W.models()[0], house["judge"])


class StepList(unittest.TestCase):
    def test_watch_runs_right_after_scan_and_stops(self):
        steps = json.loads((HERE.parent / "machine" / "steps.json").read_text())["line"]["steps"]
        ids = [s["id"] for s in steps]
        self.assertEqual(ids.index("watch"), ids.index("scan") + 1)
        self.assertTrue(next(s for s in steps if s["id"] == "watch")["stops"])


if __name__ == "__main__":
    unittest.main()
