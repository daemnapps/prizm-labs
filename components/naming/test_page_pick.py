"""page_pick.py — the landing page chosen at the brief, and the page part of a
Meta ad name. A fake catalog and funnel list for the pick; no network (the
fetch is handed in); nothing written outside a temp folder.

    python3 components/naming/test_page_pick.py
"""
import json, shutil, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import page_pick as PP  # noqa: E402

CAT = {"brands": {"acme": {"records": {
    "product_acme_body-scrub": {"type": "product", "old_names": ["scrub"],
                                "store_refs": [{"handle": "body-scrub"}]},
    "product_acme_face-scrub": {"type": "product", "old_names": []},
    "product_acme_glow-serum": {"type": "product", "old_names": ["SERUM™"],
                                           "store_refs": [{"handle": "serum"}]},
    "variant_acme_glow-serum_default": {"type": "variant", "product": "product_acme_glow-serum"},
    "variant_acme_war_default": {"type": "variant", "product": "product_acme_war"},
    "bundle_acme_set": {"type": "bundle", "label": "The Set", "components": [
        {"item": "variant_acme_glow-serum_default"}, {"item": "variant_acme_war_default"}]},
    "offer_acme_set": {"type": "offer", "label": "The Set", "item": "bundle_acme_set"},
    "offer_acme_body-scrub-3-pack": {"type": "offer", "label": "3 pack", "item": "product_acme_body-scrub"},
    "link_acme_cpk_quiz": {"type": "link", "status": "live", "label": "Quiz · 21 live ads",
                           "url": "https://recipe.acme.com/acme-scrub-cpk/quiz/"},
    "link_acme_cpk_landing": {"type": "link", "status": "live", "label": "Landing · 6 live ads",
                              "url": "https://recipe.acme.com/acme-scrub-cpk/landing.html",
                              "offers": ["offer_acme_body-scrub-3-pack"]},
    "link_acme_cpk_presell": {"type": "link", "status": "live", "label": "Presell · 5 live ads",
                              "url": "https://recipe.acme.com/acme-scrub-cpk/presell-five.html"},
    "link_acme_face_landing": {"type": "link", "status": "live", "label": "Face",
                               "url": "https://recipe.acme.com/acme-face-cpk/landing/"},
    "link_acme_store_quiz": {"type": "link", "status": "live", "label": "Store quiz",
                             "url": "https://acme.com/pages/method-quiz",
                             "surface_kind": "storefront-product-page"},
    "placement_acme_store_quiz_main": {"type": "placement", "url": "https://acme.com/pages/method-quiz",
                                       "offers": ["offer_acme_set"]},
    "link_acme_old_gone": {"type": "link", "status": "retired", "label": "old",
                           "url": "https://recipe.acme.com/acme-scrub-cpk/old.html"},
}}}}
FUNNELS = [
    {"id": "body-scrub-cpk", "product": "body-scrub", "url": "https://recipe.acme.com/acme-scrub-cpk/",
     "entry_page": "presell-five"},
    {"id": "face-scrub-cpk", "product": "face-scrub", "url": "https://recipe.acme.com/acme-face-cpk/"},
    {"id": "store", "product": None, "url": "https://acme.com/"},
]
OK = lambda url: 200


def pick(**kw):
    kw.setdefault("cat", CAT)
    kw.setdefault("fl", FUNNELS)
    kw.setdefault("fetch", OK)
    return PP.pick("acme", **kw)


class Types(unittest.TestCase):
    def test_swipe_urls(self):
        self.assertEqual(PP.type_of_url("https://mengotomars.com/pages/quiz-v6?x=1"), "quiz")
        self.assertEqual(PP.type_of_url("https://competitor-a.example/products/ccf2"), "store")
        self.assertEqual(PP.type_of_url("https://x.com/pages/10-reasons", "listicle"), "advertorial")
        self.assertEqual(PP.type_of_url("https://try.x.com/scrub/en/us/v2c/adv"), "advertorial")
        self.assertEqual(PP.type_of_url("https://x.com/landing.html"), "offer")
        self.assertIsNone(PP.type_of_url("https://x.com/pages/more-willpower-2"))

    def test_our_pages(self):
        recs = CAT["brands"]["acme"]["records"]
        self.assertEqual(PP.link_type(recs["link_acme_cpk_quiz"]), "quiz")
        self.assertEqual(PP.link_type(recs["link_acme_cpk_landing"]), "offer")
        self.assertEqual(PP.link_type(recs["link_acme_cpk_presell"]), "advertorial")


