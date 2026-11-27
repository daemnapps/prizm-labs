"""creator_picks.py — the one door to creator briefs. Runs in a temp workspace;
never touches the live queue under runs/ and never downloads.
    python3 -m unittest test_creator_picks"""
import io, json, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import creator_picks as CP

FEED = {"id": "tb--core-a", "brand": "tb", "core": "core-a", "sub": None, "title": "A"}


def card(key, views, kind="skit", lane="entertainment", age=10, platform="tiktok", what=None):
    return {"key": key, "platform": platform, "url": f"https://www.tiktok.com/@x/video/{key.split(':')[-1]}",
            "author": "x", "caption": "cap", "cover": None, "views": views, "sent": None, "punch": None,
            "age": age, "lane": lane, "kind": kind, "what": what or f"a {kind}", "format": None, "keep": True}


CARDS = {"tb--core-a": [card("tiktok:1", 9_000_000)]}


def ad(num, days, spend, dup=1, video=True, desc="I tried everything"):
    return {"id": f"facebook_{num}", "source": "trendtrack", "title": "", "description": desc,
            "video_url": "https://m/v" if video else "", "image_url": "https://m/t", "landing_page": None,
            "meta_group_ads_count": dup, "meta_page_name": "Rival", "meta_status": "active",
            "days_total": days, "first_seen": None, "reach": 1, "estimated_spend": spend}


SWEEP = {"source": "trendtrack", "domain": "rival.co",
         "items": [ad(1, 120, 50_000, 18), ad(2, 10, 90_000), ad(3, 200, 30_000, 26),
                   ad(4, 300, 99_000, video=False), ad(5, 60, 40_000, desc="story b-roll of a day")]}
OTHER = {"source": "trendtrack", "domain": "elsewhere.co", "items": [ad(9, 400, 999_000)]}
SHOP = {"brand": "tb", "posts": [
    {"id": "11", "creator": "a", "views": 26_000_000, "url": "https://www.tiktok.com/@a/video/11",
     "caption": "c", "structure_read": "nurse explains", "product": "face", "engagement": 1},
    {"id": "12", "creator": "b", "views": 3_000_000, "url": "https://www.tiktok.com/@b/video/12",
     "caption": "c", "structure_read": "car confessional", "product": "body", "sales": 4000},
    {"id": "13", "creator": "c", "views": 100_000, "url": "https://www.tiktok.com/@c/video/13",
     "caption": "c", "structure_read": "unboxing", "product": "body"}]}


