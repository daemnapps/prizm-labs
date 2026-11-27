"""page_list.py — the one page list: IDs, steps, versions, tests, the backfill and the daily check; and the page
brief the brief register opens at the start of a page chain run. A fake brand (funnel list, catalog, store
sitemap) in a temp folder; no network (every fetch is handed in); the real lists are only read.

    python3 components/naming/test_page_list.py
"""
import json, shutil, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import page_list as PL  # noqa: E402
import page_pick as PP  # noqa: E402

CAT = {"brands": {"acme": {"records": {
    "link_acme_cpk_quiz": {"type": "link", "status": "live", "url": "https://recipe.acme.com/acme-scrub-cpk/quiz/"},
    "link_acme_cpk_landing": {"type": "link", "status": "live",
                              "url": "https://recipe.acme.com/acme-scrub-cpk/landing.html"},
    "link_acme_sub_portal": {"type": "link", "status": "live",
                             "url": "https://recipe.acme.com/acme-scrub-sub/portal-yai/"},
    "link_acme_sub2_portal": {"type": "link", "status": "live",
                              "url": "https://recipe.acme.com/acme-scrub-sub/portal-yai/"},
    "link_acme_cpk_portal-off": {"type": "link", "status": "off",
                                 "url": "https://recipe.acme.com/acme-scrub-cpk/portal-old/"},
}}}}
FUNNELS = {"funnels": [
    {"id": "body-scrub-cpk", "product": "body-scrub", "status": "in use", "code_slug": "acme-scrub-cpk",
     "url": "https://recipe.acme.com/acme-scrub-cpk/", "pages": ["checkout", "landing", "oto-up-cream", "quiz",
                                                                "receipt", "oto-up-cream copy"]},
    {"id": "body-scrub-sub", "product": "body-scrub", "status": "in use", "code_slug": "acme-scrub-sub",
     "url": "https://recipe.acme.com/acme-scrub-sub/", "pages": []},
    {"id": "old", "product": "body-scrub", "status": "off (retired)", "url": "https://recipe.acme.com/acme-scrub-cpk/"},
    {"id": "store", "product": None, "status": "in use", "url": "https://acme.com/"},
]}
SITEMAP = {
    "https://acme.com/sitemap.xml": "<sitemapindex><sitemap><loc>https://acme.com/sm_products.xml</loc></sitemap>"
                                    "<sitemap><loc>https://acme.com/en-fr/sm_products.xml</loc></sitemap>"
                                    "<sitemap><loc>https://acme.com/sm_pages.xml</loc></sitemap></sitemapindex>",
    "https://acme.com/sm_products.xml": "<urlset><url><loc>https://acme.com/</loc></url>"
                                        "<url><loc>https://acme.com/products/war</loc></url></urlset>",
    "https://acme.com/en-fr/sm_products.xml": "<urlset><url><loc>https://acme.com/en-fr/products/war</loc></url></urlset>",
    "https://acme.com/sm_pages.xml": "<urlset><url><loc>https://acme.com/pages/method-quiz</loc></url>"
                                     "<url><loc>https://acme.com/blogs/learn/bumps-guide</loc></url></urlset>",
}


class Fake(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(self.td, ignore_errors=True))
        f = self.td / "brands/acme/web/funnels/funnels.json"
        f.parent.mkdir(parents=True)
        f.write_text(json.dumps(FUNNELS))
        self.list = self.td / "pages.json"
        self.list.write_text(json.dumps({"places": {}, "pages": {}}))
        self.fetched = []

    def fetch(self, url):
        self.fetched.append(url)
        return (404, url) if "gone" in url or "copy" in url else (200, url)

    def fill(self):
        data, rep = PL.backfill("acme", data=PL.load(self.list), root=self.td, cat=CAT, fetch=self.fetch,
                                fetch_text=lambda u: SITEMAP.get(u, ""), today="2026-11-14")
        PL.save(data, self.list)
        return data, rep


