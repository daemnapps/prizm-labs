"""The new Studio (/next, studio-next.html) and the read-only routes it adds to the desk: the swipe library, one
swipe's chain, the morning summary and the brand checklist. Served through the Studio's own handler, on fixture files.
"""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import video_studio as VS
import workflow_desk as WD


def put(root, ref, data):
    p = Path(root) / ref
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(data if isinstance(data, str) else json.dumps(data))
    return p


class StudioNext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        td = "runs/video-teardown/_work/acme-swipe/"
        put(root, td + "run.json", {"brand": "acme", "poster": "poster.jpg", "source": "source.mp4",
                                    "triage_lane": "ORGANIC", "post_url": "https://example.com/p/1",
                                    "_order": ["stage1", "stage3", "stage5"], "stages": {
            "stage1": {"name": "Teardown", "status": "done", "prompt_file": "components/p/teardown-v1.md",
                       "sent": "prompts/1-teardown.md", "out": "stages/1-teardown.md", "version": "1", "seconds": "12"},
            "stage3": {"name": "Injection", "status": "done", "out": "stages/3-injection.md"},
            "stage5": {"name": "Brief", "status": "done", "out": "stages/5-brief.md"}}})
        for f in ("poster.jpg", "source.mp4", "prompts/1-teardown.md", "stages/1-teardown.md",
                  "stages/3-injection.md", "stages/5-brief.md"):
            put(root, td + f, "x")
        put(root, "components/p/teardown-v1.md", "the teardown prompt")
        put(root, "runs/video-teardown/_work/other-brand/run.json", {"brand": "zed", "stages": {}})
        put(root, "runs/video-teardown/_work/odd-poster/run.json", {"brand": "acme", "poster": {"not": "a path"}})
        put(root, "runs/winners/acme/bank.json", {"rows": [
            {"id": "acme-1", "name": "Big one", "headline": "Clear skin", "format": "Video",
             "snapshots": [{"kind": "audit", "purchases": 300, "spend": 9000, "cpa": 30, "roas": 2.1}]},
            {"id": "acme-2", "name": "Small one", "format": "Video",
             "snapshots": [{"kind": "audit", "purchases": 20, "spend": 900, "cpa": 45, "roas": 1.2}]},
            {"id": "acme-3", "name": "No numbers"}]})
        put(root, "runs/ad-variations/acme/p2f-acme-2__hook/plan.json", {})
        put(root, "runs/winners/acme/brief-next.json", {"angles": [{"angle": "On sale", "purchases": 2}], "tried": []})
        put(root, "runs/swipe-organic/acme/research-mom-2026-11-01-x/worlds.json", [{"world": "Dry skin", "count": 40}])
        put(root, "brands/_TEMPLATE/onboarding.json", {"groups": ["Brand basics"], "items": [
            {"id": "story", "group": "Brand basics", "name": "Your story", "fills": ["story.md"]},
            {"id": "best-seller", "group": "Brand basics", "name": "Best seller",
             "fills": ["products/<product>/product.md", "products/<product>/images/"]},
            {"id": "position", "group": "Brand basics", "name": "Position", "fills": ["position.md (what you claim)"]}]})
        put(root, "brands/acme/story.md", "our story")
        put(root, "brands/acme/products/brush/product.md", "a brush")
        put(root, "brands/acme/onboarding-progress.json", {"done": ["position"], "skipped": []})
        cls.old = (WD.WS, WD._growth)
        WD.WS = root
        WD._growth = lambda: {"built": "now", "brands": {"acme": {"label": "ACME", "daily": [
            {"d": "2026-11-0%d" % i, "revenue": 100.0, "spend": 40.0, "profit": 30.0 if i != 3 else -10.0} for i in range(1, 9)]}}}
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), VS.H)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        WD.WS, WD._growth = cls.old
        cls.tmp.cleanup()

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=20) as r:
                return r.status, r.read(), r.headers.get("Content-Type")
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers.get("Content-Type")

    def js(self, path):
        code, body, _ = self.get(path)
        return code, json.loads(body)

    def test_page_is_served(self):
        code, body, ctype = self.get("/next")
        self.assertEqual(code, 200)
        self.assertIn("text/html", ctype)
        self.assertIn(b"<title>Studio</title>", body)

    def test_old_pages_still_served(self):
        self.assertEqual(self.get("/desk")[0], 200)

    def test_swipe_library_is_per_brand_with_covers(self):
        code, d = self.js("/api/desk/swipes?brand=acme")
        self.assertEqual(code, 200)
        labels = [s["label"] for s in d["swipes"]]
        self.assertIn("acme-swipe", labels)
        self.assertNotIn("other-brand", labels)
        row = next(s for s in d["swipes"] if s["label"] == "acme-swipe")
        self.assertEqual(row["poster"], "runs/video-teardown/_work/acme-swipe/poster.jpg")
        self.assertTrue(row["brief"])
        odd = next(s for s in d["swipes"] if s["label"] == "odd-poster")
        self.assertIsNone(odd["poster"])

    def test_one_swipe_has_every_stage_with_prompt_and_output(self):
        code, d = self.js("/api/desk/swipe?label=acme-swipe")
        self.assertEqual(code, 200)
        st = {s["id"]: s for s in d["stages"]}
        self.assertEqual(list(st), ["stage1", "stage3", "stage5"])
        self.assertEqual(st["stage1"]["prompt"], "components/p/teardown-v1.md")
        self.assertEqual(st["stage1"]["out"], "runs/video-teardown/_work/acme-swipe/stages/1-teardown.md")
        self.assertEqual(st["stage1"]["version"], "1")

    def test_unknown_or_unsafe_swipe_is_refused(self):
        self.assertEqual(self.get("/api/desk/swipe?label=nope")[0], 404)
        self.assertEqual(self.get("/api/desk/swipe?label=../etc")[0], 404)

    def test_today_sums_the_last_seven_days(self):
        code, d = self.js("/api/desk/today?brand=acme")
        self.assertEqual(code, 200)
        b = d["money"]["brands"][0]
        self.assertEqual(len(b["days"]), 7)
        self.assertEqual(b["total"]["revenue"], 700.0)
        self.assertEqual(b["total"]["profit"], 30.0 * 6 - 10.0)
        self.assertEqual(b["last"], "2026-11-08")

    def test_today_winners_ranked_and_marked_when_varied(self):
        _, d = self.js("/api/desk/today?brand=acme")
        w = d["winners"]
        self.assertEqual([x["id"] for x in w], ["acme-1", "acme-2"])
        self.assertFalse(w[0]["varied"])
        self.assertTrue(w[1]["varied"])

    def test_today_research(self):
        _, d = self.js("/api/desk/today?brand=acme")
        self.assertEqual(d["research"]["next"]["angles"][0]["angle"], "On sale")
        self.assertEqual(d["research"]["rounds"][0]["worlds"][0]["world"], "Dry skin")

    def test_today_says_when_the_money_feed_is_down(self):
        WD._growth, keep = (lambda: None), WD._growth
        try:
            _, d = self.js("/api/desk/today?brand=acme")
        finally:
            WD._growth = keep
        self.assertFalse(d["money"]["ok"])

    def test_brand_checklist_states(self):
        code, d = self.js("/api/desk/setup?brand=acme")
        self.assertEqual(code, 200)
        st = {i["id"]: i["state"] for i in d["items"]}
        self.assertEqual(st["story"], "filled")
        self.assertEqual(st["best-seller"], "partial")
        self.assertEqual(st["position"], "done")
        self.assertTrue(d["progress"])


if __name__ == "__main__":
    unittest.main()
