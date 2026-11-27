"""drama_lane.py: the lane opens only on a priced go, one clip model per lane, and each stage's check holds what it names."""
import hashlib
import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drama_lane as DL  # noqa: E402


def w(p, data):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(data if isinstance(data, str) else json.dumps(data))
    return p


class Film:
    """A film folder that passes every stage on the default model; tests break one thing at a time."""

    def __init__(self, root, model="seedance-2.5"):
        self.d = Path(root) / "film-x"
        cfg = DL.models()["models"][model]
        self.vendor = cfg["vendor_id"]
        w(self.d / "pack.json", {"ready": True, "here": {"product": [{"name": "p", "files": ["runs/ai-elements/b/products/p/model/product-sheet.png"]}]}})
        self.quote = w(self.d / "quote.json", {"drama_ads_id": "D1", "clip_model": model, "resolution": "480p", "total_credits": 90})
        DL.open_lane(self.d, self.quote, "Owner", "go", 120, model=model, now="2026-11-27T00:00:00Z")
        w(self.d / "film/sheets.json", {"sheets": [
            {"kind": "person", "name": "A", "job_id": "j-a"},
            {"kind": "place", "name": "room", "job_id": "j-r"},
            {"kind": "product", "name": "p", "source": "runs/ai-elements/b/products/p/model/product-sheet.png"}]})
        w(self.d / "film/script.json", {"clips": [{"id": "k1", "make": "fresh", "images": ["c1", "l1"], "videos": [], "voices": ["v1"]}]})
        w(self.d / "film/plan.json", {"items": []})
        w(self.d / "film/checks.json", {"script": "PASS", "plan": "PASS", "clips": {"k1": "PASS"}})
        self.prompt = w(self.d / "film/prompts/clip-k1.txt", "Handheld follow from the door to a close-up; she reacts to his line.")
        w(self.d / "film/setups.html", "<html></html>")
        self.refs = [{"role": "image_references", "value": "j-a"}, {"role": "image_references", "value": "j-r"}]
        w(self.d / "film/setups.json", {"page": "film/setups.html", "setups": [{
            "clip": "k1", "model": self.vendor, "resolution": "480p", "aspect_ratio": "9:16", "duration": 8,
            "refs": self.refs, "prompt_file": "film/prompts/clip-k1.txt",
            "prompt_sha256": hashlib.sha256(self.prompt.read_bytes()).hexdigest(),
            "camera": "handheld follow, push to close-up", "quote_credits": 24}]})
        params = dict(cfg.get("params") or {}, model=self.vendor, drama_ads_id="D1", resolution="480p",
                      aspect_ratio="9:16", duration=8, prompt=self.prompt.read_text(), medias=self.refs)
        self.request = {"params": params}
        w(self.d / "jobs.json", {"clips": [{"clip": "k1", "take": 1, "request": self.request, "job_id": "J1"}]})
        looked = {k: "pass" for k in DL.LOOKS}
        w(self.d / "film/takes.json", {"takes": [{"clip": "k1", "job_id": "J1", "accepted": True, "looked": looked}]})


class Models(unittest.TestCase):
    def test_default_is_seedance_and_wan_is_a_test_lane(self):
        m = DL.models()
        self.assertEqual(m["default"], "seedance-2.5")
        self.assertEqual(m["models"]["seedance-2.5"]["vendor_id"], "seedance_2_5")
        self.assertEqual(m["models"]["wan-3.0"]["vendor_id"], "wan3_0")
        self.assertEqual(m["models"]["wan-3.0"]["lane"], "option")
        self.assertEqual(m["models"]["wan-3.0"]["resolution"], "480p")


