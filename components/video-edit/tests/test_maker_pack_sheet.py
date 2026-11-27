"""The maker pack keeps ONE list of clips: the run sheet is rebuilt from clips.json (cold run of brief 0369, 18 Nov
2026: RUN.md asked for 52 assets under scene names while CLIPS.md asked for 30 clips under clip names). No network."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "maker"))
import maker_pack as MP  # noqa: E402


class _RS:
    @staticmethod
    def render_md(s):
        return "\n".join("### Step %d · `%s` · %s" % (st["n"], st["asset"], st["what"]) for st in s["steps"]) + "\n"


def _pack(root):
    out = Path(root)
    key = "acme_widget_brief-0001"
    steps = []
    for i, sc in enumerate(["S1", "S2"]):
        steps.append({"n": 2 * i + 1, "asset": "%s_asset-%02d.png" % (key, 2 * i + 1), "what": "start picture for %s" % sc,
                      "medium": "image", "job": "3d-print", "prompt": "draft", "references": [],
                      "print": {"credits": 2.5, "reference": ["x.png"]}})
        steps.append({"n": 2 * i + 2, "asset": "%s_asset-%02d.mp4" % (key, 2 * i + 2), "what": "clip for %s · silent" % sc,
                      "medium": "video", "job": "clips.seedance", "prompt": "draft",
                      "references": [{"n": 1, "role": "the start picture", "media_role": "start_image", "file": "?"}],
                      "settings": {"duration": 5}})
    (out / "run.json").write_text(json.dumps({"steps": steps, "gaps": ["No video production run for this brief yet, so "
                                              "every prompt here is a DRAFT from the brief"],
                                              "elements": [{"name": "ANN", "covers": ["step 3 IMAGE 1", "step 4"]},
                                                           {"name": "BOB", "kind": "cast", "covers": ["step 3 IMAGE 2", "step 4"]}],
                                              "handoff": {"folder": "runs/handoffs/x", "drive": "Shared Assets/runs/handoffs/x",
                                                          "refs": []}}))
    rec = ("One continuous clip in KITCHEN, 1 shot in order:\n  1. 4.0–6.0 s · under “a line” · ANN pours tea · face: calm"
           " · camera: handheld\nLook: soft 3D\nWardrobe: ANN in apron")
    clips = [{"id": "S1", "brief_scene": "S1", "tool": "gen.take", "recipe": rec, "secs": 4.2, "who": ["ANN"],
              "where": "KITCHEN", "return": "returned/%s_asset-02.mp4" % key, "start_words": "first S1"},
             {"id": "S2.1-2", "brief_scene": "S2", "tool": "gen.take", "recipe": rec, "secs": 7.6, "who": ["ANN"],
              "where": "KITCHEN", "return": "returned/%s_asset-04-shots1-2.mp4" % key, "print_board": "refs/S2.1-2/print-board.png"},
             {"id": "S2.3", "brief_scene": "S2", "tool": "gen.take", "recipe": rec + "\n  6.0–7.0 s · no line sung here: keep it moving",
              "secs": 2.1, "who": ["ANN"], "where": "KITCHEN", "return": "returned/%s_asset-04-shot3.mp4" % key},
             {"id": "END-card", "tool": "edit", "return": "returned/%s_end-card.mp4" % key}]
    (out / "clips.json").write_text(json.dumps({"clips": clips}))
    return out


class OneListOfClips(unittest.TestCase):
    def test_the_sheet_is_rebuilt_clip_by_clip(self):
        with tempfile.TemporaryDirectory() as t:
            out = _pack(t)
            self.assertTrue(MP._clips_into_sheet(out, _RS))
            s = json.loads((out / "run.json").read_text())
            vids = [st for st in s["steps"] if st["medium"] == "video"]
            self.assertEqual([Path(v["asset"]).name for v in vids], ["acme_widget_brief-0001_asset-02.mp4",
                             "acme_widget_brief-0001_asset-04-shots1-2.mp4", "acme_widget_brief-0001_asset-04-shot3.mp4"])
            self.assertEqual([st["n"] for st in s["steps"]], list(range(1, 7)))
            self.assertIn("acme_widget_brief-0001_asset-03-shot3.png", [st["asset"] for st in s["steps"]])
            self.assertIn("ANN pours tea", vids[1]["prompt"])           # the recipe, word for word
            self.assertNotIn("no line sung here", vids[2]["prompt"])    # an edit note never reaches the model
            self.assertEqual([v["settings"]["duration"] for v in vids], [5, 8, 4])
            self.assertIn("step 3 makes it", vids[1]["references"][0]["file"])
            self.assertEqual(s["steps"][2]["print"]["reference"], ["refs/S2.1-2/print-board.png"])
            self.assertFalse([g for g in s["gaps"] if "DRAFT" in g])
            self.assertEqual(s["elements"][0]["covers"], ["step 3 (on its print board)", "step 5 (on its print board)",
                                                          "step 4", "step 6"])
            self.assertIn("clip for S2.3", (out / "RUN.md").read_text())
            self.assertEqual(s["elements"][1]["covers"], [])          # BOB is in none of these clips

    def test_a_pack_with_no_sung_clips_is_left_alone(self):
        with tempfile.TemporaryDirectory() as t:
            out = _pack(t)
            (out / "clips.json").write_text(json.dumps({"clips": [{"id": "S1-shot-1", "tool": "gen.shot"}]}))
            before = (out / "run.json").read_text()
            self.assertFalse(MP._clips_into_sheet(out, _RS))
            self.assertEqual((out / "run.json").read_text(), before)

    def test_ordinary_shots_keep_cast_and_edit_only_scenes_leave_no_generation_steps(self):
        with tempfile.TemporaryDirectory() as t:
            out = _pack(t)
            sheet = json.loads((out / "run.json").read_text())
            sheet["steps"][1]["cast"] = [{"who": "ANN"}]
            sheet["elements"][1]["covers"] = ["step 2", "step 4"]
            (out / "run.json").write_text(json.dumps(sheet))
            (out / "clips.json").write_text(json.dumps({"clips": [
                {"id": "S1-shot-1", "brief_scene": "S1", "tool": "gen.shot", "recipe": "ANN pours tea",
                 "return": "returned/acme_widget_brief-0001_asset-02-shot-1.mp4"},
                {"id": "S1-shot-2", "brief_scene": "S1", "tool": "gen.shot", "recipe": "ANN sets down the cup",
                 "return": "returned/acme_widget_brief-0001_asset-02-shot-2.mp4"},
                {"id": "S2-shot-1", "brief_scene": "S2", "tool": "edit"}]}))
            self.assertTrue(MP._clips_into_sheet(out, _RS))
            result = json.loads((out / "run.json").read_text())
            videos = [s for s in result["steps"] if s["medium"] == "video"]
            self.assertEqual(len(videos), 2)
            self.assertEqual(len({s["asset"] for s in result["steps"]}), 4)
            self.assertEqual([s["cast"] for s in videos], [[{"who": "ANN"}], [{"who": "ANN"}]])
            self.assertEqual(result["elements"][1]["covers"], ["step 2", "step 4"])
            self.assertFalse(any("for S2" in s["what"] for s in result["steps"]))

    def test_missing_ordinary_recipe_stays_a_draft(self):
        with tempfile.TemporaryDirectory() as t:
            out = _pack(t)
            (out / "clips.json").write_text(json.dumps({"clips": [
                {"id": "S1-shot-1", "brief_scene": "S1", "tool": "gen.shot", "recipe": "",
                 "return": "returned/acme_widget_brief-0001_asset-02.mp4"}]}))
            MP._clips_into_sheet(out, _RS)
            result = json.loads((out / "run.json").read_text())
            v = next(s for s in result["steps"] if s["what"].startswith("clip for S1-shot-1"))
            self.assertTrue(v["draft"])
            self.assertEqual(v["prompt"], "draft")
            self.assertIn("missing recipe", v["prompt_source"])

    def test_the_start_words_are_the_first_shot_without_its_clock(self):
        rec = ("One continuous clip in KITCHEN, 2 shots in order:\n  1. 4.0–6.0 s · under “a line” · ANN pours tea · "
               "face: calm · camera: handheld\n  2. 6.0–8.0 s · ANN sits\nLook: soft 3D\nWardrobe: ANN in apron")
        w = MP._first_shot_words({"recipe": rec, "where": "KITCHEN"})
        self.assertIn("ANN pours tea · face: calm", w)
        self.assertNotIn("4.0–6.0", w)
        self.assertNotIn("a line", w)
        self.assertNotIn("ANN sits", w)
        self.assertIn("Wardrobe: ANN in apron", w)
        self.assertIn("Look: soft 3D", w)


if __name__ == "__main__":
    unittest.main()
