"""natural_statics: words checked with no model, every layout drawn at story size. No network, nothing filed.

    python3 components/ad-variations/machine/test_natural_statics.py
"""
import json, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import natural_statics as NS  # noqa: E402

try:
    from PIL import Image
    DRAWS = all(Path(p).is_file() for p in (NS.BOLD, NS.HELV, NS.AVN))
except ImportError:
    DRAWS = False


def sprint(d, **ad):
    base = {"id": "a", "title": "T", "why": "the push", "receipt": "winner 1", "layout": "note", "lines": ["One title", "Two title", "Three title", "Four title", "Five title", "Six title"],
            "body": ["Words here.", "", "*THING starting at $49"]}
    base.update(ad)
    return {"brand": "b", "product": "p", "avatar": "x", "angle": "promo", "label": "l", "offer": "THING starting at $49", "never": ["closing"],
            "bubble": ["THING starting at $49"], "moment": "Black Friday", "until": "Nov 30", "wordmark": "B", "copy": {}, "ads": [base], "_dir": Path(d)}


class Check(unittest.TestCase):
    def one(self, **ad):
        with tempfile.TemporaryDirectory() as d:
            return " | ".join(NS.check(sprint(d, **ad)))

    def test_clean(self):
        self.assertEqual(self.one(), "")

    def test_banned_line(self):
        self.assertIn("banned line", self.one(lines=["We were closing", "Two"]))

    def test_other_price(self):
        self.assertIn("$46", self.one(lines=["Only $46", "Two"]))

    def test_long_dash(self):
        self.assertIn("long dash", self.one(lines=["One — two", "Two"]))

    def test_no_receipt_and_no_reason(self):
        got = self.one(receipt="", why="")
        self.assertIn("no receipt", got)
        self.assertIn("no reason", got)

    def test_same_version_twice(self):
        self.assertIn("same thing", self.one(lines=["One", "One"]))

    def test_always_six(self):
        self.assertIn("ships six", self.one(lines=["One", "Two", "Three", "Four"]))

    def test_comment_needs_a_source(self):
        self.assertIn("real one", self.one(layout="comments", comments=[{"text": "I love it"}]))

    def test_picture_must_exist(self):
        self.assertIn("picture not found", self.one(layout="story", photo="none.jpg"))

    def test_copy_counts_and_banned(self):
        with tempfile.TemporaryDirectory() as d:
            sp = sprint(d)
            sp["copy"] = {"primary": ["we are closing"], "headlines": ["H", "I"], "descriptions": ["D"]}
            got = " | ".join(NS.check_copy(sp))
            self.assertIn("need 2", got)
            self.assertIn("banned line", got)

    def test_the_designer_gets_five_exact_lines_and_the_first_picture(self):
        with tempfile.TemporaryDirectory(dir=str(NS.REPO / "runs")) as d:
            (Path(d) / "drafts").mkdir()
            (Path(d) / "drafts" / "a-control.png").write_bytes(b"x")
            sp = sprint(d)
            m = NS.manifest(sp, sp["ads"][0], "brief-0001")
            self.assertEqual(m["id"], "b_p_brief-0001")
            for i, t in enumerate(sp["ads"][0]["lines"][1:], 1):
                self.assertIn("| v%d | %s |" % (i, t), m["brief"])
            self.assertTrue(m["references"][0]["path"].endswith("a-control.png"))

    def test_an_ad_never_files_short(self):
        with tempfile.TemporaryDirectory() as d:
            sp = sprint(d)
            (Path(d) / "briefs.json").write_text('{"a": "brief-0001"}')
            sp["label"] = "no-such-round"
            self.assertIn("six", NS.file_cards(sp)[0][3])

    def test_a_thread_picture_must_exist(self):
        self.assertIn("picture not found", self.one(layout="thread", thread=[{"who": "me", "photo": "none.jpg"}]))

    def test_no_gate_is_turned_off(self):
        src = Path(NS.__file__).read_text()
        for off in ("LOWEST" + "_CPA_OFF", "GATE" + "_OFF", "owner" + "-exception", "keep" + "_words"):
            self.assertNotIn(off, src)


@unittest.skipUnless(DRAWS, "needs Pillow and the Mac's own fonts")
class Draw(unittest.TestCase):
    def test_every_layout(self):
        with tempfile.TemporaryDirectory() as d:
            Image.new("RGB", (900, 900), (120, 90, 60)).save(Path(d) / "sq.jpg")
            Image.new("RGB", (1080, 1920), (60, 90, 120)).save(Path(d) / "tall.jpg")
            for lay, ad in {"story": {"photo": "tall.jpg"}, "tag": {"photo": "sq.jpg"}, "letter": {"emoji": ["\U0001f5a4"]}, "note": {},
                            "comments": {"comments": [{"text": "I love mine", "likes": 4, "source": "ad 1"}]}, "plate": {"photo": "sq.jpg"},
                            "list": {"heading": "List", "after": ["x"], "picture": {"path": "sq.jpg"}}, "search": {"photo": "sq.jpg"},
                            "thread": {"contact": "Him", "thread": [{"who": "me", "text": "hi"}, {"who": "them", "text": "{line}"}, {"who": "me", "photo": "sq.jpg", "caption": ["c"]}]}}.items():
                sp = sprint(d, layout=lay, lines=["One line / two lines", "Version"], **ad)
                self.assertEqual(len(NS.draft(sp)), 1, lay)            # the first picture only
                got = NS.draft(sp, every=True)
                self.assertEqual(len(got), 2, lay)
                with Image.open(got[0]) as im:
                    self.assertEqual(im.size, (1080, 1920), lay)
            sp["copy"] = {"primary": ["P"], "headlines": ["H"], "descriptions": ["D"]}
            self.assertIn("Ad copy", NS.page(sp).read_text())


if __name__ == "__main__":
    unittest.main()