class Lane(unittest.TestCase):
    def test_every_stage_passes_on_a_whole_film(self):
        for model in ("seedance-2.5", "wan-3.0"):
            with tempfile.TemporaryDirectory() as t:
                f = Film(t, model)
                for stage in DL.STAGES:
                    self.assertEqual(DL.check(f.d, stage), [], (model, stage))
                    self.assertTrue((f.d / "checks" / (stage + ".json")).is_file())

    def test_no_go_no_lane(self):
        with tempfile.TemporaryDirectory() as t:
            f = Film(t)
            with self.assertRaises(SystemExit):
                DL.open_lane(f.d, f.quote, "", "", 120)
            with self.assertRaises(SystemExit):
                DL.open_lane(f.d, f.quote, "Owner", "go", 50)          # cap under the quote

    def test_the_quote_must_be_on_the_lanes_model(self):
        with tempfile.TemporaryDirectory() as t:
            f = Film(t)
            with self.assertRaises(SystemExit):
                DL.open_lane(f.d, f.quote, "Owner", "go", 120, model="wan-3.0")

    def test_a_held_check_writes_no_pass(self):
        with tempfile.TemporaryDirectory() as t:
            f = Film(t)
            w(f.d / "film/checks.json", {"script": "PASS", "plan": "FAIL", "clips": {"k1": "PASS"}})
            self.assertTrue(any("plan" in b for b in DL.check(f.d, "setups")))
            self.assertFalse((f.d / "checks/setups.json").exists())

    def test_generated_product_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            f = Film(t)
            w(f.d / "film/sheets.json", {"sheets": [{"kind": "person", "name": "A", "job_id": "j"},
                                                   {"kind": "product", "name": "p", "job_id": "made", "source": "x.png"}]})
            bad = " ".join(DL.check(f.d, "sheets"))
            self.assertIn("approved casting sheet", bad)
            self.assertIn("never generated", bad)

    def test_a_still_camera_is_refused_unless_marked(self):
        with tempfile.TemporaryDirectory() as t:
            f = Film(t)
            f.prompt.write_text("Locked-off frame on the bathroom mirror.")
            s = json.loads((f.d / "film/setups.json").read_text())
            s["setups"][0]["prompt_sha256"] = hashlib.sha256(f.prompt.read_bytes()).hexdigest()
            w(f.d / "film/setups.json", s)
            self.assertTrue(any("camera move" in b for b in DL.check(f.d, "setups")))
            s["setups"][0]["static_ok"] = "black end card"
            w(f.d / "film/setups.json", s)
            self.assertEqual(DL.check(f.d, "setups"), [])

    def test_a_prompt_changed_after_publishing_is_held(self):
        with tempfile.TemporaryDirectory() as t:
            f = Film(t)
            f.prompt.write_text(f.prompt.read_text() + " More.")
            self.assertTrue(any("changed after" in b for b in DL.check(f.d, "setups")))

    def test_wan_lane_refuses_extensions_and_too_many_refs(self):
        with tempfile.TemporaryDirectory() as t:
            f = Film(t, "wan-3.0")
            w(f.d / "film/script.json", {"clips": [{"id": "k1", "make": "extension", "images": ["i"] * 11}]})
            bad = " ".join(DL.check(f.d, "setups"))
            self.assertIn("extension", bad)
            self.assertIn("11 image references", bad)

    def test_request_must_be_the_lanes_model_and_settings(self):
        with tempfile.TemporaryDirectory() as t:
            f = Film(t, "wan-3.0")
            self.assertEqual(DL.check_request(f.d, f.request), [])
            r = json.loads(json.dumps(f.request))
            r["params"].update(model="seedance_2_5", mode="omni_reference", resolution="720p")
            bad = " ".join(DL.check_request(f.d, r))
            self.assertIn("not the lane's", bad)
            self.assertIn("mode is not a setting", bad)
            self.assertIn("720p", bad)

    def test_takes_need_the_published_request_and_a_look(self):
        with tempfile.TemporaryDirectory() as t:
            f = Film(t)
            j = json.loads((f.d / "jobs.json").read_text())
            j["clips"][0]["request"]["params"]["prompt"] = "a different prompt"
            w(f.d / "jobs.json", j)
            w(f.d / "film/takes.json", {"takes": [{"clip": "k1", "job_id": "J1", "accepted": True, "looked": {"camera": "pass"}}]})
            bad = " ".join(DL.check(f.d, "takes"))
            self.assertIn("not the published setup's prompt", bad)
            self.assertIn("acting", bad)


class Decided(unittest.TestCase):
    def test_a_kept_finding_counts_only_with_its_filed_call(self):
        with tempfile.TemporaryDirectory() as t:
            f = Film(t)
            takes = json.loads((f.d / "film/takes.json").read_text())
            takes["takes"][0]["looked"]["acting"] = {"decided": "call-1"}
            w(f.d / "film/takes.json", takes)
            with unittest.mock.patch.object(DL, "_last_call", lambda run, n: None):
                self.assertTrue(any("acting" in b for b in DL.check(f.d, "takes")))
            with unittest.mock.patch.object(DL, "_last_call", lambda run, n: "call-1" if n == "k1-acting" else None):
                self.assertEqual(DL.check(f.d, "takes"), [])


class SongLane(unittest.TestCase):
    def film(self, t):
        f = Film(t)                                       # a dialogue film, then turned into a song film
        lane = json.loads((f.d / "lane.json").read_text())
        lane.update(format="song-ad", preset="/singing-ads")
        w(f.d / "lane.json", lane)
        w(f.d / "film/plan.json", {"song_seconds": 8, "windows": [{"clip": "k1", "start": 0, "end": 8}]})
        w(f.d / "lines.tsv", "0.00\t3.00\tfirst line\n3.00\t8.00\tsecond line\n")
        s = json.loads((f.d / "film/setups.json").read_text())
        s["setups"][0]["model"] = DL.models("song-ad")["models"]["seedance-2.5"]["vendor_id"]
        w(f.d / "film/setups.json", s)
        return f

    def test_song_reads_its_own_lane_settings(self):
        self.assertEqual(DL.lane_cfg("song-ad")["preset"], "/singing-ads")
        self.assertIn("lyric_beat", DL.lane_cfg("song-ad")["looks"])
        self.assertFalse(DL.models("song-ad")["models"]["seedance-2.5"]["params"]["generate_audio"])

    def test_windows_run_end_to_end_on_the_song(self):
        with tempfile.TemporaryDirectory() as t:
            f = self.film(t)
            self.assertEqual(DL.check(f.d, "setups"), [])
            w(f.d / "film/plan.json", {"song_seconds": 10, "windows": [{"clip": "k1", "start": 0, "end": 7}]})
            self.assertTrue(any("ends at" in b for b in DL.check(f.d, "setups")))

    def test_men_never_hug(self):
        with tempfile.TemporaryDirectory() as t:
            f = self.film(t)
            f.prompt.write_text("Handheld follow; he pulls his brother into a hug.")
            s = json.loads((f.d / "film/setups.json").read_text())
            s["setups"][0]["prompt_sha256"] = hashlib.sha256(f.prompt.read_bytes()).hexdigest()
            w(f.d / "film/setups.json", s)
            self.assertTrue(any("hug or kiss" in b for b in DL.check(f.d, "setups")))


if __name__ == "__main__":
    unittest.main()