class Ids(unittest.TestCase):
    def test_grammar(self):
        self.assertTrue(PL.is_page_id("acme_body-scrub-cpk_quiz"))
        for bad in ("acme_quiz", "acme_body_scrub_quiz", "Acme_x_y", "acme__quiz", "acme_x_quiz_v2"):
            self.assertFalse(PL.is_page_id(bad), bad)
        self.assertEqual(PL.parse_page_id("acme_store_product-war"),
                         {"brand": "acme", "place": "store", "page": "product-war"})
        self.assertEqual(PL.long_name("acme_store_home", "v7"), "acme_store_home_v7")
        self.assertEqual(PL.run_label("acme_body-scrub-cpk_quiz", "v3"), "body-scrub-cpk_quiz_v3")
        with self.assertRaises(ValueError):
            PL.long_name("acme_store_home", "test-a")

    def test_page_part_and_step(self):
        self.assertEqual(PL.page_part("/products/war", store=True), ("product-war", "product"))
        self.assertEqual(PL.page_part("/catalogue/body-scrub_69/", store=True), ("product-body-scrub", "product"))
        self.assertEqual(PL.page_part("/catalogue/category/skincare_1/", store=True),
                         ("collection-skincare", "collection"))
        self.assertEqual(PL.page_part("/en/about-us/", store=True), ("page-about-us", "page"))
        self.assertEqual(PL.page_part("/blogs/learn/bumps", store=True), ("article-bumps", "article"))
        self.assertEqual(PL.page_part("/", store=True), ("home", "home"))
        self.assertEqual(PL.page_part("quiz/results/"), ("quiz-results", None))
        self.assertEqual(PL.page_part("landing.html"), ("landing", None))
        for page, step in (("presell-five", "landing"), ("quiz-dry", "landing"), ("landing-clean", "landing"),
                           ("checkout-dry", "checkout"), ("oto-dw-cream", "post-purchase"),
                           ("oto-up-cream", "post-purchase"), ("thank-you", "post-purchase"),
                           ("receipt", "post-purchase"), ("cart", "cart")):
            self.assertEqual(PL.step_of(PL.kind_of(page)), step, page)


class Backfill(Fake):
    def test_every_live_address_gets_one_id(self):
        data, rep = self.fill()
        pages = data["pages"]
        for pid in ("acme_body-scrub-cpk_quiz", "acme_body-scrub-cpk_landing", "acme_body-scrub-cpk_checkout",
                    "acme_body-scrub-cpk_receipt", "acme_body-scrub-sub_portal-yai", "acme_store_home",
                    "acme_store_product-war", "acme_store_page-method-quiz", "acme_store_article-bumps-guide",
                    "acme_store_cart"):
            self.assertIn(pid, pages)
        self.assertNotIn("acme_body-scrub-cpk_oto-up-cream-copy", pages)            # a stray copy is never a page
        self.assertFalse(any("en-fr" in e["url"] for e in pages.values()))         # market copies skipped
        self.assertEqual(pages["acme_body-scrub-cpk_checkout"]["step"], "checkout")
        self.assertEqual(pages["acme_body-scrub-cpk_quiz"]["meta"], "body-scrub-cpk-quiz")
        self.assertEqual(pages["acme_body-scrub-cpk_landing"]["meta"], "body-scrub-cpk-offer")   # frozen from ads

    def test_two_old_ids_one_page_and_off_kept(self):
        data, _ = self.fill()
        e = data["pages"]["acme_body-scrub-sub_portal-yai"]
        self.assertEqual(sorted(e["old_ids"]), ["link_acme_sub2_portal", "link_acme_sub_portal"])
        self.assertEqual(data["pages"]["acme_body-scrub-cpk_portal-old"]["state"], "off")

    def test_live_place_wins_over_an_off_one(self):
        places = PL.places_for("acme", {"places": {}}, root=self.td)
        self.assertEqual(PL.place_of("acme", "https://recipe.acme.com/acme-scrub-cpk/quiz/", places)[0],
                         "body-scrub-cpk")

    def test_sitemap_pages_are_not_fetched_and_ids_never_re_pointed(self):
        data, _ = self.fill()
        self.assertFalse(any("acme.com/products" in u for u in self.fetched))
        before = json.loads(self.list.read_text())
        data, rep = self.fill()
        self.assertEqual(rep["added"], [])
        self.assertEqual(data["pages"].keys(), before["pages"].keys())

    def test_one_control_version_each(self):
        data, _ = self.fill()
        for pid, e in data["pages"].items():
            if e["state"] == "live":
                self.assertEqual([v["version"] for v in e["versions"] if v["control"]], ["v1"], pid)


