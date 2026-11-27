"""Every writing step of the picture line is handed who the ad is for (creative-strategist who.py). No model, no network.

    /usr/bin/python3 -m unittest discover -s components/image-writing/tests
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HOME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOME / "tools"))
import writing as W            # noqa: E402
import paths as P              # noqa: E402
import run as R                # noqa: E402

CARD = """# Sub-Avatar 1 · Night worker

- **Id / narrowed by:** Sub-Avatar 1 · When it happens (nights)
- **Core desire:** "I want to look awake when I walk out at dawn"
- **Pain:** He sees it in the {mirror} at six in the morning
- **One-line story:** The man nobody sees until the sun is up
"""


def workspace(d):
    av = Path(d) / "brands" / "acme" / "core-avatars" / "a1"
    (av / "sub-avatars").mkdir(parents=True)
    (Path(d) / "components").mkdir()
    (av / "profile.md").write_text('# a1\n\nHe says: "I want the marks to be gone for good"\n')
    (av / "sub-avatars" / "sub-01-night-worker.md").write_text(CARD)
    (Path(d) / "brands" / "acme" / "strategy").mkdir()
    (Path(d) / "brands" / "acme" / "strategy" / "angles.json").write_text(json.dumps({"angles": [
        {"id": "root-cause", "name": "Root cause", "what": "the cause sits under the skin", "status": "active"},
        {"id": "old", "name": "Old", "what": "gone", "status": "deprecated"}]}))
    run = Path(d) / "runs" / "r1"
    (run / "vars").mkdir(parents=True)
    (run / "out").mkdir()
    return run


class Who(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name).resolve()
        self.run_ = workspace(self.root)
        for p in (mock.patch.dict(os.environ, AI_WORKSPACE=str(self.root)), mock.patch.object(P, "BRANDS", self.root / "brands")):
            p.start()
            self.addCleanup(p.stop)
        self.pf = self.root / "prompt.md"
        self.pf.write_text("the step's own prompt\n")

    def before(self, stage="4", avatar="a1", level=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return W.before(self.run_, stage, "acme", avatar, self.pf, level).read_text()

    def ask(self, **rec):
        f = self.root / "ask.json"
        f.write_text(json.dumps(dict({"ask": "x", "brand": "acme", "avatar": "a1"}, **rec)))
        (self.run_ / "vars" / "ask.md").write_text(str(f))

    def sub(self, name="sub-01-night-worker"):
        (self.run_ / "vars" / "sub_avatar.md").write_text(name + "\n")

    def test_every_writing_step_carries_the_block_and_the_subs_own_words(self):
        self.sub()
        for s in W.STAGES:
            t = self.before(s)
            self.assertIn(W._who().MARK, t)
            self.assertIn("I want to look awake when I walk out at dawn", t)
            self.assertIn("the step's own prompt", t)

    def test_a_brace_in_the_block_is_never_an_unfilled_slot(self):
        self.sub()
        self.assertNotIn("{mirror}", self.before())

    def test_no_sub_named_speaks_to_the_whole_avatar(self):
        t = self.before()
        self.assertIn("none named", t)
        self.assertNotIn("look awake", t)

    def test_no_avatar_on_file_leaves_the_prompt_as_it_was(self):
        self.assertEqual(self.before(avatar="nobody"), "the step's own prompt\n")

    def test_the_ask_names_the_sub_the_doubt_and_the_angle_and_the_run_keeps_them(self):
        self.ask(sub_avatar="night-worker", angle="root-cause", aim={"doubt": "for-me", "desire": "to look awake", "demographic": "m/25-34"})
        t = self.before(level="unaware")
        self.assertIn("Root cause: the cause sits under the skin", t)
        self.assertIn("m/25-34", t)
        a = json.loads((self.run_ / "run.json").read_text())["aim"]
        self.assertEqual((a["avatar"], a["sub"], a["doubt"], a["desire"]), ("a1", "night-worker", "for-me", "to look awake"))

    def test_a_deprecated_angle_is_never_the_claim(self):
        self.ask(angle="old")
        self.assertNotIn("Old: gone", self.before())

    def test_the_asks_level_wins_over_the_swipes(self):
        (self.run_ / "out" / "01-teardown.md").write_text("MARKET STATE: most-aware")
        self.assertEqual(R.level_for(self.run_, "acme", "a1"), "most-aware")
        self.ask(strategy={"awareness": "problem-aware: he knows it hurts"})
        self.assertEqual(R.level_for(self.run_, "acme", "a1"), "problem-aware")
        self.before(level="most-aware")
        self.assertEqual(json.loads((self.run_ / "run.json").read_text())["aim"]["awareness"], "problem-aware")

    def test_the_level_the_language_rows_are_asked_for_is_the_asks(self):
        (self.run_ / "out" / "01-teardown.md").write_text("MARKET STATE: most-aware")
        self.ask(strategy={"awareness": "problem-aware"})
        seen = []
        with mock.patch.object(R.subprocess, "run", side_effect=lambda c, **k: seen.append(c) or mock.Mock(returncode=0, stdout="- [x] row\n", stderr="")), \
                contextlib.redirect_stdout(io.StringIO()):
            R.language("acme", "hooks", self.run_, "a1")
        self.assertEqual(json.loads(seen[0][-1])["level"], "problem-aware")

    def test_a_record_already_in_the_run_is_kept(self):
        (self.run_ / "run.json").write_text(json.dumps({"brief": "brief-0001"}))
        self.before()
        self.assertEqual(json.loads((self.run_ / "run.json").read_text())["brief"], "brief-0001")

    def test_learnings_fall_back_to_the_avatars_file(self):
        self.sub()
        W.G.quality()
        from marketing_chain_checks import viewer as VW
        with mock.patch.object(VW, "learnings", side_effect=lambda b, a, **k: "he stopped at the mirror line" if a == "a1" else ""):
            self.assertIn("he stopped at the mirror line", self.before())

    def test_a_sub_that_is_not_on_file_is_said_never_guessed(self):
        self.sub("no-such-man")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            t = W.before(self.run_, "6", "acme", "a1", self.pf).read_text()
        self.assertIn("no sub-avatar no-such-man", buf.getvalue())
        self.assertIn("none named", t)


if __name__ == "__main__":
    unittest.main()