class Door(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        ws = Path(self.tmp.name)
        (ws / "brands" / "tb").mkdir(parents=True)
        lib = ws / "components" / "elements" / "library"
        lib.mkdir(parents=True)
        (lib / "format.video.json").write_text(json.dumps({"rows": [{"id": "meme", "name": "Meme", "aliases": []}]}))
        here = ws / "here"
        (here / "records" / "desk").mkdir(parents=True)
        (here / "records" / "desk" / "products.json").write_text(json.dumps({"tb": {"_default": "prod"}}))
        (here / "records" / "desk" / "proven-sources.json").write_text(json.dumps(
            {"tb": {"trendtrack_domains": ["rival.co"], "tiktok_shop_products": {"face": "face-prod"}}}))
        for name, sw in (("rival-1", SWEEP), ("other-1", OTHER)):
            d = ws / "runs" / "trendtrack" / "market" / name
            d.mkdir(parents=True)
            (d / "ALL.json").write_text(json.dumps(sw))
        (here / "tiktok-shop").mkdir()
        (here / "tiktok-shop" / "posts.json").write_text(json.dumps(SHOP))
        (here / "tiktok-shop" / "elsewhere.json").write_text(json.dumps(dict(SHOP, brand="zz")))
        self.ws, self.here = ws, here

        def fake_download(label, url):
            v = CP.media_dir(label) / "video.mp4"
            v.parent.mkdir(parents=True, exist_ok=True)
            v.write_bytes(b"x")
            return v
        CP._FORMATS = None
        self.patches = [mock.patch.object(CP, "WS", ws), mock.patch.object(CP.D, "HERE", here),
                        mock.patch.object(CP, "PROVEN_FILE", here / "records" / "desk" / "proven-sources.json"),
                        mock.patch.object(CP.D, "feeds", lambda: [FEED]),
                        mock.patch.object(CP.D, "cards", lambda f: CARDS.get(f, [])),
                        mock.patch.object(CP, "download", fake_download)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        CP._FORMATS = None
        self.tmp.cleanup()

    def run_(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            CP.main(list(argv))
        return out.getvalue()

    def queue(self):
        return json.loads(CP.queue_file("tb").read_text())["items"]

    def items_(self):
        return [r["source"]["item"] for r in self.queue()]

    def test_pick_proven_only_ranked_on_proof_sources_take_turns(self):
        self.run_("pick", "--brand", "tb")
        # ads rank on days running first (200, 120, 60), shop videos on sales then views
        self.assertEqual(self.items_(), ["trendtrack:facebook_3", "tiktok-shop:12", "trendtrack:facebook_1",
                                         "tiktok-shop:11", "trendtrack:facebook_5"])
        keys = self.items_()
        self.assertNotIn("trendtrack:facebook_2", keys)   # ran 10 days: not proven
        self.assertNotIn("trendtrack:facebook_4", keys)   # not a video
        self.assertNotIn("trendtrack:facebook_9", keys)   # another category's sweep
        self.assertNotIn("tiktok-shop:13", keys)          # under the floor, no sales: never padded
        self.assertNotIn("tiktok:1", keys)                # organic viral posts are not a source

    def test_item_carries_source_proof_and_brief_writing_fields(self):
        self.run_("pick", "--brand", "tb")
        q = {r["source"]["item"]: r for r in self.queue()}
        r = q["trendtrack:facebook_1"]
        for k in ("swipe_id", "brand", "source_url", "video", "views", "creator_handle", "product",
                  "format", "avatar", "picked", "state", "status", "brief", "pick_source", "proof"):
            self.assertIn(k, r)
        self.assertEqual((r["pick_source"], r["proof"]["days_running"], r["proof"]["estimated_spend"]),
                         ("trendtrack", 120, 50_000))
        self.assertEqual(r["source_url"], "https://www.facebook.com/ads/library/?id=1")
        self.assertTrue(r["video"].startswith("here/records/desk/media/"))   # downloaded, repo-relative
        self.assertEqual((r["state"], r["status"], r["product"]), ("picked", "draft", "prod"))
        s = q["tiktok-shop:11"]
        self.assertEqual((s["pick_source"], s["proof"]["views"], s["product"]), ("tiktok-shop", 26_000_000, "face-prod"))
        self.assertEqual(q["tiktok-shop:12"]["proof"]["sales"], 4000)

    def test_pick_one_source(self):
        self.run_("pick", "--brand", "tb", "--sources", "tiktok-shop")
        self.assertEqual(self.items_(), ["tiktok-shop:12", "tiktok-shop:11"])

    def test_pick_skips_what_is_already_queued(self):
        self.run_("pick", "--brand", "tb", "--max", "2")
        self.run_("pick", "--brand", "tb", "--week", "2026-W47", "--max", "2")
        self.assertEqual(len(self.items_()), len(set(self.items_())))
        self.assertEqual(len(self.items_()), 4)

    def test_dropped_pick_is_never_picked_again(self):
        self.run_("pick", "--brand", "tb", "--max", "1")
        sid = self.queue()[0]["swipe_id"]
        self.run_("mark", "--brand", "tb", "--label", sid, "--state", "dropped")
        self.run_("pick", "--brand", "tb", "--max", "1")
        self.assertEqual([r["state"] for r in self.queue()], ["dropped", "picked"])

    def test_winners_slot_front_and_back(self):
        f = CP.slot_file("tb")
        f.parent.mkdir(parents=True)
        f.write_text(json.dumps({"basis": "candidates", "status": "draft",
                                 "formats": [{"format": "story b-roll", "videos": 2, "purchases": 5}],
                                 "avoid": [{"format": "nurse explains", "videos": 3, "spend": 90, "purchases": 0}]}))
        self.run_("pick", "--brand", "tb")
        q = self.queue()
        self.assertEqual(q[0]["source"]["item"], "trendtrack:facebook_5")     # selling format first
        self.assertEqual(q[0]["winning_format"]["format"], "story b-roll")
        shop = [r for r in q if r["pick_source"] == "tiktok-shop"]
        self.assertEqual(shop[-1]["avoid_format"]["format"], "nurse explains")  # avoided format last

    def test_catch_all_format_lifts_nothing(self):
        f = CP.slot_file("tb")
        f.parent.mkdir(parents=True)
        f.write_text(json.dumps({"basis": "candidates", "formats": [{"format": "other", "purchases": 9}]}))
        self.run_("pick", "--brand", "tb")
        self.assertEqual(self.queue()[0]["source"]["item"], "trendtrack:facebook_3")
        self.assertTrue(all(r["winning_format"] is None for r in self.queue()))

    def test_default_strategist_waits_for_owner_yes(self):
        rf = self.ws / "strategist.json"
        rf.write_text(json.dumps({"filled_by": "default", "command": None, "owner_yes": True}))
        with mock.patch.object(CP, "ROLE_FILE", rf):
            self.run_("pick", "--brand", "tb")
        r = self.queue()[0]
        self.assertEqual((r["status"], r["picker"]), ("draft", "creative strategist · default"))
        self.run_("mark", "--brand", "tb", "--label", r["swipe_id"], "--state", "picked", "--approve")
        self.assertEqual(self.queue()[0]["status"], "approved")

    def test_role_filled_by_a_system_without_changing_the_door(self):
        script = self.ws / "picker.py"
        script.write_text('import json; print(json.dumps([{"item": "tiktok-shop:11", "why": "the plan"}]))')
        rf = self.ws / "strategist.json"
        rf.write_text(json.dumps({"filled_by": "test picker", "command": "picker.py", "owner_yes": False}))
        with mock.patch.object(CP, "ROLE_FILE", rf):
            self.run_("pick", "--brand", "tb")
        q = self.queue()
        self.assertEqual(self.items_(), ["tiktok-shop:11"])
        self.assertEqual((q[0]["why"], q[0]["status"], q[0]["picker"]),
                         ("the plan", "approved", "creative strategist · test picker"))

    def test_winners_slot_none_yet_is_ignored(self):
        f = CP.slot_file("tb")
        f.parent.mkdir(parents=True)
        f.write_text(json.dumps({"basis": "none yet", "formats": [{"format": "story b-roll"}]}))
        self.run_("pick", "--brand", "tb")
        self.assertEqual(self.queue()[0]["source"]["item"], "trendtrack:facebook_3")

    def test_paid_pull_results_one_ad_per_advertiser_and_shop_tiktoks(self):
        def row(i, days, page, spend=10, kind="video"):
            return {"id": f"facebook_{i}", "daysRunning": days, "status": "active", "firstSeenAt": None,
                    "media": {"type": kind, "thumbnailUrl": "https://m/t"},
                    "advertiser": {"name": page}, "content": {"body": "b", "transcript": "said"},
                    "metrics": {"estimatedSpend": spend, "duplicates": 2, "reach": 5}}
        tok = {"id": "tiktok_77", "tiktokId": "77", "type": "ad", "daysRunning": 9,
               "media": {"type": "video", "thumbnailUrl": "https://m/t"},
               "content": {"description": "derm pops it"}, "profile": {"handle": "doc", "name": "Doc"},
               "metrics": {"views": 82_000_000, "likes": 5}, "shop": {"domain": "doc.shop"}}
        pulls = {"creator-tb-ads": [row(21, 400, "Alpha"), row(22, 900, "Alpha"), row(23, 80, "Beta"),
                                    row(24, 10, "Gamma"), row(25, 500, "Delta", kind="image")],
                 "creator-tb-tok": [tok, dict(tok, id="tiktok_78", tiktokId="78", type="organic",
                                              metrics={"views": 99_000_000}),
                                    dict(tok, id="tiktok_79", tiktokId="79", metrics={"views": 1_000})],
                 "creator-zz-ads": [row(31, 999, "Other brand")]}
        for name, rows in pulls.items():
            d = self.ws / "runs" / "trendtrack" / "market" / name
            d.mkdir(parents=True)
            (d / "result.json").write_text(json.dumps({"data": rows}))
        pf = self.here / "records" / "desk" / "proven-sources.json"
        pf.write_text(json.dumps({"tb": {"trendtrack_domains": [], "trendtrack_pulls": ["creator-tb-"]}}))
        c = {x["item"]: x for x in CP.trendtrack_candidates("tb", 30)}
        self.assertEqual(sorted(c), ["trendtrack:facebook_22", "trendtrack:facebook_23", "trendtrack:tiktok_77"])
        self.assertEqual(c["trendtrack:facebook_22"]["proof"]["days_running"], 900)   # Alpha's longest-running ad
        self.assertEqual(c["trendtrack:facebook_22"]["url"], "https://www.facebook.com/ads/library/?id=22")
        self.assertEqual(c["trendtrack:facebook_22"]["what"], "said")                  # the transcript
        self.assertEqual(c["trendtrack:tiktok_77"]["url"], "https://www.tiktok.com/@doc/video/77")
        self.assertEqual(c["trendtrack:tiktok_77"]["proof"]["shop"], "doc.shop")
        # organic TikTok (78) never; same creator's smaller ad (79) loses to 77
        self.run_("pick", "--brand", "tb", "--sources", "trendtrack")
        self.assertEqual(self.items_(), ["trendtrack:facebook_22", "trendtrack:tiktok_77",
                                         "trendtrack:facebook_23"])   # ads and TikToks take turns

    def test_fetch_falls_back_to_the_sources_own_copy(self):
        got = []

        def direct(label, url):
            got.append(url)
            v = CP.media_dir(label) / "video.mp4"
            v.parent.mkdir(parents=True, exist_ok=True)
            v.write_bytes(b"x")
            return v
        with mock.patch.object(CP, "download", lambda label, url: None), \
                mock.patch.object(CP, "download_direct", direct):
            self.run_("pick", "--brand", "tb", "--sources", "trendtrack", "--max", "1")
        r = self.queue()[0]
        self.assertEqual(got, ["https://m/v"])                       # the sweep's video link
        self.assertTrue(r["video"].endswith("video.mp4"))
        self.assertNotIn("note", r)

    def test_hand_pick_from_my_feeds_is_tagged(self):
        self.run_("add", "--brand", "tb", "--feed", "tb--core-a", "--item", "tiktok:1")
        self.assertEqual(self.queue()[0]["pick_source"], "my-feeds")

    def test_add_then_mark_through_to_briefed(self):
        v = self.ws / "clips" / "a.mp4"
        v.parent.mkdir()
        v.write_bytes(b"x")
        self.run_("add", "--brand", "tb", "--video", str(v), "--label", "GEN-a", "--by", "tsv")
        self.run_("add", "--brand", "tb", "--video", str(v), "--label", "GEN-a", "--by", "tsv")
        rows = self.queue()
        self.assertEqual(len(rows), 1)                                 # no doubles
        self.assertEqual(rows[0]["video"], "clips/a.mp4")              # repo-relative, never a machine path
        self.run_("mark", "--brand", "tb", "--label", "GEN-a", "--state", "torn", "--run", str(self.ws / "runs" / "x"))
        self.run_("mark", "--brand", "tb", "--label", "GEN-a", "--state", "briefed", "--brief", "runs/y/brief.md")
        r = self.queue()[0]
        self.assertEqual((r["state"], r["teardown"]["state"], r["teardown"]["run"], r["brief"]),
                         ("briefed", "torn", "runs/x", "runs/y/brief.md"))

    def test_mark_picks_up_a_video_a_teardown_downloaded(self):
        self.run_("add", "--brand", "tb", "--url", "https://www.tiktok.com/@x/video/9", "--label", "lab-9")
        v = CP.media_dir("lab-9") / "video.mp4"
        v.parent.mkdir(parents=True)
        v.write_bytes(b"x")
        self.run_("mark", "--brand", "tb", "--label", "lab-9", "--state", "tearing")
        self.assertEqual(self.queue()[0]["video"], "here/records/desk/media/lab-9/video.mp4")

    def test_drop_deprecates(self):
        self.run_("add", "--brand", "tb", "--url", "https://www.tiktok.com/@x/video/9")
        label = self.queue()[0]["swipe_id"]
        self.run_("mark", "--brand", "tb", "--label", label, "--state", "dropped")
        self.assertEqual(self.queue()[0]["status"], "deprecated")

    def test_machine_path_outside_workspace_refused(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f, self.assertRaises(SystemExit):
            self.run_("add", "--brand", "tb", "--video", f.name)

    def test_unknown_brand_refused(self):
        with self.assertRaises(SystemExit):
            self.run_("list", "--brand", "nope")


if __name__ == "__main__":
    unittest.main()