class Sells(unittest.TestCase):
    def test_product_names_resolve(self):
        self.assertEqual(PP.product_id("acme", "body-scrub", CAT), "product_acme_body-scrub")
        self.assertEqual(PP.product_id("acme", "serum", CAT), "product_acme_glow-serum")
        self.assertIsNone(PP.product_id("acme", "nothing", CAT))

    def test_funnel_offer_and_set(self):
        recs = CAT["brands"]["acme"]["records"]
        how, _ = PP.sells("acme", recs["link_acme_cpk_quiz"], "product_acme_body-scrub", CAT, FUNNELS)
        self.assertEqual(how, "direct")
        how, _ = PP.sells("acme", recs["link_acme_face_landing"], "product_acme_body-scrub", CAT, FUNNELS)
        self.assertIsNone(how)
        how, said = PP.sells("acme", recs["link_acme_store_quiz"], "product_acme_glow-serum", CAT, FUNNELS)
        self.assertEqual(how, "in-set")
        self.assertIn("The Set", said)


class Pick(unittest.TestCase):
    def test_no_swipe_page_takes_the_main_live_page(self):
        lp = pick(product="body-scrub", reg_rec={"product": "body-scrub"})
        self.assertEqual(lp["link_ids"], ["link_acme_cpk_quiz"])        # most live ads
        self.assertIn("no swipe landing page", lp["why"])
        self.assertIn("answers 200", lp["why"])

    def test_same_type_as_the_swipe_wins(self):
        rec = {"product": "body-scrub", "swipe": {"landing_page": "https://comp.com/pages/10-reasons-adv"}}
        lp = pick(reg_rec=rec)
        self.assertEqual(lp["link_ids"], ["link_acme_cpk_presell"])
        self.assertIn("advertorial", lp["why"])

    def test_a_store_swipe_falls_to_our_offer_page(self):
        rec = {"product": "body-scrub", "swipe": {"landing_page": "https://comp.com/products/thing"}}
        lp = pick(reg_rec=rec)
        self.assertEqual(lp["link_ids"], ["link_acme_cpk_landing"])
        self.assertIn("nearest kind", lp["why"])

    def test_offer_breaks_a_tie(self):
        rec = {"product": "body-scrub", "offer": "offer_acme_body-scrub-3-pack"}
        lp = pick(reg_rec=rec)
        self.assertEqual(lp["link_ids"], ["link_acme_cpk_landing"])
        self.assertIn("is on this page", lp["why"])

    def test_a_dead_page_is_skipped_and_named(self):
        lp = pick(reg_rec={"product": "body-scrub"},
                  fetch=lambda u: 404 if "quiz" in u else 200)
        self.assertEqual(lp["link_ids"], ["link_acme_cpk_landing"])
        self.assertIn("link_acme_cpk_quiz answered 404", lp["why"])
        self.assertEqual(lp["checked"]["link_acme_cpk_quiz"], 404)

    def test_sold_only_in_a_set_says_so(self):
        lp = pick(reg_rec={"product": "serum"})
        self.assertEqual(lp["link_ids"], ["link_acme_store_quiz"])
        self.assertIn("no live page sells serum on its own", lp["why"])

    def test_nothing_sells_it(self):
        lp = pick(reg_rec={"product": "face-scrub"}, fetch=lambda u: 500)
        self.assertEqual(lp["link_ids"], [])
        self.assertIn("failed its check", lp["why"])
        lp = pick(reg_rec={"product": "nothing"})
        self.assertEqual(lp["link_ids"], [])
        self.assertIn("not a acme product", lp["why"])


class SwipePage(unittest.TestCase):
    def test_reads_the_swipe_block(self):
        td = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(td, ignore_errors=True))
        (td / "comp/blocks").mkdir(parents=True)
        (td / "comp/blocks/06_x.md").write_text("# 06\n**Landing page:** `https://comp.com/pages/quiz-v6?t=1`  \n")
        (td / "comp/pages.json").write_text(json.dumps({"q": {"url": "https://comp.com/pages/quiz-v6", "type": "unknown"}}))
        (td / "comp/blocks.json").write_text(json.dumps({"blocks": [
            {"slug": "01_a", "ad_ids": [123456789], "landing_page": "https://comp.com/products/x"}]}))
        with mock.patch.object(PP, "SWIPES", td):
            sp = PP.swipe_page("acme", {"swipe": {"brand": "comp", "block_file": "06_x.md"}})
            self.assertEqual(sp["type"], "quiz")
            self.assertIn("comp/06_x.md", sp["from"])
            self.assertEqual(PP._block_page("comp", ad_id="123456789")[1], "store")


