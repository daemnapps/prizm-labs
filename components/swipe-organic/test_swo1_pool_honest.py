#!/usr/bin/env python3
"""SI-159 (organic pool honest), I-131 (lost swipes ask) item 8: every feed
row carries its receipt, an added swipe is the kind it really is and never
claims a Drive copy that is not there, the formats page survives owned
footage, and a dry run writes nothing.

    /usr/bin/python3 components/swipe-organic/test_swo1_pool_honest.py

Offline: Apify, the Drive mirror, ffmpeg and the TikTok lookups are stubbed;
every write goes to a tempfile folder, never the checkout's records/.
"""
import argparse, io, json, sys, tempfile, types, unittest
import unittest.mock as M
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import feed, add, app, sounds  # noqa: E402


def tt(pid, author, tags, views=1000):
    """One TikTok item in the actor's own wire shape."""
    return {"id": pid, "webVideoUrl": f"https://www.tiktok.com/@{author}/video/{pid}",
            "authorMeta": {"name": author}, "text": "a post", "stats": {"playCount": views},
            "hashtags": [{"name": t} for t in tags]}


class FeedReceipts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.feed = self.home / "records/avatar-feeds/test--feed"
        self.feed.mkdir(parents=True)
        src = lambda kind, value, receipt: {"kind": kind, "platform": "tiktok",
                                            "value": value, "receipt": receipt}
        (self.feed / "sources.json").write_text(json.dumps({"sources": [
            src("hashtag", "glowup", "r-glowup"), src("hashtag", "skincare", "r-skincare"),
            src("account", "@maker", "r-maker"), src("search", "night routine", "r-night")]}))
        (self.feed / "items.json").write_text(json.dumps({"items": {
            "tiktok:1": {"platform": "tiktok", "id": "1", "source": "tt-hashtags", "receipt": ""}}}))

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, argv, fake_run):
        page = types.ModuleType("feedpage")
        page.build = lambda avatar: None
        with M.patch.object(feed, "HERE", self.home), M.patch.object(feed.A, "run", fake_run), \
                M.patch.dict(sys.modules, {"feedpage": page}), \
                M.patch.object(sys, "argv", ["feed.py", "--avatar", "test--feed"] + argv), \
                redirect_stdout(io.StringIO()):
            feed.main()
        return json.loads((self.feed / "items.json").read_text())["items"]

    def test_batched_pull_every_row_has_its_receipt(self):
        def fake_run(actor, payload, **kw):
            if "hashtags" in payload:
                return [tt("7300000000000000001", "a", ["GlowUp"]),
                        tt("7300000000000000002", "b", ["#SkinCare", "glowup"]),
                        tt("7300000000000000003", "c", ["unrelated"])]
            if "profiles" in payload:
                return [tt("7300000000000000004", "Maker", []),
                        tt("7300000000000000005", "stranger", [])]
            if "searchQueries" in payload:
                return [tt("7300000000000000006", "d", [])]
            return []
        items = self.run_main([], fake_run)
        new = {k: v for k, v in items.items() if k != "tiktok:1"}
        self.assertEqual(sorted(new), ["tiktok:7300000000000000001", "tiktok:7300000000000000002",
                                       "tiktok:7300000000000000004", "tiktok:7300000000000000006"])
        for rec in new.values():
            self.assertTrue(rec["receipt"], rec)
        self.assertEqual(new["tiktok:7300000000000000001"]["source"], "tt-hashtags=glowup")
        self.assertEqual(new["tiktok:7300000000000000001"]["receipt"], "r-glowup")
        self.assertEqual(new["tiktok:7300000000000000002"]["receipt"], "r-glowup")  # first batch tag present
        self.assertEqual(new["tiktok:7300000000000000004"]["source"], "tt-accounts=@maker")
        self.assertEqual(new["tiktok:7300000000000000004"]["receipt"], "r-maker")
        self.assertEqual(new["tiktok:7300000000000000006"]["source"], "tt-search=night routine")
        # the existing row is not re-pulled, re-sourced or marked by a sweep
        self.assertEqual(items["tiktok:1"], {"platform": "tiktok", "id": "1",
                                             "source": "tt-hashtags", "receipt": ""})
        sweep = json.loads((self.feed / "sweeps.jsonl").read_text().splitlines()[-1])
        self.assertEqual(sweep["by_source"]["tt-hashtags"]["no_receipt"], 1)
        self.assertEqual(sweep["by_source"]["tt-accounts"]["no_receipt"], 1)
        self.assertEqual(sweep["by_source"]["tt-hashtags"]["new"], 2)

    def test_search_batch_of_many_terms_is_not_guessed(self):
        self.assertIsNone(feed.origin("tt-search", ["a", "b"], {}))
        self.assertEqual(feed.origin("ig-hashtag=glowup", ["glowup"], {}), "glowup")

    def test_quarantine_marks_exactly_the_unreceipted(self):
        items = {"a": {"receipt": "r"}, "b": {"receipt": ""}, "c": {},
                 "d": {"receipt": "", "quarantine": "earlier"}}
        self.assertEqual(feed.quarantine_unreceipted(items), 2)
        self.assertEqual(items["a"], {"receipt": "r"})
        for k in ("b", "c"):
            self.assertEqual(items[k], {"receipt": "", "quarantine": "no receipt (SI-159 (organic pool honest))"})
        self.assertEqual(items["d"]["quarantine"], "earlier")
        self.assertEqual(feed.quarantine_unreceipted(items), 0)

    def test_quarantine_flag_pulls_nothing(self):
        def no_run(*a, **k):
            raise AssertionError("the quarantine flag must not call Apify")
        items = self.run_main(["--quarantine-unreceipted"], no_run)
        self.assertEqual(items["tiktok:1"]["quarantine"], "no receipt (SI-159 (organic pool honest))")
        self.assertFalse((self.feed / "sweeps.jsonl").exists())