class Versions(Fake):
    def test_reserve_build_control(self):
        self.fill()
        pid = "acme_body-scrub-cpk_quiz"
        v = PL.reserve_version(pid, "acme_body-scrub_brief-0009", "variant", path=self.list)
        self.assertEqual(v, "v2")
        self.assertEqual(PL.reserve_version(pid, "acme_body-scrub_brief-0009", "variant", path=self.list), "v2")
        self.assertEqual(PL.reserve_version(pid, "acme_body-scrub_brief-0010", "variant", path=self.list), "v3")
        PL.file_build(pid, "v2", "runs/page-chain/acme/body-scrub-cpk_quiz_v2", path=self.list, today=None)
        e = PL.find(pid, PL.load(self.list))[1]
        self.assertTrue(e["versions"][1]["built"])
        PL.set_control(pid, "v2", path=self.list)
        e = PL.find(pid, PL.load(self.list))[1]
        self.assertEqual(PL.control(e)["version"], "v2")
        self.assertEqual(PL.next_version(e), "v4")                       # never reused
        with self.assertRaises(KeyError):
            PL.reserve_version("acme_store_nope", "b", "variant", path=self.list)
        with self.assertRaises(ValueError):
            PL.reserve_version(pid, "b", "challenger", path=self.list)

    def test_new_page_is_planned_until_its_control(self):
        self.fill()
        pid = "acme_body-scrub-cpk_advertorial-pigmentmemory"
        self.assertEqual(PL.reserve_version(pid, "b1", "new-page", path=self.list), "v1")
        e = PL.load(self.list)["pages"][pid]
        self.assertEqual((e["state"], e["step"]), ("planned", "landing"))
        PL.set_control(pid, "v1", path=self.list)
        self.assertEqual(PL.load(self.list)["pages"][pid]["state"], "live")


class Tests(Fake):
    def test_rules_and_result(self):
        self.fill()
        pid = "acme_body-scrub-cpk_landing"
        PL.reserve_version(pid, "b1", "variant", path=self.list)
        data = PL.load(self.list)
        t = PL.add_test(pid, {"type": "design", "control": {"version": "v1", "offer": "1"},
                              "variant": {"version": "v2", "offer": "2"}}, data=data)
        e = data["pages"][pid]
        bad = PL.test_problems(e, t)
        self.assertIn("a design test keeps the same offer in both groups", bad)
        self.assertIn("hypothesis is written before the test starts", bad)
        self.assertIn("the stop point is set before the test starts", bad)
        self.assertIn("no dated approval", bad)
        self.assertEqual((t["primary_metric"], t["confirm_metric"], t["state"]),
                         ("checkout_reached", "purchase", "draft"))
        with self.assertRaises(ValueError):
            PL.add_test(pid, {"type": "design"}, data=data)                # one test per page at a time
        t.update(hypothesis="h", stop={"min_days": 7}, variant={"version": "v2", "offer": "1"},
                 gate={"compliance": "pass", "compliance_run": "r1", "approved_by": "owner", "approved_on": "2026-11-14"})
        self.assertEqual(PL.test_problems(e, t), [])
        with self.assertRaises(ValueError):
            PL.end_test(pid, "winner", data=data)
        PL.end_test(pid, "variant wins", data=data)
        self.assertEqual(PL.control(e)["version"], "v2")
        self.assertEqual(e["tests"][0]["result"], "variant wins")


class Check(Fake):
    def test_flags_a_live_page_with_no_id_and_a_dead_one(self):
        self.fill()
        data = PL.load(self.list)
        del data["pages"]["acme_body-scrub-cpk_receipt"]
        data["pages"]["acme_body-scrub-cpk_quiz"]["url"] = "https://recipe.acme.com/acme-scrub-cpk/gone/"
        r = PL.check("acme", data=data, root=self.td, cat=CAT, fetch=self.fetch,
                     fetch_text=lambda u: SITEMAP.get(u, ""), today="2026-11-14")
        self.assertEqual([m["would_be"] for m in r["missing"]], ["acme_body-scrub-cpk_receipt"])
        self.assertEqual([d["page"] for d in r["dead"]], ["acme_body-scrub-cpk_quiz"])
        d = PL.write_check(r, root=self.td)
        self.assertTrue((d / "check.md").is_file())


