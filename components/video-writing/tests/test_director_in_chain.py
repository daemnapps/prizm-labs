#!/usr/bin/env python3
"""Stage 5d fires on its own inside the writing chain: the moment the stage-5 writer call lands a brief, the director
restages it (before any stage-5 check reads it), its calls are logged as `stage5d`, and its record rides on stage 5.
A patch, another pass, or a brief with no scene block never calls it.

A fake `claude` first on PATH plays the stage-5 writer, the director and the producer, by what its prompt asks for.
No network, no spend, no real model.

    python3 components/video-writing/tests/test_director_in_chain.py
"""
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TD = HERE.parents[1] / "video-teardown" / "machine"
sys.path.insert(0, str(HERE.parent / "machine"))
sys.path.insert(0, str(TD))
import writing_v2 as W    # noqa: E402

BRIEF = {"piece": {"title": "Test"}, "song": None, "world": [{"id": "ROOM", "description": "a room"}],
         "cast": [{"id": "LEAD", "identity_block": "a person"}],
         "scenes": [{"id": "S1", "section": "hook", "kind": "talking", "setting_id": "ROOM", "who": "LEAD",
                     "happens": "touches the shelf", "script": [{"speaker": "LEAD", "say": "I took it."}],
                     "first_frame": {"subject": "LEAD", "action": "hand on the shelf"},
                     "shots": [{"id": "S1.1", "face": "eyes down", "gestures": ["hand on shelf"]}],
                     "beats": [{"id": "B1", "shot": "S1.1", "do": "touches the shelf", "over": "I took it."}]}]}

FAKE = """#!{python}
import json, sys
prompt = sys.stdin.read()
with open({log!r}, "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")
if "# THIS RUN: THE STORYBOARD" in prompt:
    out = "```STORYBOARD\\n" + json.dumps({{"scenes": [{{"id": "S1", "pitches": [{{
        "title": "Security Cam", "rung": "L3", "premise": "caught on tape", "picture": "grainy cam",
        "happens": "is caught on the room's security cam taking it", "first_frame_action": "cam view of the shelf",
        "beats": [{{"id": "B1", "who": "LEAD", "action": "lifts it as the cam's red light blinks", "prop": "TUBE",
                   "where": "ROOM"}}],
        "shots": [{{"id": "S1.1", "face": "looks straight into the lens", "gestures": ["palms the tube"]}}]}}]}}]}}) + "\\n```"
elif "You are **the producer**" in prompt:
    out = "```SCORES\\n" + json.dumps({{"scenes": [{{"id": "S1", "pitches": [{{"title": "Security Cam",
        "stops": 9, "made": 9, "doctrine": 9, "controls": 9, "says_the_line": True, "problem_visible": True,
        "product_clear": True, "inside_the_scene": True, "why": "it is the confession"}}]}}]}}) + "\\n```"
else:
    out = "# The brief\\n\\n```json\\n" + json.dumps({brief}) + "\\n```\\n"
print(json.dumps({{"result": out, "usage": {{"input_tokens": 1, "output_tokens": 1}}, "total_cost_usd": 0,
                  "is_error": False}}))
"""


