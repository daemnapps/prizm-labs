"""Behaviour tests for the ask writer. A pretend workspace; no brand data is read."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "machine"))
import ask  # noqa: E402

_TMP = tempfile.TemporaryDirectory()
ROOT = Path(_TMP.name)
BANK = (
    "## widget — Widget\n\n- Funnel offer: **WIDGET starting at $5**. Same line on sale days.\n\n"
    "### big-sale — The sale\n\nLines creative may use, word for word: the `x` lines (\"Buy 2,\nget 1 free\" · "
    "\"Ends Sunday\"). The bare \"$1\" stays off.\n")


def _fixture():
    b = ROOT / "brands" / "brandx"
    (b / "products").mkdir(parents=True)
    (b / "strategy").mkdir()
    (b / "core-avatars" / "avatar-one").mkdir(parents=True)
    (b / "products" / "offer-bank.md").write_text(BANK)
    (b / "strategy" / "moments.json").write_text(json.dumps({"streams": {"fixed": [
        {"key": "big-sale", "window": "the first weekend of June"}]}}))


_fixture()


def args(**kw):
    base = {"brand": "brandx", "ask": "a1", "product": "widget", "avatar": "avatar-one", "said": "ads please",
            "funnel": "bottom"}
    base.update(kw)
    return base


class Build(unittest.TestCase):
    def test_offer_lines_come_from_the_banks_own_section(self):
        rec, notes = ask.build(ROOT, args(moment="big-sale", moment_line=["Ends Sunday"],
                                          window="2026-06-06 to 2026-06-07"))
        self.assertEqual(rec["offer"]["lines"], ["Buy 2, get 1 free", "Ends Sunday"])
        self.assertEqual(rec["offer"]["bank"], "brands/brandx/products/offer-bank.md#big-sale")
        self.assertEqual(rec["moment"], {"key": "big-sale", "window": "2026-06-06 to 2026-06-07",
                                         "lines": ["Ends Sunday"]})
        self.assertEqual(notes, [])

    def test_a_product_with_no_moment_uses_its_own_funnel_offer_line(self):
        rec, _ = ask.build(ROOT, args())
        self.assertEqual(rec["offer"]["lines"], ["WIDGET starting at $5"])
        self.assertNotIn("moment", rec)

    def test_an_unfindable_fact_is_reported_not_invented(self):
        rec, notes = ask.build(ROOT, args(avatar="nobody", offer_line=["Free ponies"]))
        self.assertEqual(rec["offer"]["lines"], ["Free ponies"])
        self.assertTrue(any("not word for word" in n for n in notes))
        self.assertTrue(any("avatar" in n for n in notes))

    def test_a_text_window_is_flagged(self):
        _, notes = ask.build(ROOT, args(moment="big-sale"))
        self.assertTrue(any("not a dated span" in n for n in notes))

    def test_refuses_unknown_product_and_moment(self):
        with self.assertRaises(SystemExit):
            ask.build(ROOT, args(product="nope"))
        with self.assertRaises(SystemExit):
            ask.build(ROOT, args(moment="nope"))


class Check(unittest.TestCase):
    def test_the_shape_the_readers_use(self):
        rec, _ = ask.build(ROOT, args())
        self.assertEqual(ask.check(rec), [])
        self.assertIn("missing funnel", ask.check({k: v for k, v in rec.items() if k != "funnel"}))
        self.assertTrue(ask.check(dict(rec, offer={"lines": "x", "never": []})))

    def test_the_evergreen_ask_needs_no_dated_moment(self):
        rec, _ = ask.build(ROOT, args(moment="evergreen"))
        self.assertEqual(rec["moment"], {"key": "evergreen", "window": "always on", "lines": []})
        self.assertEqual(ask.check(rec), [])

    def test_bad_count_and_maker_are_refused_in_words(self):
        for kw in ({"count": ["static_concepts=five"]}, {"count": ["nonsense"]}, {"maker": ["editor"]}):
            with self.assertRaises(SystemExit) as cm:
                ask.build(ROOT, args(**kw))
            self.assertIn("refused:", str(cm.exception))

    def test_count_makers_and_offer_section_are_written(self):
        rec, _ = ask.build(ROOT, args(count=["static_concepts=5"], maker=["statics=editor"], offer_section="big-sale",
                                      asked="2026-01-02"))
        self.assertEqual(rec["count"], {"static_concepts": 5})
        self.assertEqual(rec["makers"], {"statics": "editor"})
        self.assertEqual(rec["offer"]["bank"], "brands/brandx/products/offer-bank.md#big-sale")
        self.assertEqual(rec["asked"], "2026-01-02")

    def test_unknown_brand_is_refused(self):
        with self.assertRaises(SystemExit):
            ask.build(ROOT, args(brand="nobody"))

    def test_main_writes_once_and_refuses_to_overwrite(self):
        import os, io, contextlib
        prev = os.environ.get("AI_WORKSPACE")
        self.addCleanup(lambda: os.environ.__setitem__("AI_WORKSPACE", prev) if prev is not None
                        else os.environ.pop("AI_WORKSPACE", None))
        # the workspace is found by brandpath, which honours AI_WORKSPACE only for a real workspace shape
        (ROOT / "components").mkdir(exist_ok=True)
        os.environ["AI_WORKSPACE"] = str(ROOT)
        argv = ["new", "--brand", "brandx", "--ask", "a1", "--product", "widget", "--avatar", "avatar-one",
                "--said", "s", "--funnel", "f"]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ask.main(argv), 0)
        f = ROOT / "runs" / "creative-strategist" / "brandx" / "a1" / "ask.json"
        self.assertEqual(ask.check(json.loads(f.read_text())), [])
        with self.assertRaises(SystemExit):
            ask.main(argv)
        old = json.loads(f.read_text())
        old["gates"] = {"G1": "approved"}
        f.write_text(json.dumps(old))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ask.main(argv + ["--force"]), 0)
        self.assertEqual(json.loads(f.read_text())["gates"], {"G1": "approved"})

    def test_a_quoted_sentence_that_is_not_a_line_is_not_taken(self):
        txt = "## widget — W\n\nOn big-sale, he said \"we never run codes\" about something.\n"
        self.assertEqual(ask.bank_lines(txt, "widget", "big-sale"), [])


if __name__ == "__main__":
    unittest.main()