class PageBrief(Fake):
    """The brief register opens a page brief at the START of a run; it never carries a landing page."""
    def setUp(self):
        super().setUp()
        sys.path.insert(0, str(HERE.parent / "image-teardown" / "tools"))
        import briefs as B
        self.B = B
        self._real = B.REGISTER
        B.REGISTER = self.td / "briefs.json"
        B.REGISTER.write_text(json.dumps({"briefs": {}, "retired": {}}))
        self.addCleanup(lambda: setattr(B, "REGISTER", self._real))
        self.fill()

    def test_opens_numbered_with_its_version(self):
        B = self.B
        bid, rec = B.open_page_brief("acme", "acme_body-scrub-cpk_quiz", "variant", product="body-scrub",
                                     run="runs/page-chain/acme/body-scrub-cpk_quiz_v2", pages_file=self.list)
        self.assertEqual((rec["type"], rec["job"], rec["version"], rec["page"]),
                         ("page", "variant", "v2", "acme_body-scrub-cpk_quiz"))
        self.assertNotIn("landing_page", rec)
        self.assertNotIn("links", rec)
        self.assertTrue(bid.endswith(rec["brief"]))
        v = PL.find("acme_body-scrub-cpk_quiz", PL.load(self.list))[1]["versions"][-1]
        self.assertEqual((v["version"], v["brief"], v["job"]), ("v2", bid, "variant"))
        again = B.open_page_brief("acme", "acme_body-scrub-cpk_quiz", "variant", product="body-scrub",
                                  run="runs/page-chain/acme/body-scrub-cpk_quiz_v2", pages_file=self.list)
        self.assertEqual(again[0], bid)                                    # one run, one brief
        reg = B.load()
        with self.assertRaises(SystemExit):
            B.set_links(reg, bid, ["link_acme_cpk_quiz"])                 # a page brief has no landing page
        rec2, lp = B.with_landing(bid, "acme", "body-scrub")
        self.assertIsNone(lp)

    def test_refuses_what_is_not_a_page_job(self):
        B = self.B
        for page, job in (("acme_body-scrub-cpk_quiz", "challenger"), ("acme quiz", "variant"),
                          ("other_store_home", "variant"), ("acme_store_nope", "variant")):
            with self.assertRaises(SystemExit):
                B.open_page_brief("acme", page, job, product="body-scrub", pages_file=self.list)


