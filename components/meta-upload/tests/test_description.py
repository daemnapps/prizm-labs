"""A card always carries a description: the words check fails with none, and the filer fills an empty one with the line
most of the brand's live cards carry (the same product's first), never a price, an offer or a dated line."""
import json, os, shutil, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "naming"))
import cards as C
import to_check as T

AD = "acme_widget_brief-0001_batch-2026-11-12-a"


def png(p, size=(540, 960)):
    from PIL import Image
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (200, 120, 40)).save(p)
    return p


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "meta"
        self.env = mock.patch.dict(os.environ, {"META_CARDS_ROOT": str(self.root), "NO_AD_WORDS": "1",
                                                "MADE_BY_TOOL_GATE_OFF": "all"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp)

    def live(self, name, product, descriptions):
        d = self.root / "acme" / "3-live" / "image" / name
        d.mkdir(parents=True)
        (d / "card.json").write_text(json.dumps({"brief_id": name, "product": product,
                                                 "words": {"descriptions": descriptions}}))

    def file(self, descriptions):
        return T.to_check("acme", "image", "flexible", [png(self.tmp / "src" / "a.png")],
                          {"primary": ["Body"], "headlines": ["H"], "descriptions": descriptions}, [], None,
                          ad_name=AD, product="widget", root=str(self.root))


class WordsCheck(Base):
    def test_a_card_with_no_description_fails_the_words_check(self):
        p = self.file([])
        got = C.checks(p["target"], C.load(p["target"]), online=False)["words"]
        self.assertFalse(got["ok"])
        self.assertIn("no description", got["why"])

    def test_a_card_with_a_description_passes_it(self):
        p = self.file(["Fits any desk"])
        self.assertTrue(C.checks(p["target"], C.load(p["target"]), online=False)["words"]["ok"])


class Fill(Base):
    def test_an_empty_description_takes_the_line_most_live_cards_of_the_product_carry(self):
        self.live("brief-0010", "widget", ["Fits any desk"])
        self.live("brief-0011", "widget", ["Fits any desk"])
        self.live("brief-0012", "widget", ["Built to last"])
        self.live("brief-0013", "gadget", ["Another product's line"])
        self.live("brief-0014", "gadget", ["Another product's line"])
        self.live("brief-0015", "gadget", ["Another product's line"])
        self.assertEqual(self.file([])["card"]["words"]["descriptions"], ["Fits any desk"])

    def test_a_price_an_offer_or_a_dated_line_is_never_the_fill(self):
        self.live("brief-0010", "widget", ["Save 20% today", "$19 this week", "Sale ends Friday"])
        self.assertEqual(self.file([])["card"]["words"]["descriptions"], [])
        self.live("brief-0011", "widget", ["Built to last"])
        os.rename(self.root / "acme" / "1-check", self.root / "acme" / "was-1-check")
        self.assertEqual(self.file([])["card"]["words"]["descriptions"], ["Built to last"])

    def test_a_description_passed_in_is_kept(self):
        self.live("brief-0010", "widget", ["Fits any desk"])
        self.assertEqual(self.file(["Mine"])["card"]["words"]["descriptions"], ["Mine"])

    def test_no_live_card_leaves_it_empty_for_the_check_to_name(self):
        self.assertEqual(self.file([])["card"]["words"]["descriptions"], [])


class Switch(Base):
    def test_shipped_on(self):
        c = json.loads((HERE / "description.json").read_text())
        self.assertEqual((c["on"], c["check"], c["fill"]), (True, True, True))
        self.assertTrue(T.description_on("check") and T.description_on("fill"))

    def test_check_off_a_card_with_no_description_passes_the_words_check(self):
        with mock.patch.dict(os.environ, {"META_DESCRIPTION_OFF": "check"}):
            p = self.file([])
            self.assertTrue(C.checks(p["target"], C.load(p["target"]), online=False)["words"]["ok"])

    def test_fill_off_an_empty_description_stays_empty(self):
        self.live("brief-0010", "widget", ["Fits any desk"])
        with mock.patch.dict(os.environ, {"META_DESCRIPTION_OFF": "fill"}):
            self.assertEqual(self.file([])["card"]["words"]["descriptions"], [])

    def test_all_off_in_the_file(self):
        self.live("brief-0010", "widget", ["Fits any desk"])
        f = self.tmp / "description.json"
        f.write_text(json.dumps({"on": False}))
        with mock.patch.object(T, "HERE", self.tmp):
            p = self.file([])
            self.assertEqual(p["card"]["words"]["descriptions"], [])
            self.assertTrue(C.checks(p["target"], C.load(p["target"]), online=False)["words"]["ok"])


if __name__ == "__main__":
    unittest.main()
