"""Caption lines never share a frame: a line is gone before the next one's lead-in, also when the words abut
(13 Nov: one frame showed two lines at once). No renders, no live runs."""
import re, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compose as C  # noqa: E402
from test_elements import elements_sheet  # noqa: E402


class NoOverlap(unittest.TestCase):
    def test_abutting_words_never_put_two_lines_on_screen(self):
        root = Path(tempfile.mkdtemp())
        s = elements_sheet(root)
        s["captions"]["look"] = "bold-highlight"
        t, words = 6.0, []
        for k, w in enumerate("ONE TWO THREE FOUR FIVE SIX SEVEN EIGHT NINE".split()):
            words.append({"text": w, "start": round(t, 3), "end": round(t + 0.3, 3)})
            t += 0.3                                 # each word starts the moment the last one ends
        s["captions"]["words"] = words
        page = C.compose(s, root, root / "proj").read_text()
        spans = [(float(a), float(a) + float(d)) for a, d in
                 re.findall(r'class="clip cap" data-start="([\d.]+)" data-duration="([\d.]+)"', page)]
        spans = [x for x in spans if x[0] >= 5.9]
        self.assertGreater(len(spans), 1)
        for (a0, b0), (a1, b1) in zip(spans, spans[1:]):
            self.assertLessEqual(round(b0, 3), round(a1, 3), "a caption line runs into the next one")


if __name__ == "__main__":
    unittest.main()
