"""names.py — the alias layer (Master Plan v2, 3.3). Both name forms parse to
one dict, writers emit the new form, one brief has two spellings and one
number. No network, no model, nothing written outside a temp folder.

    python3 components/naming/test_names.py
"""
import json, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import names as N  # noqa: E402

OLD_UNIT = ("acme-bodyscrub-static-ai-none-spotcover-darkspots-tonememory-"
            "handsapplication-photostrip-p140-9x16-260902a")
OLD_FILE = OLD_UNIT + "-a01"
NEW_UNIT = ("acme_glow-body-scrub_static_ai_none_spot-cover_dark-spots_"
            "tone-memory_hands-application_photo-strip_brief-0140_9x16_"
            "batch-2026-09-02-a")
NEW_FILE = NEW_UNIT + "_asset-01"


class Slug(unittest.TestCase):
    def test_hyphen_survives_inside_a_value(self):
        self.assertEqual(N.slug("Glow Body Scrub"), "glow-body-scrub")
        self.assertEqual(N.slug("spot-cover"), "spot-cover")
        self.assertEqual(N.slug("brief-0140"), "brief-0140")

    def test_joints_and_runs_collapse(self):
        self.assertEqual(N.slug("a__b  c--d"), "a-b-c-d")
        self.assertEqual(N.slug("-edge-"), "edge")
        self.assertEqual(N.slug("Hands & Application!"), "hands-application")


class BriefSpellings(unittest.TestCase):
    def test_one_number_two_spellings(self):
        self.assertEqual(N.brief_id("p140"), "brief-0140")
        self.assertEqual(N.brief_id("brief-0140"), "brief-0140")
        self.assertEqual(N.brief_id(140), "brief-0140")
        self.assertEqual(N.brief_id("140"), "brief-0140")
        self.assertEqual(N.brief_code("brief-0140"), "p140")
        self.assertEqual(N.brief_code("p140"), "p140")
        self.assertEqual(N.brief_code(7), "p007")

    def test_not_a_brief_stays_itself(self):
        self.assertEqual(N.brief_id("none"), "none")
        self.assertEqual(N.brief_code("none"), "none")
        self.assertIsNone(N.brief_id(None))
        self.assertFalse(N.is_brief_id("none"))
        self.assertTrue(N.is_brief_id("p001") and N.is_brief_id("brief-0001"))

    def test_forms_cover_both(self):
        self.assertEqual(N.brief_forms("p003"), {"p003", "brief-0003"})
        self.assertEqual(N.brief_forms("brief-0003"), {"p003", "brief-0003"})

    def test_alias_file_reads(self):
        a = N.brief_aliases()                       # your register's map; ships empty
        for k in ("aliases", "never_used", "brand_aliases"):
            self.assertIn(k, a)


class PerProductFixture(unittest.TestCase):
    """A temp workspace: brand `acme` with an old shared-count register
    (p001 no product, p005 balm, p006 cleanser) and three serum briefs
    numbered per product in its own briefs.json, one of them with a code."""

    def setUp(self):
        import delivery_rule as D
        self.D = D
        self.td = Path(tempfile.mkdtemp())
        (self.td / "brands" / "acme" / "briefs").mkdir(parents=True)
        (self.td / "components" / "image-teardown").mkdir(parents=True)
        serum = [{"brief": f"brief-000{n}", "product": "serum", "count": N.PER_PRODUCT,
                  "title": f"serum {n}", "aliases": ["ac-01"] if n == 1 else []} for n in (1, 2, 3)]
        old = [{"brief": "brief-0005", "product": "balm", "title": "old balm"}]
        (self.td / "brands/acme/briefs/briefs.json").write_text(json.dumps({"briefs": serum + old}))
        reg = {"briefs": {
            "p001": {"id": "p001", "brief": "brief-0001", "brand": "acme", "product": None},
            "p005": {"id": "p005", "brief": "brief-0005", "brand": "acme", "product": "balm"},
            "p006": {"id": "p006", "brief": "brief-0006", "brand": "acme", "product": "cleanser"}},
            "retired": {"p007": {"brand": "acme", "product": "cleanser"}}}
        self.reg_file = self.td / "components/image-teardown/briefs.json"
        self.reg_file.write_text(json.dumps(reg))
        saved = (N.WS, N._ALIASES, D.WS, D.REGISTER)
        N.WS, D.WS, D.REGISTER = self.td, self.td, self.reg_file
        N._ALIASES = {"aliases": {"p001": "brief-0001"}, "never_used": [],
                      "brand_aliases": {"acme": {"ac01": {"product": "serum", "brief": "brief-0001"}}}}

        def restore():
            N.WS, N._ALIASES, D.WS, D.REGISTER = saved
            import shutil; shutil.rmtree(self.td, ignore_errors=True)
        self.addCleanup(restore)

    def rows(self):
        return N.register_rows() + [{**b, "brand": "acme"} for b in N.brand_briefs("acme")]


