"""The video editor's handoff (machine/editor_handoff.py): every file named with the brief key, a number that belongs to
another brief refused, a test run or a brief not from the writing chain's final stage refused, the finished videos back into returned/ at the same path as the repo. No network, no live run touched."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import editor_handoff as H  # noqa: E402


def reg(*rows):
    return {"briefs": {r["id"]: r for r in rows}}


VIDEO = {"id": "b_p_brief-0900", "brief": "brief-0900", "type": "video-ai", "brand": "b", "product": "p",
         "run": "test-run", "title": "Test Title"}
PICTURE = {"id": "b_p_brief-0901", "brief": "brief-0901", "type": "image-ai", "brand": "b", "product": "p",
           "run": "pic-run"}


class Package(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.vm = self.tmp / "test-run"
        (self.vm / "media").mkdir(parents=True)
        (self.vm / "vo").mkdir()
        for n in ("S1.mp4", "S2.mp4", "S1-F1.png", "S1-FLAST.png"):
            (self.vm / "media" / n).write_bytes(b"x")
        (self.vm / "vo" / "S1.mp3").write_bytes(b"x")
        (self.vm / "vo" / "track.mp3").write_bytes(b"x")
        (self.vm / "brief.md").write_text("# brief\n")
        self.final = self.tmp / "5-brief.md"
        self.final.write_text("# the final-stage brief\n")
        self._fs, H.final_stage = H.final_stage, lambda vm, run: self.final   # the chain's own record is checked below

    def tearDown(self):
        H.final_stage = self._fs

    def run_json(self, brief):
        (self.vm / "run.json").write_text(json.dumps({"brand": "b", "label": "test-run", "brief": brief}))

    def kit(self):
        m = self.vm / "media"
        return ({"clips": [
            {"scene": "S1", "section": "hook", "kind": "broll", "talks": False, "line": "First.", "approved": True,
             "src": str(m / "S1.mp4"), "voice": {"src": str(self.vm / "vo" / "S1.mp3")}},
            {"scene": "S2", "section": "cta", "kind": "talking", "talks": True, "line": "Second.", "approved": False,
             "src": str(m / "S2.mp4")}],
            "hooks": [{"id": "Opening 1", "text": "First."}, {"id": "Opening 2", "text": "Other."}],
            "overlays": [], "sfx": [], "music": None, "wanted": {}}, ["S2: not approved — director FLAG"])

    def test_every_file_starts_with_the_brief_id(self):
        self.run_json("brief-0900")
        rec = H.build(self.vm, out=self.tmp / "out", reg=reg(VIDEO), kit=self.kit())
        made = [p for p in (self.tmp / "out").rglob("*") if p.is_file() and p.parent.name not in ("returned",) and p.parent.parent.name != "briefs" and p.name not in ("handoff.md", "manifest.json")]
        self.assertTrue(made)
        for p in made:
            self.assertTrue(p.name.startswith("b_p_brief-0900-"), p.name)
        names = {f["file"] for f in rec["files"]}
        self.assertIn("assets/clips/b_p_brief-0900-S01-clip.mp4", names)
        self.assertIn("assets/stills/b_p_brief-0900-S01-start.png", names)
        self.assertIn("assets/voice/b_p_brief-0900-voice-full.mp3", names)

    def test_a_scene_the_machine_held_is_marked_look_first(self):
        self.run_json("brief-0900")
        H.build(self.vm, out=self.tmp / "out", reg=reg(VIDEO), kit=self.kit())
        notes = (self.tmp / "out" / "briefs" / "brief-0900" / "edit-notes.md").read_text()
        self.assertIn("**look first:** not approved — director FLAG", notes)
        self.assertIn("1080x1920", notes)
        self.assertIn("`b_p_brief-0900-control.mp4`", (self.tmp / "out" / "handoff.md").read_text())

    def test_missing_hook_clips_are_named(self):
        self.run_json("brief-0900")
        rec = H.build(self.vm, out=self.tmp / "out", reg=reg(VIDEO), kit=self.kit())
        self.assertTrue(any("opening clips" in m for m in rec["missing"]))

    def test_a_number_the_register_gives_a_picture_is_refused(self):
        self.run_json("brief-0901")
        with self.assertRaises(H.Refused) as e:
            H.build(self.vm, out=self.tmp / "out", reg=reg(VIDEO, PICTURE), kit=self.kit())
        self.assertIn("One number, two briefs", str(e.exception))

    def test_finished_videos_go_back_into_returned_at_the_same_path_as_the_repo(self):
        self.run_json("brief-0900")
        rec = H.build(self.vm, out=self.tmp / "out", reg=reg(VIDEO), kit=self.kit())
        home, label = H.place("b", "b_p_brief-0900")
        self.assertEqual(label, "Shared Assets/runs/handoffs/video-editor/b/b_p_brief-0900")
        self.assertTrue(str(home).endswith("runs/handoffs/video-editor/b/b_p_brief-0900"))
        self.assertEqual(rec["returned_to"], label + "/returned")
        sheet = (self.tmp / "out" / "handoff.md").read_text()
        self.assertIn(f"`{label}/returned/`", sheet)
        self.assertIn("`b_p_brief-0900-control.mp4`", sheet)
        self.assertTrue((self.tmp / "out" / "returned" / "README.md").is_file())

    def test_a_folder_another_tool_staged_is_not_written_over(self):
        self.run_json("brief-0900")
        (self.tmp / "out").mkdir()
        (self.tmp / "out" / "manifest.json").write_text(json.dumps({"via": "lab handoff skill"}))
        with self.assertRaises(H.Refused):
            H.build(self.vm, out=self.tmp / "out", reg=reg(VIDEO), kit=self.kit())

    def test_a_number_another_video_holds_is_refused(self):
        self.run_json("brief-0900")
        other = dict(VIDEO, run="another-run")
        with self.assertRaises(H.Refused) as e:
            H.build(self.vm, out=self.tmp / "out", reg=reg(other), kit=self.kit())
        self.assertIn("another video", str(e.exception))


    def test_every_made_clip_can_be_remade_in_higgsfield(self):
        self.run_json("brief-0900")
        run = json.loads((self.vm / "run.json").read_text())
        run["scene_models"] = {"S1": "seedance_2_5", "S3B": "seedance_2_5"}
        (self.vm / "run.json").write_text(json.dumps(run))
        (self.vm / "media" / "S3B-F1.png").write_bytes(b"x")
        (self.vm / "clips" / "omni" / "G01-C1").mkdir(parents=True)
        (self.vm / "clips" / "omni" / "G01-C1" / "mcp-request.json").write_text(json.dumps(
            {"prompt": "The person in image 1 speaks the line in audio 1.", "duration": 6, "resolution": "720p",
             "aspect_ratio": "9:16", "voice": str(self.vm / "vo" / "S1.mp3")}))
        (self.vm / "clips" / "plan.json").write_text(json.dumps({"calls": [
            {"id": "G01-C1", "scenes": ["S1"], "start_frame": "S1-F1", "talking": True, "prompt": "the plan's words"},
            {"id": "G02-C1-1", "scenes": ["S3B"], "start_frame": "S3B-F1", "prompt": "part one", "duration": 4},
            {"id": "G02-C1-2", "scenes": ["S3B"], "start_frame": "G02-C1-1-LAST", "prompt": "part two", "duration": 4},
            {"id": "G03-C1", "scenes": ["S4"], "prompt": ""}]}))
        rec = H.build(self.vm, out=self.tmp / "out", reg=reg(VIDEO), kit=self.kit())
        self.assertEqual([r["name"] for r in rec["higgsfield"]], ["S01", "S03B", "S03B-part2"])
        hf = self.tmp / "out" / "higgsfield"
        first = (hf / "S01" / "prompt.md").read_text()
        self.assertIn("The person in image 1 speaks the line in audio 1.", first)   # what was sent, not the plan
        self.assertIn("Seedance 2.5", first)
        self.assertTrue((hf / "S01" / "b_p_brief-0900-S01-IMAGE-1.png").is_file())
        self.assertTrue((hf / "S01" / "b_p_brief-0900-S01-AUDIO-1.mp3").is_file())
        self.assertIn("the last frame of the `S03B` clip", (hf / "S03B-part2" / "prompt.md").read_text())
        self.assertIn("higgsfield/", (self.tmp / "out" / "handoff.md").read_text())

    def test_approved_pictures_hand_off_without_clips(self):
        """L-80: a brief with approved scene pictures and no clips still hands off: the approved picture and the clip prompt
        word for word per scene; a picture remade after approval, or never approved, is left out."""
        import hashlib
        self.run_json("brief-0900")
        for n in ("S1.mp4", "S2.mp4"):
            (self.vm / "media" / n).unlink()
        (self.vm / "media" / "S1-F1.png").write_bytes(b"approved")
        (self.vm / "media" / "S3-F1.png").write_bytes(b"remade")
        (self.vm / "media" / "S5-F1.png").write_bytes(b"never")
        sha = lambda b: hashlib.sha1(b).hexdigest()[:16]
        (self.vm / "shot-approvals.json").write_text(json.dumps({
            "G01": {"picture": str(self.vm / "media" / "S1-F1.png"), "sha": sha(b"approved")},
            "G02": {"picture": str(self.vm / "media" / "S3-F1.png"), "sha": sha(b"older bytes")}}))
        (self.vm / "clips").mkdir()
        (self.vm / "clips" / "plan.json").write_text(json.dumps({"calls": [
            {"id": "G01-C1", "section_id": "G01", "section": "Section 1", "scenes": ["S1"], "start_frame": "S1-F1", "talking": True,
             "prompt": "Image 1 is the first frame. She says it.", "model": "bytedance/seedance-2.5/reference-to-video",
             "duration": 6, "resolution": "480p", "lines": [{"text": "First."}]},
            {"id": "G02-C1", "section_id": "G02", "scenes": ["S3"], "start_frame": "S3-F1", "prompt": "remade picture"},
            {"id": "G03-C1", "section_id": "G03", "scenes": ["S5"], "start_frame": "S5-F1", "prompt": "never approved"}]}))
        rec = H.build(self.vm, out=self.tmp / "out", reg=reg(VIDEO), kit=({"clips": [], "hooks": [], "overlays": [], "sfx": [],
                                                                            "music": None, "wanted": {}}, []))
        out = self.tmp / "out"
        self.assertEqual(rec["stage"], "pictures")
        self.assertEqual([r["name"] for r in rec["higgsfield"]], ["S01"])
        self.assertEqual((out / "assets" / "stills" / "b_p_brief-0900-S01-start.png").read_bytes(), b"approved")
        self.assertEqual(list((out / "assets" / "clips").iterdir()), [])
        md = (out / "higgsfield" / "S01" / "prompt.md").read_text()
        self.assertIn("Image 1 is the first frame. She says it.", md)
        self.assertIn("IMAGE-1", md)
        self.assertNotIn("remade picture", md)
        self.assertIn("the editor makes it", (out / "briefs" / "brief-0900" / "edit-notes.md").read_text())
        self.assertIn("clips, the edit, B-roll and effects are the editor's", (out / "handoff.md").read_text())

    def test_no_clips_and_no_approved_picture_is_refused(self):
        self.run_json("brief-0900")
        with self.assertRaises(H.Refused):
            H.build(self.vm, out=self.tmp / "out", reg=reg(VIDEO),
                    kit=({"clips": [], "hooks": [], "overlays": [], "sfx": [], "music": None, "wanted": {}}, []))

    def test_the_folder_carries_brief_run_sheet_and_refs(self):
        """BRIEF.md, RUN.md, run.json and refs/ ride in the folder (components/briefs runsheet.pack). The sheet names two
        tracked repo files, read only; everything is written under the temp folder."""
        self.run_json("brief-0900")
        sheet = {"brief_key": "b_p_brief-0900", "brief": "brief-0900", "brand": "b", "title": "Test Title", "product": None,
                 "brief_file": "tools/video-edit/CLAUDE.md", "built": "now", "run": "test-run",
                 "return": {"role": H.ROLE, "name_pattern": "b_p_brief-0900_asset-NN.<ext>", "repo": "x", "drive": "x"},
                 "elements": [], "gaps": [], "steps": [{
                     "n": 1, "asset": "b_p_brief-0900_asset-01.mp4", "what": "clip G01", "medium": "video",
                     "job": "clips.seedance", "model_house": {"registry": "m", "door": "higgsfield"},
                     "higgsfield_model": "seedance_2_5", "model_name": "Seedance 2.5", "prompt": "Image 1 is the first frame.",
                     "prompt_source": "the chain", "cast": [], "words_on_top": [], "bars": None, "findings": [],
                     "references": [{"n": 1, "kind": "image", "role": "the start picture", "media_role": "start_image",
                                     "file": "tools/video-edit/machine/defaults.json", "exists": True, "element": None}],
                     "settings": {"aspect_ratio": "9:16", "duration": 4, "resolution": "480p", "generate_audio": False,
                                  "endpoint": "bytedance/seedance-2.5/image-to-video", "count": 1}}]}
        out = self.tmp / "out"
        rec = H.build(self.vm, out=out, reg=reg(VIDEO), kit=self.kit(), runsheet=sheet)
        for f in ("BRIEF.md", "RUN.md", "run.json", "refs/step-01-image-1-start-picture.json"):
            self.assertTrue((out / f).is_file(), f)
        self.assertEqual(rec["runsheet"]["refs"], 1)
        r = json.loads((out / "run.json").read_text())["steps"][0]["references"][0]
        self.assertEqual(r["drive"], "Shared Assets/runs/handoffs/video-editor/b/b_p_brief-0900/refs/step-01-image-1-start-picture.json")
        self.assertIn("`refs/`", (out / "handoff.md").read_text())

    def test_scene_letters_keep_scenes_apart(self):
        self.assertEqual([H._num(s) for s in ("S3", "S3B", "S22C")], ["S03", "S03B", "S22C"])


class FinalStage(unittest.TestCase):
    def test_test_runs_are_refused_by_name(self):
        for label in ("v2test-expert-drkim", "batchtest-meme", "cellimure-doll-dryrun", "fw-v9-dry", "scratch-wiring-test"):
            with self.assertRaises(H.Refused, msg=label) as e:
                H.final_stage(Path("/x") / label, {"label": label, "brief_from": "runs/video-teardown/_work/a/stages/5-brief.md"})
            self.assertIn("test run", str(e.exception))

    def test_a_brief_that_is_not_the_writing_chains_last_stage_is_refused(self):
        with self.assertRaises(H.Refused) as e:
            H.final_stage(Path("/x/real-ad"), {"label": "real-ad", "brief_from": "runs/video-production/b/real-ad/brief-body.md"})
        self.assertIn("final stage", str(e.exception))


if __name__ == "__main__":
    unittest.main()
