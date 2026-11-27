"""director: one move per scene, kept by the stated machine rule; gaps recorded, never made; same facts, same file."""
import json
import tempfile
import unittest
from pathlib import Path

import director as D

LIB = D.library()


def scene(name, a, b, beats, shots, changes=(), pair=(None, ""), cands=()):
    return {"scene": name, "title": name, "start": a, "end": b, "word": "words", "kinds": ["ai"], "objects": [],
            "shots": [{"id": name + ".1", "what": w, "props": []} for w in shots], "tags": ["downbeat", "kick"],
            "beats": [t for t in beats if a <= t < b], "downbeats": [t for t in beats[::4] if a <= t < b],
            "changes": list(changes), "all_beats": list(beats), "pair": pair,
            "candidates": [{"id": c} for c in cands]}


BEATS = [round(i * 0.5, 2) for i in range(40)]          # 120 BPM, a downbeat every 2 s
TARGET = {"stopping_power": 4, "dramatisation": 4, "absurdity": 4, "intensity": 4, "realism": 3}


class Timing(unittest.TestCase):
    def test_a_hand_off_move_fires_on_the_hand_off_and_says_if_it_is_on_the_beat(self):
        a, b = scene("S1", 0, 6.0, BEATS, ["x"]), scene("S2", 6.0, 9.0, BEATS, ["y"])
        f = D.fire("whip-pan-handoff", a, b)
        self.assertEqual((f["at"], f["where"], f["on_beat"]), (6.0, "hand-off", True))
        a["end"] = 6.3
        self.assertFalse(D.fire("whip-pan-handoff", a, b)["on_beat"])
        self.assertIsNone(D.fire("whip-pan-handoff", a, None))            # the last scene hands off to nothing

    def test_an_in_scene_move_takes_the_hit_before_the_downbeat_and_never_a_drop_out(self):
        sc = scene("S1", 0, 6.0, BEATS, ["x"], changes=[{"at": 3.1, "what": "music drops out"}, {"at": 4.7, "what": "the hit"}])
        self.assertEqual(D.fire("punch-in-kick", sc, None)["at"], 4.7)
        sc["changes"] = [{"at": 3.1, "what": "music drops out"}]
        f = D.fire("punch-in-kick", sc, None)
        self.assertEqual((f["at"], f["kind"]), (2.0, "downbeat"))          # the first downbeat clear of the cut

    def test_shapes_and_motions_pair_across_a_hand_off(self):
        self.assertEqual(D.pair("she empties the round metal collar", "the manager presses the wax seal"),
                         ("shape", "round: collar -> seal"))
        self.assertEqual(D.pair("she lifts her arms", "he lifts his chin")[0], "motion")
        self.assertEqual(D.pair("she looks at the lens", "a jar on the shelf"), (None, ""))   # the camera lens is no shape


