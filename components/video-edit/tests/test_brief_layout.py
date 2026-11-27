"""The brief layout (machine/brief_layout.py): one caption style runs through the whole piece, taken from the swipe's
caption read for the hook; a later read naming another style is a note, never applied; card lines are one block."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import brief_layout as L  # noqa: E402

DOC = {"edit": {"captions": "white text with a black outline, centred, through S2; from S3 on, black text on a white box at lower centre"},
       "scenes": [{"id": "S1", "kind": "broll", "on_screen": "2025 / how sad"},
                  {"id": "S2", "kind": "broll", "on_screen": "a for the first 0.4 s, then b"},
                  {"id": "S3", "kind": "card", "lines": ["one", "two"]}]}
TIMES = [{"scene": "S1", "start": 0, "end": 2}, {"scene": "S2", "start": 2, "end": 4}, {"scene": "S3", "start": 4, "end": 6}]


class OneStyle(unittest.TestCase):
    def test_the_hooks_style_runs_all_the_way_through(self):
        ws = L.words(DOC, TIMES)
        self.assertEqual({(w["look"], w["where"]) for w in ws}, {("headline-plain", "centre")})
        style, notes = L.caption_style(DOC)
        self.assertEqual(style["look"], "headline-plain")
        self.assertEqual(len(notes), 1)                                   # the white-box read is noted, not used

    def test_card_lines_are_one_block_and_splits_hold(self):
        ws = L.words(DOC, TIMES)
        self.assertEqual([w["text"] for w in ws], ["2025\nhow sad", "a", "b", "one\ntwo"])

    def test_no_read_falls_back_to_the_tiktok_outline(self):
        style, notes = L.caption_style({"scenes": []})
        self.assertEqual((style["look"], notes), ("headline-plain", []))


class Lanes(unittest.TestCase):
    def test_the_roll_sheet_puts_each_scene_on_its_lane(self):
        doc = {"roll_sheet": [{"scene": "S1", "roll": "B-silent"}, {"scene": "S2", "roll": "G"}],
               "scenes": [{"id": "S1", "kind": "broll"}, {"id": "S2", "kind": "greenscreen"}, {"id": "S3", "kind": "card"},
                          {"id": "S4", "kind": "talking", "voice": "hi"}, {"id": "S5", "kind": "endcard"}]}
        self.assertEqual(L.lanes(doc), {"S1": "B", "S2": "G", "S3": "C", "S4": "A", "S5": "E"})

    def test_a_card_slot_is_named_by_its_words(self):
        self.assertEqual(L.shows({"kind": "card", "lines": ["one", "two"]}), "one / two")


class SprtnCalls(unittest.TestCase):
    """2026-11-07, laid out on sprtn-18000-men."""
    def test_a_roll_sheet_row_remade_as_moving_broll_puts_the_scene_on_broll(self):
        doc = {"roll_sheet": [{"scene": "", "roll": "C", "dropped": "re-made as moving B-roll S2: the render moves"}],
               "scenes": [{"id": "S1", "kind": "broll"}, {"id": "S2", "kind": "card", "lines": ["x"]}]}
        self.assertEqual(L.lanes(doc)["S2"], "B")

    def test_an_untimed_end_card_keeps_the_swipes_length_from_the_end(self):
        doc = {"song": {"sections": [{"name": "outro", "scene": "S1", "seconds": 7}]},
               "scenes": [{"id": "S1", "kind": "broll", "beats": [1, 2, 3]},
                          {"id": "S2", "kind": "endcard", "source": "0:36.0 - 0:41.0 · E · [endcard]"}]}
        times, end, _ = L.clock(doc)
        self.assertEqual((times[1]["start"], end), (2.0, 7.0))

    def test_end_card_offer_and_button_lines_are_on_screen(self):
        doc = {"scenes": [{"id": "S1", "kind": "endcard", "endcard": {"offer_lines": ["USE IT"], "cta": "TAP BELOW", "guarantee": "90 days"}}]}
        ws = L.words(doc, [{"scene": "S1", "start": 0, "end": 5}])
        self.assertEqual([w["text"] for w in ws], ["USE IT\nTAP BELOW"])


class SoundRows(unittest.TestCase):
    """compose.py puts each sound on its own lane (lanes.json): the voice read and its cuts on Voice, music on Music,
    room tone and effects below. A row is display only."""
    def test_voice_music_room_tone_and_effects_each_on_their_row(self):
        import re
        import subprocess
        import tempfile
        import compose as C
        d = Path(tempfile.mkdtemp())
        wav = d / "a.wav"
        png = d / "a.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=d=1", "-t", "1", str(wav)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=108x192", "-frames:v", "1", str(png)], check=True)
        sheet = {"meta": {"label": "rows-test", "width": 1080, "height": 1920, "fps": 30}, "overlays": [], "markers": [],
                 "picture": [{"id": "S1", "roll": "a", "src": str(png), "start": 0, "duration": 1, "source_start": 0,
                              "scene": "S1", "still": True, "volume_db": None, "drift": False, "track": 2, "row": "B-roll",
                              "label": "S1", "why": "test"}],
                 "captions": {"look": None, "words": []}, "controls": {"captions": {"value": "off"}},
                 "voice": {"src": str(wav), "start": 0}, "music": {"src": str(wav), "start": 0},
                 "voice_cuts": [{"id": "vc", "src": str(wav), "start": 0, "duration": 0.5, "source_start": 0}],
                 "room_tone": [{"id": "rt", "src": str(wav), "start": 0, "duration": 0.5}],
                 "sfx": [{"id": "fx", "src": str(wav), "at": 0.5}]}
        C.compose(sheet, d, d / "p", captions=False)
        rows = dict(re.findall(r'<audio id="([a-z]+)[^"]*"[^>]*data-track-index="(\d+)"', (d / "p" / "index.html").read_text()))
        self.assertEqual(rows, {"voice": "8", "vc": "8", "music": "10", "rt": "12", "fx": "13"})


if __name__ == "__main__":
    unittest.main()
