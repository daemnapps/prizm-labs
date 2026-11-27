"""edit_moves: the moves director's picks laid into the cut sheet; the edit stage's rows never hold."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import edit_moves as EM
import edit_stage as ES


def sheet():
    return {"picture": [
        {"id": "S1", "scene": "S1", "start": 0.0, "duration": 6.002, "source_start": 0, "still": False, "label": "S1"},
        {"id": "S2", "scene": "S2", "start": 6.0, "duration": 4.002, "source_start": 0, "still": False, "label": "S2"}]}


def picks(B, edits):
    (Path(B) / "edit").mkdir(exist_ok=True)
    (Path(B) / "edit" / "moves-picks.json").write_text(json.dumps({"edits": edits}))


class Apply(unittest.TestCase):
    def test_a_hand_off_move_is_a_transition_compose_draws(self):
        with tempfile.TemporaryDirectory() as d:
            picks(d, [{"scene": "S1", "move": "match-cut-shape", "transition": "match", "at": 6.0, "at_in_scene": 6.0,
                       "where": "hand-off", "event": "the hand-off"}])
            sh = sheet()
            laid = EM.apply(d, sh)
            self.assertEqual(sh["layers"]["transitions"], [{"id": "director-S1", "after_scene": "S1", "kind": "match",
                                                            "why": "moves director: match-cut-shape"}])
            self.assertIn("S1 -> S2", laid[0]["landed"])

    def test_an_in_scene_punch_splits_the_clip_on_its_frame_and_keeps_the_footage_running(self):
        with tempfile.TemporaryDirectory() as d:
            picks(d, [{"scene": "S2", "move": "crash-zoom", "punch": 1.18, "at": 8.0, "at_in_scene": 2.0,
                       "where": "in-scene", "event": "the downbeat at 8.00 s"}])
            sh = sheet()
            EM.apply(d, sh)
            a, b = sh["picture"][1], sh["picture"][2]
            cut = round(round(2.0 * EM.FPS) / EM.FPS, 4)
            self.assertEqual(b["id"], "S2-punch")
            self.assertEqual(b["punch"], 1.18)
            self.assertAlmostEqual(b["start"], 6.0 + cut, places=3)
            self.assertAlmostEqual(b["source_start"], cut, places=3)                 # the same footage, carried on
            self.assertAlmostEqual(a["duration"], cut + 0.002, places=3)
            self.assertAlmostEqual(b["start"] + b["duration"], 10.002, places=3)     # the scene ends where it did
            self.assertEqual(len(sh["picture"]), 3)

    def test_a_beat_too_near_a_cut_or_a_missing_scene_is_not_laid_and_says_why(self):
        with tempfile.TemporaryDirectory() as d:
            picks(d, [{"scene": "S2", "move": "punch-in-kick", "punch": 1.1, "at": 9.9, "at_in_scene": 3.9,
                       "where": "in-scene", "event": "x"},
                      {"scene": "S9", "move": "whip-pan-handoff", "transition": "whip", "at": 1, "at_in_scene": 1,
                       "where": "hand-off", "event": "x"},
                      {"scene": "S2", "move": "whip-pan-handoff", "transition": "whip", "at": 10, "at_in_scene": 4,
                       "where": "hand-off", "event": "x"}])
            sh = sheet()
            laid = EM.apply(d, sh)
            self.assertEqual([x["landed"] for x in laid], [None, None, None])
            self.assertIn("of a cut", laid[0]["why"])
            self.assertIn("not in this cut", laid[1]["why"])
            self.assertIn("no scene follows", laid[2]["why"])
            self.assertEqual(len(sh["picture"]), 2)
            self.assertNotIn("layers", sh)

    def test_the_switch_off_lays_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            picks(d, [{"scene": "S1", "move": "whip-pan-handoff", "transition": "whip", "at": 6, "at_in_scene": 6,
                       "where": "hand-off", "event": "x"}])
            sh = sheet()
            with mock.patch.dict("os.environ", {"VIDEO_STUDIO_EDIT_OFF": "director"}):
                self.assertEqual(EM.apply(d, sh), [])
            self.assertNotIn("layers", sh)


class StageRows(unittest.TestCase):
    def test_rows_are_laid_or_reasoned_never_open(self):
        rec = {"scenes": [
            {"scene": "S1", "pick": {"name": "Whip", "from": "the director's Bold", "reason": "on the beat",
                                     "edit": {"scene": "S1", "move": "whip-pan-handoff", "at": 6.0, "event": "the hand-off"}},
             "gaps": [{"move": "morph", "option": "Wild", "gap": "needs paid generation (~28 credits): not made"}]},
            {"scene": "S2", "pick": {"name": "no move", "from": "the clean cut", "reason": "under the floor", "edit": None},
             "gaps": []}]}

        class FakeDirector:
            @staticmethod
            def direct(B, R, mode, say=None):
                self.assertEqual(mode, "rules")
                return rec
        with tempfile.TemporaryDirectory() as d:
            B = Path(d)
            (B / "studio-build").mkdir()
            (B / "studio-build" / "cutsheet.json").write_text(json.dumps({"director_moves": [
                {"scene": "S1", "move": "whip-pan-handoff", "landed": "whip on the hand-off S1 -> S2 at 6.00 s"}]}))
            with mock.patch.object(EM, "director", lambda: FakeDirector), \
                    mock.patch.object(ES, "conf", lambda: {"director_pitch": "rules"}):
                rows = EM.stage("p", B, B)
            self.assertEqual([r["id"] for r in rows], ["director-S1", "director-S1-gap-morph", "director-S2"])
            self.assertIn("laid in the edit", rows[0]["landed"])
            self.assertIn("paid generation", rows[1]["reason"])
            self.assertIn("clean cut stays", rows[2]["reason"])
            self.assertEqual(ES.check(rows, {}), [])                               # nothing the director writes holds
            (B / "edit").mkdir()                                                     # the Checks panel draws every row
            (B / "edit" / "stage.json").write_text(json.dumps({"moves": rows}))
            board = ES.board_rows(B)
            self.assertEqual([x["ok"] for x in board], [True, None, None])


if __name__ == "__main__":
    unittest.main()