class PerProduct(PerProductFixture):
    """the owner, 2026-10-01: "brief numbers count per brand AND product — each
    product starts at 1 inside its brand." Older briefs keep their numbers."""

    def test_next_number_per_brand_and_product(self):
        rows = self.rows()
        self.assertEqual(N.next_brief_number(rows, "acme", "serum"), 4)
        self.assertEqual(N.next_brief_number(rows, "acme", "balm"), 6)
        self.assertEqual(N.next_brief_number(rows, "acme", "cleanser"), 8)     # retired p007 stays taken
        self.assertEqual(N.next_brief_number(rows, "acme", "a-product-not-made-yet"), 1)
        self.assertEqual(N.next_brief_number(rows, "other", "serum"), 1)         # brands never share

    def test_old_briefs_with_no_product_do_not_block_a_product(self):
        rows = [{"brand": "x", "product": None, "brief": "brief-0007"},
                {"brand": "x", "product": "balm", "brief": "brief-0002"}]
        self.assertEqual(N.next_brief_number(rows, "x", "balm"), 3)
        self.assertEqual(N.next_brief_number(rows, "x", "serum"), 1)
        self.assertEqual(N.next_brief_number(rows, "x", None), 8)

    def test_a_per_product_key(self):
        k = N.brief_key("ACME", "Serum", "brief-0004")
        self.assertEqual(k, "acme_serum_brief-0004")
        self.assertEqual(N.parse_brief_key(k), ("acme", "serum", "brief-0004"))
        self.assertEqual((N.brief_id(k), N.brief_code(k), N.brief_number(k)), ("brief-0004", k, 4))
        self.assertTrue(N.is_brief_id(k))
        self.assertEqual(N.brief_key("acme", None, 3), "acme_none_brief-0003")

    def test_old_ids_unchanged(self):
        self.assertEqual(N.brief_id("p001"), "brief-0001")
        self.assertEqual(N.brief_code("brief-0001"), "p001")
        self.assertEqual(N.brief_header("acme", "brief-0005")["title"], "old balm")
        self.assertEqual(N.brief_header("acme", "p005")["title"], "old balm")
        self.assertEqual(N.brief_header("acme", "brief-0005", "bodyscrub")["title"], "old balm")  # old word, old brief

    def test_the_product_picks_between_briefs_sharing_a_number(self):
        self.assertEqual(N.brief_header("acme", "brief-0001", "serum")["title"], "serum 1")
        self.assertEqual(N.brief_header("acme", "acme_serum_brief-0002")["title"], "serum 2")
        self.assertIsNone(N.brief_header("acme", "brief-0001", "balm"))        # the old p001: no header

    def test_brand_and_number_alone_is_refused_when_shared(self):
        with self.assertRaises(N.AmbiguousBrief) as cm:
            N.brief_header("acme", "brief-0001")
        self.assertIn("brief-0001 is used by more than one ACME product", str(cm.exception))
        self.assertIn("say which", str(cm.exception))
        self.assertEqual(N.brief_header("acme", "brief-0002")["title"], "serum 2")  # not shared: fine

    def test_brand_codes_resolve_inside_their_brand_only(self):
        self.assertEqual(N.brand_alias("acme", "ac01"), ("serum", "brief-0001"))
        self.assertEqual(N.brief_header("acme", "ac01")["title"], "serum 1")
        self.assertEqual(N.brief_header("acme", "AC-01")["title"], "serum 1")    # the record's own alias
        self.assertEqual(N.brief_id("ac01"), "ac01")                             # never the old p001
        self.assertIsNone(N.brand_alias("other", "ac01"))


