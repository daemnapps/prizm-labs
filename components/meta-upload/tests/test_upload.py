"""The uploader's promises: words are cut, never written; nothing reaches
Meta without an approval; and the real 260923a hand-off plans cleanly."""
import tempfile, json, sys, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import drop, upload

HANDOFF = HERE / "tests/fixtures/handoff"     # a trimmed, brand-neutral hand-off (SI-126); see its README.md

ROW = """Same spot, five years running.

See how it works 👉

*97 words.*

**One line each.** writer's notes, never copy.

**HEADLINES**

1. **It comes right back** — 4 words
2. **Not stubborn. It's remembered.** — 4 words

**DESCRIPTIONS**

1. **Turmeric body scrub** — 3 words

---
"""


class Words(unittest.TestCase):
    def test_body_stops_at_word_count(self):
        self.assertEqual(drop.body_of(ROW), "Same spot, five years running.\n\nSee how it works 👉")

    def test_headlines_and_descriptions(self):
        self.assertEqual(drop.listed(ROW, "HEADLINES"), ["It comes right back", "Not stubborn. It's remembered."])
        self.assertEqual(drop.listed(ROW, "DESCRIPTIONS"), ["Turmeric body scrub"])

    def test_no_list_is_empty_not_invented(self):
        self.assertEqual(drop.listed("just a body", "HEADLINES"), [])


class Gate(unittest.TestCase):
    def test_refuses_without_first_go(self):
        with mock.patch.object(upload, "approvals", return_value={"first_go": None, "approved": []}):
            with self.assertRaises(SystemExit) as e:
                upload.approval_for("anything")
            self.assertIn("first go", str(e.exception))

    def test_refuses_unlisted_handoff(self):
        with mock.patch.object(upload, "approvals", return_value={"first_go": {"said": "go"}, "approved": []}):
            with self.assertRaises(SystemExit):
                upload.approval_for("not-approved")


class Payload(unittest.TestCase):
    def test_flexible_first_asset_matches_and_sits_on_the_ad(self):
        b = mock.Mock(page_id="P", instagram_id="IG")
        ad = {"meta_ad_name": "n", "kind": "image", "media": ["a.png", "b.png"], "cta": "SHOP_NOW", "url": "https://x/p",
              "bodies": ["B1", "B2"], "titles": ["T1"], "descriptions": []}
        body = upload.flexible_ad(ad, b, {"media": {"a.png": "H1", "b.png": "H2"}}, None)
        story = body["creative"]["object_story_spec"]
        group = body["creative_asset_groups_spec"]["groups"][0]
        self.assertEqual(story["link_data"]["image_hash"], group["images"][0]["hash"])
        self.assertNotIn("creative_asset_groups_spec", body["creative"])
        self.assertNotIn("asset_feed_spec", body["creative"])
        self.assertEqual(story["instagram_user_id"], "IG")
        self.assertEqual([t["text_type"] for t in group["texts"]], ["primary_text", "primary_text", "headline"])

    def test_video_flexible_ad_keeps_its_descriptions(self):
        """4 Oct 2026: the first video batch reached Meta without its two descriptions."""
        b = mock.Mock(page_id="P", instagram_id=None)
        ad = {"meta_ad_name": "n", "kind": "video", "media": ["a.mp4"], "cta": "SHOP_NOW", "url": "https://x/p",
              "bodies": ["B1"], "titles": ["T1"], "descriptions": ["D1", "D2"]}
        body = upload.flexible_ad(ad, b, {"media": {"a.mp4": "V1", "V1#thumb": "H1"}}, None)
        texts = body["creative_asset_groups_spec"]["groups"][0]["texts"]
        self.assertEqual([t["text"] for t in texts if t["text_type"] == "description"], ["D1", "D2"])


