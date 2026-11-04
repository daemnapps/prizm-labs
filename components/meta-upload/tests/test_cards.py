"""The card road's promises: checks catch a bad card; a card moves, never
copies; nothing uploads without the owner's approve on it; one card -> one ad per
page in Meta (flexible or carousel, slides in order), ids on the card, folder
in 3-live, one line per ad in live.jsonl; a Meta error leaves it in
2-approved; a re-run makes nothing twice. All against a fake Meta."""
import json, os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from PIL import Image
import cards as C, upload as U
import ad_sets as AS
import fake_meta
from fake_meta import FakeMeta

PAGE = {"link_id": "link_brand_b_cpk_quiz", "url": "https://recipe.brand-b.com/brand-b-scrub-cpk/quiz/"}
NAME = "brand_b_brilliance-body-scrub_brief-0154_batch-2026-10-02-a"


def pic(path, size=(540, 960)):
    Image.new("RGB", size, (200, 120, 60)).save(path)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "meta"
        os.environ["META_CARDS_ROOT"] = str(self.root)
        C.ensure_tree(self.root, ["brand-b"])
        C._cache.clear()
        fake_meta.WORLD.clear()
        self.live = Path(self.tmp.name) / "live.jsonl"
        self.p = [mock.patch.object(U, "LIVE", self.live),
                  mock.patch.object(C, "page_status", return_value=200),
                  # the test pages sell body scrub, so the test brand's one offer is body scrub
                  mock.patch.object(C, "strategy_offer", return_value={"product": "brilliance-body-scrub",
                                                                      "match": ["brand-b-scrub-cpk"]}),
                  # the test card's ad set is one already running in Meta (ad_sets.py, 2026-10-27)
                  mock.patch.object(AS, "live", return_value={"adset_brand_b_spot-hider_pigment-memory"})]
        for x in self.p:
            x.start()

    def tearDown(self):
        for x in self.p:
            x.stop()
        os.environ.pop("META_CARDS_ROOT", None)
        self.tmp.cleanup()

    def card(self, lane="image", fmt="flexible", n=2, name=NAME, size=(540, 960), **over):
        f = self.root / "brand-b" / "1-check" / lane / name
        f.mkdir(parents=True)
        media = []
        for i in range(1, n + 1):
            m = f"{name}_{'slide' if fmt == 'carousel' else 'asset'}-{i:02d}.png"
            pic(f / m, size)
            media.append(m)
        c = {"schema": C.SCHEMA, "brand": "brand-b", "lane": lane, "format": fmt, "ad_name": name,
             "product": "brilliance-body-scrub", "avatar": "spot-hider", "angle": "pigment-memory", "media": media,
             "words": {"primary": ["Body one."], "headlines": ["H1", "H2", "H3"][:n] if fmt == "carousel" else ["H1"],
                       "descriptions": ["D1"]},
             "pages": [PAGE], "checks": {}, "approval": None, "meta": [],
             "diversity": {"verdict": "new", "moves_apart": 4, "same_on": []}}
        c.update(over)
        C.save(f, c)
        return f

    def approve(self, f, start="PAUSED"):
        c = C.load(f)
        c["approval"] = {"by": "the owner", "at": "2026-10-01T12:00:00", "decision": "approve", "start": start}
        C.save(f, c)
        return C.move(f, "2-approved")


