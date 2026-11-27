"""shot_list: a take with its own beats gets only the swipe shots' timing and camera, never their people, actions or
graphics. python3 -m unittest test_take_shot_list_own_beats.py"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import take as T  # noqa: E402

FM = {"shots": [{"start": 0.0, "end": 2.7, "map": {
    "camera": {"distance": "medium", "height": "eye level", "held": "held by someone else", "move": "push-in at the end"},
    "start_frame": "Blonde Woman stands on the right. A green WhatsApp box graphic is superimposed.",
    "end_frame": "Blonde Woman looks away in disgust.",
    "moments": [{"t": 1.5, "who": "Blonde Woman", "does": "holds position near his chest, sniffing", "face": "eyes closed"}]}}]}


class OwnBeats(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "framemap").mkdir()
        (self.d / "framemap" / "framemap.json").write_text(json.dumps(FM))
        (self.d / "source.mp4").write_bytes(b"")
        self.take = {"motion": {"source": str(self.d / "source.mp4"), "from": 0, "to": 2.7}, "cast": {"JUDGE": {}}}

    def test_own_beats_keep_only_camera_and_timing(self):
        t = dict(self.take, script=[{"speaker": "JUDGE", "do": "inspects his jaw through the loupe"}])
        text = T.shot_list(t)
        self.assertIn("Shot 1 (0.0-2.7 s)", text)
        self.assertIn("push-in at the end", text)
        for leak in ("Blonde", "WhatsApp", "sniffing", "graphic", "opens on"):
            self.assertNotIn(leak, text)

    def test_no_beats_keeps_the_swipe_direction(self):
        text = T.shot_list(dict(self.take, script=[{"speaker": "JUDGE", "say": "hi"}]))
        self.assertIn("opens on", text)


if __name__ == "__main__":
    unittest.main()


class SwipeLeaks(unittest.TestCase):
    """swipe_leaks: the swipe's people, actions and graphics in a prompt stop the take; our own words and the camera
    never do."""
    def setUp(self):
        OwnBeats.setUp(self)
        self.take = dict(self.take, script=[{"speaker": "JUDGE", "do": "inspects his jaw through the loupe"}])

    def test_the_swipes_words_are_caught(self):
        leaks = T.swipe_leaks(self.take, "JUDGE leans in, sniffing; a green WhatsApp box; Blonde Woman looks away.")
        for w in ("sniffing", "whatsapp", "blonde"):
            self.assertIn(w, leaks)

    def test_our_words_and_the_camera_pass(self):
        self.assertEqual(T.swipe_leaks(self.take, "JUDGE inspects his jaw through the loupe. Camera: medium, eye level, "
                                                  "held by someone else, push-in at the end."), [])

    def test_a_word_meant_on_purpose_passes(self):
        t = dict(self.take, allow_words=["sniffing"])
        self.assertNotIn("sniffing", T.swipe_leaks(t, "she is sniffing"))
