"""A story preset reaches every writing pass (2026-11-21). No model is called.

A run names a preset (`--preset <id>`) or lets the chain pick one (`--preset auto`, from the run's format and
awareness, rotating away from presets already written for the same avatar). Every pass is handed the preset's shape
on top, under the ask; a dry run files the prompt exactly as it would be sent and calls nothing; the written brief is
checked against the preset as notes, never a hold."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
M = HERE.parent / "machine"
sys.path.insert(0, str(M))
sys.path.insert(0, str(HERE.parents[1] / "video-teardown" / "machine"))
sys.path.insert(0, str(HERE.parents[1] / "creative-controls"))

import writing_v2 as W  # noqa: E402
import story_presets as SP  # noqa: E402


class FakeR:                                       # the teardown's call seam, stood in: no model is called
    PURE_TEXT, CHATTER = "", ()
    calls = []

    @staticmethod
    def _cli_model(m):
        return m

    @staticmethod
    def _claude_run(argv, prompt, **kw):
        FakeR.calls.append(prompt)
        return mock.Mock(stdout=json.dumps({"result": "INJECTION\n" + "x" * 50, "usage": {}}), stderr="")

    @staticmethod
    def now():
        return "now"

    @staticmethod
    def _clean_env():
        return {}


class StoryPreset(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        self.work = self.ws / "runs" / "video-teardown" / "_work"
        self.run = self._run("piece", {"brand": "zz-brand", "stages": {}, "layers": {"format": "personal-story"},
                                       "declared_audience": {"avatar": "zz-avatar"},
                                       "scratch": {"awareness": "problem-aware"}})
        self.p = [mock.patch.object(W, "WS", self.ws), mock.patch.object(W, "_story_presets", lambda: SP)]
        for p in self.p:
            p.start()
        FakeR.calls = []
        W._DRY[0] = False

    def tearDown(self):
        for p in self.p:
            p.stop()
        W._DRY[0] = False
        self.tmp.cleanup()

    def _run(self, label, st):
        d = self.work / label
        d.mkdir(parents=True)
        (d / "run.json").write_text(json.dumps(st))
        return d

    def _st(self):
        return json.loads((self.run / "run.json").read_text())

    def test_no_preset_named_is_no_block(self):
        self.assertEqual(W.preset_block(self.run, self._st()), "")
        self.assertIsNone(W.preset_check(self.run))

    def test_naming_a_preset_keeps_it_on_the_run(self):
        rec = W.name_preset(self.run, "shrink-the-creature")
        self.assertEqual((self.run / "vars" / "story-preset.md").read_text().strip(), "shrink-the-creature")
        self.assertEqual(rec["picked_by"], "named")
        self.assertEqual(self._st()["story_preset"]["id"], "shrink-the-creature")

    def test_an_unknown_preset_is_refused_before_any_pass(self):
        with self.assertRaises(SystemExit):
            W.name_preset(self.run, "no-such-preset")
        self.assertFalse((self.run / "vars" / "story-preset.md").exists())

    def test_the_block_is_the_shape_and_says_our_research_fills_it(self):
        W.name_preset(self.run, "shrink-the-creature")
        b = W.preset_block(self.run, self._st())
        self.assertTrue(b.startswith("## THE STORY PRESET — `shrink-the-creature`"))
        for want in ("| 49–72% | 0:22–0:32 |", "avatar file", "verbatim words", "objection bank", "offer bank",
                     "hook-3s", "physics"):
            self.assertIn(want, b)

    def test_auto_picks_from_the_format_and_rotates_per_avatar(self):
        first = W.name_preset(self.run, "auto")
        self.assertEqual(first["picked_by"], "chain")
        self.assertEqual(SP.get(first["id"])["format"]["script_format"], "personal-story")
        self.assertIn("zz-avatar", first["why"])
        nxt = self._run("piece-2", {"brand": "zz-brand", "stages": {}, "layers": {"format": "personal-story"},
                                    "declared_audience": {"avatar": "zz-avatar"},
                                    "scratch": {"awareness": "problem-aware"}})
        second = W.name_preset(nxt, "auto")
        self.assertNotEqual(first["id"], second["id"], "the same avatar does not get the same preset twice")
        other = self._run("piece-3", {"brand": "zz-brand", "stages": {}, "layers": {"format": "personal-story"},
                                      "declared_audience": {"avatar": "other-avatar"},
                                      "scratch": {"awareness": "problem-aware"}})
        self.assertEqual(W.name_preset(other, "auto")["id"], first["id"], "another avatar starts fresh")

    def _pass(self):
        out = self.run / "stages" / "3-injection.md"
        out.parent.mkdir(exist_ok=True)
        (self.run / "prompts").mkdir(exist_ok=True)
        with mock.patch.dict(sys.modules, {"run": FakeR}):
            W._HAND[0] = None
            W.claude_v2("THE PASS'S OWN PROMPT", out)
        return out

    def test_every_pass_is_handed_the_preset_on_top(self):
        W.name_preset(self.run, "shrink-the-creature")
        self._pass()
        self.assertTrue(FakeR.calls[0].startswith("## THE STORY PRESET — `shrink-the-creature`"))
        self.assertIn("THE PASS'S OWN PROMPT", FakeR.calls[0])

    def test_a_dry_run_files_the_prompt_and_calls_nothing(self):
        W.name_preset(self.run, "shrink-the-creature")
        W._DRY[0] = True
        with self.assertRaises(W.DryRunStop):
            self._pass()
        self.assertEqual(FakeR.calls, [])
        filed = (self.run / "prompts" / "3-injection.md").read_text()
        self.assertTrue(filed.startswith("## THE STORY PRESET"))
        self.assertIn("THE PASS'S OWN PROMPT", filed)
        self.assertTrue(issubclass(W.DryRunStop, RuntimeError), "the chain's stage loop stops on it like any stop")

    def test_the_brief_is_checked_against_the_preset_as_notes(self):
        W.name_preset(self.run, "shrink-the-creature")
        (self.run / "stages").mkdir()
        brief = {"scenes": [{"start": 0, "happens": "the creature fills the sink"}, {"start": 40}]}
        (self.run / "stages" / "5-brief.md").write_text("# Brief\n\n```json\n%s\n```\n" % json.dumps(brief))
        notes = W.preset_check(self.run)
        self.assertTrue(notes)
        self.assertEqual(self._st()["writing_notes"]["story_preset"], notes)
        self.assertNotEqual((self._st()["stages"].get("stage5") or {}).get("status"), "held")


if __name__ == "__main__":
    unittest.main(verbosity=2)
