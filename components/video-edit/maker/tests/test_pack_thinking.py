"""The editor hand-off pack under the logic layer (2026-11-18): a scene the footage decision passed arrives as a file,
a scene it did not pass still goes to the maker, how the ad is made comes from the chain's one rule, and the pack
carries the thinking (idea, angle, openings, caption look, pace, the decision trail). No Drive, no ffmpeg, no model:
a whole production in a temp workspace, the source read and the cut faked."""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ENV = ("VIDEO_PRODUCTIONS", "VIDEO_STUDIO_DATA", "VIDEO_WRITING", "VIDEO_STUDIO_WRITING", "VIDEO_STUDIO_BOARD_DATA",
       "VIDEO_PRODUCTION_BOARD")


def load(name, key):
    spec = importlib.util.spec_from_file_location(key, str(HERE / (name + ".py")))
    m = importlib.util.module_from_spec(spec)
    sys.modules[key] = m
    spec.loader.exec_module(m)
    return m


def trim(step, label, clip, t_in, t_out):
    return ({"id": step, "tool": "ffmpeg.trim", "inputs": {"source": "slot:" + step, "in": t_in, "out": t_out}, "params": {}},
            {step: {"file": Path(label).name, "drive_location": label, "clip_id": clip, "creator": "a creator"}})


