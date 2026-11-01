#!/usr/bin/env python3
"""handoff.py — offline tests. Run: python3 components/handoff-standard/skill/tests/test_handoff.py

No network, no Drive, no key. The brand and the brief come from the brief
register (the first brief whose brief file is on disk), never from a literal
here; the catalog is a fixture written in the shape the catalog tool emits
(one record per id), plus one in the survey shape (catalog.json)."""
import json, shutil, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import handoff as H  # noqa: E402


def pick_brief():
    """The first register brief with a brief file on disk: (brief id, brand, product)."""
    reg = H.BR.load()
    for key, rec in reg["briefs"].items():
        brand = rec.get("brand")
        if not brand or not rec.get("run"):
            continue
        rec = dict(rec, id=key)
        if H.brief_file(rec, brand):
            return H.N.brief_id(key), brand, rec.get("product") or (rec.get("declares") or {}).get("product")
    return None, None, None


BID, BRAND, PRODUCT = pick_brief()


def registered_links(brand):
    """Every landing page the register records on this brand's briefs."""
    out = []
    for rec in dict.values(H.BR.load()["briefs"]):
        if rec.get("brand") == brand:
            out += [x if isinstance(x, str) else x.get("id") for x in rec.get("links") or []]
    return sorted(set(filter(None, out)))