class Checks(Base):
    def test_meta_strategy_checks(self):
        # 7 Oct 2026: a variation of a running creative, a page off the one offer, re-used footage
        f = self.card(diversity={"verdict": "variation", "moves_apart": 1, "same_on": ["who", "format"]})
        live = self.root / "brand-b" / "3-live" / "image" / "old"
        live.mkdir(parents=True)
        pic(live / "old_asset-01.png")
        with mock.patch.object(C, "strategy_offer", return_value={"product": "brilliance-face-scrub",
                                                                 "match": ["brand-b-facescrub-cpk"]}):
            c = C.check_and_save(f, meta=FakeMeta("brand-b"))
        bad = {k for k, v in c["checks"].items() if not v["ok"]}
        self.assertEqual(bad, {"diversity", "offer", "new_footage"})
        self.assertIn("variation", c["checks"]["diversity"]["why"])

    def test_unscored_card_waits_for_approve(self):
        f = self.card(diversity=None)
        c = C.check_and_save(f, meta=FakeMeta("brand-b"))
        self.assertIn("scored when you approve", c["checks"]["diversity"]["why"])

    def test_good_card_passes(self):
        f = self.card()
        c = C.check_and_save(f, meta=FakeMeta("brand-b"))
        self.assertTrue(C.passed(c), {k: v for k, v in c["checks"].items() if not v["ok"]})
        self.assertEqual(c["checks"]["ad_set"]["why"], "adset_brand_b_spot-hider_pigment-memory")
        self.assertIn("body-scrub-cpk", c["checks"]["campaign"]["why"])

    def test_designed_thumbnails_pass_and_a_bad_one_is_named(self):
        """4 Oct 2026: the thumbnail check reused a name the rest of checks() needs and broke every card with thumbs."""
        f = self.card(n=1)
        c = C.load(f)
        pic(f / "t1.png", (1080, 1920))
        c["thumbs"] = {c["media"][0]: "t1.png"}
        C.save(f, c)
        out = C.checks(f, C.load(f), meta=FakeMeta("brand-b"))
        self.assertTrue(out["thumbs"]["ok"], out["thumbs"])
        self.assertTrue(out["name"]["ok"], out["name"])
        pic(f / "t1.png", (1080, 1080))
        self.assertFalse(C.checks(f, C.load(f), meta=FakeMeta("brand-b"))["thumbs"]["ok"])

    def test_wrong_ratio_and_no_headline(self):
        f = self.card(size=(1080, 1080), words={"primary": ["x"], "headlines": [], "descriptions": []})
        c = C.checks(f, C.load(f), meta=FakeMeta("brand-b"))
        self.assertFalse(c["ratio"]["ok"])
        self.assertFalse(c["words"]["ok"])

    def test_carousel_needs_two_slides(self):
        f = self.card(lane="carousel", fmt="carousel", n=1)
        self.assertFalse(C.checks(f, C.load(f), meta=FakeMeta("brand-b"))["media"]["ok"])

    def test_wrong_product_page(self):
        f = self.card(pages=[{"link_id": "link_brand_b_cpk_brilliance-face-scrub_landing"}])
        c = C.checks(f, C.load(f), meta=FakeMeta("brand-b"))
        self.assertFalse(c["product"]["ok"])

    def test_page_not_live(self):
        f = self.card()
        with mock.patch.object(C, "page_status", return_value=404):
            self.assertFalse(C.checks(f, C.load(f), meta=FakeMeta("brand-b"))["pages"]["ok"])

    def test_bad_name(self):
        f = self.card(name="brand_b_not-a-name")
        self.assertFalse(C.checks(f, C.load(f), meta=FakeMeta("brand-b"))["name"]["ok"])

    def test_page_cap_full(self):
        f = self.card()
        with mock.patch.object(C, "PAGE_AD_LIMIT", 3):
            self.assertFalse(C.checks(f, C.load(f), meta=FakeMeta("brand-b"))["page_cap"]["ok"])


class Moves(Base):
    def test_move_is_a_rename(self):
        f = self.card()
        new = C.move(f, "2-approved")
        self.assertFalse(f.exists())
        self.assertTrue((new / "card.json").is_file())
        self.assertEqual(C.where(new)["state"], "2-approved")
        self.assertEqual(C.where(new)["lane"], "image")

    def test_folder_of_refuses_escape(self):
        for bad in ("../x", "brand-b/1-check/image/..", "brand-b/9-x/image/a", "a/b"):
            with self.assertRaises(ValueError):
                C.folder_of(bad)


