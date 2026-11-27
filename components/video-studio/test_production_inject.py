"""Production spec → injection, with no model called: python3 -m unittest test_production_inject."""
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import production_inject as PI

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "video-teardown" / "machine"))
import production_spec as PS  # noqa: E402

SPEC = {"shots": [{"id": "K01", "from": 0.0, "to": 2.7, "capabilities": [
    {"id": "C1", "kind": "motion", "capability": "close approach", "mandate": "closes to 5 cm in 0.5 s", "slot": "OUR_ACTION", "ref": "K01.C1"},
    {"id": "C2", "kind": "camera", "capability": "push-in", "mandate": "pushes in 5% over 2.7 s", "slot": "FIXED", "ref": "K01.C2"}]},
    {"id": "K02", "from": 2.7, "to": 3.8, "capabilities": []}, {"id": "K03", "from": 9.0, "to": 12.0, "capabilities": []}],
    "casting": [{"role": "the inspector", "function": "moves down the line", "count": 1}]}


class Spec(unittest.TestCase):
    def test_the_answer_keeps_known_shots_kinds_and_slots(self):
        got = {"shots": [{"id": "K01", "capabilities": [{"id": "C1", "kind": "motion", "mandate": "m", "slot": "our_action"},
                                                         {"id": "C2", "kind": "dance", "mandate": "m", "slot": "FIXED"}]},
                         {"id": "K99", "capabilities": []}]}
        sp = PS.clean(got, {"K01"})
        self.assertEqual([c["ref"] for c in sp["shots"][0]["capabilities"]], ["K01.C1"])
        self.assertEqual(sp["shots"][0]["capabilities"][0]["slot"], "OUR_ACTION")
        self.assertEqual(len(sp["dropped"]), 2)

    def test_a_run_with_no_frame_map_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                PS.framemap_words(d)


class LinesLineUp(unittest.TestCase):
    TAKE = {"script": [{"speaker": "B", "say": "Did you say it?"}, {"speaker": "A", "say": "I did."}, {"speaker": "B", "say": "Same."}]}

    def test_every_line_once_in_order_by_its_speaker_passes(self):
        rows = [{"line": None, "say": "", "who": "A"}, {"line": 1, "speaker": "B", "say": "Did you say it?", "who": "B"},
                {"line": 2, "speaker": "A", "say": "I did.", "who": "B"}, {"line": 3, "speaker": "B", "say": "Same."}]
        self.assertEqual(PI.line_check(self.TAKE, rows), [])

    def test_a_line_given_to_the_wrong_speaker_reworded_missing_or_invented_is_named(self):
        rows = [{"line": 1, "speaker": "A", "say": "Did you say it?"}, {"line": 2, "speaker": "A", "say": "I really did."},
                {"line": None, "speaker": "B", "say": "Wow."}]
        got = " | ".join(PI.line_check(self.TAKE, rows))
        self.assertIn("line 1 belongs to B, the row gives it to A", got)
        self.assertIn('line 2 is reworded', got)
        self.assertIn('line 3 (B: "Same.") is missing', got)
        self.assertIn('"Wow.", which is not a line of our script', got)

    def test_lines_out_of_order_are_named(self):
        rows = [{"line": 2, "speaker": "A", "say": "I did."}, {"line": 1, "speaker": "B", "say": "Did you say it?"},
                {"line": 3, "speaker": "B", "say": "Same."}]
        self.assertIn("line 1 comes out of order", " ".join(PI.line_check(self.TAKE, rows)))