class MetaPage(unittest.TestCase):
    def test_funnel_id_and_page(self):
        self.assertEqual(PP.meta_page("link_acme_cpk_quiz", CAT, FUNNELS), "body-scrub-cpk-quiz")
        self.assertEqual(PP.meta_page("link_acme_cpk_landing", CAT, FUNNELS), "body-scrub-cpk-offer")
        self.assertEqual(PP.meta_page("link_acme_face_landing", CAT, FUNNELS), "face-scrub-cpk-offer")
        self.assertEqual(PP.meta_page("link_acme_cpk_presell", CAT, FUNNELS), "body-scrub-cpk-presell-five")
        self.assertIsNone(PP.meta_page("link_acme_unknown", CAT, FUNNELS))
        self.assertIsNone(PP.meta_page("not-a-link", CAT, FUNNELS))



class Record(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(self.td, ignore_errors=True))
        (self.td / "brands/acme/briefs").mkdir(parents=True)
        self.reg = self.td / "register.json"

    def _files(self, reg_links=None):
        head = {"brief": "brief-0005", "product": "body-scrub", "count": "brand+product"}
        (self.td / "brands/acme/briefs/briefs.json").write_text(json.dumps({"briefs": [head]}))
        rec = {"brand": "acme", "brief": "brief-0005", "product": "body-scrub"}
        if reg_links:
            rec["links"] = reg_links
        self.reg.write_text(json.dumps({"briefs": {"acme_body-scrub_brief-0005": rec}}))
        return head, rec

    def test_register_written_brand_file_untouched(self):
        head, rec = self._files()
        brand_file = self.td / "brands/acme/briefs/briefs.json"
        before = brand_file.read_bytes()
        lp = {"link_ids": ["link_acme_cpk_quiz"], "why": "w"}
        with mock.patch.object(PP, "brief_record", lambda *a: ("acme_body-scrub_brief-0005", rec, head)):
            got, where = PP.record("acme", "brief-0005", lp=lp, register=self.reg, root=self.td)
        reg = json.loads(self.reg.read_text())["briefs"]["acme_body-scrub_brief-0005"]
        self.assertEqual(reg["landing_page"]["link_ids"], ["link_acme_cpk_quiz"])
        self.assertEqual(reg["links"], ["link_acme_cpk_quiz"])         # the field the hand-off reads
        self.assertEqual(brand_file.read_bytes(), before)               # a machine never writes brands/, SI-97 (brand research proposals)
        self.assertEqual(len(where), 1)
        self.assertFalse((self.td / "runs/naming").exists())            # a register record needs no proposal

    def test_hand_chosen_links_are_kept(self):
        head, rec = self._files(reg_links=["link_acme_cpk_landing"])
        lp = {"link_ids": ["link_acme_cpk_quiz"], "why": "w"}
        with mock.patch.object(PP, "brief_record", lambda *a: ("acme_body-scrub_brief-0005", rec, head)):
            got, _ = PP.record("acme", "brief-0005", lp=lp, register=self.reg, root=self.td)
        self.assertEqual(got["link_ids"], ["link_acme_cpk_landing"])
        self.assertEqual(got["picker_would"], ["link_acme_cpk_quiz"])
        reg = json.loads(self.reg.read_text())["briefs"]["acme_body-scrub_brief-0005"]
        self.assertEqual(reg["links"], ["link_acme_cpk_landing"])

    def test_landing_ids_reads_the_record(self):
        with mock.patch.object(PP, "brief_record",
                               lambda *a: (None, None, {"landing_page": {"link_ids": ["link_acme_cpk_quiz"]}})):
            self.assertEqual(PP.landing_ids("acme", "brief-0005"), ["link_acme_cpk_quiz"])
        with mock.patch.object(PP, "brief_record", lambda *a: ("k", {"links": ["link_acme_x"]}, None)):
            self.assertEqual(PP.landing_ids("acme", "brief-0005"), ["link_acme_x"])
        self.assertEqual(PP.landing_ids("acme", "none"), [])


if __name__ == "__main__":
    unittest.main()