class Upload(Base):
    def test_refused_without_owners_approve(self):
        f = C.move(self.card(), "2-approved")
        with self.assertRaises(SystemExit) as e:
            U.upload_card(f, m=FakeMeta("brand-b"), log=lambda *_: None)
        self.assertIn("REFUSED", str(e.exception))

    def test_refused_outside_2_approved(self):
        f = self.card()
        c = C.load(f)
        c["approval"] = {"by": "the owner", "decision": "approve", "start": "PAUSED"}
        C.save(f, c)
        with self.assertRaises(SystemExit):
            U.upload_card(f, m=FakeMeta("brand-b"), log=lambda *_: None)

    def test_flexible_goes_live(self):
        m = FakeMeta("brand-b")
        new, card = U.upload_card(self.approve(self.card()), m=m, log=lambda *_: None)
        self.assertEqual(C.where(new)["state"], "3-live")
        self.assertEqual(card["meta"][0]["meta_ad_name"], NAME + "_body-scrub-cpk-quiz")   # <funnel id>-<page>, as the live ads read
        ads = [p for e, p in m.posts if e == "ads"]
        self.assertEqual(len(ads), 1)
        self.assertEqual(ads[0]["status"], "PAUSED")
        self.assertIn("creative_asset_groups_spec", ads[0])
        self.assertEqual(ads[0]["creative"]["object_story_spec"]["link_data"]["link"], PAGE["url"])
        camp = [p for e, p in m.posts if e == "campaigns"][0]
        self.assertEqual(camp["status"], "PAUSED")
        line = json.loads(self.live.read_text().splitlines()[0])
        self.assertEqual((line["ad_name"], line["lane"], line["brand"]), (NAME, "image", "brand-b"))
        self.assertEqual(C.load(new)["meta"][0]["ad_id"], line["ad_id"])

    def test_start_on(self):
        m = FakeMeta("brand-b")
        U.upload_card(self.approve(self.card(), "ACTIVE"), m=m, log=lambda *_: None)
        self.assertEqual([p for e, p in m.posts if e == "ads"][0]["status"], "ACTIVE")
        # 7 Oct 2026: "On" switches on the campaign and ad set this upload made
        made = {p["id"] for e, p in m.posts if e == "update" and p.get("status") == "ACTIVE"}
        made_here = {x["id"] for edge in ("campaigns", "adsets") for x in m.w[edge]}
        self.assertTrue(made and made <= made_here)

    def test_start_paused_switches_nothing_on(self):
        m = FakeMeta("brand-b")
        U.upload_card(self.approve(self.card(), "PAUSED"), m=m, log=lambda *_: None)
        self.assertFalse([p for e, p in m.posts if e == "update"])

    def test_approve_needs_on_or_paused(self):
        import approve as A
        code, out = A.approve("anything", None, "the owner")
        self.assertEqual(code, 400)

    def test_carousel_keeps_slide_order(self):
        m = FakeMeta("brand-b")
        f = self.card(lane="carousel", fmt="carousel", n=3)
        U.upload_card(self.approve(f), m=m, log=lambda *_: None)
        ad = [p for e, p in m.posts if e == "ads"][0]
        ld = ad["creative"]["object_story_spec"]["link_data"]
        self.assertNotIn("creative_asset_groups_spec", ad)
        self.assertEqual([k["image_hash"] for k in ld["child_attachments"]],
                         [f"hash-{NAME}_slide-0{i}.png" for i in (1, 2, 3)])
        self.assertEqual([k["name"] for k in ld["child_attachments"]], ["H1", "H2", "H3"])
        self.assertIs(ld["multi_share_optimized"], False)
        self.assertIs(ld["multi_share_end_card"], False)
        self.assertEqual(ld["message"], "Body one.")
        self.assertEqual(ld["call_to_action"]["type"], "SHOP_NOW")
        self.assertIn("url_tags", ad["creative"])
        self.assertIn("degrees_of_freedom_spec", ad["creative"])

    def test_meta_error_stays_in_2_approved_then_retry_is_safe(self):
        f = self.approve(self.card())
        with self.assertRaises(SystemExit):
            U.upload_card(f, m=FakeMeta("brand-b", fail_on="ads"), log=lambda *_: None)
        self.assertTrue(f.exists())
        self.assertIn("Invalid parameter", C.load(f)["upload_error"]["error"])
        m = FakeMeta("brand-b")
        new, card = U.upload_card(f, m=m, log=lambda *_: None)
        self.assertEqual(C.where(new)["state"], "3-live")
        self.assertNotIn("upload_error", card)
        # the campaign and ad set made on the failed run were found by name, not made again
        self.assertEqual([e for e, _ in m.posts if e in ("campaigns", "adsets")], [])


