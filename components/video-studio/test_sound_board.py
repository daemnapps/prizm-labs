"""The Sound board: the swipe's sounds found and named per scene, ours matched, the checks, a take made. No network,
no spend.  python3 -m unittest test_sound_board.py"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sound_board as SB  # noqa: E402

SHEET = {"music": {"present": True, "measured": {"present": True, "starts": 0.0, "ends": 41.9, "changes": [
    {"at": 12, "what": "drops out"}, {"at": 15, "what": "builds / hits"}, {"at": 41, "what": "drops out"}]}},
    "vocal_sounds": [{"at": 9.36, "end": 15.04, "sound": "sighs", "speaker": "speaker_0"}]}
WORDS = {"words": [{"start": 0.0, "end": 2.98, "text": "[sniffs]", "type": "audio_event", "speaker": "speaker_0"},
                   {"start": 3.06, "end": 3.3, "text": "Ew.", "type": "word", "speaker": "speaker_0"},
                   {"start": 14.02, "end": 15.06, "text": "[sighs]", "type": "audio_event", "speaker": "speaker_0"},
                   {"start": 15.14, "end": 15.26, "text": "It's", "type": "word", "speaker": "speaker_1"},
                   {"start": 15.3, "end": 15.38, "text": "Oh", "type": "word", "speaker": "speaker_1"}]}


class SwipeSounds(unittest.TestCase):
    def test_music_sections_are_named_build_break_hit_drop_out(self):
        names = [s["name"] for s in SB.music_sections(SHEET, 0.0, 42.0)]
        self.assertEqual(names, ["build", "break", "hit", "drop", "out"])

    def test_a_scene_gets_only_its_own_sections_and_the_hit_on_its_end(self):
        got = [(s["name"], s["at"]) for s in SB.music_sections(SHEET, 0.0, 15.0)]
        self.assertEqual(got, [("build", 0.0), ("break", 12.0), ("hit", 15.0)])

    def test_vocal_sounds_are_events_and_lone_interjections_not_words(self):
        got = SB.vocal_sounds(WORDS, SHEET, 0.0, 15.1)
        self.assertEqual([v["name"] for v in got], ["sniffs", '"Ew."', "sighs"])   # "Oh" sits inside speech; sighs once

    def test_a_long_event_span_is_cut_to_the_sound(self):
        self.assertEqual(SB.tight(0.0, 2.98), (0.48, 2.98))


class Checks(unittest.TestCase):
    def test_lands_within_one_frame(self):
        f = 1 / 23.976
        self.assertTrue(SB.check_lands(2.26, 2.28, f)["ok"])
        bad = SB.check_lands(2.26, 2.40, f)
        self.assertFalse(bad["ok"])
        self.assertIn("late", bad["short"])

    def test_level_within_three_db(self):
        self.assertTrue(SB.check_level(9.0, 7.5, "over the music")["ok"])
        bad = SB.check_level(9.0, 2.0, "over the music")
        self.assertFalse(bad["ok"])
        self.assertIn("too quiet", bad["short"])
        self.assertIsNone(SB.check_level(None, 2.0, "x")["ok"])

    def test_the_ear_passes_same_and_close(self):
        self.assertTrue(SB.check_ear({"match": "close", "differs": "a bit brighter"})["ok"])
        self.assertFalse(SB.check_ear({"match": "different"})["ok"])
        self.assertIsNone(SB.check_ear({"error": "no key"})["ok"])


class Ours(unittest.TestCase):
    def test_made_from_names_the_bank_file_or_the_prompt(self):
        self.assertEqual(SB.made_from_effect({"file": "/x/Shared Assets/banks/sfx/click.mp3"})["kind"], "bank")
        self.assertEqual(SB.made_from_effect({"file": "/b/t.mp3", "prompt": "a pop"})["kind"], "prompt")

    def test_latest_cut_is_the_highest_version(self):
        with tempfile.TemporaryDirectory() as td:
            for v in ("rough-cut-v2-sdr.mp4", "rough-cut-v18-sdr.mp4", "rough-cut-v18-raw.mp4", "rough-cut-v9-sdr.mp4"):
                Path(td, v).write_bytes(b"")
            self.assertTrue(SB.latest_cut(td).endswith("rough-cut-v18-sdr.mp4"))

    def test_music_made_from_names_the_take_and_its_cue(self):
        bed = {"source": "elevenlabs", "take": "take-s11.mp3",
               "cue_sheet": [{"at": 0.0, "until": 12.0, "what": "the build under the line walk"}]}
        mf = SB.music_made_from(bed, 0.0, 12.0)
        self.assertIn("take-s11.mp3", mf["label"])
        self.assertIn("the build", mf["label"])


class Ear(unittest.TestCase):
    def test_a_silent_clip_is_never_sent_to_the_ear(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td) / "a.mp3", Path(td) / "b.mp3"
            SB.ff("-f", "lavfi", "-t", "1", "-i", "sine=frequency=440", a)
            SB.ff("-f", "lavfi", "-t", "1", "-i", "anullsrc=r=44100:cl=mono", b)
            got = SB.ear(a, b, "sound effect")
        self.assertEqual(got["match"], "different")
        self.assertIn("ours is silent", got["differs"])
        self.assertIsNone(got["model"])


class MakeATake(unittest.TestCase):
    def test_a_take_goes_through_sound_generation_with_its_prompt_kept(self):
        card = {"kind": "effect", "name": "click", "soft": False,
                "swipe": {"at": 2.26, "until": None, "job": "caption-pop"}}
        seen = {}

        def transport(url, body, key):
            seen["url"], seen["body"] = url, json.loads(body)
            return b"ID3fake"
        with tempfile.TemporaryDirectory() as td:
            t = SB.make_take(card, Path(td) / "t.mp3", key="k", transport=transport)
            self.assertEqual(Path(t["file"]).read_bytes(), b"ID3fake")
        self.assertIn("/v1/sound-generation", seen["url"])
        self.assertIn("click", seen["body"]["text"])
        self.assertIn("caption pop", t["prompt"])
        self.assertGreaterEqual(seen["body"]["duration_seconds"], 0.5)

    def test_a_room_heard_as_silence_is_asked_for_as_a_quiet_room(self):
        self.assertIn("quiet small indoor room", SB.take_prompt({"kind": "room", "name": "room tone", "room_word": "silence", "swipe": {}}))

    def test_room_tone_loops(self):
        card = {"kind": "room", "name": "room tone", "room_word": "a quiet bathroom", "swipe": {"at": 13.1}}
        body = {}
        with tempfile.TemporaryDirectory() as td:
            SB.make_take(card, Path(td) / "r.mp3", key="k",
                         transport=lambda u, b, k: body.update(json.loads(b)) or b"x")
        self.assertTrue(body["loop"])
        self.assertIn("bathroom", body["text"])


if __name__ == "__main__":
    unittest.main()
