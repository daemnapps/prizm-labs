"""edit_stage: the swipe's edit moves read, set on our clock, laid or reasoned; the covers wait for the edit pass."""
import json
import tempfile
import unittest
from pathlib import Path

import edit_stage as ES

FM = {"shots": [
    {"id": "K01", "start": 0.0, "end": 2.667, "map": {"edit": "zoom · the shot ends with a rapid digital punch-in and a red vignette", "camera": {"move": "steady"}}},
    {"id": "K02", "start": 2.667, "end": 3.833, "map": {"edit": "cut", "camera": {"move": "drift"}}},
    {"id": "K03", "start": 3.833, "end": 6.833, "map": {"edit": "cut. Hard cut.", "camera": {"move": "push in on jar"}}},
    {"id": "K04", "start": 6.833, "end": 10.333, "map": {"edit": "cut. A static graphic of a perfume bottle is overlaid", "camera": {}}}]}
SOUND = {"effects": {"effects": [{"at": 2.26, "name": "typewriter", "job": "caption-pop"},
                                 {"at": 9.01, "name": "woosh", "job": "transition"}]},
         "music": {"measured": {"changes": [{"at": 6, "what": "drops out"}, {"at": 9, "what": "builds / hits"}]}}}
ROWS = [{"scene": "S1", "copies": "K01", "share": 0.25}, {"scene": "S1", "copies": "K02", "share": 0.25},
        {"scene": "S2", "copies": "K03", "share": 0.5}, {"scene": "S2", "copies": "K04", "share": 0.5}]
LAYOUT = {"scenes": [{"scene": "S1", "start": 0.0, "end": 4.0}, {"scene": "S2", "start": 4.0, "end": 10.0}]}


class Moves(unittest.TestCase):
    def test_moves_are_read_and_plain_cuts_are_not_moves(self):
        kinds = [m["kind"] for m in ES.read_moves(FM, SOUND)]
        self.assertEqual(sorted(kinds), sorted(["punch-in", "sfx", "push-in", "music-drop", "graphic-pop", "sfx", "music-hit"]))

    def test_the_punch_in_at_a_shots_end_sits_at_its_end(self):
        p = next(m for m in ES.read_moves(FM, SOUND) if m["kind"] == "punch-in")
        self.assertAlmostEqual(p["swipe_at"], 2.37, places=2)

    def test_the_clock_keeps_the_place_inside_the_copying_shot(self):
        ours = ES.clock(FM, ROWS, LAYOUT)
        self.assertEqual(ours(0.0), 0.0)
        self.assertEqual(ours(2.667), 1.0)                  # K02 starts where S1's first quarter ends
        self.assertEqual(ours(5.333), 5.5)                  # half way through K03 = half way through its 3 s slot
        self.assertIsNone(ours(30.0))

    def test_effects_are_laid_once_from_the_bank_and_a_missing_sound_gets_a_reason(self):
        moves = [{"id": "sfx-1", "kind": "sfx", "ours": 2.0, "sound": "typewriter", "what": "t", "swipe_at": 2.26},
                 {"id": "sfx-2", "kind": "sfx", "ours": 8.0, "sound": "buzzer", "what": "b", "swipe_at": 9.0},
                 {"id": "sfx-3", "kind": "sfx", "ours": 9.0, "sound": "woosh", "what": "w", "swipe_at": 9.01}]
        bed = {"effects": [{"at": 9.4, "sound": "whoosh"}]}
        laid = ES.lay_sfx(moves, bed, {"typewriter": "/bank/typewriter.mp3"}, start=0.0)
        self.assertEqual(laid, ["sfx-1"])
        self.assertIn("no 'buzzer'", moves[1]["reason"])
        self.assertTrue(moves[2]["landed"].startswith("already"))
        self.assertEqual([e["at"] for e in bed["effects"]], [2.0, 9.4])

    def test_music_changes_are_laid_by_the_beds_stop(self):
        bed = {"dropout": [6.0, 9.0]}
        self.assertIn("drops out", ES.music_laid({"kind": "music-drop", "ours": 6.2}, bed))
        self.assertIn("hits", ES.music_laid({"kind": "music-hit", "ours": 9.1}, bed))
        self.assertIsNone(ES.music_laid({"kind": "music-drop", "ours": 20.0}, bed))

    def test_an_open_move_holds_and_a_reason_or_a_layer_closes_it(self):
        moves = [{"id": "flash-1", "kind": "flash"}, {"id": "push-in-2", "kind": "push-in"}]
        self.assertEqual(ES.check(moves, {}), ["flash-1", "push-in-2"])
        moves = [{"id": "flash-1", "kind": "flash"}, {"id": "push-in-2", "kind": "push-in"}]
        self.assertEqual(ES.check(moves, {"flash-1": {"landed": "card layer"}, "push-in-2": {"reason": "real footage"}}), [])

    def test_a_drawn_graphic_pop_is_not_laid(self):
        with tempfile.TemporaryDirectory() as d:
            drawn = {"graphic-pop-1": {"landed": "CSS shapes in the card"}}
            m = [{"id": "graphic-pop-1", "kind": "graphic-pop"}]
            self.assertEqual(ES.check(m, drawn), ["graphic-pop-1"])
            pic = Path(d) / "prop" / "tub.png"
            pic.parent.mkdir()
            pic.write_bytes(b"x")
            (pic.parent / "run.json").write_text("{}")
            m = [{"id": "graphic-pop-1", "kind": "graphic-pop"}]
            self.assertEqual(ES.check(m, {"graphic-pop-1": {"landed": "card layer from " + str(pic)}}), [])