class DeliveryPerProduct(PerProductFixture):
    def m(self, name):
        return self.D.match_brief(name, self.D.load("acme")[0]["briefs"], "acme")

    def test_a_shared_bare_number_is_held_not_guessed(self):
        with self.assertRaises(N.AmbiguousBrief) as cm:
            self.m("brief-0001 from the editor")
        self.assertIn("ACME", str(cm.exception))

    def test_alias_product_or_old_code_decides(self):
        self.assertEqual((self.m("AC-01 delivery")["brief"], self.m("AC-01 delivery")["product"]), ("brief-0001", "serum"))
        self.assertEqual(self.m("brief-0002 serum")["product"], "serum")
        self.assertIsNone(self.m("p001")["product"])                   # pNNN is the old count's spelling
        self.assertEqual(self.m("p005")["product"], "balm")
        self.assertIsNone(self.m("brief-0004 serum"))                  # not issued yet: never the old p004


class BatchAndAsset(unittest.TestCase):
    def test_batch_both_spellings(self):
        self.assertEqual(N.norm_batch("260902a"), "batch-2026-09-02-a")
        self.assertEqual(N.norm_batch("batch-2026-09-02-a"), "batch-2026-09-02-a")
        self.assertEqual(N.batch_id(__import__("datetime").date(2026, 9, 2), "c"),
                         "batch-2026-09-02-c")

    def test_asset_both_spellings(self):
        self.assertEqual(N.norm_asset("a01"), "asset-01")
        self.assertEqual(N.norm_asset("asset-01"), "asset-01")
        self.assertEqual(N.asset_n("a07"), 7)
        self.assertEqual(N.asset_n("asset-07"), 7)
        self.assertIsNone(N.asset_n("9x16"))


class ParseAny(unittest.TestCase):
    def test_old_unit_and_file(self):
        u = N.parse_any(OLD_UNIT)
        self.assertEqual(u["form"], "old")
        self.assertEqual(u["brief"], "p140")
        self.assertEqual(u["brief_id"], "brief-0140")
        self.assertEqual(u["batch_id"], "batch-2026-09-02-a")
        self.assertIsNone(u["asset_n"])
        self.assertEqual(u["ad_name"], OLD_UNIT)
        f = N.parse_any(OLD_FILE)
        self.assertEqual((f["asset"], f["asset_n"], f["asset_id"]), ("a01", 1, "asset-01"))
        self.assertEqual(f["ad_name"], OLD_UNIT)

    def test_new_unit_and_file(self):
        u = N.parse_any(NEW_UNIT)
        self.assertEqual(u["form"], "new")
        self.assertEqual(u["product"], "glow-body-scrub")
        self.assertEqual(u["brief"], "brief-0140")
        self.assertEqual(u["brief_id"], "brief-0140")
        self.assertEqual(u["batch_id"], "batch-2026-09-02-a")
        f = N.parse_any(NEW_FILE)
        self.assertEqual((f["asset"], f["asset_n"], f["asset_id"]), ("asset-01", 1, "asset-01"))
        self.assertEqual(f["ad_name"], NEW_UNIT)

    def test_old_and_new_join_on_the_same_keys(self):
        o, n = N.parse_any(OLD_FILE), N.parse_any(NEW_FILE)
        for k in ("brief_id", "batch_id", "asset_id", "ratio", "brand"):
            self.assertEqual(o[k], n[k], k)

    def test_path_and_extension_are_stripped(self):
        self.assertEqual(N.parse_any(f"/x/y/{NEW_FILE}.png")["asset_n"], 1)
        self.assertEqual(N.parse_any(f"{OLD_FILE}.jpg")["asset_n"], 1)

    def test_not_ours(self):
        self.assertIsNone(N.parse_any(""))
        self.assertIsNone(N.parse_any(None))
        self.assertIsNone(N.parse_any("-".join(OLD_UNIT.split("-")[:-1])))     # 12 values
        self.assertIsNone(N.parse_any(OLD_FILE + "-x"))                         # 15
        self.assertIsNone(N.parse_any(NEW_UNIT.replace("brief-0140", "p140")))  # mixed
        self.assertIsNone(N.parse_any(NEW_FILE.replace("asset-01", "a01")))
        self.assertIsNone(N.parse_any("ai_bs_p133_h1-3_v4_Coco"))

    def test_parse_is_parse_any(self):
        self.assertEqual(N.parse(OLD_FILE), N.parse_any(OLD_FILE))

    def test_to_new_shows_the_old_name_in_the_new_joint(self):
        self.assertEqual(
            N.to_new(OLD_FILE),
            "acme_bodyscrub_static_ai_none_spotcover_darkspots_tonememory_"
            "handsapplication_photostrip_brief-0140_9x16_batch-2026-09-02-a_asset-01")
        self.assertEqual(N.parse_any(N.to_new(OLD_UNIT))["brief_id"], "brief-0140")