class Server(Base):
    def setUp(self):
        super().setUp()
        # one approver, as these tests assume; the real approvers.json is the team's list and may hold several
        p = mock.patch("upload.approvers", return_value=["the owner"])
        p.start()
        self.addCleanup(p.stop)

    def test_approve_refused_while_a_check_fails(self):
        import approve as A
        f = self.card(words={"primary": ["x"], "headlines": [], "descriptions": []})
        with mock.patch.object(A, "FAKE", FakeMeta):
            code, out = A.approve(C.card_id(f), "PAUSED")
        self.assertEqual(code, 409)
        self.assertTrue(f.exists())
        self.assertIsNone(C.load(f)["approval"])

    def test_approve_goes_live(self):
        import approve as A
        f = self.card()
        with mock.patch.object(A, "FAKE", FakeMeta):
            code, out = A.approve(C.card_id(f), "PAUSED")
        self.assertTrue(out["ok"], out)
        new = C.folder_of(out["id"])
        self.assertEqual(C.load(new)["approval"]["by"], "the owner")

    def test_disapprove_needs_a_reason_and_a_note(self):
        import approve as A
        f = self.card()
        self.assertEqual(A.disapprove(C.card_id(f), [], "x")[0], 400)
        self.assertEqual(A.disapprove(C.card_id(f), ["words"], " ")[0], 400)
        self.assertEqual(A.disapprove(C.card_id(f), ["nope"], "x")[0], 400)
        self.assertTrue(f.exists())
        code, out = A.disapprove(C.card_id(f), ["words"], "headline too long")
        self.assertEqual(C.where(C.folder_of(out["id"]))["state"], "sent-back")
        a = C.load(C.folder_of(out["id"]))["approval"]
        self.assertEqual((a["decision"], a["note"], a["by"]), ("disapprove", "headline too long", "the owner"))
        self.assertEqual(a["reasons"][0]["tool"], "copywriter")