class Hypothesis(PageBrief):
    """The testing loop's hand-off: a hypothesis record becomes a variant page brief and a drafted test."""
    def write(self, **over):
        h = {"id": "acme_quiz_hyp-20261114-1", "kind": "hypothesis", "page_id": "acme_body-scrub-cpk_quiz", "type": "design",
             "control": {"version": "v1", "path": "/acme-scrub-cpk/quiz/", "offer": "1"}, "variant_offer": "1",
             "hypothesis": "Move the price above the fold -> more reach checkout, because 19 of 30 never scrolled to it",
             "change": "price block above the fold", "primary_metric": "checkout_reached", "confirm_metric": "purchase",
             "stop": {"min_days": 7}, "evidence": {"recordings": {"left": 30, "converted": 10}}, "status": "draft"}
        h.update(over)
        f = self.td / "hypothesis.json"
        f.write_text(json.dumps(h))
        return f

    def test_hypothesis_opens_a_variant_brief_and_drafts_the_test(self):
        B = self.B
        f = self.write()
        bid, rec = B.open_page_brief_from_hypothesis(f, pages_file=self.list)
        self.assertEqual((rec["job"], rec["version"], rec["page"]), ("variant", "v2", "acme_body-scrub-cpk_quiz"))
        self.assertEqual(rec["hypothesis"]["change"], "price block above the fold")
        self.assertEqual(rec["hypothesis"]["id"], "acme_quiz_hyp-20261114-1")
        e = PL.load(self.list)["pages"]["acme_body-scrub-cpk_quiz"]
        t = e["tests"][0]
        self.assertEqual((t["state"], t["control"]["version"], t["variant"]["version"], t["type"]),
                         ("draft", "v1", "v2", "design"))
        self.assertEqual(t["hypothesis"], json.loads(f.read_text())["hypothesis"])
        self.assertEqual(t["hypothesis_id"], "acme_quiz_hyp-20261114-1")
        self.assertEqual(B.open_page_brief_from_hypothesis(f, pages_file=self.list)[0], bid)   # one hypothesis, one brief
        PL.file_build("acme_body-scrub-cpk_quiz", "v2", "runs/page-chain/acme/body-scrub-cpk_quiz_v2", path=self.list)
        t = PL.load(self.list)["pages"]["acme_body-scrub-cpk_quiz"]["tests"][0]
        self.assertTrue(t["variant"]["path"].endswith("/quiz/v2/"))
        self.assertIn("compliance check has not passed", PL.test_problems(e, t))     # the gate stays shut

    def test_a_bad_or_stale_hypothesis_opens_nothing(self):
        B = self.B
        for over in ({"change": ""}, {"type": "design", "variant_offer": "2"}, {"page_id": "acme quiz"},
                     {"control": {"version": "v9", "offer": "1"}}, {"status": "live"}):
            with self.assertRaises(SystemExit, msg=str(over)):
                B.open_page_brief_from_hypothesis(self.write(**over), pages_file=self.list)
        self.assertEqual(B.load()["briefs"], {})


class Archived(Fake):
    def test_archived_page_is_kept_but_not_used(self):
        self.fill()
        data = PL.load(self.list)
        pid = "acme_store_page-method-quiz"
        data["pages"][pid]["state"] = "archived"
        PL.save(data, self.list)
        data = PL.load(self.list)
        self.assertFalse(PL.usable(pid, data))
        self.assertFalse(PL.usable("https://acme.com/pages/method-quiz", data))
        self.assertTrue(PL.usable("acme_body-scrub-cpk_quiz", data))
        self.assertEqual(PL.find(pid, data)[0], pid)                        # still on the list
        with self.assertRaises(ValueError):
            PL.reserve_version(pid, "b1", "variant", path=self.list)          # no new version for it
        r = PL.check("acme", data=data, root=self.td, cat=CAT, fetch=self.fetch,
                     fetch_text=lambda u: SITEMAP.get(u, ""), today="2026-11-14")
        self.assertEqual(r["missing"], [])                                    # the daily check does not flag it


