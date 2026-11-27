#!/usr/bin/env python3
"""The Production page shows the production chain's run, read-only (chain_view.py, 20 Nov 2026): the dry run's
stations and quote, each scene's idea, shot cameras with the swipe shot they build on, and the beats.

    python3 components/video-studio/test_chain_view.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain_view as CV  # noqa: E402


class ChainView(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="chainview_"))
        self.wr = self.tmp / "writing"
        (self.wr / "framemap" / "shots").mkdir(parents=True)
        (self.wr / "framemap" / "shots" / "K01-mid.jpg").write_bytes(b"jpg")
        self.live = self.tmp / "runs" / "video-production" / "b" / "L"
        self.shadow = self.live / "dry-run" / "video-production" / "b" / "L"
        (self.shadow / "clips").mkdir(parents=True)
        (self.shadow / "storyboard.json").write_text(json.dumps({"sections": [
            {"id": "G01", "scenes": ["S1"], "seconds": 4.0, "maker": "lip-sync", "swipe": {"shots": [{"id": "K01"}]}}]}))
        (self.shadow / "BUDGET.md").write_text("# Budget\n\n**Key:** 1 section · 1 picture\n")
        (self.shadow / "clips" / "camera-motion.json").write_text(json.dumps({"scenes": {"S1": {
            "kind": "talking", "sources": ["the swipe's motion pattern (frame map)", "the director's pick (5d)"],
            "camera": {"shots": [{"shot": "S1.1", "angle": "front", "move": "handheld", "why": "the swipe's camera",
                                  "copies": "K01"}]},
            "motion": {"title": "The Paper Fan", "premise": "a fan", "beats": [{"id": "B1", "over": "Hi", "do": "bends"}],
                       "swipe": [{"shot": "K01", "camera": "still", "moments": [{"at": 0.0, "does": "points"}]}]}}},
            "held": {}}))
        (self.live / "dry-run" / "dry-run.json").write_text(json.dumps({
            "stations": [{"station": "brief", "state": "done", "said": "accepted"},
                         {"station": "clips", "state": "waiting", "said": "waits for the go"}],
            "quote": {"higgsfield_credits": {"low": 1, "likely": 2, "high": 3}}, "live": "cmd", "at": "now"}))
        r = {"brand": "b", "label": "L", "writing_run": str(self.wr)}
        lane = mock.MagicMock()
        lane.resolve.return_value = r
        lane.run_dir.return_value = self.live
        p = mock.patch.object(CV, "LANE", lane)
        p.start()
        self.addCleanup(p.stop)
        self.brief = {"brief": "writing-run"}

    def test_the_dry_run_is_shown_station_by_station_with_its_quote(self):
        v = CV.view("p1", self.brief)
        self.assertEqual(v["mode"], "dry run")
        self.assertEqual([s["id"] for s in v["stations"]], ["brief", "clips"])
        self.assertEqual(v["quote"]["higgsfield_credits"]["likely"], 2)
        self.assertEqual(v["budget"], "1 section · 1 picture")

    def test_each_scene_shows_its_idea_shot_cameras_swipe_and_beats(self):
        s = CV.view("p1", self.brief)["scenes"]["S1"]
        self.assertEqual(s["title"], "The Paper Fan")
        self.assertEqual(s["shots"][0], {"shot": "S1.1", "angle": "front", "move": "handheld",
                                         "why": "the swipe's camera", "copies": "K01", "side": None})
        self.assertEqual(s["beats"][0]["do"], "bends")
        self.assertEqual(s["swipe"][0]["moments"][0]["does"], "points")
        self.assertEqual(CV.swipe_still(self.brief, "K01"), str(self.wr / "framemap" / "shots" / "K01-mid.jpg"))
        self.assertIsNone(CV.swipe_still(self.brief, "../etc"))           # only a swipe shot id is served

    def test_a_card_shows_our_start_picture_and_our_cast_once_the_run_has_them(self):
        brief = self.wr / "stages" / "5-brief.md"
        brief.parent.mkdir(parents=True)
        brief.write_text("```json\n" + json.dumps({"cast": [{"id": "yai", "bank_id": "yai"}],
                                                   "scenes": [{"id": "S1", "looks": {"yai": "look-1"}}]}) + "\n```\n")
        CV.LANE.resolve.return_value = dict(CV.LANE.resolve.return_value, brief=str(brief))
        pic = self.live / "media" / "S1-F1.png"
        pic.parent.mkdir(parents=True)
        pic.write_bytes(b"png")
        (self.live / "direct.json").write_text(json.dumps({"S1-F1": {"file": str(pic)}}))
        v = CV.view("p1", self.brief)
        self.assertEqual(v["mode"], "live")                      # the live run, with the dry run's plan until its own
        self.assertEqual(v["plan_from"], "dry run")
        s = v["scenes"]["S1"]
        self.assertEqual(s["picture"], "S1-F1")
        self.assertEqual(s["cast"], [{"id": "yai", "bank": "yai"}])
        self.assertEqual(s["title"], "The Paper Fan")

    def test_every_clip_call_lays_out_its_inputs_in_send_order(self):
        pic = self.live / "media" / "S1-F1.png"
        pic.parent.mkdir(parents=True, exist_ok=True)
        pic.write_bytes(b"png")
        (self.live / "direct.json").write_text(json.dumps({"S1-F1": {"file": str(pic)}}))
        (self.live / "clips").mkdir(parents=True, exist_ok=True)    # a reference not on disk still shows, labelled
        (self.live / "clips" / "plan.json").write_text(json.dumps({"calls": [
            {"id": "G01-C1", "scenes": ["S1"], "start_frame": "S1-F1", "talking": True, "people": ["yai"],
             "image_refs": [{"file": "runs/ai-elements/b/products/p/model/product-sheet.png", "job": "x"},
                            {"file": "runs/ai-elements/b/products/p/model/formula/p-formula.jpg", "job": "y"}],
             "refs": [{"kind": "movement", "file": "refs/m.mp4"}]},
            {"id": "G02-C1", "scenes": ["S2"], "start_frame": "S2-F1", "talking": True, "people": ["yai"],
             "image_refs": []}], "problems": []}))
        calls = {c["id"]: c for c in CV.view("p1", self.brief)["calls"]}
        kinds = [i["kind"] for i in calls["G01-C1"]["inputs"]]
        self.assertEqual(kinds, ["start", "product", "texture", "movement", "voice"])
        self.assertEqual(calls["G01-C1"]["inputs"][0]["key"], "in-G01-C1-1")
        self.assertIsNone(calls["G01-C1"]["warn"])
        self.assertIn("no casting sheets", calls["G02-C1"]["warn"])
        self.assertNotIn("file", calls["G01-C1"]["inputs"][0])               # the page never sees a path

    def test_the_speaker_speaks_in_their_own_banked_voice(self):
        brief = self.wr / "stages" / "5-brief.md"
        brief.parent.mkdir(parents=True, exist_ok=True)
        brief.write_text("```json\n" + json.dumps({"cast": [{"id": "yai", "bank_id": "yai-t"}, {"id": "k"}],
                                                   "scenes": [{"id": "S1", "speaker": "yai"}, {"id": "S2", "speaker": "yai"},
                                                              {"id": "S3", "speaker": "k"}]}) + "\n```\n")
        CV.LANE.resolve.return_value = dict(CV.LANE.resolve.return_value, brief=str(brief))
        home = self.tmp / "repo"
        vf = home / "runs" / "ai-elements" / "b" / "casting" / "yai-t" / "voice.json"
        vf.parent.mkdir(parents=True)
        vf.write_text(json.dumps({"voice_id": "V-YAI", "name": "yai"}))
        with mock.patch.object(CV.ST, "REPO", home):
            v = CV.speaker_voice(self.brief)
        self.assertEqual(v["voice_id"], "V-YAI")

    def test_nothing_is_written(self):
        before = sorted(str(p) for p in self.tmp.rglob("*"))
        CV.view("p1", self.brief)
        self.assertEqual(sorted(str(p) for p in self.tmp.rglob("*")), before)

    def test_a_brief_the_chain_has_not_run_says_so(self):
        import shutil
        shutil.rmtree(self.live)
        v = CV.view("p1", self.brief)
        self.assertIsNone(v["mode"])
        self.assertIn("not run", v["why"])


if __name__ == "__main__":
    unittest.main()
