#!/usr/bin/env python3
"""An AI-lane production's AI shots are the production chain's (owner ruling, 20 Nov 2026): next_due offers "Make the
AI shots" before the hand-off, the Studio's step only starts the chain's own command (ai_lane.py) and shows its run,
a dry run is the default, and the hand-off waits until the chain has made the clips.

    python3 components/video-studio/test_ai_shots_stage.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ai_shots as AS  # noqa: E402
import video_studio as VS  # noqa: E402

SHOT = {"tool": "gen.shot", "model": None, "prompt": "she lifts the bowl", "seed": None, "inputs": {"refs": []},
        "params": {"lines": [{"say": "One line."}], "lips": "on"}}


class FakeChain:
    """The production chain's command (ai_lane.py), faked: every call is recorded; `status` reports the clips made."""
    def __init__(self, B, made=None, multi=None, after_start=False):
        self.B, self.calls, self.after_start = B, [], after_start
        self.made = made or {}               # call id -> [scenes]
        self.run = Path(B) / "chain-run"
        (self.run / "clips").mkdir(parents=True, exist_ok=True)

    def __call__(self, args):
        args = [str(a) for a in args]
        self.calls.append(args)
        if args[0] == "status":
            calls = []
            for cid, scenes in ({} if self.after_start and not self.started() else self.made).items():
                (self.run / "clips" / (cid + ".mp4")).write_bytes(b"x")
                calls.append({"id": cid, "scenes": scenes, "clip": "clips/%s.mp4" % cid, "camera_motion": True})
            return 0, json.dumps({"run": str(self.run), "stations": [{"id": i, "name": n, "done": bool(self.made)}
                                                                     for i, n in AS.STEPS], "calls": calls,
                                  "waiting_prints": [], "camera_motion": {"S1": "CAMERA AND MOTION ..."}})
        if "--dry-run" in args:
            return 0, json.dumps({"stations": [{"station": i, "state": "done", "said": n} for i, n in AS.STEPS],
                                  "quote": {"higgsfield_credits": {"low": 1, "likely": 2, "high": 3}}, "live": "cmd"})
        return 0, "made"

    def started(self):
        """The chain commands that START something (a status read starts nothing)."""
        return [c for c in self.calls if c[0] != "status"]