class Inject(unittest.TestCase):
    def test_the_scene_takes_the_shots_it_copies_or_its_reference_spans(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual([s["id"] for s in PI.copied_shots(d, {"motion": {"copies": ["K02"]}}, SPEC)], ["K02"])
            (Path(d) / "motion").mkdir()
            (Path(d) / "motion" / "ref.json").write_text(json.dumps({"spans": [{"from": 0.0, "to": 3.8}]}))
            self.assertEqual([s["id"] for s in PI.copied_shots(d, {}, SPEC)], ["K01", "K02"])

    def test_the_tools_list_is_read_off_the_tools(self):
        t = PI.tools()
        self.assertIn("squat", t["motion"]["can"])
        self.assertIn("neck", t["motion"]["reach_parts"])
        self.assertIn("disgust", t["performance"]["faces"])

    def test_our_scene_fills_the_slots_and_gaps_are_named(self):
        with tempfile.TemporaryDirectory() as d:
            sd = Path(d)
            (sd / "take.json").write_text(json.dumps({"cast": {"A": {"look": "a woman"}, "B": {"look": "a man"}}, "copies": ["K01"],
                                                      "script": [{"speaker": "A", "say": "Oh.", "do": "inspects him"}]}))
            (sd / "spec.json").write_text(json.dumps(SPEC))
            answer = {"roles": {"the inspector": "A"},
                      "script": [{"capability": "K01.C1", "from": 0, "to": 2.7, "line": 1, "speaker": "A", "who": "A", "action": "leans in close", "target": "B's jaw", "say": "Oh."}],
                      "staging": "A walks to B.", "slots": [{"capability": "K01.C1", "slot": "OUR_ACTION", "ours": "leans in close", "filled_from": "script 1"}],
                      "routes": [{"capability": "K01.C1", "kind": "motion", "tool": "motion chain"}, {"capability": "K01.C2", "kind": "camera", "tool": "GAP", "gap": "x"},
                                 {"capability": "K01.C3", "kind": "edit", "tool": "edit stage", "gap": "a note, not a gap"}]}
            seen = {}

            def asker(text, model):
                seen["text"] = text
                return json.dumps(answer), {"model": "stub"}
            sh = PI.inject(sd, sd / "spec.json", write=True, asker=asker)
            self.assertIn("closes to 5 cm in 0.5 s", seen["text"])            # the source's capability, not its content
            self.assertIn("inspects him", seen["text"])                       # our scene
            self.assertEqual([g["capability"] for g in sh["gaps"]], ["K01.C2"])
            t = json.loads((sd / "take.json").read_text())
            self.assertEqual(t["script"][0]["action"], "leans in close")
            self.assertEqual(t["script"][0]["target"], "B's jaw")
            self.assertTrue((sd / "take.before-inject.json").exists())
            self.assertIn("| K01.C2 | camera | GAP | x |", (sd / "production-sheet.md").read_text())
            # rows that do not line up are kept for the board but never written into the take
            answer["script"][0]["speaker"] = "B"
            (sd / "take.json").write_text((sd / "take.before-inject.json").read_text())
            sh = PI.inject(sd, sd / "spec.json", write=True, asker=asker)
            self.assertIn("line 1 belongs to A, the row gives it to B", sh["line_check"][0])
            self.assertEqual(json.loads((sd / "take.json").read_text())["script"][0].get("do"), "inspects him")


class Dials(unittest.TestCase):
    """The writing's dials reach the direction as the take carries them, and a sheet directed without them is redone."""
    ANSWER = {"roles": {}, "script": [{"capability": "K01.C1", "from": 0, "to": 2.7, "line": 1, "speaker": "A", "who": "A",
                                       "action": "leans in", "say": "Oh."}], "staging": "", "slots": [], "routes": []}
    CONTROLS = {"preset": "maxed", "levels": {"absurdity": "4 (surreal)", "humor": "3 (edged)"}}

    def scene(self, d, **dials):
        run = Path(d) / "run"
        (run / "framemap").mkdir(parents=True)
        (run / "framemap" / "framemap.json").write_text("{}")
        (run / "production-spec.json").write_text(json.dumps(SPEC))
        sd = Path(d) / "S1"
        sd.mkdir()
        (sd / "take.json").write_text(json.dumps(dict({"cast": {"A": {}}, "motion": {"source": str(run / "source.mp4"), "copies": ["K01"]},
                                                       "script": [{"speaker": "A", "say": "Oh."}]}, **dials)))
        return sd

    def test_the_dials_block_carries_the_take_dials_only(self):
        with tempfile.TemporaryDirectory() as d:
            sd = self.scene(d, controls=self.CONTROLS, emotion="surprise, then anxiety", doctrine={"section": "hook"})
            text, _ = PI.build_prompt(sd, json.loads((sd / "take.json").read_text()), SPEC)
            block = text.split("production adds no dial of its own):", 1)[1].split("What our tools can make", 1)[0]
            got = json.loads(block)
            self.assertEqual(list(got), ["controls", "emotion", "doctrine"])
            self.assertEqual(got["controls"]["levels"]["absurdity"], "4 (surreal)")
        with tempfile.TemporaryDirectory() as d:
            sd = self.scene(d)
            text, _ = PI.build_prompt(sd, json.loads((sd / "take.json").read_text()), SPEC)
            self.assertIn(PI.NO_DIALS, text)

    def test_a_sheet_directed_without_the_dials_is_directed_again_once(self):
        with tempfile.TemporaryDirectory() as d:
            sd = self.scene(d)
            calls = []

            def asker(text, model):
                calls.append(text)
                return json.dumps(self.ANSWER), {"model": "stub"}
            with mock.patch.object(PI, "ask", asker):
                PI.ensure(sd)                                   # first direction: no dials on the take
                self.assertEqual(len(calls), 1)
                PI.ensure(sd)                                   # nothing changed: the sheet stands
                self.assertEqual(len(calls), 1)
                take = json.loads((sd / "take.json").read_text())
                take["controls"] = self.CONTROLS                 # the writing's dials laid on (take_sheet.carry)
                (sd / "take.json").write_text(json.dumps(take))
                PI.ensure(sd)
                self.assertEqual(len(calls), 2)
                self.assertIn("4 (surreal)", calls[1])
                sheet = json.loads((sd / "production-sheet.json").read_text())
                self.assertEqual(sheet["dials"], {"controls": self.CONTROLS})
                PI.ensure(sd)
                self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
