import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import input_rules as IR

GOOD = ("INPUTS\nIMAGE 1 is the reference.\n\nTHE PICTURE\nA woman holds the tube.\n\nTHE FRAME\nSafe zone is the centre 4:5.\n\n"
        "RULES\nDo not change anything else in IMAGE 1. No writing in the picture except the exact words THE PICTURE gives.")


class Rules(unittest.TestCase):
    def test_every_model_file_has_status_on_every_entry(self):
        for f in (Path(IR.HERE) / "inputs").glob("*.json"):
            d = IR.load(f.stem)
            self.assertIn(d["status"], ("draft", "approved", "deprecated"))
            for k in ("inputs", "structure", "avoid"):
                for e in d[k]:
                    self.assertIn(e["status"], ("draft", "approved", "deprecated"), (f.stem, k, e))

    def test_size_rule(self):
        self.assertIsNone(IR.valid_size("1152x2048"))
        self.assertIsNone(IR.valid_size("1440x2560"))
        self.assertIn("multiples of 16", IR.valid_size("1000x1800"))
        self.assertIn("3840", IR.valid_size("4000x2000"))
        self.assertIn("3:1", IR.valid_size("1024x3200"))

    def test_a_clean_request_has_no_findings(self):
        self.assertEqual(IR.check("gpt-image-2.5", GOOD, [{"path": "/x/a.png"}], size="1152x2048", quality="high"), [])

    def test_too_many_images_is_an_error(self):
        f = IR.check("gpt-image-2.5", GOOD, [{"path": f"/x/{i}.png"} for i in range(17)], size="1152x2048")
        self.assertIn("max-images", [x["id"] for x in f if x["level"] == "error"])

    def test_an_unnumbered_image_is_a_warning(self):
        f = IR.check("gpt-image-2.5", GOOD, [{"path": "/x/a.png"}, {"path": "/x/b.png"}], size="1152x2048")
        self.assertIn("number-inputs", [x["id"] for x in f])

    def test_studio_wording_and_author_quotes_are_flagged(self):
        f = IR.check("gpt-image-2.5", GOOD + " cinematic studio lighting (the owner, 2026-10-25: x)", size="1152x2048")
        ids = [x["id"] for x in f]
        self.assertIn("studio-wording", ids)
        self.assertIn("author-quotes", ids)

    def test_bad_quality_and_size_are_errors(self):
        ids = [x["id"] for x in IR.check("gpt-image-2.5", GOOD, size="1000x1800", quality="ultra") if x["level"] == "error"]
        self.assertEqual(sorted(ids), ["quality", "size"])

    def test_render_matches_the_file(self):
        self.assertIn("up to 16", IR.render("gpt-image-2.5"))
        self.assertEqual((IR.HERE / "slices" / "gpt-image-2.5.md").read_text(), IR.render("gpt-image-2.5"))

    def test_the_model_house_job_finds_its_models_rules(self):
        self.assertEqual(IR.model_of("pictures.edit"), "gpt-image-2.5")
        self.assertEqual(IR.for_job("pictures.edit")["medium"], "image")
        self.assertEqual(IR.for_job("clips.seedance")["medium"], "video")

    def test_a_job_whose_model_has_no_file_is_refused_by_name(self):
        gaps = [c for c in IR.coverage() if not c["file"]]
        for c in gaps:
            with self.assertRaises(KeyError) as cm:
                IR.for_job(c["job"])
            self.assertIn(c["registry_id"], str(cm.exception))

    def test_coverage_covers_both_image_and_video_jobs(self):
        media = {c["medium"] for c in IR.coverage()}
        self.assertEqual(media, {"image", "video"})
        by = {c["job"]: c for c in IR.coverage()}
        self.assertTrue(by["pictures.generate"]["filled"] and by["clips.seedance"]["filled"])

    VIDEO_SHEETS = ("higgsfield-motion-control", "higgsfield-object-swap", "eleven-v3", "eleven-ttv-v3", "eleven-music-v2.5",
                    "real-esrgan", "bytedance-upscaler-video", "trellis.2-4b", "gemini-3.1-pro-preview", "suno")

    def test_every_video_job_in_the_house_is_filled_and_deep(self):
        by = {c["registry_id"]: c for c in IR.coverage(everything=True)}
        for rid in self.VIDEO_SHEETS:
            if rid == "suno":
                continue                      # by hand, not a Model House job
            self.assertIn(rid, by, rid)
            c = by[rid]
            self.assertTrue(c["file"] and c["filled"] and c["sourced"], (rid, c))
            self.assertGreaterEqual(c["counts"]["inputs"], 8, rid)
            self.assertGreaterEqual(c["counts"]["structure"], 5, rid)
            self.assertGreaterEqual(c["counts"]["avoid"], 4, rid)
            self.assertGreaterEqual(c["counts"]["qualities"], 2, rid)

    def test_default_coverage_still_lists_only_pictures_and_clips(self):
        self.assertEqual({c["medium"] for c in IR.coverage()}, {"image", "video"})
        self.assertTrue({c["medium"] for c in IR.coverage(everything=True)} > {"image", "video"})

    def test_new_sheets_are_drafts_with_a_source_on_every_rule(self):
        for rid in self.VIDEO_SHEETS:
            d = IR.load(rid)
            self.assertEqual(d["status"], "draft", rid)
            self.assertIn(d["medium"], ("video", "voice", "music", "upscale", "3d", "judge"), rid)
            for k in ("inputs", "structure", "avoid"):
                for e in d[k]:
                    self.assertTrue(e.get("source"), (rid, k, e))
                    self.assertEqual(e["status"], "draft", (rid, k, e))
            self.assertEqual(IR.HERE.joinpath("slices", rid + ".md").read_text(), IR.render(rid), rid)

    def test_motion_control_and_swap_agree_the_person_is_the_baseline_never_the_master(self):
        for rid in ("higgsfield-motion-control", "higgsfield-object-swap"):
            d = IR.load(rid)
            rules = " ".join(r["id"] + " " + r["rule"] for r in d["structure"]).lower()
            self.assertIn("baseline", rules, rid)
            self.assertNotIn("send the whole casting sheet", rules, rid)
            self.assertNotIn("full-sheet", [r["id"] for r in d["structure"]], rid)
            self.assertIn("master-as-person" if rid.endswith("control") else "master-only", [a["id"] for a in d["avoid"]])
        swap = IR.load("higgsfield-object-swap")
        self.assertIn("replaces-never-adds", [r["id"] for r in swap["structure"]])

    def test_both_genjutsu_sheets_carry_the_machine_readable_never_send_list(self):
        for rid in ("higgsfield-motion-control", "higgsfield-object-swap"):
            self.assertIn("master", IR.limits(rid)["never_send_stems"], rid)
        self.assertEqual(IR.limits("higgsfield-motion-control")["video_seconds_range"], [3, 30])
        self.assertEqual(IR.limits("higgsfield-object-swap")["min_video_seconds"], 4)

    def test_a_clip_for_motion_control_is_held_to_its_limits(self):
        ids = lambda **kw: [f["id"] for f in IR.check("higgsfield-motion-control", "Image 1 is her. Video 1 is the move.", [{"path": "/x/a.png"}], **kw) if f["level"] == "error"]
        self.assertEqual(ids(duration=12, videos=1), [])
        self.assertIn("duration", ids(duration=2, videos=1))
        self.assertIn("max-videos", ids(duration=12, videos=2))
        self.assertIn("image-format", [f["id"] for f in IR.check("higgsfield-motion-control", "Image 1", [{"path": "/x/a.gif"}])])

    def test_the_higgsfield_door_refuses_what_it_cannot_do_and_its_cheap_defaults(self):
        ids = [f["id"] for f in IR.check("gpt-image-2.5", GOOD, size="1152x2048", door="higgsfield", mask=True) if f["level"] == "error"]
        self.assertEqual(sorted(ids), ["door-defaults", "door-no-mask", "door-no-size"])
        self.assertEqual(IR.check("gpt-image-2.5", GOOD, door="higgsfield", quality="high", resolution="2k", variant="sunburst"), [])

    def test_no_brand_name_in_definitions(self):
        for f in (IR.HERE / "inputs").glob("*.json"):
            self.assertNotRegex(f.read_text().lower(), r"brand-b|brand-a|flex|crush")


if __name__ == "__main__":
    unittest.main()