class AiLaneProduction(unittest.TestCase):
    def setUp(self):
        self.briefs = Path(tempfile.mkdtemp(prefix="studio_ai_shots_")).resolve()
        p = mock.patch.object(VS, "BRIEFS", str(self.briefs))
        p.start()
        self.addCleanup(p.stop)
        self.B = self.briefs / "p1"
        self.scenes = ["S1", "S2"]
        rows = []
        for s in self.scenes:
            (self.B / "scenes" / s).mkdir(parents=True)
            (self.B / "scenes" / s / "take-1.json").write_text(json.dumps({"steps": [
                dict(SHOT, id="shot-1", note=s + ".1"), dict(SHOT, id="shot-2", note=s + ".2")]}))
            rows += [{"id": s + ".1", "scene": s}, {"id": s + ".2", "scene": s}]
        (self.B / "brief.json").write_text(json.dumps({
            "order": self.scenes, "picks": {s: "take-1" for s in self.scenes}, "lane": "ai", "lane_why": "test",
            "lane_by": "test", "shot_fill": {"brand": "acme"}, "brief": "brand_b-x"}))
        (self.B / "shot-list.json").write_text(json.dumps({"shots": rows}))
        (self.B / "shot-fill.json").write_text(json.dumps({"decided_by": "ai lane", "shots": rows}))
        c = mock.patch.object(AS, "CONF", self.briefs / "no-conf.json")
        c.start()
        self.addCleanup(c.stop)
        e = mock.patch.dict("os.environ", {"VIDEO_STUDIO_AI_SHOTS_DRY_RUN": ""})   # the machine switch off here
        e.start()
        self.addCleanup(e.stop)
        self.said = []

    def say(self, sid, state, said=""):
        self.said.append((sid, state, said))

    def due(self):
        with mock.patch.object(VS, "song_due", lambda n: None):
            return VS.next_due("p1")

    def test_next_due_offers_the_ai_shots_before_the_hand_off(self):
        with mock.patch.object(AS, "chain", FakeChain(self.B)):
            self.assertEqual(AS.scenes_due(self.B, json.loads((self.B / "brief.json").read_text())), self.scenes)
            self.assertEqual(self.due(), "aishots")
        self.assertEqual(VS.NEXT_STAGES["aishots"][0], "Make the AI shots")

    def test_the_stage_only_starts_the_chains_command(self):
        ch = FakeChain(self.B)
        out = AS.run("p1", self.B, self.say, runner=ch)          # the default is the chain's dry run
        self.assertTrue(out["dry_run"])
        self.assertEqual(ch.started(), [["brand_b-x", "--json", "--dry-run"]])   # status reads start nothing
        self.assertEqual(out["quote"]["high"], 3)
        self.assertEqual({s for s, st, _ in self.said if st == "done"}, {i for i, _ in AS.STEPS})
        self.assertFalse((self.B / "ai-shots.json").exists())
        for s in self.scenes:                                    # nothing laid, nothing made by the Studio
            self.assertEqual(json.loads((self.B / "scenes" / s / "take-1.json").read_text())["steps"][0]["tool"],
                             "gen.shot")

    def test_the_live_run_is_the_chains_and_its_clips_are_shown(self):
        ch = FakeChain(self.B, made={"G01-C1": ["S1"], "G02-C1": ["S2", "S3"]}, after_start=True)
        out = AS.run("p1", self.B, self.say, dry_run=False, runner=ch, probe=lambda f: 4.0)
        self.assertEqual(ch.started()[0][:3], ["brand_b-x", "--yes", "--cap"])
        self.assertEqual(out["made"], ["S1"])                      # one-scene clips are laid into the take
        wf = json.loads((self.B / "scenes" / "S1" / "take-1.json").read_text())
        self.assertEqual([x["tool"] for x in wf["steps"]], ["ffmpeg.trim"])
        self.assertEqual(wf["sources"]["ai-take"]["call"], "G01-C1")
        self.assertTrue((self.B / "scenes" / "S1" / "take-1.before-ai-shots.json").exists())
        self.assertEqual(out["left"], [])                           # S2 is the chain's multi-scene clip: covered
        with mock.patch.object(AS, "chain", ch):
            self.assertNotEqual(self.due(), "aishots")

    def test_clips_the_chain_already_made_are_laid_without_starting_it(self):
        ch = FakeChain(self.B, made={"G01-C1": ["S1"], "G02-C1": ["S2"]})
        out = AS.run("p1", self.B, self.say, runner=ch, probe=lambda f: 4.0)
        self.assertEqual(ch.started(), [])                         # nothing started, nothing spent
        self.assertEqual(sorted(out["made"]), ["S1", "S2"])
        self.assertEqual(out["left"], [])

    def test_the_chains_per_scene_file_is_laid_for_a_scene_split_over_calls(self):
        ch = FakeChain(self.B, made={"G01-C1": ["S1"], "G02-C1": ["S2"], "G02-C2": ["S2"]})
        (ch.run / "media").mkdir(parents=True, exist_ok=True)
        (ch.run / "media" / "S2.mp4").write_bytes(b"joined")
        out = AS.run("p1", self.B, self.say, runner=ch, probe=lambda f: 4.0)
        wf = json.loads((self.B / "scenes" / "S2" / "take-1.json").read_text())
        self.assertTrue(wf["sources"]["ai-take"]["drive_location"].endswith("media/S2.mp4"))
        self.assertIn("S2", out["made"])

    def test_the_chains_cut_is_laid_scene_by_scene_with_its_own_voice(self):
        import subprocess
        ch = FakeChain(self.B, made={"G01-C1": ["S1"], "G02-C1": ["S2", "S3"]})
        ed = ch.run / "edit"
        ed.mkdir(parents=True, exist_ok=True)
        rows = []
        for sid in ("S1", "S2", "S3"):                       # S3 is not a Studio scene: it goes with S2
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "1",
                            str(ed / (sid + ".wav"))], check=True)
            (ed / (sid + ".words.json")).write_text(json.dumps({"words": [{"w": sid, "start": 0.1, "end": 0.5}]}))
            rows.append({"scene": sid, "file": "edit/%s.mp4" % sid, "voice": "edit/%s.wav" % sid,
                         "words": "edit/%s.words.json" % sid, "seconds": 1.0, "text": sid, "voice_from": "x"})
        (ed / "EDIT.json").write_text(json.dumps({"scenes": rows}))
        (self.B / "voice").mkdir(exist_ok=True)
        (self.B / "voice" / "reads.json").write_text(json.dumps({"lines": {}}))
        out = AS.run("p1", self.B, self.say, runner=ch, probe=lambda f: 1.0)
        self.assertEqual(ch.started(), [])                                     # nothing started, nothing spent
        self.assertEqual(sorted(out["made"]), ["S1", "S2"])
        wf = json.loads((self.B / "scenes" / "S2" / "take-1.json").read_text())
        self.assertEqual([x["tool"] for x in wf["steps"]], ["voice.read", "ffmpeg.trim", "ffmpeg.trim"])
        self.assertEqual(wf["steps"][0]["inputs"]["file"], "voice/chain/S2.wav")
        reads = json.loads((self.B / "voice" / "reads.json").read_text())["lines"]["S2"]
        self.assertEqual([w["w"] for w in reads["words"]], ["S2", "S3"])
        self.assertEqual(reads["words"][1]["start"], 1.1)                       # S3's words after S2's second
        self.assertTrue((self.B / "voice" / "chain" / "S2.wav").is_file())

    def test_no_writing_run_stops_before_anything_starts(self):
        b = json.loads((self.B / "brief.json").read_text())
        b.pop("brief")
        (self.B / "brief.json").write_text(json.dumps(b))
        ch = FakeChain(self.B)
        out = AS.run("p1", self.B, self.say, runner=ch)
        self.assertEqual(ch.calls, [])
        self.assertEqual(out["stopped"], "no writing run")

    def test_dry_run_is_the_default_and_the_config_turns_on_the_live_run(self):
        self.assertTrue(AS.conf()["dry_run"])
        (self.briefs / "no-conf.json").write_text(json.dumps({"dry_run": False, "cap_credits": 200}))
        ch = FakeChain(self.B)
        AS.run("p1", self.B, self.say, runner=ch, probe=lambda f: 4.0)
        self.assertEqual(ch.started()[0], ["brand_b-x", "--yes", "--cap", "200"])

    def test_the_hand_off_refuses_while_ai_shots_are_unmade(self):
        job = {"id": "j", "n": "p1", "stage": "maker", "name": "x",
               "steps": [{"id": i, "name": nm, "state": "waiting", "said": ""} for i, nm in VS.NEXT_STAGES["maker"][1]]}
        with mock.patch.object(AS, "chain", FakeChain(self.B)):
            VS._run_next(job)
        self.assertEqual(job["steps"][0]["state"], "stopped")
        self.assertFalse((self.B / "maker-pack.json").exists())


