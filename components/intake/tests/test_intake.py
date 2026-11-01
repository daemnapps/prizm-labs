#!/usr/bin/env python3
"""intake's tests — stdlib unittest, no network, no model.

    python3 components/intake/tests/test_intake.py

Every test runs against a TINY FAKE WORKSPACE in a temp folder (fake brands,
fake pools, a fake element library), reached through `AI_WORKSPACE`. The real
pools, the real `runs/` and the real `brands/` are never read or written here.
"""
import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"
if str(TOOLS) not in sys.path:
    sys.path.append(str(TOOLS))                             # appended, never inserted at 0

import paths as P                                           # noqa: E402
import pools                                                # noqa: E402
import run as R                                             # noqa: E402


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def lib_list(ids):
    return {"rows": [{"id": i, "name": i, "status": "draft", "approved": False} for i in ids]}


def build(ws, paid=True, organic=True):
    """alpha + beta are made-up brands; rivalco is a made-up advertiser."""
    (ws / "components").mkdir(parents=True)
    put(ws / "brands/alpha/meta/account.json", {"account_id": "111"})
    (ws / "brands/beta").mkdir(parents=True)
    lib = ws / "components/elements/library"
    put(lib / "format.video.json", lib_list(["song-ad", "meme"]))
    put(lib / "format.image.json", lib_list(["stickynote"]))
    put(lib / "format.carousel.json", lib_list([]))
    put(lib / "format.copy.json", lib_list(["short-form"]))
    put(lib / "format.page.json", lib_list(["listicle", "quiz"]))
    put(lib / "format.email.json", lib_list(["launch"]))
    put(lib / "structure.video.json", lib_list(["character-sketch"]))
    if paid:
        pool = ws / "components/swipe-paid"
        put(pool / "rivalco/blocks.json", {"brand": "rivalco", "blocks": [{
            "nn": "01", "slug": "big-claim", "headline": "A big claim", "primary_text": "words words",
            "landing_page": "https://rival.example/p",
            "media": {
                "1001": {"video": "https://cdn.example/1001.mp4", "image": "https://cdn.example/1001.jpg",
                         "fields": {"media": "video", "format": "unclassified"}},
                "1002": {"video": "", "image": "https://cdn.example/1002.jpg",
                         "fields": {"media": "static", "format": "stickynote"}},
                "1003": {"video": "https://cdn.example/1003.mp4", "image": ""},
                "1004": {"video": "https://cdn.example/1004.mp4", "image": "",
                         "fields": {"media": "video", "format": "unclassified"}}}}]})
        put(pool / "rivalco/pages.json", {"pages-ten-reasons": {"type": "listicle", "url": "https://rival.example/10"},
                                          "home": {"type": "unknown", "url": "https://rival.example/"}})
        put(pool / "judgements.json", {"swipe:paid:rivalco:1004": {"fields": {"format": "animatedstory"}, "verdict": "swipe"}})
        put(pool / "own/111/ads.json", {"ads": [{"id": "a1", "name": "our video", "media": "video"},
                                                 {"id": "a2", "name": "our static", "media": "static"}]})
        put(pool / "own/live/ads.json", {"ads": [{"id": "a1", "name": "our video", "media": "video"},
                                                  {"id": "a9", "name": "nobody's", "media": "video"}]})
    if organic:
        pool = ws / "components/swipe-organic"
        put(pool / "records/avatar-feeds/alpha--some-sub/items.json", {
            "tiktok:77": {"platform": "tiktok", "id": "77", "url": "https://www.tiktok.com/@x/video/77", "kind": "video",
                          "caption": "a post", "sift": {"format": "character-sketch"}},
            "tiktok:78": {"platform": "tiktok", "id": "78", "url": "https://www.tiktok.com/@x/video/78", "kind": "video",
                          "caption": "another", "sift": {"format": "unread"}},
            "tiktok:79": {"platform": "tiktok", "id": "79", "url": "https://www.tiktok.com/@x/video/79", "kind": "video",
                          "sift": {"format": "new:made-up-structure"}}})
        put(pool / "records/avatar-feeds/someone--saves/items.json", {
            "instagram:AAA": {"platform": "instagram", "id": "AAA", "url": "https://www.instagram.com/p/AAA/", "kind": "save",
                              "brand_fit": "beta"},
            "instagram:BBB": {"platform": "instagram", "id": "BBB", "url": "https://www.instagram.com/p/BBB/", "kind": "save",
                              "brand_fit": "general"},
            "instagram:CCC": {"platform": "instagram", "id": "CCC", "url": "https://www.instagram.com/p/CCC/", "kind": "image"}})
        put(pool / "records/swipe-videos/BBB/format.json", {"code": "BBB", "format_id": "character-sketch"})
        put(pool / "slides-guy/posts.json", {"creator": "slides-guy", "posts": [
            {"id": "900", "slides": 9, "url": "https://www.tiktok.com/@s/video/900", "file": "01_s-900.md"}]})