class PickRule(unittest.TestCase):
    def test_paid_no_drawer_and_ruled_out_moves_are_gaps_not_picks(self):
        a, b = scene("S1", 0, 6.0, BEATS, ["x"]), scene("S2", 6.0, 9.0, BEATS, ["y"])
        pitches = [{"option": "Safe", "moves": ["flash-insert"]}, {"option": "Bold", "moves": ["morph"]},
                   {"option": "Wild", "moves": ["breaks-the-edge"]}]
        p = D.pick(a, b, pitches, TARGET, LIB, {})
        gaps = " ".join(g["gap"] for o in pitches for g in o["gaps"])
        self.assertIn("no flash frames", gaps)
        self.assertIn("paid generation", gaps)
        self.assertIn("no drawer", gaps)
        self.assertTrue(p["from"].startswith("the best move the edit lays from the shortlist"))                 # the machine still lays one free move
        self.assertIn(p["moves"][0], D.LAY)

    def test_a_shape_match_cut_needs_a_shape_pair_and_wins_with_one(self):
        a, b = scene("S1", 0, 6.0, BEATS, ["x"]), scene("S2", 6.0, 9.0, BEATS, ["y"])
        pitches = [{"option": "Safe", "moves": ["punch-in-kick"]}, {"option": "Bold", "moves": ["match-cut-shape"]}]
        p = D.pick(a, b, pitches, TARGET, LIB, {})
        self.assertEqual(p["moves"], ["punch-in-kick"])
        self.assertFalse(pitches[1]["eligible"])
        a["pair"] = ("shape", "round: collar -> seal")
        pitches = [{"option": "Safe", "moves": ["punch-in-kick"]}, {"option": "Bold", "moves": ["match-cut-shape"]}]
        p = D.pick(a, b, pitches, TARGET, LIB, {})
        self.assertEqual(p["moves"], ["match-cut-shape"])
        self.assertEqual(p["edit"], {"scene": "S1", "move": "match-cut-shape", "at": 6.0, "at_in_scene": 6.0,
                                     "where": "hand-off", "event": "the hand-off, on the beat at 6.00 s",
                                     "transition": "match", "after_scene": "S1", "into_scene": "S2"})
        self.assertIn("share a shape", p["reason"])

    def test_a_repeated_move_loses_to_a_fresh_one_and_a_weak_move_leaves_the_clean_cut(self):
        a, b = scene("S1", 0, 6.0, BEATS, ["x"]), scene("S2", 6.0, 9.0, BEATS, ["y"])
        two = lambda: [{"option": "Safe", "moves": ["punch-in-kick"]}, {"option": "Bold", "moves": ["crash-zoom"]}]  # noqa: E731
        self.assertEqual(D.pick(a, b, two(), TARGET, LIB, {})["moves"], ["crash-zoom"])
        self.assertEqual(D.pick(a, b, two(), TARGET, LIB, {"crash-zoom": 2})["moves"], ["punch-in-kick"])
        p = D.pick(a, b, two(), TARGET, LIB, {"crash-zoom": 4, "punch-in-kick": 4})
        self.assertIsNone(p["edit"])
        self.assertIn("under the floor", p["reason"])

class Cards(unittest.TestCase):
    def test_a_card_or_end_card_is_never_punched_in(self):
        a, b = scene("S1", 0, 6.0, BEATS, ["x"]), scene("S2", 6.0, 9.0, BEATS, ["y"])
        a["roll"] = "E"
        p = D.pick(a, None, [{"option": "Safe", "moves": ["crash-zoom"]}], TARGET, LIB, {})
        self.assertIsNone(p)                                                    # last scene, a card: nothing to lay
        a["roll"] = "C"
        p = D.pick(a, b, [{"option": "Safe", "moves": ["crash-zoom"]}], TARGET, LIB, {})
        self.assertEqual(p["moves"], ["whip-pan-handoff"])                     # the hand-off still can move


class DirectorsMoment(unittest.TestCase):
    def test_the_directors_second_is_kept_when_it_sits_on_a_beat_else_the_moves_own_moment(self):
        a, b = scene("S1", 0, 6.0, BEATS, ["x"]), scene("S2", 6.0, 9.0, BEATS, ["y"])
        on = D.pick(a, b, [{"option": "Bold", "moves": ["crash-zoom"], "fires_at": 3.55}], TARGET, LIB, {})
        self.assertEqual((on["edit"]["at"], on["edit"]["event"]), (3.5, "the beat at 3.50 s"))
        off = D.pick(a, b, [{"option": "Bold", "moves": ["crash-zoom"], "fires_at": 3.3}], TARGET, LIB, {})
        self.assertEqual(off["edit"]["at"], 2.0)                               # the first downbeat clear of the cut
        self.assertIn("sits on no beat", off["reason"])

    def test_every_move_of_a_combined_option_must_be_layable_and_all_are_laid(self):
        a, b = scene("S1", 0, 6.0, BEATS, ["x"]), scene("S2", 6.0, 9.0, BEATS, ["y"])
        bad = [{"option": "Bold", "moves": ["crash-zoom", "match-cut-motion"]}]
        self.assertTrue(D.pick(a, b, bad, TARGET, LIB, {})["from"].startswith("the best move the edit lays from the shortlist"))
        self.assertIn("share no motion", bad[0]["gaps"][0]["gap"])
        both = D.pick(a, b, [{"option": "Bold", "moves": ["crash-zoom", "whip-pan-handoff"]}], TARGET, LIB, {})
        self.assertEqual([e["move"] for e in both["edits"]], ["crash-zoom", "whip-pan-handoff"])
        self.assertEqual(both["edits"][1]["transition"], "whip")