class CardNames(unittest.TestCase):
    def test_card_ads_are_named_funnel_dash_page(self):
        """One place makes the page part (page_pick.meta_page): the card uploader
        names each ad `<unit>_<funnel id>-<page>`, as the live ads read."""
        with tempfile.TemporaryDirectory() as t:
            unit = "brand-a_glow-body-scrub_brief-0137_batch-2026-09-30-a"
            card = {"brand": "brand-a", "ad_name": unit, "product": "glow-body-scrub", "brief_id": "brief-0137",
                    "avatar": "avatar-four", "angle": "honest-timeline", "media": [], "words": {},
                    "pages": [{"link_id": "link_brand-a_cpk_quiz", "url": "https://recipe.brand-a.example/brand-a-scrub-cpk/quiz/"},
                              {"link_id": "link_brand-a_cpk_landing", "url": "https://recipe.brand-a.example/brand-a-scrub-cpk/landing.html"}]}
            p = upload.card_plan(Path(t), card)
            names = sorted(r["meta_ad_name"] for r in p["ads"] + p["held"])
            self.assertEqual(names, [f"{unit}_body-scrub-cpk-offer", f"{unit}_body-scrub-cpk-quiz"])


class RealHandoff(unittest.TestCase):
    """The fixture hand-off, planned inside a temp workspace: the hand-off
    folder, its drop's copy.csv under runs/, the brand's files under brands/,
    and a 1×1 PNG per asset written here (no committed binaries)."""
    PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="

    def setUp(self):
        import base64, shutil, brand as B, build
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        ws = Path(t.name).resolve()
        man = json.loads((HANDOFF / "manifest.json").read_text())
        self.folder = ws / "handoff" / man["name"]
        shutil.copytree(HANDOFF / "assets", self.folder / "assets")
        shutil.copytree(HANDOFF / "references", self.folder / "references")
        shutil.copy(HANDOFF / "manifest.json", self.folder / "manifest.json")
        for f in json.loads((HANDOFF / "assets/index.json").read_text())["files"]:
            (self.folder / f).parent.mkdir(parents=True, exist_ok=True)
            (self.folder / f).write_bytes(base64.b64decode(self.PNG))
        drop_dir = ws / "runs/image-teardown" / man["brand"] / "261001a" / "deliverable"
        drop_dir.mkdir(parents=True)
        shutil.copy(HANDOFF / "drop/copy.csv", drop_dir / "copy.csv")
        shutil.copytree(HANDOFF / "brand", ws / "brands" / man["brand"])
        for mod, attr, v in ((B, "BRANDS", ws / "brands"), (upload, "REPO", ws), (build, "REPO", ws),
                             (drop, "REPO", ws), (drop, "DRIVE", ws / "no-drive"), (upload.N, "WS", ws)):
            p = mock.patch.object(mod, attr, v)
            p.start()
            self.addCleanup(p.stop)

    def test_plan_names_and_pages(self):
        p = upload.plan(self.folder)
        self.assertEqual(len(p["ads"]), 2)
        for ad in p["ads"]:
            self.assertTrue(ad["meta_ad_name"].startswith(ad["unit"] + "_"))
            # the build host is swapped for the brand domain the funnel registry names
            self.assertTrue(ad["url"].startswith("https://shop.zzbrand.example/"))
            self.assertTrue(ad["titles"] and ad["bodies"])
            self.assertEqual(ad["ad_set"], "adset_zzbrand_night-worker_slow-reset")
            self.assertTrue(ad["campaign"])
        # a glow-balm ad is never pointed at the lip-balm page
        self.assertFalse([a for a in p["ads"] if "lip-balm" in a["link_id"]])
        self.assertEqual([h["why"] for h in p["held"] if "lip-balm" in h["link_id"]],
                         [["the ad sells glowbalm but the page lip-offer sells lip-balm"]] * 2)



class Thumbnails(unittest.TestCase):
    def test_a_designed_thumbnail_is_uploaded_else_metas_frame(self):
        import tempfile, upload as U
        from fake_meta import FakeMeta
        with tempfile.TemporaryDirectory() as d:
            t = Path(d) / "a_thumb.jpg"; t.write_bytes(b"x")
            m = FakeMeta("brand-a") if "brand" in FakeMeta.__init__.__code__.co_varnames else FakeMeta()
            self.assertEqual(U.thumb_for(m, {"thumbs": {"v.mp4": str(t)}}, "v.mp4", "vid-1"), "hash-a_thumb.jpg")
            self.assertEqual(U.thumb_for(m, {"thumbs": {}}, "w.mp4", "vid-2"), "thumb-vid-2")


if __name__ == "__main__":
    unittest.main()