class OneGo(unittest.TestCase):
    """One go (THROUGH): every due stage of the line in turn, stopping at the first step that stops."""
    def setUp(self):
        self.briefs = Path(tempfile.mkdtemp(prefix="studio_go_")).resolve()
        (self.briefs / "p1").mkdir()
        p = mock.patch.object(VS, "BRIEFS", str(self.briefs))
        p.start()
        self.addCleanup(p.stop)

    def go(self, dues, stop_at=None):
        ran = []
        queue = list(dues)

        def run_next(job):
            ran.append(job["stage"])
            for st in job["steps"]:
                st["state"] = "stopped" if job["stage"] == stop_at else "done"
        job = {"id": "j", "n": "p1", "stage": queue.pop(0), "done": False, "through": True,
               "file": str(self.briefs / "p1" / "next-job.json"), "steps": [{"id": "x", "state": "waiting"}]}
        VS.save(job["file"], job)
        with mock.patch.object(VS, "_run_next", run_next), \
                mock.patch.object(VS, "next_due", lambda n: queue.pop(0) if queue else None):
            VS.run_next_job("p1")
        return ran

    def test_every_due_stage_runs_in_turn(self):
        self.assertEqual(self.go(["aishots", "cut", "check", "render", "edit", "covers"]),
                         ["aishots", "cut", "check", "render", "edit"])       # covers stays a person's press

    def test_a_stopped_step_ends_the_go(self):
        self.assertEqual(self.go(["aishots", "cut", "check", "render"], stop_at="check"), ["aishots", "cut", "check"])


class SheetFromShots(unittest.TestCase):
    def test_gen_shot_steps_read_as_one_take_with_a_cut_per_shot(self):
        import take_sheet as TS
        wf = {"steps": [{"id": "voice", "tool": "voice.ai", "params": {"speaker": "HOST"}},
                        dict(SHOT, id="shot-1", note="S1.1", params={"lines": [{"say": "one two three four"}], "lips": "on"}),
                        dict(SHOT, id="shot-2", note="S1.2", params={"lines": [{"say": "five six"}], "lips": "on"})]}
        sc = {"shots": [{"id": "S1.1", "angle": "front, eye level.", "camera_move": "push in"},
                        {"id": "S1.2", "angle": "low", "camera_move": "handheld"}], "happens": "she does it"}
        with mock.patch.object(TS, "brief_scene", lambda run, s: sc):
            p = TS.shots_params("/nowhere", "S1", wf, "run")
        self.assertEqual(p["shot_steps"], ["shot-1", "shot-2"])
        self.assertEqual([ln["say"] for ln in p["script"]], ["one two three four", "five six"])
        self.assertEqual({ln["speaker"] for ln in p["script"]}, {"HOST"})
        cam = p["camera"]
        self.assertTrue(cam["directed"])
        self.assertEqual([x["words"] for x in cam["shots"]], ["front, eye level, push in", "low, handheld"])
        self.assertGreater(cam["shots"][0]["seconds"], cam["shots"][1]["seconds"])   # timed on each shot's words
        self.assertIsNone(TS.shots_params("/nowhere", "S1", {"steps": []}, "run"))


if __name__ == "__main__":
    unittest.main()
