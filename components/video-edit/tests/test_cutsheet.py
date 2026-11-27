"""The gate and the caption grouping. No media, no renders, no live runs."""
import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import compose as C, cutsheet as CS

def sheet(root: Path, **over):
    for f in ("a.mp4", "b.mp4", "v.mp3"): (root / f).write_bytes(b"x")
    d = json.loads((Path(CS.TOOL) / "machine/defaults.json").read_text())
    s = {"meta": {"brand": "t", "label": "t", "width": 1080, "height": 1920, "fps": 30}, "controls": d,
         "voice": {"src": "v.mp3", "start": 0, "volume_db": 0}, "music": None, "sfx": [],
         "picture": [{"id": "a1", "roll": "a", "src": "a.mp4", "start": 0, "duration": 10, "source_start": 0, "why": "line"},
                     {"id": "b1", "roll": "b", "src": "b.mp4", "start": 2, "duration": 2, "source_start": 0, "why": "shows it"}],
         "captions": {"look": "bold-highlight", "words": [{"text": "Hi", "start": 0.1, "end": 0.4}]}, "overlays": []}
    s.update(over); return s

class Gate(unittest.TestCase):
    def setUp(self): self.t = tempfile.TemporaryDirectory(); self.root = Path(self.t.name)
    def tearDown(self): self.t.cleanup()
    def red(self, s): return CS.check(s, self.root, probe=lambda p: 10.0)
    def test_green(self): self.assertEqual(self.red(sheet(self.root)), [])
    def test_hole(self):
        s = sheet(self.root); s["picture"][0]["start"] = 1
        self.assertTrue(any("hole" in r for r in self.red(s)))
    def test_broll_needs_aroll(self):
        s = sheet(self.root); s["picture"][1]["start"] = 9.5
        self.assertTrue(any("nothing under it" in r for r in self.red(s)))
    def test_trim_past_source(self):
        s = sheet(self.root); s["picture"][1]["source_start"] = 9
        self.assertTrue(any("past the source" in r for r in self.red(s)))
    def test_unknown_look_names_the_real_ones(self):
        s = sheet(self.root); s["captions"]["look"] = "fancy"
        self.assertTrue(any("bold-highlight" in r for r in self.red(s)))
    def test_talking_clip_must_keep_its_sound(self):
        s = sheet(self.root); s["voice"] = None; s["picture"][0].update(talks=True, volume_db=None)
        self.assertTrue(any("muted" in r for r in self.red(s)))
    def test_two_voices(self):
        s = sheet(self.root); s["picture"][0].update(talks=True, volume_db=0)
        self.assertTrue(any("two voices" in r for r in self.red(s)))
    def test_broll_over_a_voice_cut_is_fine(self):
        s = sheet(self.root); s["voice"] = None
        s["picture"] = [{"id": "b1", "roll": "b", "src": "b.mp4", "start": 0, "duration": 4, "source_start": 0, "why": "covers its voice"}]
        s["voice_cuts"] = [{"id": "v1", "src": "v.mp3", "start": 0, "duration": 4, "source_start": 0, "volume_db": 0}]
        s["captions"]["words"] = [{"text": "Hi", "start": 0.1, "end": 0.4}]
        self.assertEqual(self.red(s), [])
    def test_cut_needs_a_why(self):
        s = sheet(self.root); s["picture"][0]["why"] = ""
        self.assertTrue(any("why" in r for r in self.red(s)))
    def test_overlay_in_safe_zone(self):
        s = sheet(self.root, overlays=[{"id": "h", "kind": "hook", "text": "x", "start": 0, "duration": 2, "y_pct": 90}])
        self.assertTrue(any("buttons cover" in r for r in self.red(s)))
    def test_loud_music(self):
        s = sheet(self.root, music={"src": "v.mp3", "start": 0, "volume_db": -4})
        self.assertTrue(any("fight the words" in r for r in self.red(s)))

class Pace(unittest.TestCase):
    def test_dead_air_is_cut_and_breath_is_kept(self):
        import run as R
        w = lambda t, s, e: {"text": t, "start": s, "end": e}
        segs = R.speech_segments([w("This,", 0.05, 0.39), w("the", 1.93, 2.05), w("old", 2.15, 2.31)], 0.4)
        self.assertEqual(len(segs), 2)
        self.assertLess(sum(b - a for a, b in segs), 1.2)   # 2.3 s of source, the 1.5 s hole gone
    def test_broll_is_placed_by_the_words_it_names(self):
        import run as R
        w = lambda t, s, e: {"text": t, "start": s, "end": e}
        words = [w("is", 3.0, 3.1), w("why", 3.1, 3.3), w("the", 3.3, 3.4), w("sunscreen", 3.4, 3.9), w("hasn't", 3.9, 4.2), w("worked.", 4.2, 4.6)]
        self.assertEqual(R.span_of({"from": "is why", "to": "worked"}, words), (3.0, 4.6))

class Lines(unittest.TestCase):
    def test_breaks_on_pause_full_line_and_full_stop(self):
        w = lambda t, s, e: {"text": t, "start": s, "end": e}
        lines = C.caption_lines([w("a", 0, .2), w("b", .2, .4), w("c", .4, .6), w("d", .6, .8), w("e.", 2, 2.2), w("f", 2.2, 2.4)], 3)
        self.assertEqual([[x["text"] for x in l] for l in lines], [["a", "b", "c"], ["d"], ["e."], ["f"]])

if __name__ == "__main__": unittest.main()