def digest(root):
    h = hashlib.sha256()
    for f in sorted(p for p in Path(root).rglob("*") if p.is_file()):
        h.update(str(f.relative_to(root)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


class Case(unittest.TestCase):
    paid = organic = True

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name) / "ws"
        build(self.ws, self.paid, self.organic)
        self.old = os.environ.get("AI_WORKSPACE")
        os.environ["AI_WORKSPACE"] = str(self.ws)

    def tearDown(self):
        if self.old is None:
            os.environ.pop("AI_WORKSPACE", None)
        else:
            os.environ["AI_WORKSPACE"] = self.old
        self.tmp.cleanup()

    def go(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            rc = R.main(list(argv))
        return rc, out.getvalue()

    def index(self, brand, label):
        d = self.ws / "runs/intake" / brand / label
        return d, [json.loads(l) for l in (d / "swipes.jsonl").read_text().splitlines()]


class TestWorkspace(Case):
    def test_the_fake_workspace_is_the_one_in_use(self):
        self.assertEqual(P.workspace(), self.ws)
        self.assertEqual(P.brands(), ["alpha", "beta"])

    def test_tools_folder_is_never_first_on_the_path(self):
        self.assertNotEqual(sys.path[0], str(TOOLS))


class TestRecords(Case):
    def by_id(self):
        return {r["id"]: r for r in pools.read_all()}

    def test_one_shape_for_every_swipe(self):
        for r in pools.read_all():
            self.assertEqual(set(r), {"id", "source", "owner", "kind", "route", "swiped_for", "asset",
                                      "format", "structure", "title", "pool"})
            self.assertEqual(set(r["asset"]), {"url", "file", "drive", "thumb"})
            self.assertIn(r["source"], ("paid", "organic", "own"))

    def test_kind_comes_from_the_asset_and_picks_the_teardown(self):
        r = self.by_id()
        self.assertEqual((r["swipe:paid:rivalco:1001"]["kind"], r["swipe:paid:rivalco:1001"]["route"]), ("video", "video-teardown"))
        self.assertEqual((r["swipe:paid:rivalco:1002"]["kind"], r["swipe:paid:rivalco:1002"]["route"]), ("image", "image-teardown"))
        self.assertEqual(r["swipe:paid:rivalco:block-big-claim"]["route"], "copy-teardown")
        self.assertEqual(r["swipe:paid:rivalco:page-home"]["route"], "page-teardown")
        self.assertEqual((r["swipe:organic:slidesguy:900"]["kind"], r["swipe:organic:slidesguy:900"]["route"]), ("carousel", "image-teardown"))
        self.assertEqual(r["swipe:organic:alphasomesub:tiktok-77"]["route"], "video-teardown")

    def test_a_link_that_does_not_say_is_unknown_not_guessed(self):
        r = self.by_id()["swipe:organic:someonesaves:instagram-AAA"]
        self.assertEqual((r["kind"], r["route"]), ("unknown", "unrouted"))

    def test_a_pulled_post_is_a_video_and_carries_its_structure_read(self):
        r = self.by_id()["swipe:organic:someonesaves:instagram-BBB"]
        self.assertEqual((r["kind"], r["structure"]), ("video", "character-sketch"))

    def test_the_words_a_pool_uses_for_nobody_labelled_this_are_empty(self):
        r = self.by_id()
        self.assertEqual(r["swipe:paid:rivalco:1001"]["format"], "")       # unclassified
        self.assertEqual(r["swipe:paid:rivalco:1003"]["format"], "")       # no fields at all
        self.assertEqual(r["swipe:paid:rivalco:page-home"]["format"], "")  # unknown
        self.assertEqual(r["swipe:organic:alphasomesub:tiktok-78"]["structure"], "")  # unread

    def test_a_persons_call_is_laid_over_the_pool(self):
        self.assertEqual(self.by_id()["swipe:paid:rivalco:1004"]["format"], "animatedstory")

    def test_the_brand_is_discovered_from_the_folders(self):
        r = self.by_id()
        self.assertEqual(r["swipe:organic:alphasomesub:tiktok-77"]["swiped_for"], "alpha")   # the feed's name
        self.assertEqual(r["swipe:organic:someonesaves:instagram-AAA"]["swiped_for"], "beta")  # the item's brand_fit
        self.assertEqual(r["swipe:organic:someonesaves:instagram-BBB"]["swiped_for"], "shared")
        self.assertEqual(r["swipe:own:111:a1"]["swiped_for"], "alpha")     # brands/alpha/meta/account.json
        self.assertEqual(r["swipe:own:live:a9"]["swiped_for"], "shared")
        self.assertEqual(r["swipe:paid:rivalco:1001"]["swiped_for"], "shared")

    def test_an_ad_in_two_own_files_is_one_swipe(self):
        self.assertEqual(sum(1 for r in pools.read_all() if r["id"].endswith(":a1")), 1)


class TestRun(Case):
    def test_no_brand_is_an_error_not_a_default(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            R.main(["--dry-run"])

    def test_dry_run_writes_nothing_and_touches_no_pool(self):
        before = digest(self.ws)
        rc, out = self.go("--brand", "alpha", "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("would file to", out)
        self.assertFalse((self.ws / "runs").exists())
        self.assertEqual(digest(self.ws), before)

    def test_a_real_run_files_the_index_and_leaves_both_pools_exactly_as_they_were(self):
        before = digest(self.ws / "lab")
        rc, _ = self.go("--brand", "alpha", "--label", "t1")
        self.assertEqual(rc, 0)
        d, recs = self.index("alpha", "t1")
        self.assertEqual(sorted(p.name for p in d.iterdir()), ["check.json", "run.json", "summary.md", "swipes.jsonl"])
        self.assertEqual(digest(self.ws / "lab"), before)
        run = json.loads((d / "run.json").read_text())
        self.assertEqual((run["model_calls"], run["spend"], run["counts"]["swipes"]), (0, 0, len(recs)))
        self.assertIn("video-teardown", (d / "summary.md").read_text())

    def test_the_index_is_this_brands_swipes_plus_the_shared_ones(self):
        self.go("--brand", "alpha", "--label", "t2")
        _, recs = self.index("alpha", "t2")
        self.assertEqual({r["swiped_for"] for r in recs}, {"alpha", "shared"})
        self.go("--brand", "beta", "--label", "t2")
        _, recs = self.index("beta", "t2")
        self.assertEqual({r["swiped_for"] for r in recs}, {"beta", "shared"})

    def test_source_and_kind_filters(self):
        self.go("--brand", "alpha", "--label", "f1", "--source", "competitor")
        self.assertEqual({r["owner"] for r in self.index("alpha", "f1")[1]}, {"competitor"})
        self.go("--brand", "alpha", "--label", "f2", "--source", "own")
        self.assertEqual({r["source"] for r in self.index("alpha", "f2")[1]}, {"own"})
        self.go("--brand", "alpha", "--label", "f3", "--source", "organic", "--kind", "video")
        self.assertEqual({(r["source"], r["kind"]) for r in self.index("alpha", "f3")[1]}, {("organic", "video")})
        self.go("--brand", "alpha", "--label", "f4", "--limit", "2")
        self.assertEqual(len(self.index("alpha", "f4")[1]), 2)


class TestGates(Case):
    def test_check_json_is_keyed_by_gate(self):
        self.go("--brand", "alpha", "--label", "g1")
        check = json.loads((self.ws / "runs/intake/alpha/g1/check.json").read_text())
        self.assertEqual(set(check), {"inputs", "elements"})
        self.assertEqual(check["inputs"], {"result": "pass", "problems": []})

    def test_an_unknown_format_is_marked_with_the_real_ids_never_passed_never_invented(self):
        rc, _ = self.go("--brand", "alpha", "--label", "g2")           # default gate mode is warn
        self.assertEqual(rc, 0)
        d, recs = self.index("alpha", "g2")
        r = {x["id"]: x for x in recs}
        bad = r["swipe:paid:rivalco:1004"]
        self.assertEqual((bad["format"], bad["format_state"], bad["format_list"]), ("animatedstory", "unknown-format", "format/video"))
        self.assertIn("song-ad", bad["format_problem"])                # the real ids are beside it
        self.assertEqual(r["swipe:paid:rivalco:1002"]["format_state"], "known")
        self.assertEqual(r["swipe:paid:rivalco:1001"]["format_state"], "empty")
        self.assertEqual(r["swipe:paid:rivalco:page-pages-ten-reasons"]["format_state"], "known")
        self.assertEqual(r["swipe:organic:alphasomesub:tiktok-79"]["structure_state"], "unknown-structure")
        self.assertEqual(r["swipe:organic:alphasomesub:tiktok-77"]["structure_state"], "known")
        check = json.loads((d / "check.json").read_text())
        self.assertEqual(check["elements"]["result"], "HELD")           # warn still SAYS held
        self.assertEqual(len(check["elements"]["problems"]), 2)

    def test_on_hold_an_unknown_format_stops_the_index(self):
        rc, out = self.go("--brand", "alpha", "--label", "g3", "--gates", "hold")
        self.assertEqual(rc, 2)
        d = self.ws / "runs/intake/alpha/g3"
        self.assertFalse((d / "swipes.jsonl").exists())
        self.assertEqual(json.loads((d / "check.json").read_text())["elements"]["result"], "HELD")
        self.assertIn("HELD", json.loads((d / "run.json").read_text())["result"])

    def test_a_clean_slice_passes_on_hold(self):
        rc, _ = self.go("--brand", "alpha", "--label", "g4", "--gates", "hold", "--kind", "image")
        self.assertEqual(rc, 0)
        check = json.loads((self.ws / "runs/intake/alpha/g4/check.json").read_text())
        self.assertEqual(check["elements"]["result"], "pass")

    def test_a_brand_that_is_not_a_folder_is_held_and_gets_no_run_folder(self):
        rc, out = self.go("--brand", "nobody", "--label", "g5")
        self.assertEqual(rc, 2)
        self.assertIn("not a brand folder", out)
        self.assertFalse((self.ws / "runs").exists())


class TestMissingPool(Case):
    organic = False

    def test_a_missing_pool_holds_at_inputs(self):
        rc, out = self.go("--brand", "alpha", "--label", "m1")
        self.assertEqual(rc, 2)
        self.assertIn("organic swipe pool", out)
        check = json.loads((self.ws / "runs/intake/alpha/m1/check.json").read_text())
        self.assertEqual(check["inputs"]["result"], "HELD")
        self.assertFalse((self.ws / "runs/intake/alpha/m1/swipes.jsonl").exists())


if __name__ == "__main__":
    unittest.main(verbosity=1)
