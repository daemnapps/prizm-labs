"""The workflow desk's server routes (/desk, /api/desk/*), served through the Studio's own handler, on fixture files.

Nothing here runs a real command: the jobs the desk would start are captured, and the runner's read-only pass is faked.
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

STEPS = [
    {"id": "swipe", "name": "Start", "executor": "agent", "does": "Start from a swipe or our own.",
     "done_when": "runs/video-teardown/_work/{teardown}/run.json"},
    {"id": "brief", "name": "Writing chain brief", "executor": "agent", "does": "Write the brief.",
     "evidence": ["{brief}"]},
    {"id": "pack", "name": "Studio pack", "executor": "command", "does": "Pack it.",
     "run": "python3 components/video-studio/higgsfield/hf_route.py pack {brief} --brand {brand} --label {pack_label}",
     "done_when": "runs/higgsfield/{brand}/drama-ads-{pack_label}/pack.json"},
    {"id": "price", "name": "Price, then the owner's go", "executor": "agent", "quote": True, "does": "THE ONE STOP.",
     "stops_for": "the owner", "evidence": ["runs/higgsfield/{brand}/drama-ads-{pack_label}/quote.json",
                                            "runs/higgsfield/{brand}/drama-ads-{pack_label}/lane.json"]},
    {"id": "clips", "name": "Clips", "executor": "agent", "paid": True, "does": "Make the clips.",
     "evidence": ["runs/higgsfield/{brand}/drama-ads-{pack_label}/jobs.json"]},
]


def put(root, ref, data):
    p = Path(root) / ref
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(data if isinstance(data, str) else json.dumps(data))
    return p


class Desk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = cls.root = Path(cls.tmp.name)
        v = {"brand": "acme", "label": "acme-fight", "teardown": "acme-fight", "pack_label": "acme-fight",
             "writing_run": "runs/video-teardown/_work/acme-fight", "source": "own",
             "brief": "runs/video-teardown/_work/acme-fight/stages/5-brief.md"}
        put(root, "runs/video-production/acme/workflow-acme-fight/workflow-state.json",
            {"format": "micro-drama", "state": "waiting", "values": v, "updated": "2026-11-27T10:00:00Z",
             "receipts": {"swipe": {}, "brief": {}, "pack": {}},
             "next": {"station": "price", "name": "Price, then the owner's go", "quote": True}})
        put(root, "runs/video-production/acme/workflow-acme-fight/pack.log", "packed\n")
        put(root, "runs/video-teardown/_work/acme-fight/run.json", {"brand": "acme", "_order": ["stage3"], "stages": {
            "stage3": {"name": "Injection", "status": "done", "prompt_file": "components/video-writing/prompts/p-v1.md",
                       "sent": "prompts/3-injection.md", "out": "stages/3-injection.md"}}})
        put(root, "components/video-writing/prompts/p-v1.md", "the prompt {slot}")
        put(root, "runs/video-teardown/_work/acme-fight/prompts/3-injection.md", "the prompt as sent")
        put(root, "runs/video-teardown/_work/acme-fight/stages/3-injection.md", "what came out")
        put(root, "runs/video-teardown/_work/acme-fight/stages/5-brief.md", "the brief")
        film = "runs/higgsfield/acme/drama-ads-acme-fight/"
        put(root, film + "pack.json", {"ready": True})
        put(root, film + "quote.json", {"drama_ads_id": "x1", "clip_model": "seedance-2.5", "total_credits": 405,
                                        "clips": {"count": 9, "total_seconds": 135},
                                        "models": {"seedance-2.5": {"credits": 405, "resolution": "480p"},
                                                   "wan-3.0": {"credits": 101.25, "resolution": "480p"}}})
        put(root, film + "clips/k1.mp4", "not really a video")
        put(root, film + "checks/go.json", {"pass": True})
        (root / "brands/acme/core-avatars/tired-mom").mkdir(parents=True)
        put(root, "brands/acme/products/brush.md", "a brush")
        cls.old = (WD.WS, WD.steps_for, WD.dry_next, WD.launch, WD.preset)
        WD.WS = root
        WD.steps_for = lambda fmt, route="ai": STEPS
        WD.dry_next = lambda fmt, brand, label: {"station": "price", "reason": "THE ONE STOP"}
        cls.launched = []
        WD.launch = lambda key, what, cmds, log: cls.launched.append((key, what, cmds)) or {"id": "j1", "what": what}
        WD.preset = lambda brand, avatar: {"id": "kitchen-standoff"}
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), VS.H)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        WD.WS, WD.steps_for, WD.dry_next, WD.launch, WD.preset = cls.old
        cls.tmp.cleanup()

    def setUp(self):
        self.launched.clear()

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=20) as r:
                body = r.read()
                return r.status, body, r.headers.get("Content-Type")
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers.get("Content-Type")

    def post(self, path, data):
        req = urllib.request.Request(self.base + path, data=json.dumps(data).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def js(self, path):
        code, body, _ = self.get(path)
        return code, json.loads(body)

    # --- the page and what it reads ---
    def test_the_page_is_served(self):
        code, body, ctype = self.get("/desk")
        self.assertEqual(code, 200)
        self.assertIn("text/html", ctype)
        self.assertIn(b"Video workflows", body)

    def test_the_lines_offered_are_the_live_ones(self):
        code, d = self.js("/api/desk/lines")
        self.assertEqual(code, 200)
        self.assertEqual([l["id"] for l in d["lines"]], ["micro-drama", "song-ad"])
        self.assertEqual(set(d["starts"]), {"swipe", "own", "winner"})

    def test_pieces_lists_every_workflow_with_the_price_flag(self):
        code, d = self.js("/api/desk/pieces")
        self.assertEqual(code, 200)
        p = d["pieces"][0]
        self.assertEqual((p["brand"], p["label"], p["line"], p["quote"]), ("acme", "acme-fight", "Micro drama", True))

    def test_a_piece_shows_every_station_its_prompt_outputs_and_price(self):
        code, p = self.js("/api/desk/piece/acme/acme-fight")
        self.assertEqual(code, 200)
        self.assertEqual([s["status"] for s in p["stations"]], ["done", "done", "done", "now", "later"])
        st = {s["id"]: s for s in p["stations"]}
        self.assertEqual(st["brief"]["does"], "Write the brief.")
        w = st["brief"]["writing"][0]
        self.assertEqual((w["prompt"], w["sent"], w["out"]), ("components/video-writing/prompts/p-v1.md",
                                                             "runs/video-teardown/_work/acme-fight/prompts/3-injection.md",
                                                             "runs/video-teardown/_work/acme-fight/stages/3-injection.md"))
        self.assertEqual(st["pack"]["log"], "runs/video-production/acme/workflow-acme-fight/pack.log")
        self.assertIn("runs/higgsfield/acme/drama-ads-acme-fight/pack.json", [o["path"] for o in st["pack"]["outputs"]])
        pr = st["price"]["price"]
        self.assertTrue(pr["ready"])
        self.assertFalse(pr["lane_open"])
        self.assertEqual(pr["total_credits"], 405)
        self.assertEqual({m["id"] for m in pr["models"]}, {"seedance-2.5", "wan-3.0"})
        self.assertTrue(st["clips"]["paid"])
        self.assertEqual(p["gallery"]["clips"][0]["path"], "runs/higgsfield/acme/drama-ads-acme-fight/clips/k1.mp4")
        self.assertEqual(p["checks"][0]["stage"], "go")
        self.assertIsNone(p["ask"])                    # at a ready price, nothing is asked of Claude

    def test_an_unknown_piece_is_404(self):
        self.assertEqual(self.js("/api/desk/piece/acme/nope")[0], 404)
        self.assertEqual(self.js("/api/desk/piece/acme/..%2F..")[0], 404)

    def test_files_are_read_inside_the_repo_only(self):
        code, t = self.js("/api/desk/text?path=runs/video-teardown/_work/acme-fight/stages/3-injection.md")
        self.assertEqual((code, t["text"]), (200, "what came out"))
        for bad in ("../etc/passwd", "/etc/hosts", "runs/../../x.md", "keys/.env"):
            self.assertEqual(self.js("/api/desk/text?path=" + bad)[0], 404, bad)

    def test_media_is_served_from_runs_only(self):
        code, body, ctype = self.get("/api/desk/media?path=runs/higgsfield/acme/drama-ads-acme-fight/clips/k1.mp4")
        self.assertEqual((code, ctype), (200, "video/mp4"))
        self.assertEqual(self.get("/api/desk/media?path=brands/acme/products/brush.md")[0], 404)

    def test_brands_and_teardowns(self):
        code, d = self.js("/api/desk/brands")
        self.assertEqual(d["brands"][0], {"id": "acme", "avatars": ["tired-mom"], "products": ["brush"], "winner": False})
        self.assertEqual(self.js("/api/desk/teardowns?brand=acme")[1], {"teardowns": []})

    # --- the go: only the owner's own words, at or over the price ---
    def test_the_go_needs_a_name_words_and_a_cap(self):
        for bad in ({}, {"approved_by": "Owner", "cap": 500}, {"said": "go", "cap": 500},
                    {"approved_by": "Owner", "said": "go"}):
            code, d = self.post("/api/desk/piece/acme/acme-fight/go", bad)
            self.assertEqual(code, 400, bad)
        self.assertEqual(self.launched, [])

    def test_the_go_refuses_a_cap_below_the_price(self):
        code, d = self.post("/api/desk/piece/acme/acme-fight/go", {"approved_by": "Owner", "said": "go", "cap": 100})
        self.assertEqual(code, 400)
        self.assertIn("405", d["error"])
        self.assertEqual(self.launched, [])

    def test_the_go_opens_the_lane_then_marks_the_price_done(self):
        code, d = self.post("/api/desk/piece/acme/acme-fight/go",
                            {"approved_by": "Owner", "said": "go on this", "cap": 450, "model": "wan-3.0"})
        self.assertEqual(code, 200)
        (key, what, cmds), = self.launched
        self.assertEqual(key, "acme/acme-fight")
        open_argv, complete_argv = cmds[0][1], cmds[1][1]
        self.assertTrue(open_argv[1].endswith("higgsfield/drama_lane.py"))
        self.assertEqual(open_argv[2], "open")
        for flag, val in (("--approved-by", "Owner"), ("--said", "go on this"), ("--cap", "450.0"),
                          ("--model", "wan-3.0"), ("--format", "micro-drama")):
            self.assertEqual(open_argv[open_argv.index(flag) + 1], val)
        self.assertEqual(complete_argv[2:4], ["complete", "micro-drama"])
        self.assertEqual(complete_argv[complete_argv.index("--station") + 1], "price")

    def test_no_go_when_the_piece_is_not_at_its_price(self):
        old = WD.dry_next
        WD.dry_next = lambda *a: {"station": "brief"}
        try:
            code, d = self.post("/api/desk/piece/acme/acme-fight/go", {"approved_by": "O", "said": "go", "cap": 999})
        finally:
            WD.dry_next = old
        self.assertEqual(code, 400)
        self.assertEqual(self.launched, [])

    # --- moving on and starting never pay ---
    def test_move_on_runs_the_workflow_without_paying(self):
        code, d = self.post("/api/desk/piece/acme/acme-fight/run", {})
        self.assertEqual(code, 200)
        argv = self.launched[0][2][0][1]
        self.assertEqual(argv[2:4], ["run", "micro-drama"])
        self.assertNotIn("--allow-paid", argv)

    def test_start_checks_what_it_is_given(self):
        for bad in ({"format": "meme", "start": "own", "brand": "acme", "label": "x"},
                    {"format": "micro-drama", "start": "own", "brand": "nobody", "label": "x"},
                    {"format": "micro-drama", "start": "own", "brand": "acme", "label": ""},
                    {"format": "micro-drama", "start": "swipe", "brand": "acme", "label": "x", "teardown": "missing"},
                    {"format": "micro-drama", "start": "winner", "brand": "acme", "label": "x", "teardown": "acme-fight"},
                    {"format": "micro-drama", "start": "own", "brand": "acme", "label": "fight"}):   # already on the desk
            code, d = self.post("/api/desk/start", bad)
            self.assertEqual(code, 400, bad)
        self.assertEqual(self.launched, [])

    def test_start_our_own_story_sets_up_then_runs(self):
        code, d = self.post("/api/desk/start", {"format": "micro-drama", "start": "own", "brand": "acme",
                                                "label": "Dinner Table", "avatar": "tired-mom", "product": "brush"})
        self.assertEqual(code, 200)
        self.assertEqual(d["label"], "acme-dinner-table")
        (key, what, cmds), = self.launched
        scratch, run = cmds[0][1], cmds[1][1]
        self.assertTrue(scratch[1].endswith("video-writing/machine/scratch.py"))
        self.assertEqual(scratch[scratch.index("--preset") + 1], "kitchen-standoff")
        self.assertNotIn("--write", scratch)
        self.assertEqual(run[2:4], ["run", "micro-drama"])
        self.assertIn("source=own", run)
        self.assertIn("pack_label=acme-dinner-table", run)
        self.assertNotIn("--allow-paid", run)

    def test_start_from_a_swipe(self):
        code, d = self.post("/api/desk/start", {"format": "song-ad", "start": "swipe", "brand": "acme",
                                                "label": "jingle", "teardown": "acme-fight"})
        self.assertEqual(code, 200)
        run = self.launched[0][2][0][1]
        self.assertIn("teardown=acme-fight", run)
        self.assertIn("source=swipe", run)

    # --- what the Studio served before still answers the same ---
    def test_the_studio_routes_still_answer(self):
        code, body, ctype = self.get("/")
        self.assertEqual(code, 200)
        self.assertEqual(body, (Path(VS.HERE) / "studio.html").read_bytes())
        self.assertEqual(self.get("/canvas")[0], 200)
        self.assertEqual(self.get("/nope")[0], 404)
        self.assertEqual(self.post("/api/nope", {})[0], 404)
        self.assertEqual(self.js("/api/desk/nope")[0], 404)


if __name__ == "__main__":
    unittest.main()