class FewerMetaCalls(Base):
    """12 Oct 2026, after "User request limit reached" (code 17): listing never calls Meta, the Page ad
    count is asked once an hour per brand and never blocks, a scorer failure never blocks, campaign and
    ad set ids are remembered per brand, the ads list is read only to finish a half-done ad, and every
    video of an ad is waited on in one read."""

    def test_listing_a_view_never_calls_meta(self):
        import approve as A
        self.card()
        with mock.patch("meta.Meta", side_effect=AssertionError("Meta called on a page load")), \
                mock.patch.object(C, "page_status", side_effect=AssertionError("page fetched on a page load")):
            out = A.cards_json("check")
        chk = {c["key"]: c for c in out["cards"][0]["checks"]}
        self.assertTrue(chk["page_cap"]["ok"])
        self.assertIn("when you approve", chk["page_cap"]["why"])

    def test_page_count_asked_once_for_a_batch(self):
        m1, m2 = FakeMeta("brand-b"), FakeMeta("brand-b")
        self.assertEqual(C.page_ads("brand-b", m1)["count"], 3)
        self.assertEqual(C.page_ads("brand-b", m2)["count"], 3)       # another approve, the file answers
        asked = [g for m in (m1, m2) for g in m.gets if g[0].endswith("/ads_volume")]
        self.assertEqual(len(asked), 1)
        self.assertTrue(C.page_ads_file("brand-b").is_file())

    def test_request_limit_passes_with_a_note(self):
        class Limited(FakeMeta):
            def get(self, path, **params):
                raise SystemExit('Meta 400: {"error":{"message":"(#17) User request limit reached","code":17,'
                                 '"error_subcode":2446079}}')
        f = self.card()
        c = C.checks(f, C.load(f), meta=Limited("brand-b"))["page_cap"]
        self.assertTrue(c["ok"])
        self.assertIn("request limit", c["why"])

    def test_scorer_failure_does_not_block_the_upload(self):
        import approve as A, types
        broken = types.ModuleType("check")
        broken.score_card = mock.Mock(side_effect=ImportError("no module named tag"))
        f = self.card(diversity=None)
        with mock.patch.dict(sys.modules, {"check": broken}), mock.patch.object(A, "FAKE", None), \
                mock.patch.object(A, "meta_for", lambda b: FakeMeta(b)):
            code, out = A.approve(C.card_id(f), "PAUSED", "the owner")
        self.assertEqual(code, 200, out)
        self.assertTrue(out["ok"], out)
        dv = C.load(C.folder_of(out["id"]))["diversity"]
        self.assertEqual(dv["verdict"], "unscored")
        self.assertIn("no module named tag", dv["why"])

    def test_ids_remembered_per_brand(self):
        m1 = FakeMeta("brand-b")
        U.upload_card(self.approve(self.card()), m=m1, log=lambda *_: None)
        self.assertFalse([x for x in m1.lists if x.endswith("/ads")])  # a fresh upload never lists ads
        m2 = FakeMeta("brand-b")
        U.upload_card(self.approve(self.card(name=NAME.replace("brief-0154", "brief-0155"))), m=m2, log=lambda *_: None)
        self.assertEqual(m2.lists, [])                                   # campaign + ad set from ids.json
        self.assertEqual([e for e, _ in m2.posts if e in ("campaigns", "adsets")], [])
        ids = json.loads((U.brand_runs("brand-b") / "ids.json").read_text())
        self.assertEqual(len(ids["campaigns"]), 1)
        self.assertEqual(len(ids["ad_sets"]), 1)
        self.assertTrue(str(U.brand_runs("brand-b")).startswith(str(self.root)))   # a trial never writes runs/

    def test_every_video_waited_on_in_one_read(self):
        f = self.root / "brand-b" / "1-check" / "video" / NAME
        f.mkdir(parents=True)
        for i in (1, 2):
            (f / f"v{i}.mp4").write_bytes(b"x")
        C.save(f, {"schema": C.SCHEMA, "brand": "brand-b", "lane": "video", "format": "flexible", "ad_name": NAME,
                   "product": "brilliance-body-scrub", "avatar": "spot-hider", "angle": "pigment-memory",
                   "media": ["v1.mp4", "v2.mp4"], "words": {"primary": ["B"], "headlines": ["H"], "descriptions": []},
                   "pages": [PAGE], "checks": {}, "approval": None, "meta": []})
        m = FakeMeta("brand-b")
        U.upload_card(self.approve(f), m=m, log=lambda *_: None)
        reads = [g for g in m.gets if g[0] == "" and "ids" in g[1]]
        self.assertEqual(len(reads), 1)
        self.assertEqual(len(reads[0][1]["ids"].split(",")), 2)
        sent = [i for i, (e, _) in enumerate(m.posts) if e == "advideos"]
        ad = [i for i, (e, _) in enumerate(m.posts) if e == "ads"]
        self.assertEqual(len(sent), 2)
        self.assertLess(max(sent), ad[0])


if __name__ == "__main__":
    unittest.main()