class Pack(unittest.TestCase):
    def setUp(self):
        self.saved = {k: os.environ.pop(k) for k in ENV if k in os.environ}
        for k in [k for k in sys.modules if k.startswith(("video_edit_maker_", "maker_chain_"))]:
            sys.modules.pop(k)
        self.ws = Path(tempfile.mkdtemp(prefix="mp_ws_")).resolve()
        (self.ws / "components").mkdir()
        self.prod = self.ws / "prod"
        self.W = self.ws / "runs" / "video-teardown" / "_work" / "b-run-1"
        (self.W / "stages").mkdir(parents=True)
        os.environ["VIDEO_PRODUCTIONS"] = str(self.prod)
        os.environ["VIDEO_WRITING"] = str(self.W.parent)
        os.environ["VIDEO_STUDIO_BOARD_DATA"] = str(self.ws / "board")
        self.mp = load("maker_pack", "video_edit_maker_maker_pack")
        self.mp._here("maker_timeline").build = lambda out: None          # the pages and edit files are not under test
        self.mp._here("maker_editfiles").build = lambda out: None
        self.cuts = []
        OC = self.mp._chain("video-production", "owned_clips")
        OC.readable = lambda ref: Path(ref)
        OC.cut = lambda src, a, b, dst: (self.cuts.append((str(src), a, b)), Path(dst).parent.mkdir(parents=True, exist_ok=True),
                                        Path(dst).write_bytes(b"ours"))

    def tearDown(self):
        for k in ENV:
            os.environ.pop(k, None)
        os.environ.update(self.saved)
        shutil.rmtree(self.ws, ignore_errors=True)

    # ------------------------------------------------------------ a production on disk
    def production(self, lane="mix", scenes=None, footage=None, trail=None, with_lane=True):
        n = "idea-9"
        B = self.prod / n
        scenes = scenes or self.three_scenes()
        brief = {"brief": "b-run-1", "idea": n, "title": "The Test Ad", "order": list(scenes), "picks": {s: "take-1" for s in scenes},
                 "style": {"id": "phone-ugc"}, "deliver": {"width": 1080, "height": 1920},
                 "trail": [{"at": "2026-11-18T03:00:00+00:00", "stage": "production", "decision": "how the ad is made",
                            "choice": lane, "why": "the footage decision passed 2 of 3 shot(s)", "by": "the chain"}]}
        if with_lane:
            brief.update(lane=lane, lane_why="the footage decision passed 2 of 3 shot(s)", lane_by="the chain")
        for s, (steps, sources, made) in scenes.items():
            d = B / "scenes" / s
            d.mkdir(parents=True)
            (d / "take-1.json").write_text(json.dumps({"title": s, "words": "", "steps": steps, "sources": sources}))
            if made:
                (d / "out" / "take-1").mkdir(parents=True)
                (d / "out" / "take-1" / (s + ".mp4")).write_bytes(b"studio cut")
        (B / "brief.json").write_text(json.dumps(brief))
        (self.W / "run.json").write_text(json.dumps({
            "brand": "b", "product": "p", "format_id": "remedy",
            "trail": trail if trail is not None else [
                {"at": "2026-11-18T01:00:00+00:00", "stage": "pick", "decision": "which post", "choice": "the top shared post",
                 "why": "comments level with likes", "by": "the feed rule"}]}))
        doc = {"piece": {"angle": "the tool reaches what hands cannot", "avatar": "the-avatar", "awareness": "problem-aware",
                         "format": "remedy"},
               "hooks": [{"id": "Opening 1 · Control", "text": "Your hands were never going to reach it.", "take": "control", "opener_scene": "S1"},
                         {"id": "Opening 2 · V1", "text": "I tried everything first.", "take": "what he tried"}],
               "layers": {"captions": {"look": ""}}, "scenes": []}
        (self.W / "stages" / "5-brief.md").write_text("# brief\n\n```json\n" + json.dumps(doc) + "\n```\n")
        (self.W / "stages" / "4i-controlling-idea.md").write_text(
            "### THE CONTROLLING IDEA\nHis own hands hand the job to the tool.\n\n### THE LINE IT TURNS ON\n\"x\"\n")
        footage = footage if footage is not None else {
            "S1": {"plan": "cut", "clip": {"shared_path": "Shared Assets/x/a.mp4", "clip_id": "a", "in": 1.0, "out": 3.0}},
            "S3": {"plan": "cut", "clip": {"shared_path": "Shared Assets/x/c.mp4", "clip_id": "c", "in": 0.5, "out": 2.5}},
            "S2": {"plan": "generate", "nearest": {"shared_path": "Shared Assets/x/b.mp4", "clip_id": "b"}}}
        (self.W / "stages" / "storyboard-footage.json").write_text(json.dumps({"scenes": footage}))
        (self.ws / "board" / "handoff-requests").mkdir(parents=True, exist_ok=True)
        (self.ws / "board" / "handoff-requests" / (n + ".json")).write_text(json.dumps({"scenes": [
            {"id": "S2", "happens": "he rinses the tool", "source": "0:02.0 - 0:04.0 · B · rinse",
             "swipeShots": [{"k": "K02", "len": 2.0, "does": "rinses the tool"}]}]}))
        return n

    def three_scenes(self):
        s1, src1 = trim("shot-1", "Shared Assets/x/a.mp4", "a", 1.0, 3.0)      # passed, and the Studio has cut it
        s2, src2 = trim("shot-1", "Shared Assets/x/b.mp4", "b", 0.0, 2.0)      # our closest clip, NOT passed (a Real pass)
        s3, src3 = trim("shot-1", "Shared Assets/x/c.mp4", "c", 0.5, 2.5)      # passed, never cut by the Studio
        return {"S1": ([s1], src1, True), "S2": ([s2], src2, True), "S3": ([s3], src3, False)}

    def build(self, n):
        rec = self.mp.build(n, drive=False)
        out = Path(rec["folder"])
        return rec, out, json.loads((out / "clips.json").read_text())

    # ------------------------------------------------------------ our footage reaches the editor
    def test_a_passed_scene_the_studio_cut_arrives_as_made(self):
        rec, out, doc = self.build(self.production())
        s1 = next(r for r in doc["scenes"] if r["scene"] == "S1")
        self.assertEqual((s1["status"], s1["file"]), ("made", "made/01-S1.mp4"))
        self.assertEqual((out / "made" / "01-S1.mp4").read_bytes(), b"studio cut")
        self.assertIn("passed by the footage decision", s1["why"])
        self.assertEqual(s1["ours"][0]["file"], "Shared Assets/x/a.mp4")

    def test_a_passed_scene_never_cut_is_cut_here_so_it_still_arrives_as_a_file(self):
        rec, out, doc = self.build(self.production())
        s3 = next(r for r in doc["scenes"] if r["scene"] == "S3")
        self.assertEqual((s3["status"], s3["file"]), ("made", "made/03-S3.mp4"))
        self.assertEqual((out / "made" / "03-S3.mp4").read_bytes(), b"ours")
        self.assertEqual(self.cuts, [("Shared Assets/x/c.mp4", 0.5, 2.5)])

    def test_a_scene_the_decision_did_not_pass_still_goes_to_the_maker(self):
        rec, out, doc = self.build(self.production())
        s2 = next(r for r in doc["scenes"] if r["scene"] == "S2")
        self.assertEqual(s2["status"], "needs clips")
        self.assertNotIn("file", s2)
        clip = next(c for c in doc["clips"] if c["scene"] == "S2")
        self.assertEqual(clip["our_cut"], "ours-reference/02-S2.mp4", "our cut rides along as a reference only")
        self.assertIn("not passed by the footage decision", s2["why"])
        self.assertEqual(rec["made"], 2)

    def test_the_ai_lane_is_unchanged_every_shot_is_made(self):
        rec, out, doc = self.build(self.production(lane="ai"))
        self.assertEqual([r.get("file") for r in doc["scenes"]], [None, None, None])
        self.assertEqual(self.cuts, [])

    def test_the_real_lane_is_unchanged_our_cut_on_every_shot(self):
        rec, out, doc = self.build(self.production(lane="real"))
        self.assertEqual([r.get("file") for r in doc["scenes"]], ["made/01-S1.mp4", "made/02-S2.mp4", None])

    def test_a_captioned_pass_never_counts(self):
        footage = {"S1": {"plan": "cut", "clip": {"shared_path": "Shared Assets/x/a.mp4", "clip_id": "a", "text_marks": ["caption"]}}}
        self.assertEqual(self.mp.passed_clips(footage), set())
        footage["S1"]["clip"]["text_marks"] = ["clean"]
        self.assertEqual(self.mp.passed_clips(footage), {("Shared Assets/x/a.mp4", "a")})

    def test_a_clip_that_cannot_be_read_is_said_on_its_row_and_the_pack_still_builds(self):
        OC = self.mp._chain("video-production", "owned_clips")

        def gone(ref):
            raise FileNotFoundError("not on the Drive")
        OC.readable = gone
        rec, out, doc = self.build(self.production())
        s3 = next(r for r in doc["scenes"] if r["scene"] == "S3")
        self.assertEqual(s3["status"], "our footage: not cut yet")
        self.assertIn("could not be read or cut", s3["ours_note"])
        self.assertEqual(s3["ours"][0]["in"], 0.5, "the source and its times ride along so nobody has to find them")

    # ------------------------------------------------------------ how the ad is made: the chain's call
    def test_the_lane_and_its_reason_come_from_the_chain(self):
        rec, out, doc = self.build(self.production())
        self.assertEqual((doc["lane"], doc["lane_by"]), ("mix", "the chain"))
        self.assertIn("passed 2 of 3", doc["lane_why"])
        self.assertIn("- Lane: AI + Real", (out / "CLIPS.md").read_text())

    def test_a_production_with_no_lane_reads_as_every_other_tool_reads_it(self):
        """This builder printed "AI (every shot made)" for a production the Studio's own tools read as real."""
        rec, out, doc = self.build(self.production(with_lane=False))
        self.assertEqual(doc["lane"], "real")
        self.assertIn("- Lane: Real", (out / "CLIPS.md").read_text())
        self.assertEqual([r.get("file") for r in doc["scenes"]], ["made/01-S1.mp4", "made/02-S2.mp4", None])

    # ------------------------------------------------------------ the pack carries the thinking
    def test_clips_json_carries_idea_angle_openings_look_pace_and_trail(self):
        doc = self.build(self.production())[2]
        th = doc["thinking"]
        self.assertEqual(th["idea"], "His own hands hand the job to the tool.")
        self.assertEqual(th["angle"], "the tool reaches what hands cannot")
        self.assertIsNone(th["concept"], "no concept is named upstream yet: said as none, never invented")
        self.assertEqual([h["id"] for h in doc["hooks"]], ["Opening 1 · Control", "Opening 2 · V1"])
        self.assertEqual((doc["caption_look"]["look"], doc["caption_look"]["by"]), ("edits-glow", "the format"))
        self.assertEqual((doc["pace"]["name"], doc["pace"]["by"]), ("whole-breathing", "the format"))
        self.assertEqual([r["stage"] for r in doc["trail"]], ["pick", "production"], "every stage's rows, oldest first")

    def test_the_clip_page_says_why_the_ad_is_built_this_way(self):
        out = self.build(self.production())[1]
        text = (out / "CLIPS.md").read_text()
        for must in ("## Why this ad is built this way", "**Idea:** His own hands hand the job to the tool.",
                     "**Angle:** the tool reaches what hands cannot", "**Caption look:** Edits glow",
                     "**Pace:** whole-breathing", "### The openings", "Your hands were never going to reach it.",
                     "### How we got here", "comments level with likes"):
            self.assertIn(must, text)

    def test_the_brief_page_gets_the_thinking_once(self):
        out = self.build(self.production())[1]
        th = json.loads((out / "clips.json").read_text())["thinking"]
        (out / "BRIEF.md").write_text("# The run sheet's own brief\n\nWhat to make.\n")
        self.mp._into_brief(out, th)
        self.mp._into_brief(out, th)                                   # a rebuilt pack does not stack it
        text = (out / "BRIEF.md").read_text()
        self.assertTrue(text.startswith("# The run sheet's own brief"))
        self.assertEqual(text.count("## Why this ad is built this way"), 1)
        self.assertIn("**How it is made:** AI + Real", text)

    def test_no_trail_on_file_is_said_as_none(self):
        n = self.production(trail=[])
        b = self.prod / n / "brief.json"
        d = json.loads(b.read_text())
        d.pop("trail")
        b.write_text(json.dumps(d))
        out = self.build(n)[1]
        self.assertIn("No decision trail is on file for this brief yet.", (out / "CLIPS.md").read_text())


if __name__ == "__main__":
    unittest.main()