class AddHonest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.lib = self.home / "lib"

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, src, mirrored):
        def never(*a, **k):
            raise AssertionError("an image is never stripped or probed")
        with M.patch.object(add, "HERE", self.home), M.patch.object(add, "LIB", self.lib), \
                M.patch.object(add, "mirror", lambda code: mirrored), \
                M.patch.object(add, "tiktok_facts", lambda code: {}), \
                M.patch.object(add, "strip_of", never if src.suffix != ".mp4" else (lambda v, o: None)), \
                M.patch.object(add, "probe", never if src.suffix != ".mp4" else (lambda v: 12)), \
                redirect_stdout(io.StringIO()):
            return add.add([str(src)], [], "test-pool", "test-brand", "organic", "creator")

    def test_image_is_an_image_and_keeps_its_suffix(self):
        src = self.home / "swipe-one.jpg"
        src.write_bytes(b"jpg")
        row = self.add(src, True)[0]
        self.assertEqual(row["kind"], "image")
        self.assertEqual(row["seconds"], 0)
        self.assertTrue((self.lib / "swipe-one" / "image.jpg").is_file())
        self.assertFalse((self.lib / "swipe-one" / "video.mp4").exists())
        self.assertTrue(row["drive"].endswith("/swipe-one/image.jpg"), row["drive"])
        self.assertNotIn("mirror", row)

    def test_mirror_false_files_pending_and_no_drive(self):
        src = self.home / "clip-two.mp4"
        src.write_bytes(b"mp4")
        row = self.add(src, False)[0]
        self.assertEqual(row["kind"], "video")
        self.assertTrue((self.lib / "clip-two" / "video.mp4").is_file())
        self.assertEqual(row["mirror"], "pending")
        self.assertNotIn("drive", row)
        filed = json.loads((self.home / "test-pool" / "posts.json").read_text())["posts"][0]
        self.assertEqual(filed["mirror"], "pending")
        self.assertNotIn("drive", filed)


class SoundsDryRun(unittest.TestCase):
    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            drive, local, pool = t / "drive", t / "local", t / "pool.json"
            drive.mkdir()
            (drive / "snd-1.mp3").write_bytes(b"mp3")       # on the Drive, no local copy yet
            pool.write_text(json.dumps({"rows": {
                "snd-1": {"id": "snd-1", "file": "x/snd-1.mp3"},
                "snd-2": {"id": "snd-2", "audio_url": "https://example.invalid/a.mp3"}}}))
            before = sorted(str(p) for p in t.rglob("*"))
            with M.patch.object(sounds, "DRIVE", drive), M.patch.object(sounds, "LOCAL", local), \
                    M.patch.object(sounds, "POOL", pool), M.patch.object(sounds, "tier", lambda: "FREE"), \
                    redirect_stdout(io.StringIO()) as out:
                sounds.audio(argparse.Namespace(dry_run=True, fallback=False))
            self.assertIn("would save 1", out.getvalue())
            self.assertEqual(sorted(str(p) for p in t.rglob("*")), before)
            self.assertFalse(local.exists())


class FormatsPage(unittest.TestCase):
    def test_format_with_no_views_renders(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            fmt = {"id": "fmt-own", "name": "Owned footage", "mechanic": "m", "why_it_works": "w",
                   "beats": ["b1"], "higgsfield": {"image": "i", "motion": "mo"},
                   "evidence": [{"code": "own-clip", "note": "our own footage"}]}
            (t / "formats.json").write_text(json.dumps({"formats": [fmt]}))
            (t / "saves").mkdir()
            (t / "saves" / "catalog.json").write_text(json.dumps({"rows": []}))
            with M.patch.object(app, "HERE", t), M.patch.object(app, "SAVES", t / "saves"), \
                    M.patch.object(app, "VID", t / "none"):
                page = app.format_page("fmt-own")
                fmt["evidence"][0]["views"] = 12345
                (t / "formats.json").write_text(json.dumps({"formats": [fmt]}))
                proved = app.format_page("fmt-own")
        self.assertIn("Owned footage", page)
        self.assertNotIn("views proved it", page)
        self.assertIn("12,345 views proved it", proved)


if __name__ == "__main__":
    unittest.main()
