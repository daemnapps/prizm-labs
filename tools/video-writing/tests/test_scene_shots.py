#!/usr/bin/env python3
"""Scenes are sequences (BRIEF-SPEC "Scenes and shots", 2026-11-08): one moment split into one scene per line is
caught, and folding it keeps every shot, line, speaker and beat in order.

    python3 components/video-writing/tests/test_scene_shots.py

Stdlib `unittest`, Python 3.9. No network, no model, no key.
"""
import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "machine"))
import scene_shots as SS  # noqa: E402


def turn(n, speaker, say, parent="S1"):
    sid = f"S1T{n}"
    return {"id": sid, "section": "hook", "kind": "talking", "speaker": speaker, "voice": say, "parent_scene": parent,
            "setting_id": "SET", "who": "HOST, GUEST", "first_frame": {"subject": f"frame {n}"},
            "last_frame": {"change": f"end {n}"},
            "shots": [{"id": f"{sid}.1", "copies": "K01", "lines": [{"say": say}]}],
            "beats": [{"id": "B1", "shot": f"{sid}.1", "do": f"beat {n}"}]}


class SceneShots(unittest.TestCase):
    def setUp(self):
        self.scenes = [turn(1, "HOST", "Question?"), turn(2, "GUEST", "Answer."), turn(3, "HOST", "Why?"),
                       {"id": "S2", "section": "proof", "kind": "card", "shots": [{"id": "S2.1"}]}]

    def test_a_split_moment_is_caught(self):
        got = SS.check(self.scenes)
        self.assertEqual(len(got), 1)
        self.assertIn("S1T1–S1T3", got[0])

    def test_fold_keeps_every_shot_line_and_speaker_in_order(self):
        out = SS.fold(self.scenes)
        self.assertEqual([s["id"] for s in out], ["S1", "S2"])
        s1 = out[0]
        self.assertEqual([sh["id"] for sh in s1["shots"]], ["S1.1", "S1.2", "S1.3"])
        self.assertEqual([sh["speaker"] for sh in s1["shots"]], ["HOST", "GUEST", "HOST"])
        self.assertEqual([x["speaker"] for x in s1["script"]], ["HOST", "GUEST", "HOST"])
        self.assertEqual(s1["voice"], "Question? Answer. Why?")
        self.assertEqual(s1["speaker"], "several")
        self.assertEqual([b["shot"] for b in s1["beats"]], ["S1.1", "S1.2", "S1.3"])
        self.assertEqual(s1["first_frame"]["subject"], "frame 1")
        self.assertEqual(s1["last_frame"]["change"], "end 3")
        self.assertEqual([sh.get("scene_master") for sh in s1["shots"]], [None, "S1.1", "S1.1"])
        self.assertEqual(s1["take"], "continuous")               # every shot copies K01: the swipe holds one take
        self.assertEqual(s1["motion"], {"copies": "K01"})

    def test_cards_and_separate_moments_stay_apart(self):
        other = turn(4, "HOST", "Elsewhere.", parent="S9")
        out = SS.fold(self.scenes[:2] + [other] + self.scenes[3:])
        self.assertEqual([s["id"] for s in out], ["S1", "S1T4", "S2"])

    def test_a_brief_already_in_sequences_passes(self):
        self.assertEqual(SS.check(SS.fold(self.scenes)), [])


if __name__ == "__main__":
    unittest.main()