class DirectorInTheChain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.log = t / "calls.jsonl"
        bin_dir = t / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "claude"
        fake.write_text(FAKE.format(python=sys.executable, log=str(self.log), brief=repr(BRIEF)))
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        self.run = t / "run"
        (self.run / "stages").mkdir(parents=True)
        (self.run / "prompts").mkdir()
        (self.run / "run.json").write_text(json.dumps({"brand": "brand-a", "stages": {}}))
        names = ("PATH", "CLAUDE_CODE_OAUTH_TOKEN_CHAIN", "ANTHROPIC_API_KEY_CHAIN", "VT_CLAUDE_TIMEOUT")
        self.prev = {k: os.environ.get(k) for k in names}
        os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
        os.environ["CLAUDE_CODE_OAUTH_TOKEN_CHAIN"] = "not-a-token"
        os.environ["ANTHROPIC_API_KEY_CHAIN"] = "not-a-key"
        os.environ["VT_CLAUDE_TIMEOUT"] = "60"
        self.hand = W._HAND[0]
        W._HAND[0] = None
        W._CURRENT.clear()

    def tearDown(self):
        for k, v in self.prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        W._HAND[0] = self.hand
        W._CURRENT.clear()
        self.tmp.cleanup()

    def calls(self):
        return [json.loads(x) for x in self.log.read_text().splitlines()] if self.log.is_file() else []

    def brief(self):
        import re
        t = (self.run / "stages" / "5-brief.md").read_text()
        return json.loads(re.findall(r"```json\s*\n(.*?)\n```", t, re.S)[-1])

    def test_the_stage_5_writer_call_fires_the_director_on_its_own(self):
        W._CURRENT["key"] = "stage5"
        W.claude_v2("Write the brief.", self.run / "stages" / "5-brief.md", "opus")
        self.assertEqual(len(self.calls()), 3)                         # the writer, the director, the producer
        s1 = self.brief()["scenes"][0]
        self.assertEqual(s1["happens"], "is caught on the room's security cam taking it")
        self.assertEqual(s1["happens_swipe"], "touches the shelf")
        self.assertEqual(s1["beats"][0]["action"], "lifts it as the cam's red light blinks")
        self.assertEqual(s1["shots"][0]["face"], "looks straight into the lens")
        self.assertEqual(s1["shots"][0]["face_swipe"], "eyes down")
        self.assertEqual(s1["shots"][0]["gestures"], ["palms the tube"])
        self.assertEqual(s1["shots"][0]["gestures_swipe"], ["hand on shelf"])
        rec = W._CURRENT["director"]
        self.assertEqual((rec["state"], rec["kept"], rec["scenes"]), ("done", 1, 1))
        self.assertEqual([c["stage"] for c in W._CURRENT["calls"]].count("stage5d"), 2)
        self.assertTrue((self.run / "director" / "picks.json").is_file())
        self.assertTrue((self.run / "stages" / "5-brief.before-director.md").is_file())

    def test_the_director_runs_on_the_chains_own_door_and_tier_models(self):
        W._CURRENT["key"] = "stage5"
        W.claude_v2("Write the brief.", self.run / "stages" / "5-brief.md", "opus")
        from run_kit.model import TIERS
        argvs = self.calls()[1:]
        self.assertEqual([a[a.index("--model") + 1] for a in argvs], [TIERS["designs"], TIERS["checks"]])
        for a in argvs:
            self.assertEqual(a[a.index("--allowed-tools") + 1], "")

    def test_a_patch_or_another_pass_never_calls_it(self):
        for key in ("stage5-patch", "stage4v2b"):
            W._CURRENT.clear()
            W._CURRENT["key"] = key
            W.claude_v2("Write it.", self.run / "stages" / f"{key}.md", "opus")
            self.assertNotIn("director", W._CURRENT)
        self.assertEqual(len(self.calls()), 2)
        self.assertFalse((self.run / "director").exists())

    def test_a_brief_with_no_scene_block_is_left_alone(self):
        out = self.run / "stages" / "5-brief.md"
        out.write_text("# A creator brief\n\nno scenes here\n")
        self.assertIsNone(W.director_after("stage5", self.run, out, caller=lambda t, tier: self.fail("called")))
        self.assertEqual(out.read_text(), "# A creator brief\n\nno scenes here\n")

    def test_a_director_that_cannot_run_stops_the_stage(self):
        # owner ruling 2026-11-20: an undirected brief is never accepted; the stage fails with the reason and reruns
        out = self.run / "stages" / "5-brief.md"
        text = "# The brief\n\n```json\n" + json.dumps(BRIEF) + "\n```\n"
        out.write_text(text)

        def broken(t, tier):
            raise RuntimeError("the door is shut")
        with self.assertRaises(Exception) as got:
            W.director_after("stage5", self.run, out, caller=broken)
        self.assertIn("the door is shut", str(got.exception) + str(W._CURRENT.get("director")))
        self.assertEqual(W._CURRENT["director"]["state"], "failed")
        self.assertEqual(out.read_text(), text)                        # the brief is as stage 5 wrote it, not accepted


if __name__ == "__main__":
    unittest.main()
