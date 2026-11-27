"""Beats carried as fields into the take, and the made take read against them (2026-11-15).
python3 -m unittest test_take_beats (no network: the reader is stubbed)."""
import json
import tempfile
import unittest
from pathlib import Path

import take as TK
import take_beats as TB

CAST = {"JUDGE": {"look": "a woman in a satin dress"}, "ANDRE": {"look": "a masked man"}, "SEAN": {"look": "a masked man"}}


def take(**kw):
    return dict({"cast": CAST, "script": [
        {"speaker": "JUDGE", "say": "", "who": "JUDGE", "action": "lifts the loupe to her eye and leans in", "prop": "brass loupe",
         "target": "ANDRE's jaw and neck", "where": "first in the line"},
        {"speaker": "JUDGE", "say": "Ew.", "who": "JUDGE", "action": "turns her head away, nose wrinkled"},
        {"speaker": "JUDGE", "say": "", "who": "JUDGE", "action": "drops into a full squat", "target": "SEAN"}]}, **kw)


class Fields(unittest.TestCase):
    def test_a_beat_is_said_from_its_fields(self):
        w = TK.beat_words(take()["script"][0], 1)
        self.assertIn("1. JUDGE lifts the loupe to her eye and leans in, holding the brass loupe, to ANDRE's jaw and neck (first in the line).", w)

    def test_a_prop_or_target_already_in_the_action_is_not_said_twice(self):
        ln = {"who": "JUDGE", "action": "lifts the brass loupe to ANDRE's jaw", "prop": "brass loupe", "target": "ANDRE's jaw"}
        self.assertEqual(TK._mc().beat_action(ln), "JUDGE lifts the brass loupe to ANDRE's jaw")

    def test_an_old_prose_beat_still_reads_and_is_listed_to_split(self):
        t = {"cast": CAST, "script": [{"speaker": "JUDGE", "say": "", "do": "sniffs his neck"}]}
        self.assertIn("1. sniffs his neck.", TK.beat_words(t["script"][0], 1))
        g = TB.gaps(t)
        self.assertEqual(len(g), 1)
        self.assertFalse(g[0]["stop"])
        self.assertIn("split it", g[0]["why"])

    def test_a_beat_with_no_who_or_a_stranger_stops_the_take(self):
        t = take()
        t["script"][1] = {"speaker": "JUDGE", "say": "Ew.", "action": "turns away"}
        t["script"][2] = dict(t["script"][2], who="MARCUS")
        why = " ".join(g["why"] for g in TB.gaps(t) if g["stop"])
        self.assertIn("no who", why)
        self.assertIn("MARCUS does it but is not in the cast", why)

    def test_a_target_outside_the_cast_stops_the_take(self):
        t = take()
        t["script"][2] = dict(t["script"][2], target="KOFI")
        self.assertTrue(any("KOFI is not in the cast" in g["why"] for g in TB.gaps(t)))

    def test_a_target_name_followed_by_punctuation_is_read(self):
        t = take()
        t["script"][2] = dict(t["script"][2], target="ANDRE, then SEAN")
        self.assertEqual(TB.gaps(t), [])

    def test_beats_as_fields_take_only_the_swipe_shots_camera(self):
        src = Path(TK.__file__).read_text()
        self.assertIn('(ln or {}).get("action")', src)

    def test_a_complete_take_has_no_gaps(self):
        self.assertEqual(TB.gaps(take()), [])

    def test_seeded_beats_carry_the_action_when_the_script_only_speaks(self):
        t = {"cast": CAST, "script": [{"speaker": "JUDGE", "say": "Ew.", "lips": "on"}],
             "beats": [{"who": "JUDGE", "action": "turns away", "target": "ANDRE"}, {"who": "JUDGE", "action": "squats", "target": "SEAN"}]}
        self.assertEqual(len(TB.beats_of(t)), 2)
        self.assertEqual(TB.gaps(t), [])
        self.assertEqual(TK._mc().actions_of(t), ["JUDGE turns away, to ANDRE", "JUDGE squats, to SEAN"])


class DirectedCamera(unittest.TestCase):
    def test_our_shots_are_the_camera_and_the_swipe_shots_are_left_out(self):
        t = take(camera={"directed": True, "shots": [{"seconds": 2.7, "words": "medium two-shot, eye level, slow push in"},
                                                      {"seconds": 1.1, "words": "close-up on her face, low angle"}]},
                 swipe_shots="anything")
        words = TK.camera_words(t["camera"])
        self.assertIn("Shot 1 (0-2.7 s): medium two-shot, eye level, slow push in.", words)
        self.assertIn("Shot 2 (2.7-3.8 s): close-up on her face, low angle.", words)
        self.assertEqual(TK.shot_list(t), "")


class ReadTheTake(unittest.TestCase):
    def _stub(self, answer):
        return lambda text, clip: (json.dumps(answer), {"model": "stub", "prompt": text})

    def test_every_beat_seen_passes(self):
        with tempfile.TemporaryDirectory() as d:
            clip = Path(d) / "take.mp4"
            clip.write_bytes(b"x")
            res = TB.hold_misses(take(), clip, ask=self._stub({"beats": [{"beat": k, "seen": True} for k in (1, 2, 3)],
                                                               "cast": {"ok": True}, "lineup": {"ok": True}}))
            self.assertTrue(res["pass"])
            self.assertTrue(clip.exists())
            rec = json.loads((Path(d) / "take.mp4.beats.json").read_text())
            self.assertIn("lifts the loupe to her eye", rec["prompt"])          # the reader is given our fields
            self.assertIn('"prop": "brass loupe"', rec["prompt"])

    def test_a_beat_acted_another_way_is_not_used(self):
        with tempfile.TemporaryDirectory() as d:
            clip = Path(d) / "take.mp4"
            clip.write_bytes(b"x")
            ans = {"beats": [{"beat": 1, "seen": False, "shows": "she sniffs his neck, no loupe"}, {"beat": 2, "seen": True}],
                   "cast": {"ok": True}, "lineup": {"ok": False, "why": "a fifth man joins at 9 s"}}
            with self.assertRaises(SystemExit) as e:
                TB.hold_misses(take(), clip, ask=self._stub(ans))
            msg = str(e.exception)
            self.assertIn("beat 1 not shown (she sniffs his neck, no loupe)", msg)
            self.assertIn("beat 3 not shown (not read)", msg)          # a beat the reader skipped is a miss, never a pass
            self.assertIn("line-up: a fifth man joins at 9 s", msg)
            self.assertFalse(clip.exists())
            self.assertTrue((Path(d) / "take.beats-miss.mp4").exists())


class SceneReview(unittest.TestCase):
    def test_the_review_page_shows_inputs_beats_and_the_exact_prompt(self):
        with tempfile.TemporaryDirectory() as d:
            sd = Path(d)
            (sd / "start.png").write_bytes(b"png")
            planned = {"picture": str(sd / "start.png"), "prompt": "THE EXACT PROMPT", "route": "r", "seconds": 15,
                       "cost": {"amount": 1}, "voices": [], "beat_gaps": []}
            page = TK.review(sd, take(), planned, {"motion": "passed"})
            html = page.read_text()
            self.assertIn("THE EXACT PROMPT", html)
            self.assertIn("brass loupe", html)
            self.assertIn('src="../start.png"', html)
            rec = json.loads((sd / "review" / "input-review.json").read_text())
            self.assertEqual(rec["beats"][0]["target"], "ANDRE's jaw and neck")
            self.assertEqual([i["role"] for i in rec["inputs"]][:2], ["start picture", "cast · JUDGE"])


if __name__ == "__main__":
    unittest.main()
