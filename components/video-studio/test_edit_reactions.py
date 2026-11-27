"""The edit stage's sound from the swipe, by ear: music from the checked listen, the people's own sounds laid."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edit_stage as ES  # noqa: E402

SOUND = {"music": {"present": True, "heard": {"genre": "Pop", "subgenre": "Synth-Pop", "instruments": ["synthesizer"]},
                   "measured": {"tempo_bpm": 161.5, "changes": [{"at": 12, "what": "drops out"}]},
                   "checked": {"agreed": True, "family": "hip-hop", "genre": "R&B / Hip-Hop", "subgenre": "Trapsoul",
                               "bpm": 80, "felt_tempo": "half-time", "instruments": ["808 bass", "trap hi-hats"],
                               "mood_words": ["moody"]}},
         "human_sounds": [{"at": 2.7, "until": 3.0, "sound": "ew", "feeling": "disgust"},
                          {"at": 8.5, "until": 10, "sound": "mmm", "feeling": "delighted"},
                          {"at": 12.5, "until": 14, "sound": "sigh", "feeling": "aroused"},
                          {"at": 20.0, "until": 21, "sound": "word", "feeling": "none"}]}


class Reactions(unittest.TestCase):
    def test_the_music_is_the_checked_listen_not_the_name(self):
        plan, _ = ES.music_plan(SOUND, lambda t: t, 30.0)
        styles = " ".join(plan["positive_global_styles"])
        self.assertIn("Trapsoul", styles)
        self.assertIn("808 bass", styles)
        self.assertNotIn("Synth-Pop", styles)
        self.assertIn("synth-pop", plan["negative_global_styles"])

    def test_every_sound_is_a_move_on_our_clock_and_feelings_turn_up(self):
        moves = ES.reaction_moves(SOUND, lambda t: t + 1.0)
        self.assertEqual([m["sound"] for m in moves], ["ew", "mmm", "sigh"])
        self.assertEqual(moves[0]["ours"], 3.7)
        self.assertIn("disgusted", ES.reaction_text("ew", "disgust"))
        self.assertIn("pleasure", ES.reaction_text("sigh", "aroused"))
        self.assertIsNone(ES.reaction_text("word", "none"))

    def test_laid_in_the_voice_once_and_held_without_a_voice(self):
        B = Path(tempfile.mkdtemp())
        (B / "music").mkdir()
        moves = ES.reaction_moves(SOUND, lambda t: t)
        bed = {"effects": []}
        self.assertEqual(ES.lay_reactions(B, moves, bed, {}), [])
        self.assertIn("no voice named", moves[0]["reason_open"])
        made = []
        orig = ES.make_reaction
        ES.make_reaction = lambda text, voice, out, **k: (made.append(text), Path(out).write_bytes(b"x"))
        try:
            moves = ES.reaction_moves(SOUND, lambda t: t)
            got = ES.lay_reactions(B, moves, bed, {"edit_voices": {"reactions": "voice-1"}})
            self.assertEqual(len(got), 3)
            self.assertEqual([e["at"] for e in bed["effects"]], [2.7, 8.5, 12.5])
            again = ES.reaction_moves(SOUND, lambda t: t)
            self.assertEqual(ES.lay_reactions(B, again, bed, {"edit_voices": {"reactions": "voice-1"}}), [])
            self.assertEqual(len(made), 3)
            self.assertTrue(all(m.get("landed") for m in again))
        finally:
            ES.make_reaction = orig


if __name__ == "__main__":
    unittest.main()
