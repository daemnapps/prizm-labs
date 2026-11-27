#!/usr/bin/env python3
"""BRIEF-SPEC rule 9 (2026-11-12): every swipe shot's picture is measured against the voice, and the take is made the
way that picture needs: lips on, mimed, or the voice laid over a silent picture.

    python3 components/video-studio/test_lips.py

Stdlib unittest, Python 3.9; no model, no video, no key (the face reading itself is not run here).
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lips as L  # noqa: E402
import seed_from_brief as SB  # noqa: E402
import take as T  # noqa: E402


def frames(jaws, x=0.5, size=0.3, feat=None, fps=8):
    return [{"t": i / fps, "faces": [] if j is None else [{"x": x, "size": size, "jaw": j, "feat": feat}]}
            for i, j in enumerate(jaws)]


TALK = [0.05, 0.4, 0.1, 0.5, 0.05, 0.45, 0.1, 0.4, 0.05, 0.5, 0.1, 0.45, 0.05, 0.4, 0.1, 0.5]   # 2 s, opening and closing
GASP = [0.02] * 6 + [0.5, 0.6, 0.6, 0.5] + [0.02] * 6                                             # one opening, a gasp
STILL = [0.02] * 16
SPEECH = [(0.0, 2.0)]


class Pictures(unittest.TestCase):
    def test_the_owner_speaking_is_talking(self):
        self.assertEqual(L.judge(frames(TALK), 0, 2, SPEECH, True)["picture"], "talking")

    def test_someone_else_mouthing_the_voice_is_mime(self):
        self.assertEqual(L.judge(frames(TALK), 0, 2, SPEECH, False)["picture"], "mime")

    def test_one_opening_is_a_reaction_not_speech(self):
        self.assertEqual(L.judge(frames(GASP), 0, 2, SPEECH, True)["picture"], "reaction")

    def test_the_owner_on_screen_with_a_still_mouth_is_present(self):
        got = L.judge(frames(STILL), 0, 2, SPEECH, True)
        self.assertEqual((got["picture"], got["lips"]), ("present", "off"))

    def test_no_face_is_away(self):
        self.assertEqual(L.judge(frames([None] * 16), 0, 2, SPEECH, True)["picture"], "away")

    def test_no_voice_is_silent(self):
        self.assertEqual(L.judge(frames(TALK), 0, 2, [], True)["picture"], "silent")

    def test_the_moving_face_is_told_by_likeness(self):
        owner, other = [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]
        self.assertEqual(L.judge(frames(TALK, feat=other), 0, 2, SPEECH, None, owner, 0.7)["picture"], "mime")
        self.assertEqual(L.judge(frames(TALK, feat=owner), 0, 2, SPEECH, None, owner, 0.7)["picture"], "talking")

    def test_each_speaker_has_their_own_face(self):
        a, b, stranger = [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]
        refs = [(a, 0.7), (b, 0.7)]
        self.assertEqual(L.judge(frames(TALK, feat=b), 0, 2, SPEECH, None, refs)["picture"], "talking")
        self.assertEqual(L.judge(frames(TALK, feat=stranger), 0, 2, SPEECH, None, refs)["picture"], "mime")
        # with a speaker whose face was never learned, an unknown mouth is not called a mime
        self.assertEqual(L.judge(frames(TALK, feat=stranger), 0, 2, SPEECH, None, refs, None, False)["picture"], "talking")


class Owners(unittest.TestCase):
    def test_who_speaks_comes_from_the_cast_list(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "stages").mkdir()
            (Path(d) / "stages" / "1-teardown.md").write_text(
                "**CAST**\n\n### Presenter\n* **Role and screen time:** on screen; Voice (00:00 - 00:20).\n"
                "* **Voice:** bright.\n\n### Older Woman 1 (Couch)\n* **Role and screen time:** on screen.\n"
                "* **Voice:** None.\n\n**Husband**\n*   **Role and screen time:** On screen 1:51. Speaks: none.\n")
            self.assertEqual(L.voice_owners(d), ["presenter"])


class Takes(unittest.TestCase):
    def take(self, lips, mouthed_by=None):
        ln = {"speaker": "NARRATOR", "say": "I stole it.", "lips": lips}
        if mouthed_by:
            ln["mouthed_by"] = mouthed_by
        return {"script": [ln], "speakers": {"NARRATOR": ["r.mp3"]}}

    def test_a_voice_over_line_sends_no_voice_and_keeps_mouths_closed(self):
        tk = self.take("off")
        self.assertEqual(T.speaking(tk), {})
        text = T.prompt(tk, [], False)
        self.assertIn("voice-over", text)
        self.assertNotIn("I stole it", text)       # a voice-over line is never typed into the prompt
        self.assertIn("Mouths stay closed", text)

    def test_a_mimed_line_names_who_mouths_it(self):
        text = T.prompt(self.take("mime", "Husband"), [], False)
        self.assertIn("Husband mouths these words with no sound", text)

    def test_a_spoken_line_keeps_its_voice(self):
        tk = self.take("on")
        self.assertEqual(list(T.speaking(tk)), ["NARRATOR"])
        self.assertIn("lips matching every word", T.prompt(tk, [("NARRATOR", "v.mp3")], False))


class Seeding(unittest.TestCase):
    def test_a_run_of_shots_is_talking_if_anyone_speaks_in_it(self):
        pics = {"K01": {"picture": "present"}, "K02": {"picture": "talking"}, "K03": {"picture": "away"}}
        self.assertEqual(SB.picture_of(SB.k_ids("K01-K03"), pics)[0], "talking")
        self.assertEqual(SB.lips_of("present"), "off")
        self.assertEqual(SB.k_ids("K05-K07, K42"), ["K05", "K06", "K07", "K42"])


if __name__ == "__main__":
    unittest.main()