def fixture_catalog(root, brand, product, extra=None):
    """Shape B: one JSON per record, as offer-system-design.md §C lays them out."""
    recs = [
        {"id": f"product_{brand}_{H.N.slug(product)}", "type": "product", "brand": brand, "status": "on-sale",
         "label": product, "old_names": [product.replace("-", "")]},
        {"id": f"product_{brand}_gone", "type": "product", "brand": brand, "status": "retired"},
        {"id": f"offer_{brand}_test-offer", "type": "offer", "brand": brand, "status": "live", "price": "$1"},
        {"id": f"offer_{brand}_old-offer", "type": "offer", "brand": brand, "status": "not-live"},
        {"id": f"link_{brand}_test-page", "type": "link", "brand": brand, "status": "live",
         "url": "https://example.test/page/"},
        {"id": f"guarantee_{brand}_test-guarantee", "type": "guarantee", "brand": brand, "status": "live"},
        {"id": "product_otherbrand_thing", "type": "product", "brand": "otherbrand", "status": "on-sale"},
    ] + [
        # the landing pages the register records on the picked brief (briefs.py --link,
        # 2026-10-01) are real catalog ids; the fixture knows them as the catalog does
        {"id": l, "type": "link", "brand": brand, "status": "live", "url": f"https://example.test/{l}/"}
        for l in registered_links(brand)
    ] + (extra or [])
    d = Path(root) / "catalog"
    for sub in ("products", "offers", "web"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    for r in recs:
        (d / "products" / f"{r['id']}.json").write_text(json.dumps(r))
    return d


@unittest.skipIf(BID is None, "no register brief with a brief file on disk")
class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="handoff-test-"))
        self.cat = fixture_catalog(self.tmp, BRAND, PRODUCT)
        self.staging = self.tmp / "staging"
        self.ledger = self.staging / "ledger.jsonl"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sidecar(self, body):
        p = self.tmp / "ids.json"
        p.write_text(json.dumps(body))
        return str(p)

    def ledger_rows(self):
        return [json.loads(l) for l in self.ledger.read_text().splitlines()] if self.ledger.is_file() else []

    def folders(self):
        return [p for p in self.staging.rglob("manifest.json")]

    # ---- refusals -------------------------------------------------------
    def test_refuses_unknown_brief(self):
        with self.assertRaises(H.Refused) as cm:
            H.run("creator", BRAND, ["brief-9999"], catalog=self.cat, staging=self.staging, online=False)
        self.assertTrue(any("unknown brief" in r for r in cm.exception.reasons), cm.exception.reasons)
        self.assertEqual(self.folders(), [], "a refusal writes no folder")
        rows = self.ledger_rows()
        self.assertEqual(rows[-1]["verdict"]["event"], "refused")
        self.assertIn("brief-9999", rows[-1]["asked"])

    def test_refuses_unknown_product_id(self):
        side = self.sidecar({BID: {"product": "not-a-product"}})
        with self.assertRaises(H.Refused) as cm:
            H.run("graphic-designer", BRAND, [BID], catalog=self.cat, staging=self.staging, ids_file=side, online=False)
        self.assertTrue(any("not-a-product" in r and "not in the catalog" in r for r in cm.exception.reasons), cm.exception.reasons)
        self.assertEqual(self.folders(), [])

    def test_refuses_unknown_offer_and_link(self):
        side = self.sidecar({BID: {"offers": [f"offer_{BRAND}_nope"], "links": [{"id": f"link_{BRAND}_nowhere"}]}})
        with self.assertRaises(H.Refused) as cm:
            H.run("graphic-designer", BRAND, [BID], catalog=self.cat, staging=self.staging, ids_file=side, online=False)
        reasons = "\n".join(cm.exception.reasons)
        self.assertIn(f"offer_{BRAND}_nope", reasons)
        self.assertIn(f"link_{BRAND}_nowhere", reasons)
        self.assertEqual(self.folders(), [])

    def test_refuses_retired_product_and_not_live_offer_for_publish_role(self):
        side = self.sidecar({BID: {"product": f"product_{BRAND}_gone", "offers": [f"offer_{BRAND}_old-offer"],
                                   "links": [{"id": f"link_{BRAND}_test-page"}]}})
        with self.assertRaises(H.Refused) as cm:
            H.run("clipper", BRAND, [BID], catalog=self.cat, staging=self.staging, ids_file=side, online=False)
        reasons = "\n".join(cm.exception.reasons)
        self.assertIn("retired", reasons)
        self.assertIn("not-live", reasons)

    def test_refuses_role_input_missing(self):
        with self.assertRaises(H.Refused) as cm:
            H.run("video-editor", BRAND, [BID], catalog=self.cat, staging=self.staging, online=False)
        self.assertTrue(any("edit kit" in r for r in cm.exception.reasons), cm.exception.reasons)
        with self.assertRaises(H.Refused) as cm:
            H.run("clipper", BRAND, [BID], catalog=self.cat, staging=self.staging, online=False)
        self.assertTrue(any("landing page" in r for r in cm.exception.reasons), cm.exception.reasons)

    def test_refuses_unknown_role_and_missing_catalog(self):
        with self.assertRaises(H.Refused):
            H.run("someone", BRAND, [BID], catalog=self.cat, staging=self.staging, online=False)
        with self.assertRaises(H.Refused) as cm:
            H.run("creator", BRAND, [BID], catalog=self.tmp / "missing.json", staging=self.staging, online=False)
        self.assertIn("catalog not found", cm.exception.reasons[0])

    # ---- the happy path -------------------------------------------------
    def test_happy_path_writes_handoff_and_manifest(self):
        side = self.sidecar({BID: {"offers": [f"offer_{BRAND}_test-offer"],
                                   "links": [{"id": f"link_{BRAND}_test-page"}],
                                   "parts": [f"guarantee_{BRAND}_test-guarantee"]}})
        root, m = H.run("graphic-designer", BRAND, [BID], catalog=self.cat, staging=self.staging,
                        ids_file=side, online=False, when="2026-09-28")
        self.assertEqual(m["name"], f"graphic-designer-handoff_{BRAND}_2026-09-28")
        self.assertEqual(root, self.staging / "graphic-designer" / BRAND / m["name"])
        for f in ("handoff.md", "manifest.json", "assets/index.json", "returned/README.md",
                  "references/products.json", "references/offers.json", "references/links.json", "references/parts.json",
                  f"briefs/{BID}/brief.md", f"briefs/{BID}/brief.json"):
            self.assertTrue((root / f).is_file(), f)
        md = (root / "handoff.md").read_text()
        heads = [l for l in md.splitlines() if l.startswith("## ")]
        self.assertEqual([h[:4].strip() for h in heads], [f"## {i}" for i in range(1, 9)], heads)
        self.assertIn(f"link_{BRAND}_test-page", md)
        self.assertIn("https://example.test/page/", md)
        self.assertIn("Nothing goes live without the owner's go", md)
        # the manifest
        self.assertEqual(m["schema"], H.SCHEMA)
        self.assertTrue(m["checks_passed"])
        self.assertEqual(m["ids"]["products"], [f"product_{BRAND}_{H.N.slug(PRODUCT)}"])
        self.assertEqual(m["ids"]["offers"], [f"offer_{BRAND}_test-offer"])
        self.assertEqual(m["ids"]["links"], [f"link_{BRAND}_test-page"])
        self.assertEqual(m["ids"]["parts"], [f"guarantee_{BRAND}_test-guarantee"])
        self.assertEqual(m["drive"], {"target": f"Shared Assets/handoffs/graphic-designer/{BRAND}/{m['name']}", "written": False})
        self.assertEqual(m["briefs"][0]["id"], BID)
        self.assertEqual(m["catalog"]["shape"], "B")
        self.assertTrue(all(c["result"] in ("ok", "not checked") for c in m["checks"]))
        self.assertTrue(any(c["check"] == "link answers" and c["result"] == "not checked" for c in m["checks"]))
        # it round-trips as JSON from disk
        self.assertEqual(json.loads((root / "manifest.json").read_text())["name"], m["name"])
        # the ledger
        rows = self.ledger_rows()
        self.assertEqual(rows[-1]["verdict"]["event"], "sent")
        self.assertEqual(rows[-1]["item"], m["name"])
        self.assertEqual(rows[-1]["briefs"], [BID])
        # the same day twice → a second name, never an overwrite
        root2, m2 = H.run("graphic-designer", BRAND, [BID], catalog=self.cat, staging=self.staging,
                          ids_file=side, online=False, when="2026-09-28")
        self.assertEqual(m2["name"], m["name"] + "-2")

    def test_old_spelling_and_old_product_name_resolve(self):
        old = H.N.brief_code(BID)
        side = self.sidecar({old: {"product": PRODUCT.replace("-", "")}})
        root, m = H.run("creator", BRAND, [old], catalog=self.cat, staging=self.staging, ids_file=side, online=False)
        self.assertEqual(m["briefs"][0]["id"], BID)
        self.assertEqual(m["briefs"][0]["old_code"], old)
        self.assertEqual(m["ids"]["products"], [f"product_{BRAND}_{H.N.slug(PRODUCT)}"])

    # ---- assets: the files themselves, copied in ------------------------
    def test_kit_and_email_files_are_copied_not_linked(self):
        kit = self.tmp / "kit"
        (kit / "scenes").mkdir(parents=True)
        (kit / "edit-kit.json").write_text("{}")
        (kit / "scenes" / "01.mp4").write_bytes(b"fake mp4")
        (kit / ".DS_Store").write_bytes(b"x")
        root, m = H.run("video-editor", BRAND, [BID], catalog=self.cat, staging=self.staging, kit=str(kit), online=False)
        self.assertEqual(root.relative_to(self.staging).parts, ("video-editor", BRAND, m["name"]), "no extra level")
        self.assertTrue((root / "assets/kit/scenes/01.mp4").is_file())
        self.assertFalse((root / "assets/kit").is_symlink())
        self.assertFalse((root / "assets/kit/.DS_Store").exists())
        self.assertEqual(sorted(f for f in m["assets"] if f.startswith("assets/kit/")), ["assets/kit/edit-kit.json", "assets/kit/scenes/01.mp4"])
        run = self.tmp / "email-run"
        (run / "deliverable").mkdir(parents=True)
        (run / "media").mkdir()
        (run / "deliverable" / "preview.html").write_text("<html></html>")
        (run / "media" / "hero.png").write_bytes(b"\x89PNG fake")
        (run / "stage1--sent.md").write_text("not an asset")
        # the email files are copied the same way whichever role takes them (the
        # uploader's own link check needs the brief's drop pages named, not tested here)
        root, m = H.run("graphic-designer", BRAND, [BID], catalog=self.cat, staging=self.staging,
                        email_run=str(run), online=False)
        self.assertEqual(sorted(f for f in m["assets"] if f.startswith("assets/email/")), ["assets/email/deliverable/preview.html", "assets/email/media/hero.png"])
        self.assertIn("assets/email/deliverable/preview.html", json.loads((root / "assets/index.json").read_text())["files"])

    def test_empty_kit_refuses(self):
        (self.tmp / "empty-kit").mkdir()
        with self.assertRaises(H.Refused) as cm:
            H.run("video-editor", BRAND, [BID], catalog=self.cat, staging=self.staging, kit=str(self.tmp / "empty-kit"), online=False)
        self.assertTrue(any("no files" in r for r in cm.exception.reasons), cm.exception.reasons)
        self.assertEqual(self.folders(), [])

    # ---- drive ----------------------------------------------------------
    def test_drive_copy_records_path_and_never_overwrites(self):
        mount = self.tmp / "Shared Assets"
        mount.mkdir()
        old = H.DRIVE_MOUNT
        H.DRIVE_MOUNT = mount
        try:
            root, m = H.run("graphic-designer", BRAND, [BID], catalog=self.cat, staging=self.staging,
                            online=False, when="2026-09-28", drive=True)
            dest = mount / "handoffs" / "graphic-designer" / BRAND / m["name"]
            self.assertTrue((dest / "handoff.md").is_file())
            self.assertTrue((dest / "returned" / "README.md").is_file())
            self.assertTrue(m["drive"]["written"])
            self.assertEqual(m["drive"]["path"], f"Shared Assets/handoffs/graphic-designer/{BRAND}/{m['name']}/")
            on_drive = json.loads((dest / "manifest.json").read_text())
            self.assertTrue(on_drive["drive"]["written"])
            self.assertIn("this folder is on Drive", (dest / "handoff.md").read_text())
            self.assertTrue(self.ledger_rows()[-1]["drive_written"])
            # the local copy moved aside: Drive still has it, so the next is -2, never an overwrite
            shutil.rmtree(root)
            root2, m2 = H.run("graphic-designer", BRAND, [BID], catalog=self.cat, staging=self.staging,
                              online=False, when="2026-09-28", drive=True)
            self.assertEqual(m2["name"], m["name"] + "-2")
            self.assertTrue((dest / "handoff.md").is_file())
            # no mount → refused, nothing written
            H.DRIVE_MOUNT = self.tmp / "not-mounted"
            with self.assertRaises(H.Refused) as cm:
                H.run("creator", BRAND, [BID], catalog=self.cat, staging=self.staging, online=False, drive=True)
            self.assertIn("not mounted", cm.exception.reasons[0])
            self.assertFalse((self.staging / "creator").exists())
        finally:
            H.DRIVE_MOUNT = old

    def test_no_drive_by_default_from_code(self):
        root, m = H.run("graphic-designer", BRAND, [BID], catalog=self.cat, staging=self.staging, online=False)
        self.assertFalse(m["drive"]["written"])

    # ---- take back ------------------------------------------------------
    def test_take_back_joins_files_and_live_ids(self):
        side = self.sidecar({BID: {"links": [{"id": f"link_{BRAND}_test-page"}]}})
        root, m = H.run("graphic-designer", BRAND, [BID], catalog=self.cat, staging=self.staging, ids_file=side, online=False)
        ret = root / "returned"
        (ret / f"{BID}_asset-01.png").write_bytes(b"\x89PNG fake")
        (ret / f"{H.N.brief_code(BID)}-a02.png").write_bytes(b"\x89PNG fake")
        (ret / "live-ids.json").write_text(json.dumps([{"ad_name": "x", "channel": "meta", "platform_id": "1234567890"},
                                                        {"ad_name": "y", "channel": "meta", "platform_id": None}]))
        idx = H.take_back("graphic-designer", BRAND, m["name"], self.staging, self.ledger)
        by = {f["file"]: f for f in idx["files"]}
        self.assertEqual(by[f"{BID}_asset-01.png"]["brief_id"], BID)
        self.assertEqual(by[f"{BID}_asset-01.png"]["asset_id"], "asset-01")
        self.assertEqual(by[f"{H.N.brief_code(BID)}-a02.png"]["brief_id"], BID)
        self.assertEqual(by[f"{H.N.brief_code(BID)}-a02.png"]["asset_id"], "asset-02")
        self.assertEqual([l["live_id"] for l in idx["live_ids"]], ["live_meta_1234567890", None])
        m2 = json.loads((root / "manifest.json").read_text())
        self.assertEqual(sorted(m2["returned"]["received"]), sorted([f"{BID}_asset-01.png", f"{H.N.brief_code(BID)}-a02.png", "live-ids.json"]))
        rows = self.ledger_rows()
        self.assertEqual(rows[-1]["verdict"]["event"], "returned")
        self.assertEqual(rows[-1]["live_ids"], ["live_meta_1234567890"])
        with self.assertRaises(H.Refused):
            H.take_back("graphic-designer", BRAND, "no-such-handoff", self.staging, self.ledger)