class Writers(unittest.TestCase):
    def test_ad_name_writes_the_new_form_from_old_spellings(self):
        ad = N.ad_name("Acme", "Glow Body Scrub", "static", "ai", "none",
                       "spot cover", "dark spots", "tone memory",
                       "hands application", "photo strip", "p140", "9x16", "260902a")
        self.assertEqual(ad, NEW_UNIT)
        self.assertEqual(N.asset_name(ad, 1), NEW_FILE)
        self.assertEqual(N.parse_any(N.asset_name(ad, 12))["asset_n"], 12)

    def test_ad_name_refuses_a_blank_or_a_bad_list_value(self):
        with self.assertRaises(SystemExit):
            N.ad_name("a", "b", "gif", "ai", "none", "c", "d", "e", "f", "g", "p1", "9x16", "260902a")
        with self.assertRaises(SystemExit):
            N.ad_name("a", "", "static", "ai", "none", "c", "d", "e", "f", "g", "p1", "9x16", "260902a")

    def test_no_brief_is_written_as_none(self):
        ad = N.ad_name("a", "b", "static", "ugc", "rose", "c", "d", "e", "f", "g",
                       "none", "4x5", "batch-2026-09-28-b")
        self.assertTrue(ad.endswith("_none_4x5_batch-2026-09-28-b"))
        self.assertEqual(N.parse_any(ad)["brief_id"], "none")


class BatchesUsed(unittest.TestCase):
    def test_both_spellings_count_as_taken(self):
        import datetime as dt
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "one").mkdir(); (root / "two").mkdir()
            (root / "one/manifest.json").write_text(json.dumps(
                {"batch": "260902a", "ads": [{"name": OLD_FILE}]}))
            (root / "two/manifest.json").write_text(json.dumps(
                {"batch": "batch-2026-09-02-b",
                 "ads": [{"name": NEW_FILE.replace("batch-2026-09-02-a", "batch-2026-09-02-c")}]}))
            used = N.batches_used(dt.date(2026, 9, 2), roots=[root])
        self.assertEqual(used, {"a", "b", "c"})


class RealRoots(unittest.TestCase):
    """5.4: the batch letter is picked off the REAL run roots. Every lane
    files under runs/<lane>/<brand>/, so runs/ itself heads the list — a lane
    added tomorrow is scanned without touching this file."""

    def test_runs_folder_heads_the_roots(self):
        self.assertEqual(N.RUNS[0], N.WS / "runs")

    def test_a_delivered_batch_under_runs_counts_as_taken(self):
        # a real delivered batch (runs/<lane>/<brand>/<yymmdd><letter>/...) is
        # found by the recursive scan; its letter is never handed out again
        days = set()
        for m in (N.WS / "runs").rglob("manifest.json"):
            try:
                b = N.norm_batch(json.loads(m.read_text()).get("batch"))
            except (ValueError, OSError, AttributeError):
                continue
            if b and N.BATCH_NEW.match(b):
                days.add(b)
        if not days:
            self.skipTest("no delivered batch under runs/ in this checkout")
        import datetime
        b = sorted(days)[0]                      # batch-YYYY-MM-DD-x
        day = datetime.date.fromisoformat(b[len("batch-"):-2])
        self.assertIn(b[-1], N.batches_used(day))


class FolderWas(unittest.TestCase):
    """2 Oct 2026: naming.json keeps the delivery folder's name from before the
    rule renamed it, so the work queue can match it back to its package."""

    def test_folder_was_kept(self):
        import delivery_rule as D
        td = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(td, ignore_errors=True))
        f = td / "AB-02 The Hen's Coat"
        f.mkdir()
        (f / "AB-02 v1.mp4").write_text("v")
        unit = "acme_serum_brief-0002_batch-2026-10-02-a"
        D.apply([(f, unit, [(f / "AB-02 v1.mp4", unit + "_asset-01.mp4")], "brief-0002")])
        nj = json.loads((td / unit / "naming.json").read_text())
        self.assertEqual((nj["folder_was"], nj["brief"]), ("AB-02 The Hen's Coat", "brief-0002"))
        # a later pass over the named folder keeps the first name
        (td / unit / "loose.mp4").write_text("v")
        D.apply([(td / unit, unit, [(td / unit / "loose.mp4", unit + "_asset-02.mp4")], "brief-0002")])
        nj = json.loads((td / unit / "naming.json").read_text())
        self.assertEqual(nj["folder_was"], "AB-02 The Hen's Coat")
        self.assertEqual(len(nj["files"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=1)
