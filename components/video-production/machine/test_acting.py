"""python3 machine/test_acting.py — every to-camera shot says what the face and hands visibly do (V46). No network."""
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_sp = importlib.util.spec_from_file_location("acting", HERE / "acting.py")
A = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(A)


class Acting(unittest.TestCase):
    def test_an_emotion_word_is_not_a_visible_action(self):
        self.assertFalse(A.visible("shocked"))
        self.assertFalse(A.visible("a little skeptical and then confident"))
        self.assertTrue(A.visible("eyes narrow, the lips press together"))
        self.assertFalse(A.visible(""))

    def test_the_bank_has_a_video_line_for_every_emotion(self):
        b = A.bank()
        self.assertEqual(len(b), 12)
        self.assertTrue(all(e["video"] for e in b.values()))

    def test_a_blank_face_is_filled_from_the_emotions_bank_line(self):
        shots, notes = A.fill([{"id": "S1", "emotion": "disgust at the stain", "face": "disgusted", "gestures": "taps the counter"}],
                              {"gestures": ""}, True)
        self.assertEqual(shots[0]["face"], "The close-up, the wince")
        self.assertTrue(any(n["status"] == "filled" and n["field"] == "face" for n in notes))

    def test_an_empty_field_with_nothing_to_fill_it_from_is_marked_not_applicable_with_a_reason(self):
        shots, notes = A.fill([{"id": "S2", "face": "", "gestures": ""}], {}, True)
        na = [n for n in notes if n["status"] == "not applicable"]
        self.assertTrue(na and all(n.get("reason") for n in na))
        self.assertEqual(shots[0]["face"], "")

    def test_no_character_section_is_said_once_not_sent_silently_as_nothing(self):
        _, notes = A.fill([{"id": "S1", "face": "lips press", "gestures": "taps"}], {}, True, {1, 2, 3})
        self.assertTrue(any(n["field"] == "character" and "Life marks and gestures" in n["reason"] for n in notes))

    def test_a_silent_call_is_not_held_to_it(self):
        _, notes = A.fill([{"id": "S1"}], {}, False)
        self.assertEqual(notes, [])

    def test_the_persons_own_gestures_cover_an_empty_gestures_field(self):
        _, notes = A.fill([{"id": "S1", "face": "lips press", "gestures": ""}], {"gestures": "tucks hair"}, True, {2})
        self.assertTrue(any(n["field"] == "gestures" and n["status"] == "ok" for n in notes))


if __name__ == "__main__":
    unittest.main()
