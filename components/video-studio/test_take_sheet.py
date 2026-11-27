import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import take_sheet as T  # noqa: E402


class TakeSheet(unittest.TestCase):
    def test_k_ids(self):
        self.assertEqual(T.k_ids("K05-K07"), ["K05", "K06", "K07"])
        self.assertEqual(T.k_ids(["K53, K55-K56", "K61", "K61"]), ["K53", "K55", "K56", "K61"])
        self.assertEqual(T.k_ids(["K109-K110"]), ["K109", "K110"])
        self.assertEqual(T.k_ids(None), [])

    def test_window(self):
        with tempfile.TemporaryDirectory() as d:
            fm = Path(d) / "framemap.json"
            fm.write_text(json.dumps({"shots": [{"id": "K01", "start": 0, "end": 1.5},
                                                {"id": "K02", "start": 1.5, "end": 3.1},
                                                {"id": "K03", "start": 3.1, "end": 6.34}]}))
            self.assertEqual(T.window(fm, ["K01", "K03"]), (0.0, 6.34))
            self.assertIsNone(T.window(fm, ["K99"]))

    def test_people(self):
        names = ["creator", "HUSBAND", "HOTEL MANAGER"]
        self.assertEqual(T.people("creator's hands", names), ["creator"])
        self.assertEqual(T.people("HUSBAND and creator", names), ["HUSBAND", "creator"])
        self.assertEqual(T.people("nobody", names), [])
        self.assertEqual(T.people("", names), [])


BLOCK = """...end on the feeling with the offer on it., Preset: Maxed (maxed) — The house default.

- intensity: 4 (peak)
- absurdity: 4 (surreal)
- ad_likeness: 0 (native)
- valence: -2 (aversive)

THE NEXT PART
"""


class WritingDials(unittest.TestCase):
    """The creative dials the writing set reach the take sheet as set; production adds none."""

    def run_dir(self, d, prompts):
        r = Path(d) / "writing" / "run-a"
        (r / "prompts").mkdir(parents=True)
        for name, text in prompts.items():
            (r / "prompts" / name).write_text(text)
        (r / "run.json").write_text(json.dumps({"brand": "x"}))
        return r

    def production(self, d, params):
        bd = Path(d) / "briefs" / "idea-1"
        (bd / "scenes" / "S1").mkdir(parents=True)
        (bd / "brief.json").write_text(json.dumps({"brief": "run-a", "picks": {"S1": "take-1"}}))
        (bd / "scenes" / "S1" / "take-1.json").write_text(json.dumps({"steps": [
            {"id": "voice", "tool": "voice.ai", "params": {}}, {"id": "take", "tool": "gen.take", "params": params}]}))
        return bd

    def test_the_target_is_read_exactly_as_the_writing_sent_it(self):
        got = T.parse_target(BLOCK)
        self.assertEqual(got["preset"], "maxed")
        self.assertEqual(got["levels"], {"intensity": "4 (peak)", "absurdity": "4 (surreal)",
                                         "ad_likeness": "0 (native)", "valence": "-2 (aversive)"})
        self.assertIsNone(T.parse_target("no dials here"))

    def test_the_brief_prompt_wins_over_an_earlier_stage(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.run_dir(d, {"3-injection.md": BLOCK.replace("4 (surreal)", "1 (odd)"), "5-brief.md": BLOCK})
            got = T.controls_target(r)
            self.assertEqual(got["levels"]["absurdity"], "4 (surreal)")
            self.assertIn("5-brief", got["came_from"])

    def test_the_sheet_carries_the_scene_dials_and_the_target_and_nothing_else(self):
        with tempfile.TemporaryDirectory() as d:
            self.run_dir(d, {"5-brief.md": BLOCK})
            bd = self.production(d, {"delivery": {"style": "storyteller"}, "doctrine": {"section": "hook"}})
            with mock.patch.object(T.ST, "WRITING", Path(d) / "writing"), mock.patch.object(T, "brief_scene", return_value={}):
                got = T.writing_dials(bd, "S1")
            self.assertEqual(list(got), ["controls", "delivery", "doctrine"])     # no emotion was written: none added
            self.assertEqual(got["controls"]["levels"]["intensity"], "4 (peak)")
            self.assertEqual(got["delivery"], {"style": "storyteller"})

    def test_a_step_seeded_without_them_reads_the_brief_scene(self):
        with tempfile.TemporaryDirectory() as d:
            self.run_dir(d, {"5-brief.md": BLOCK})
            bd = self.production(d, {"controls": {"preset": "maxed", "levels": {"humor": "3 (edged)"}}})
            scene = {"id": "S1", "emotion": "surprise", "delivery": {"pacing": "fast"}, "doctrine": {"section": "hook"}}
            with mock.patch.object(T.ST, "WRITING", Path(d) / "writing"), mock.patch.object(T, "brief_scene", return_value=scene):
                got = T.writing_dials(bd, "S1")
            self.assertEqual(got["controls"]["levels"], {"humor": "3 (edged)"})     # the step's own target is kept
            self.assertEqual(got["emotion"], "surprise")
            self.assertEqual(got["delivery"], {"pacing": "fast"})

    def test_carry_lays_only_the_dials_on_a_sheet_that_exists(self):
        with tempfile.TemporaryDirectory() as d:
            self.run_dir(d, {"5-brief.md": BLOCK})
            bd = self.production(d, {"delivery": {"style": "storyteller"}, "emotion": "surprise", "doctrine": {"section": "hook"}})
            f = bd / "scenes" / "S1" / "take.json"
            f.write_text(json.dumps({"script": [{"say": "Hi."}], "fixes": ["keep"], "production_sheet": "p.json"}))
            with mock.patch.object(T.ST, "WRITING", Path(d) / "writing"):
                self.assertEqual(sorted(T.carry(bd, "S1")), ["controls", "delivery", "doctrine", "emotion"])
                take = json.loads(f.read_text())
                self.assertEqual(take["fixes"], ["keep"])
                self.assertEqual(take["script"], [{"say": "Hi."}])
                self.assertEqual(take["emotion"], "surprise")
                self.assertIsNone(T.carry(bd, "S1"))                                    # already carried: untouched
                f.write_text("not json")
                self.assertIsNone(T.carry(bd, "S1"))
                self.assertEqual(f.read_text(), "not json")                            # an unreadable sheet is left alone


if __name__ == "__main__":
    unittest.main()