class Production(unittest.TestCase):
    def make(self, root):
        B = Path(root) / "p1"
        for s, words in (("S1", "I took it from the collar."), ("S2", "He pressed the seal.")):
            (B / "scenes" / s).mkdir(parents=True)
            (B / "scenes" / s / "take-1.json").write_text(json.dumps({"title": s, "lane": "ai", "words": words}))
        (B / "scenes" / "S1" / "take.json").write_text(json.dumps({"beats": [{"shot": "S1.1", "who": "HER", "action": "lifts the tube out of the round collar"}]}))
        (B / "scenes" / "S2" / "take.json").write_text(json.dumps({"beats": [{"shot": "S2.1", "who": "HIM", "action": "presses the wax seal"}]}))
        (B / "brief.json").write_text(json.dumps({"title": "Test", "order": ["S1", "S2"], "picks": {"S1": "take-1", "S2": "take-1"},
                                                  "lane": "ai"}))
        (B / "studio-build").mkdir()
        (B / "studio-build" / "layout.json").write_text(json.dumps({"length": 8.0, "scenes": [
            {"scene": "S1", "start": 0.0, "end": 6.0}, {"scene": "S2", "start": 6.0, "end": 8.0}]}))
        (B / "music").mkdir()
        (B / "music" / "bed.json").write_text(json.dumps({"starts_at": 0.0, "cue_sheet": [{"at": 0, "until": 8, "what": "groove"}]}))
        (B / "music" / "bed.mp3").write_bytes(b"x")
        R = Path(root) / "run"
        R.mkdir()
        return B, R

    def test_the_whole_pass_writes_the_edit_data_once_for_the_same_facts(self):
        with tempfile.TemporaryDirectory() as t:
            B, R = self.make(t)
            beats = lambda f: {"beats": BEATS, "tempo_bpm": 120, "by": "test"}  # noqa: E731
            rec = D.direct(B, R, "rules", beats_fn=beats)
            s1 = rec["scenes"][0]
            self.assertEqual(s1["hand_off_pair"], {"kind": "shape", "what": "round: collar -> seal"})
            self.assertEqual(s1["pick"]["moves"], ["match-cut-shape"])
            self.assertEqual(rec["edits"][0]["transition"], "match")
            self.assertEqual([o["option"] for o in s1["pitches"]], ["Safe", "Bold", "Wild"])
            f = B / "edit" / "moves-picks.json"
            m = f.stat().st_mtime_ns
            D.direct(B, R, "rules", beats_fn=beats)
            self.assertEqual(f.stat().st_mtime_ns, m)                        # same facts: the file is not rewritten
            self.assertTrue((B / "edit" / "moves-picks.md").exists())

    def test_the_director_answer_is_read_and_a_dead_door_falls_back_to_the_rules(self):
        with tempfile.TemporaryDirectory() as t:
            B, R = self.make(t)
            beats = lambda f: {"beats": BEATS, "tempo_bpm": 120, "by": "test"}  # noqa: E731
            answer = ('### Safe ...\n```json\n[{"option": "Safe", "moves": ["whip-pan-handoff"], "where": "hand-off", "cost": "free"},'
                      ' {"option": "Bold", "moves": ["match-cut-shape"], "where": "hand-off", "cost": "free"},'
                      ' {"option": "Wild", "moves": ["morph"], "where": "hand-off", "cost": "paid"}]\n```')
            seen = []
            rec = D.direct(B, R, "claude", ask=lambda p: seen.append(p) or answer, beats_fn=beats)
            self.assertIn("round: collar -> seal", "".join(seen[:1]) + rec["scenes"][0]["hand_off_pair"]["what"])
            self.assertNotIn("{scene}", seen[0])                              # every brace filled
            self.assertEqual(rec["scenes"][0]["pick"]["moves"], ["match-cut-shape"])
            self.assertTrue(any("paid generation" in g["gap"] for g in rec["scenes"][0]["gaps"]))

            def dead(p):
                raise RuntimeError("no login")
            rec = D.direct(B, R, "claude", ask=dead, force=True, beats_fn=beats)
            self.assertEqual(rec["scenes"][0]["pitches"][0]["by"], "rules (shortlist order)")


if __name__ == "__main__":
    unittest.main()
