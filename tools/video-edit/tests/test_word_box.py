"""The word box (the owner, 2026-10-10, the first song ad): a box behind the ONE word being sung or said,
moving word to word — until then only the whole caption line could sit on a box. And a song ad's
kit starts on that look. No renders, no downloads, no live runs."""
import json, re, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compose as C, cutsheet as CS, run as R  # noqa: E401
from test_elements import elements_sheet


class WordBox(unittest.TestCase):
    def page(self, look):
        root = Path(tempfile.mkdtemp()); s = elements_sheet(root)
        s["captions"]["look"] = look
        return C.compose(s, root, root / "proj").read_text(), s

    def test_each_word_gets_its_own_box_while_it_is_said(self):
        page, s = self.page("word-box")
        self.assertRegex(page, r'<span id="cap0w0" class="wb">')
        self.assertIn(".cap .wb{", page)
        w0 = s["captions"]["words"][0]
        self.assertIn(f'tl.set("#cap0w0",{{backgroundColor:"#8E3BD6"}},{round(w0["start"], 3)});', page)
        self.assertRegex(page, r'tl\.set\("#cap0w0",\{backgroundColor:"transparent"\},')
        # the line's own plate stays clear: only the word is boxed
        self.assertIn(".cap .plate{display:inline-block;padding:.18em .5em;border-radius:.2em;background:transparent}", page)

    def test_box_on_and_off_in_word_order_never_two_at_once(self):
        page, _ = self.page("word-box")
        sets = [(m.group(1), m.group(2), float(m.group(3))) for m in
                re.finditer(r'tl\.set\("#(cap0w\d+)",\{backgroundColor:"([^"]+)"\},([\d.]+)\)', page)]
        on = [t for w, c, t in sets if c != "transparent"]
        off = [t for w, c, t in sets if c == "transparent"]
        self.assertEqual(on, sorted(on))
        for a, b in zip(off, on[1:]):
            self.assertLessEqual(a, b, "a word's box goes off before the next one comes on")

    def test_a_whole_line_look_has_no_word_box(self):
        page, _ = self.page("bold-highlight")
        self.assertNotIn('class="wb"', page)
        self.assertNotIn("backgroundColor", page)

    def test_a_match_swipe_look_can_box_the_word(self):
        look = {"id": "match-swipe", "font": "montserrat", "weight": 900, "size_px": 70, "color": "#FFFFFF",
                "highlight": "#FFFFFF", "word_box": "#123456", "max_words": 3, "zone": "caption-band",
                "word_spacing": "normal", "letter_spacing": "0"}
        page, _ = self.page(look)
        self.assertIn('backgroundColor:"#123456"', page)

    def test_the_row_is_in_the_bank_and_green(self):
        rows = {r["id"]: r for r in json.loads((CS.TOOL / "looks/bank.json").read_text())["looks"]}
        self.assertIn("word-box", rows)
        self.assertEqual(rows["word-box"]["status"], "draft")
        self.assertEqual(CS.look_red(rows["word-box"], "word-box"), [])


class SongAdLook(unittest.TestCase):
    def test_a_song_ad_kit_starts_on_the_word_box(self):
        c = R.controls_for(None)
        self.assertEqual(R.format_look(c, {"format": "song-ad"}, {})["caption_look"]["value"], "word-box")

    def test_the_runs_own_controls_win(self):
        c = R.controls_for(None)
        self.assertEqual(R.format_look(c, {"format": "song-ad"}, {"caption_look": {"value": "one-word"}})["caption_look"]["value"],
                         c["caption_look"]["value"])

    def test_other_formats_keep_the_default(self):
        c = R.controls_for(None)
        self.assertEqual(R.format_look(c, {"format": "micro-drama"}, {})["caption_look"]["value"], "bold-highlight")


if __name__ == "__main__":
    unittest.main()
