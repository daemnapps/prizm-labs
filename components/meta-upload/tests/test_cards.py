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
import fake_meta
from fake_meta import FakeMeta

PAGE = {"link_id": "link_brand-a_cpk_quiz", "url": "https://recipe.brand-a.example/brand-a-scrub-cpk/quiz/"}
NAME = "brand-a_glow-body-scrub_brief-0154_batch-2026-10-02-a"


def pic(path, size=(540, 960)):
    Image.new("RGB", size, (200, 120, 60)).save(path)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "meta"
        os.environ["META_CARDS_ROOT"] = str(self.root)
        C.ensure_tree(self.root, ["brand-a"])
        C._cache.clear()
        fake_meta.WORLD.clear()
        self.live = Path(self.tmp.name) / "live.jsonl"
        self.p = [mock.patch.object(U, "LIVE", self.live),
                  mock.patch.object(C, "page_status", return_value=200),
                  # the test pages sell body scrub, so the test brand's one offer is body scrub
                  mock.patch.object(C, "strategy_offer", return_value={"product": "glow-body-scrub",
                                                                      "match": ["brand-a-scrub-cpk"]})]
        for x in self.p:
            x.start()

    def tearDown(self):
        for x in self.p:
            x.stop()
        os.environ.pop("META_CARDS_ROOT", None)
        self.tmp.cleanup()

    def card(self, lane="image", fmt="flexible", n=2, name=NAME, size=(540, 960), **over):
        f = self.root / "brand-a" / "1-check" / lane / name
        f.mkdir(parents=True)
        media = []
        for i in range(1, n + 1):
            m = f"{name}_{'slide' if fmt == 'carousel' else 'asset'}-{i:02d}.png"
            pic(f / m, size)
            media.append(m)
        c = {"schema": C.SCHEMA, "brand": "brand-a", "lane": lane, "format": fmt, "ad_name": name,
             "product": "glow-body-scrub", "avatar": "avatar-four", "angle": "pigment-memory", "media": media,
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
        live = self.root / "brand-a" / "3-live" / "image" / "old"
        live.mkdir(parents=True)
        pic(live / "old_asset-01.png")
        with mock.patch.object(C, "strategy_offer", return_value={"product": "glow-face-scrub",
                                                                 "match": ["brand-a-facescrub-cpk"]}):
            c = C.check_and_save(f, meta=FakeMeta("brand-a"))
        bad = {k for k, v in c["checks"].items() if not v["ok"]}
        self.assertEqual(bad, {"diversity", "offer", "new_footage"})
        self.assertIn("variation", c["checks"]["diversity"]["why"])

    def test_unscored_card_waits_for_approve(self):
        f = self.card(diversity=None)
        c = C.check_and_save(f, meta=FakeMeta("brand-a"))
        self.assertIn("scored when you approve", c["checks"]["diversity"]["why"])

    def test_good_card_passes(self):
        f = self.card()
        c = C.check_and_save(f, meta=FakeMeta("brand-a"))
        self.assertTrue(C.passed(c), {k: v for k, v in c["checks"].items() if not v["ok"]})
        self.assertEqual(c["checks"]["ad_set"]["why"], "adset_brand-a_avatar-four_pigment-memory")
        self.assertIn("body-scrub-cpk", c["checks"]["campaign"]["why"])

    def test_designed_thumbnails_pass_and_a_bad_one_is_named(self):
        """4 Oct 2026: the thumbnail check reused a name the rest of checks() needs and broke every card with thumbs."""
        f = self.card(n=1)
        c = C.load(f)
        pic(f / "t1.png", (1080, 1920))
        c["thumbs"] = {c["media"][0]: "t1.png"}
        C.save(f, c)
        out = C.checks(f, C.load(f), meta=FakeMeta("brand-a"))
        self.assertTrue(out["thumbs"]["ok"], out["thumbs"])
        self.assertTrue(out["name"]["ok"], out["name"])
        pic(f / "t1.png", (1080, 1080))
        self.assertFalse(C.checks(f, C.load(f), meta=FakeMeta("brand-a"))["thumbs"]["ok"])

    def test_wrong_ratio_and_no_headline(self):
        f = self.card(size=(1080, 1080), words={"primary": ["x"], "headlines": [], "descriptions": []})
        c = C.checks(f, C.load(f), meta=FakeMeta("brand-a"))
        self.assertFalse(c["ratio"]["ok"])
        self.assertFalse(c["words"]["ok"])

    def test_carousel_needs_two_slides(self):
        f = self.card(lane="carousel", fmt="carousel", n=1)
        self.assertFalse(C.checks(f, C.load(f), meta=FakeMeta("brand-a"))["media"]["ok"])

    def test_wrong_product_page(self):
        f = self.card(pages=[{"link_id": "link_brand-a_cpk_glow-face-scrub_landing"}])
        c = C.checks(f, C.load(f), meta=FakeMeta("brand-a"))
        self.assertFalse(c["product"]["ok"])

    def test_page_not_live(self):
        f = self.card()
        with mock.patch.object(C, "page_status", return_value=404):
            self.assertFalse(C.checks(f, C.load(f), meta=FakeMeta("brand-a"))["pages"]["ok"])

    def test_bad_name(self):
        f = self.card(name="brand-a_not-a-name")
        self.assertFalse(C.checks(f, C.load(f), meta=FakeMeta("brand-a"))["name"]["ok"])

    def test_page_cap_full(self):
        f = self.card()
        with mock.patch.object(C, "PAGE_AD_LIMIT", 3):
            self.assertFalse(C.checks(f, C.load(f), meta=FakeMeta("brand-a"))["page_cap"]["ok"])


class Moves(Base):
    def test_move_is_a_rename(self):
        f = self.card()
        new = C.move(f, "2-approved")
        self.assertFalse(f.exists())
        self.assertTrue((new / "card.json").is_file())
        self.assertEqual(C.where(new)["state"], "2-approved")
        self.assertEqual(C.where(new)["lane"], "image")

    def test_folder_of_refuses_escape(self):
        for bad in ("../x", "brand-a/1-check/image/..", "brand-a/9-x/image/a", "a/b"):
            with self.assertRaises(ValueError):
                C.folder_of(bad)


class Upload(Base):
    def test_refused_without_damons_approve(self):
        f = C.move(self.card(), "2-approved")
        with self.assertRaises(SystemExit) as e:
            U.upload_card(f, m=FakeMeta("brand-a"), log=lambda *_: None)
        self.assertIn("REFUSED", str(e.exception))

    def test_refused_outside_2_approved(self):
        f = self.card()
        c = C.load(f)
        c["approval"] = {"by": "the owner", "decision": "approve", "start": "PAUSED"}
        C.save(f, c)
        with self.assertRaises(SystemExit):
            U.upload_card(f, m=FakeMeta("brand-a"), log=lambda *_: None)

    def test_flexible_goes_live(self):
        m = FakeMeta("brand-a")
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
        self.assertEqual((line["ad_name"], line["lane"], line["brand"]), (NAME, "image", "brand-a"))
        self.assertEqual(C.load(new)["meta"][0]["ad_id"], line["ad_id"])

    def test_start_on(self):
        m = FakeMeta("brand-a")
        U.upload_card(self.approve(self.card(), "ACTIVE"), m=m, log=lambda *_: None)
        self.assertEqual([p for e, p in m.posts if e == "ads"][0]["status"], "ACTIVE")
        # 7 Oct 2026: "On" switches on the campaign and ad set this upload made
        made = {p["id"] for e, p in m.posts if e == "update" and p.get("status") == "ACTIVE"}
        made_here = {x["id"] for edge in ("campaigns", "adsets") for x in m.w[edge]}
        self.assertTrue(made and made <= made_here)

    def test_start_paused_switches_nothing_on(self):
        m = FakeMeta("brand-a")
        U.upload_card(self.approve(self.card(), "PAUSED"), m=m, log=lambda *_: None)
        self.assertFalse([p for e, p in m.posts if e == "update"])

    def test_approve_needs_on_or_paused(self):
        import approve as A
        code, out = A.approve("anything", None, "the owner")
        self.assertEqual(code, 400)

    def test_carousel_keeps_slide_order(self):
        m = FakeMeta("brand-a")
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
            U.upload_card(f, m=FakeMeta("brand-a", fail_on="ads"), log=lambda *_: None)
        self.assertTrue(f.exists())
        self.assertIn("Invalid parameter", C.load(f)["upload_error"]["error"])
        m = FakeMeta("brand-a")
        new, card = U.upload_card(f, m=m, log=lambda *_: None)
        self.assertEqual(C.where(new)["state"], "3-live")
        self.assertNotIn("upload_error", card)
        # the campaign and ad set made on the failed run were found by name, not made again
        self.assertEqual([e for e, _ in m.posts if e in ("campaigns", "adsets")], [])


class Server(Base):
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


if __name__ == "__main__":
    unittest.main()