class Fixes(PageBrief):
    """Team fixes: a fix list opens a new-control brief; the built version takes the control mark only through the gate."""
    def write(self, **over):
        f = {"id": "acme-quiz-20261114", "kind": "fix-list", "page_id": "acme_body-scrub-cpk_quiz",
             "control": {"version": "v1", "path": "/acme-scrub-cpk/quiz/"}, "state": "ready",
             "fixes": [{"id": "f1", "where": {"section_job": "offer", "section": "§2 offer"},
                        "what": "button above the fold", "type": "design", "value_usd_month": 900}], "status": "draft"}
        f.update(over)
        p = self.td / "fixes.json"
        p.write_text(json.dumps(f))
        return p

    def test_fix_list_to_new_control_through_the_gate(self):
        B = self.B
        bid, rec = B.open_page_brief_from_fixes(self.write(), pages_file=self.list)
        self.assertEqual((rec["job"], rec["version"]), ("new-control", "v2"))
        self.assertEqual(rec["fixes"]["fixes"][0]["fix"], "button above the fold")
        data = PL.load(self.list)
        pid = "acme_body-scrub-cpk_quiz"
        with self.assertRaises(ValueError):                                   # not built yet
            PL.approve_version(pid, "v2", "approver", compliance_run="c1", data=data)
        PL.file_build(pid, "v2", "runs/page-chain/acme/body-scrub-cpk_quiz_v2", data=data)
        data["approvers"] = {"new-control": ["owner"], "variant": ["owner"]}
        with self.assertRaises(ValueError):
            PL.approve_version(pid, "v2", "someone-else", compliance_run="c1", data=data)   # only the named approver
        PL.approve_version(pid, "v2", "owner", compliance_run="c1", data=data, today="2026-11-14")
        self.assertEqual(PL.control(data["pages"][pid])["version"], "v2")

    def test_refused_while_a_test_is_open_or_the_control_moved(self):
        B = self.B
        data = PL.load(self.list)
        PL.reserve_version("acme_body-scrub-cpk_quiz", "b0", "variant", data=data)
        PL.add_test("acme_body-scrub-cpk_quiz", {"type": "design", "control": {"version": "v1"},
                                                  "variant": {"version": "v2"}}, data=data)
        PL.save(data, self.list)
        with self.assertRaises(SystemExit):
            B.open_page_brief_from_fixes(self.write(), pages_file=self.list)
        with self.assertRaises(SystemExit):
            B.open_page_brief_from_fixes(self.write(control={"version": "v9"}), pages_file=self.list)

    def test_page_context(self):
        pid = "acme_body-scrub-cpk_quiz"
        run = self.td / "runs/page-chain/acme/body-scrub-cpk_quiz_v2"
        run.mkdir(parents=True)
        (run / "structure.json").write_text(json.dumps({"sections": [{"job": "hook", "move": "m", "form": "f"}]}))
        data = PL.load(self.list)
        PL.reserve_version(pid, "b1", "new-control", data=data)
        PL.file_build(pid, "v2", "runs/page-chain/acme/body-scrub-cpk_quiz_v2", data=data)
        PL.set_control(pid, "v2", data=data)
        ctx = PL.page_context(pid, data=data, root=self.td)
        self.assertEqual(ctx["control"]["version"], "v2")
        self.assertEqual(ctx["sections"], [{"job": "hook", "move": "m", "form": "f"}])
        self.assertNotIn("page_json", ctx)
        (run / "page.json").write_text("{}")
        self.assertEqual(PL.page_context(pid, data=data, root=self.td)["page_json"],
                         "runs/page-chain/acme/body-scrub-cpk_quiz_v2/page.json")
        self.assertIsNone(PL.page_context("acme_body-scrub-cpk_checkout", data=data, root=self.td)["sections"])


class AdBriefs(Fake):
    def test_page_ids_from_link_ids(self):
        self.fill()
        data = PL.load(self.list)
        self.assertEqual(PP.page_ids_of(["link_acme_cpk_landing", "link_acme_sub2_portal", "link_nope"], data),
                         ["acme_body-scrub-cpk_landing", "acme_body-scrub-sub_portal-yai"])
        self.assertEqual(PL.meta("link_acme_cpk_landing", data), "body-scrub-cpk-offer")


class Real(unittest.TestCase):
    """The real list, read only."""
    def test_real_list_is_clean(self):
        data = PL.load()
        self.assertGreater(len(data["pages"]), 0)
        for pid, e in data["pages"].items():
            self.assertTrue(PL.is_page_id(pid), pid)
            self.assertEqual(pid, f"{e['brand']}_{e['place']}_{e['page']}")
            self.assertIn(e["status"], ("draft", "approved", "deprecated"))
            self.assertIn(e["state"], PL.PAGE_STATES)
            if e["state"] == "live":
                self.assertIn(e["step"], PL.STEPS, pid)
                self.assertEqual(len([v for v in e["versions"] if v.get("control")]), 1, pid)
            for t in e.get("tests") or []:
                self.assertIn(t["state"], PL.TEST_STATES)
                self.assertNotIn("status", t)

    def test_meta_names_of_live_ads_unchanged(self):
        """The Meta piece read through the page list equals what live ad names already say."""
        data = PL.load()
        for pid, e in data["pages"].items():
            for link in e.get("old_ids") or []:
                if not link.startswith("link_"):
                    continue
                old = PP.meta_page(link, cat=PP.catalog())
                if old:
                    self.assertEqual(PP.meta_page(link), old, link)
                    self.assertEqual(PP.meta_page(pid), old, pid)


if __name__ == "__main__":
    unittest.main()