class Due(unittest.TestCase):
    def setUp(self):
        from unittest import mock
        self.p = [mock.patch.object(ES, "has_frame_map", lambda B: True), mock.patch.object(ES, "closed", lambda n, B: None)]
        for x in self.p:
            x.start()

    def tearDown(self):
        for x in self.p:
            x.stop()

    def test_never_due_without_a_frame_map_or_on_a_closed_card(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            B = Path(d)
            (B / "rough-cut-v1-sdr.mp4").write_bytes(b"x")
            self.assertTrue(ES.due("p", B))
            with mock.patch.object(ES, "has_frame_map", lambda B: False):
                self.assertFalse(ES.due("p", B))
            with mock.patch.object(ES, "closed", lambda n, B: "its card is live on Meta (x)"):
                self.assertFalse(ES.due("p", B))

    def test_a_run_with_no_frame_map_writes_its_result_and_passes(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            B = Path(d)
            (B / "rough-cut-v1-sdr.mp4").write_bytes(b"x")
            st = ES.run("p", B, run_dir=Path(d) / "no-run")
            self.assertEqual(st["moves"], [])
            self.assertIn("nothing to lay", st["note"])
            self.assertTrue((B / "edit" / "stage.json").is_file())
            self.assertFalse(ES.due("p", B))

    def test_due_after_a_render_until_the_stage_has_run(self):
        import os
        import time
        with tempfile.TemporaryDirectory() as d:
            B = Path(d)
            self.assertFalse(ES.due("p", B))                 # nothing rendered yet
            (B / "rough-cut-v1-sdr.mp4").write_bytes(b"x")
            self.assertTrue(ES.due("p", B))
            (B / "edit").mkdir()
            time.sleep(0.01)
            (B / "edit" / "stage.json").write_text(json.dumps({"open": []}))
            self.assertFalse(ES.due("p", B))
            # V57 (16 Nov): the swipe's moves are suggestions while "hold" is off; a hard row (a line not heard as
            # written, a silent bed, the brief's own notes) holds whatever the switch says
            (B / "edit" / "stage.json").write_text(json.dumps({"open": ["flash-1"]}))
            self.assertEqual(ES.due("p", B), ES.part_on("hold"))
            (B / "edit" / "stage.json").write_text(json.dumps({"open": ["line-1"], "hard_open": ["line-1"]}))
            self.assertTrue(ES.due("p", B))
            os.environ["VIDEO_STUDIO_EDIT_OFF"] = "1"
            try:
                self.assertFalse(ES.due("p", B))
            finally:
                os.environ.pop("VIDEO_STUDIO_EDIT_OFF")


class SwipeSound(unittest.TestCase):
    SOUND = {"music": {"present": True,
                       "measured": {"tempo_bpm": 161.5, "key": "D minor", "changes": [{"at": 12, "what": "drops out"}, {"at": 15, "what": "builds / hits"}]},
                       "heard": {"genre": "Pop", "subgenre": "Synth-Pop", "instruments": ["synthesizer", "drum machine"], "mood_words": ["upbeat"]}}}

    def test_the_plan_is_the_swipes_sound_cut_on_our_clock(self):
        plan, cues = ES.music_plan(self.SOUND, lambda t: t * 1.0, 48.0)
        self.assertIn("Synth-Pop Pop", plan["positive_global_styles"])
        self.assertIn("162 BPM", plan["positive_global_styles"])
        self.assertIn("vocals", plan["negative_global_styles"])
        self.assertEqual([c["at"] for c in cues], [0.0, 12.0, 15.0])
        self.assertEqual(sum(s["duration_ms"] for s in plan["sections"]), 48000)
        self.assertIn("drums", plan["sections"][1]["negative_local_styles"])

    def test_the_made_bed_is_from_the_swipe_low_at_the_drop_and_keeps_its_effects(self):
        with tempfile.TemporaryDirectory() as d:
            B = Path(d)
            (B / "music").mkdir()
            (B / "music" / "bed.json").write_text(json.dumps({"effects": [{"at": 2.26, "sound": "typewriter"}]}))
            sent = {}

            def fake(url, body, key):
                sent["plan"] = json.loads(body)["composition_plan"]
                return b"ID3"
            bed = ES.make_music(B, self.SOUND, lambda t: t, 48.0, transport=fake, key="fake")
            self.assertTrue(bed["from_swipe"])
            self.assertEqual(bed["effects"][0]["sound"], "typewriter")
            self.assertIsNone(ES.silent_gap(bed))
            self.assertTrue(sent["plan"]["sections"])

    def test_a_silent_drop_out_is_found(self):
        bed = {"duck_points": [{"t": 0, "v": 0}, {"t": 0.05, "v": 0.5}, {"t": 12.0, "v": 0}, {"t": 15.0, "v": 0},
                               {"t": 15.1, "v": 0.2}, {"t": 48.0, "v": 0}]}
        self.assertEqual(ES.silent_gap(bed), (12.0, 15.0))


class DirectorFailsLoudly(unittest.TestCase):
    def test_a_crashed_director_is_retried_then_holds_the_stage(self):
        # owner ruling 2026-11-20: retry then fail loudly — the director's crash is an open row, never "reasoned"
        import sys
        import types
        from unittest import mock
        tries = []

        def stage(*a):
            tries.append(1)
            raise RuntimeError("no model")
        with tempfile.TemporaryDirectory() as t:
            B, R = Path(t) / "b", Path(t) / "r"
            B.mkdir()
            (R / "framemap").mkdir(parents=True)
            (R / "framemap" / "framemap.json").write_text(json.dumps(FM))
            with mock.patch.dict(sys.modules, {"edit_moves": types.SimpleNamespace(stage=stage)}), \
                    mock.patch.object(ES, "part_on", lambda name: name == "director"):
                st = ES.run("0001", B=B, run_dir=R)
        self.assertEqual(len(tries), 2)
        self.assertIn("director", st["hard_open"])
        row = next(m for m in st["moves"] if m["id"] == "director")
        self.assertNotIn("reason", row)
        self.assertIn("no model", row["open_why"])


if __name__ == "__main__":
    unittest.main()


class CameraMovesOnOurClips(unittest.TestCase):
    """A footage lane: the swipe's push-ins and punch-ins land on our shots that copy their swipe shot."""

    def test_moves_land_on_the_picks_and_unmatched_get_a_reason(self):
        import json, tempfile
        from pathlib import Path
        import edit_stage as ES2
        B = Path(tempfile.mkdtemp())
        (B / "picks.json").write_text(json.dumps({"shots": {"S1.1": {"source": "L-1", "in": 0}, "S2.K09": {"source": "L-2", "in": 3}}}))
        (B / "shot-list.json").write_text(json.dumps({"shots": [{"id": "S1.1", "copies": "K01"}, {"id": "S2.K09", "copies": "K09"}]}))
        brief = {"lane": "real"}
        moves = [{"id": "push-in-1", "kind": "push-in", "k": "K01"}, {"id": "punch-in-2", "kind": "punch-in", "k": "K09"},
                 {"id": "push-in-3", "kind": "push-in", "k": "K77"}, {"id": "sfx-1", "kind": "sfx", "k": "K01"}]
        laid = ES2.lay_camera(B, moves, brief)
        self.assertEqual(laid, ["push-in-1", "punch-in-2"])
        p = json.loads((B / "picks.json").read_text())["shots"]
        self.assertEqual(p["S1.1"]["params"]["move"], "push")
        self.assertEqual(p["S2.K09"]["params"]["move"], "punch")
        self.assertIn("not copied", moves[2]["reason"])
        self.assertNotIn("landed", moves[3])
        self.assertEqual(json.loads((B / "brief.json").read_text())["edit"]["push-in-1"]["landed"][:7], "push-in")

    def test_the_ai_lane_lays_nothing(self):
        import tempfile
        from pathlib import Path
        import edit_stage as ES2
        self.assertEqual(ES2.lay_camera(Path(tempfile.mkdtemp()), [{"id": "p", "kind": "push-in", "k": "K1"}], {"lane": "ai"}), [])