class CatalogShapeTests(unittest.TestCase):
    def test_survey_shape_resolves_ids_offers_and_old_names(self):
        brand = "acme"
        tmp = Path(tempfile.mkdtemp(prefix="handoff-cat-"))
        try:
            f = tmp / "catalog.json"
            f.write_text(json.dumps({"meta": {}, "brands": {brand: {
                "products": [{"id": f"product_{brand}_widget", "status": "on-sale"}],
                "bundles": [{"id": f"bundle_{brand}_widget-3-pack", "status": "on-sale"}],
                "parts": [{"id": f"gift_{brand}_free-bag", "kind": "gift"}],
                "offers": [{"ids": [f"offer_{brand}_widget-buy-2", f"offer_{brand}_widget-buy-2-refill"], "status": "live"}],
                "placements": [{"id": f"link_{brand}_shop_landing", "url": "https://shop.example.test/"},
                               {"id": f"placement_{brand}_shop_landing_main-1"}],
                "old_names": [{"old": "wdgt · Widget™ · the-widget", "layer": "product", "new": f"product_{brand}_widget"}],
            }, "otherbrand": {"products": [{"id": "product_otherbrand_x"}]}}}))
            c = H.Catalog(f, brand)
            self.assertEqual(c.shape, "A")
            self.assertEqual(c.resolve("widget", "product"), f"product_{brand}_widget")
            self.assertEqual(c.resolve("Widget™", "product"), f"product_{brand}_widget")
            self.assertEqual(c.resolve("widget-3-pack", "product"), f"bundle_{brand}_widget-3-pack")
            self.assertEqual(c.resolve(f"offer_{brand}_widget-buy-2-refill", "offer"), f"offer_{brand}_widget-buy-2-refill")
            self.assertEqual(c.resolve("widget-buy-2", "offer"), f"offer_{brand}_widget-buy-2")
            self.assertEqual(c.resolve(f"link_{brand}_shop_landing", "link"), f"link_{brand}_shop_landing")
            self.assertEqual(c.url(f"link_{brand}_shop_landing"), "https://shop.example.test/")
            self.assertEqual(c.resolve("free-bag", "part"), f"gift_{brand}_free-bag")
            self.assertIsNone(c.resolve("product_otherbrand_x", "product"))
            self.assertIsNone(c.resolve(f"product_{brand}_widget", "offer"), "a product id is not an offer id")
            self.assertIsNone(c.resolve("not-recorded", "offer"))
            self.assertEqual(c.status(f"offer_{brand}_widget-buy-2"), "live")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_batch_tokens(self):
        self.assertTrue(H.is_batch("batch-2026-09-23-a"))
        self.assertTrue(H.is_batch("260923a"))
        self.assertFalse(H.is_batch("brief-0140"))
        self.assertEqual(H.batch_forms("batch-2026-09-23-a") & {"260923a", "batch-2026-09-23-a"}, {"260923a", "batch-2026-09-23-a"})

    def test_ads_get_short_names_and_their_pictures(self):
        """An ad is listed by its short form (names.short_unit / short_meta), the
        old 13-part name beside it, and its pictures are copied under the short name."""
        tmp = Path(tempfile.mkdtemp(prefix="handoff-ads-"))
        try:
            old = "acme-widget-static-ai-none-avatar-problem-angle-concept-format-p154-9x16-260923a"
            folder = tmp / old
            folder.mkdir()
            (folder / f"{old}-a01.png").write_bytes(b"\x89PNG fake")
            (folder / f"{old}-a02.png").write_bytes(b"\x89PNG fake")
            ad = {"ad_name": old, "batch_id": "batch-2026-09-23-a", "folder": str(folder),
                  "pictures": [f"{old}-a01.png", f"{old}-a02.png"]}
            g = {"brand": "acme", "extra": {}, "briefs": [{
                "id": "brief-0154", "product_id": "product_acme_widget",
                "link_ids": ["link_acme_cpk_quiz", "link_acme_cpk_landing"], "ads": [ad]}]}
            plan = H.plan_assets(g)
            unit = "acme_widget_brief-0154_batch-2026-09-23-a"
            self.assertEqual(ad["short"], unit)
            self.assertEqual([m["meta_ad_name"] for m in ad["meta_names"]], [f"{unit}_cpk-quiz", f"{unit}_cpk-landing"])
            self.assertEqual([d for d, _ in plan], [f"ads/{unit}/{unit}_asset-01.png", f"ads/{unit}/{unit}_asset-02.png"])
            self.assertEqual(ad["files"][0]["was"], f"{old}-a01.png")
            (folder / f"{old}-a02.png").unlink()
            ad.pop("short")
            with self.assertRaises(H.Refused) as cm:
                H.plan_assets(g)
            self.assertTrue(any("not found" in r for r in cm.exception.reasons), cm.exception.reasons)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_funnel_is_the_link_ids_page_part(self):
        self.assertEqual(H.funnel_of("link_acme_cpk_quiz"), "cpk-quiz")
        self.assertEqual(H.funnel_of("link_acme_cpk-subscribe_landing"), "cpk-subscribe-landing")

    def test_funnel_follows_the_live_meta_names(self):
        """A link the catalog and funnel list know is named `<funnel id>-<page>`,
        the way the live Brand A ads read (…_body-scrub-cpk-quiz / …-offer)."""
        self.assertEqual(H.funnel_of("link_brand-a_cpk_quiz"), "body-scrub-cpk-quiz")
        self.assertEqual(H.funnel_of("link_brand-a_cpk_landing"), "body-scrub-cpk-offer")
        self.assertEqual(H.funnel_of("link_brand-a_cpk_glow-face-scrub_landing"), "face-scrub-cpk-offer")

    def test_roles_are_the_seven(self):
        self.assertEqual(sorted(H.ROLES), sorted(["creator-manager", "creator", "clipper", "graphic-designer",
                                                  "video-editor", "ad-uploader", "klaviyo-uploader"]))
        for name, r in H.ROLES.items():
            for k in ("title", "comes_from", "job_types", "inside", "told", "comes_back", "stops_at", "needs", "publish", "steps", "returned"):
                self.assertIn(k, r, f"{name}.{k}")
            self.assertTrue(all(n in H.NEEDS_WORDS for n in r["needs"]), name)


if __name__ == "__main__":
    unittest.main(verbosity=1)


class QueueNameTests(unittest.TestCase):
    """A one-brief video-editor hand-off is named by the brief's short form (the owner, 2026-10-09)."""

    def test_editor_folder_takes_the_brief_short_form(self):
        g = {"role": "video-editor", "brand": "brand-a",
             "briefs": [{"id": "brief-0292", "product_id": "product_brand-a_glow-face-scrub"}]}
        self.assertEqual(H.queue_base(g), "brand-a_glow-face-scrub_brief-0292")

    def test_other_roles_and_many_briefs_keep_the_dated_name(self):
        b = {"id": "brief-0292", "product_id": "product_brand-a_glow-face-scrub"}
        self.assertIsNone(H.queue_base({"role": "graphic-designer", "brand": "brand-a", "briefs": [b]}))
        self.assertIsNone(H.queue_base({"role": "video-editor", "brand": "brand-a", "briefs": [b, b]}))
