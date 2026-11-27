#!/usr/bin/env python3
"""The clip rules (clip_rules.py, CLIP-RULES.md): who speaks is who is in frame, a render gets a render prompt and never
mixes with live action, the product is never drawn without its photo, the beats match the picture. The picture read is
faked here; nothing is called.

    python3 components/video-production/machine/test_clip_rules.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clip_rules as CR  # noqa: E402

PROMPT = ("Image 1 is the first frame and shows the person: keep this exact person.\n\n"
          "Native phone-camera footage: available room light. The person talks to the camera.\n\n"
          "0-8s: The person moves the way they always does.\n\n"
          "CAMERA AND MOTION (the director's plan for S1, \"Idea\"):\nCamera: S1.1: front, hold.\n\n"
          "Constant throughout: one continuous take. Marks kept exactly as in Image 1: a scar on her wrist. "
          "Nobody speaks.")


class ClipRules(unittest.TestCase):
    def setUp(self):
        self.run = Path(tempfile.mkdtemp(prefix="cliprules_"))
        (self.run / "media").mkdir()
        (self.run / "clips").mkdir()
        for k in ("S1-F1", "S2-F1", "S3-F1"):
            (self.run / "media" / f"{k}.png").write_bytes(k.encode())
        (self.run / "brief.md").write_text("```json\n" + json.dumps({"cast": [{"id": "lead"}, {"id": "friend"}]}) + "\n```\n")
        self.reads = {b"S1-F1": {"people": ["friend"], "faces": ["friend"], "render": False, "contradicts": []},
                      b"S2-F1": {"people": [], "faces": [], "render": True, "contradicts": []},
                      b"S3-F1": {"people": ["friend"], "faces": ["friend"], "render": False,
                                 "contradicts": [{"beat": "B1", "kind": "done", "why": "the jacket is already off"},
                                                 {"beat": "B2", "kind": "impossible", "why": "the bowl holds powder"},
                                                 {"beat": "B9", "kind": "done", "why": "the lid is already open"}]}}

    def ask(self, q, pics):
        return self.reads[Path(pics[0]).read_bytes()]

    def plan(self, calls):
        (self.run / "clips" / "plan.json").write_text(json.dumps({"calls": calls, "problems": []}))

    def call(self, cid, start, **kw):
        c = {"id": cid, "scenes": [start.split("-")[0]], "start_frame": start, "prompt": PROMPT,
             "seedance": {"prompt": PROMPT}, "params": {"prompt": PROMPT}, "people": ["lead"], "image_refs": []}
        c.update(kw)
        return c

    def test_1_a_speaker_not_in_frame_is_refused(self):
        self.plan([self.call("C1", "S1-F1", talking=True, voice_parts=[{"person": "lead"}])])
        added = CR.apply(self.run, ask=self.ask)
        self.assertTrue(any("CLIP RULE 1" in p and "lead" in p for p in added), added)

    def test_1_a_silent_call_loses_marks_of_someone_not_in_frame(self):
        self.plan([self.call("C1", "S1-F1", talking=False)])
        CR.apply(self.run, ask=self.ask)
        c = json.loads((self.run / "clips" / "plan.json").read_text())["calls"][0]
        self.assertNotIn("Marks kept", c["prompt"])
        self.assertEqual(c["prompt"], c["seedance"]["prompt"])

    def test_2_a_render_gets_the_render_prompt(self):
        self.plan([self.call("C2", "S2-F1", talking=False)])
        added = CR.apply(self.run, ask=self.ask)
        c = json.loads((self.run / "clips" / "plan.json").read_text())["calls"][0]
        self.assertEqual(added, [])
        self.assertIn("explainer render", c["prompt"])
        self.assertIn("CAMERA AND MOTION", c["prompt"])
        self.assertNotIn("phone-camera", c["prompt"])
        self.assertNotIn("talks to the camera", c["prompt"])
        self.assertEqual(c["prompt"], c["params"]["prompt"])                     # the gate's SENT check holds

    def test_2_a_render_never_says_an_overlay_word(self):
        out = CR.render_prompt("Image 1 is x.\n\nCAMERA AND MOTION (the director's plan for S2, \"I\"):\n"
                               "Camera: S2.1: close cross-section view, push-in.")
        self.assertNotIn("cross-section", out)
        self.assertIn("close cut-away view", out)

    def test_2_a_render_that_talks_or_mixes_live_action_is_refused(self):
        (self.run / "media" / "S2-shot-2.png").write_bytes(b"S1-F1")             # a live picture as a later shot
        rel = str((self.run / "media" / "S2-shot-2.png").resolve().relative_to(CR.WS.resolve())) \
            if str(self.run.resolve()).startswith(str(CR.WS.resolve())) else None
        shots = [{"shot": "S2.2", "file": rel}] if rel else []
        self.plan([self.call("C2", "S2-F1", talking=True, voice_parts=[{"person": "lead"}], shot_pictures=shots)])
        added = CR.apply(self.run, ask=self.ask)
        self.assertTrue(any("CLIP RULE 2" in p and "talk" in p for p in added), added)

    def test_3_a_product_line_without_its_photo_is_refused(self):
        self.plan([self.call("C1", "S1-F1", prompt=PROMPT + " The real product is 15.2 cm tall: draw it at that true size.")])
        added = CR.apply(self.run, dry=True)
        self.assertTrue(any("CLIP RULE 3" in p for p in added), added)
        self.plan([self.call("C1", "S1-F1", prompt=PROMPT + " The real product is 15.2 cm tall.",
                             image_refs=[{"file": "runs/x/products/p/photo.png", "job": "the real product"}])])
        self.assertEqual([p for p in CR.apply(self.run, dry=True) if "RULE 3" in p], [])

    def test_4_a_beat_already_done_is_dropped_an_absurd_one_kept_an_unfound_one_refused(self):
        block = ("CAMERA AND MOTION (the director's plan for S3, \"Idea\"):\nCamera: S3.1: front, hold.\n"
                 "Beat by beat, each one moving: B1 slips off the jacket; B2 a boulder rolls out of the bowl.")
        pr = PROMPT.replace("CAMERA AND MOTION (the director's plan for S1, \"Idea\"):\nCamera: S1.1: front, hold.", block)
        self.plan([self.call("C3", "S3-F1", talking=False, people=["friend"], prompt=pr)])
        added = CR.apply(self.run, ask=self.ask)
        c = json.loads((self.run / "clips" / "plan.json").read_text())["calls"][0]
        self.assertNotIn("slips off the jacket", c["prompt"])                       # done before the clip: dropped
        self.assertIn("a boulder rolls out of the bowl", c["prompt"])              # absurd on purpose: kept, noted
        self.assertEqual([x["beat"] for x in c["dropped_beats"]], ["B1"])
        self.assertEqual([x["beat"] for x in c["beat_notes"]], ["B2"])
        self.assertTrue(any("CLIP RULE 4" in p and "B9" in p for p in added), added)   # not in the plan: refused
        again = CR.apply(self.run, ask=self.ask)                                    # a second pass changes nothing
        self.assertFalse(any("B1" in p for p in again), again)
        self.assertEqual(len(json.loads((self.run / "clips" / "plan.json").read_text())["calls"][0]["beat_notes"]), 1)

    def test_a_silent_call_loses_every_talking_word_and_the_talking_movement_video(self):
        pr = ("Image 1 is the first frame and shows her.\n"
              "Video 1 is a real person's movement only: copy how the head moves while talking and the mouth.\n"
              "Video 2 is a real person using a product, for the movement only.\n\n"
              "Native phone-camera footage, nothing styled. The person talks to the camera, static phone frame.\n\n"
              "CAMERA AND MOTION (the director's plan for S1, \"Idea\"):\nBeat by beat, each one moving: B1 over \"she said\": "
              "she lifts the cup.\n\nConstant throughout: one take. Nobody speaks; mouths stay closed. Their head nods with "
              "their words.")
        c = {"id": "C1", "prompt": pr, "talking": False, "endpoint": "reference-to-video",
             "refs": [{"kind": "movement", "file": "a.mp4"}, {"kind": "movement", "file": "b.mp4"}]}
        gone = CR.silent_clean(c)
        self.assertEqual([g["file"] for g in gone], ["a.mp4"])
        self.assertNotIn("talks to the camera", c["prompt"])
        self.assertNotIn("while talking", c["prompt"])
        self.assertNotIn("with their words", c["prompt"])
        self.assertIn("Video 1 is a real person using a product", c["prompt"])          # renumbered in send order
        self.assertIn("Nobody speaks; mouths stay closed.", c["prompt"])                # a silence is kept
        self.assertIn('over "she said"', c["prompt"])                                   # the beat's words are kept

    def test_a_product_lookalike_is_named_as_not_the_product(self):
        self.reads[b"S1-F1"] = dict(self.reads[b"S1-F1"], lookalikes=["three cream discs"])
        self.plan([self.call("C1", "S1-F1", talking=False, people=["friend"])])
        CR.apply(self.run, ask=self.ask)
        c = json.loads((self.run / "clips" / "plan.json").read_text())["calls"][0]
        self.assertIn("(the three cream discs) stay exactly as they are in the picture", c["prompt"])

    def test_a_dry_run_reads_no_picture_and_reads_are_kept(self):
        self.plan([self.call("C1", "S1-F1")])
        CR.apply(self.run, dry=True, ask=lambda *a: self.fail("a dry run asked"))
        self.plan([self.call("C1", "S1-F1")])
        CR.apply(self.run, ask=self.ask)
        CR.apply(self.run, ask=lambda *a: self.fail("asked twice for the same picture"))

    def test_6_every_call_says_nothing_is_added_that_is_not_in_the_picture(self):
        self.plan([self.call("C1", "S1-F1")])
        CR.apply(self.run, dry=True)
        c = json.loads((self.run / "clips" / "plan.json").read_text())["calls"][0]
        self.assertIn("no container, tube, jar", c["prompt"])
        self.assertEqual(c["prompt"].count(CR.NO_ADD_MARK), 1)
        CR.apply(self.run, dry=True)                                                 # idempotent
        c = json.loads((self.run / "clips" / "plan.json").read_text())["calls"][0]
        self.assertEqual(c["prompt"].count(CR.NO_ADD_MARK), 1)
        self.assertEqual(c["prompt"], c["seedance"]["prompt"])

    def test_7_no_words_or_arrow_on_screen_and_no_quoted_line_to_draw(self):
        pr = ("Image 1 is the first frame.\nVideo 1 is movement only: no words or subtitles.\n\n"
              "6.4-10.0s, as the person starts \"Tap below to\u2026\": The person points.\n"
              "At the end of the take: she holds the book. Only Tap below to buy and its arrow remain as added "
              "typography.\n\nConstant throughout: one take.")
        out = CR.no_text(pr)
        self.assertNotIn("Tap below", out)
        self.assertIn("6.4-10.0s: The person points.", out)
        self.assertIn("she holds the book.", out)
        self.assertIn("no words or subtitles", out)                                  # a sentence that forbids stays
        self.assertIn(CR.NO_TEXT_MARK, out)
        self.assertLess(out.index(CR.NO_TEXT_MARK), out.index("Constant throughout"))

    def test_8_a_listener_never_speaks_and_a_shot_without_the_speaker_is_a_stop(self):
        self.reads[b"S1-F1"] = {"people": ["lead", "friend"], "faces": ["lead", "friend"], "render": False,
                                "contradicts": []}
        self.plan([self.call("C1", "S1-F1", talking=True, voice_parts=[{"person": "lead"}])])
        added = CR.apply(self.run, ask=self.ask)
        c = json.loads((self.run / "clips" / "plan.json").read_text())["calls"][0]
        self.assertIn("friend never speaks: lips closed", c["prompt"])
        self.assertFalse(any("RULE 8" in p for p in added), added)
        shot = self.run / "media" / "S1-shot-2.png"
        shot.write_bytes(b"S3-F1")                                                   # shows only the friend
        if str(self.run.resolve()).startswith(str(CR.WS.resolve())):
            rel = str(shot.resolve().relative_to(CR.WS.resolve()))
            self.plan([self.call("C1", "S1-F1", talking=True, voice_parts=[{"person": "lead"}],
                                 shot_pictures=[{"shot": "S1.2", "file": rel}])])
            added = CR.apply(self.run, ask=self.ask)
            self.assertTrue(any("RULE 8" in p for p in added), added)

    def test_9_a_render_keeps_its_liquids_liquid_and_its_surface_on(self):
        out = CR.render_prompt("Image 1 is x.\n\nCAMERA AND MOTION (the director's plan for S6, \"I\"):\nCamera: S6.1: hold.")
        self.assertIn("nothing grows, sprouts, forms fibres".lower(), out.lower())
        self.assertIn("nothing lifts, peels", out)

    def test_11_a_call_without_its_casting_files_is_refused(self):
        import importlib.util
        from unittest import mock
        sheet = {"file": "runs/ai-elements/b/products/p/model/product-sheet.png", "job": "the real p"}
        head = {"file": "runs/ai-elements/b/casting/lead/headshot.png", "job": "lead"}
        fake = mock.MagicMock()
        fake.for_call.return_value = [head, sheet]
        real = CR._load
        with mock.patch.object(CR, "_load", lambda n: fake if n == "clip_refs" else real(n)):
            self.plan([self.call("C1", "S1-F1")])
            self.assertTrue(any("RULE 11" in x for x in CR.apply(self.run, dry=True)))
            self.plan([self.call("C1", "S1-F1", image_refs=[head])])           # the product sheet left out
            self.assertTrue(any("RULE 11" in x and "product-sheet" in x for x in CR.apply(self.run, dry=True)))
            self.plan([self.call("C1", "S1-F1", image_refs=[head, sheet])])
            self.assertFalse(any("RULE 11" in x for x in CR.apply(self.run, dry=True)))
            c = json.loads((self.run / "clips" / "plan.json").read_text())["calls"][0]
            self.assertIn("The product is exactly the one in its reference pictures", c["prompt"])  # rule 6 with the product
            self.assertNotIn("label, packaging or product appears", c["prompt"])

    def test_every_call_talking_or_silent_gets_the_chains_references(self):
        from unittest import mock
        cr = CR._load("clip_refs")
        head = {"file": "components/CLAUDE.md", "job": "a person"}
        prod = {"file": "CLAUDE.md", "job": "the product"}
        with mock.patch.object(cr, "person_refs", return_value=[head]), \
                mock.patch.object(cr, "product_refs", return_value=[prod]), \
                mock.patch.object(cr, "prop_refs", return_value=[]), mock.patch.object(cr, "picture_refs", return_value=[]), \
                mock.patch.object(cr, "limit", return_value=29):
            silent = cr.for_call(self.run, {"talking": False}, CR.WS)
            self.assertEqual([r["file"] for r in silent], ["components/CLAUDE.md", "CLAUDE.md"])
            long_take = cr.for_call(self.run, {"talking": True}, CR.WS, people=False)
            self.assertEqual([r["file"] for r in long_take], ["CLAUDE.md"])           # the product always goes

    def test_13_a_beat_that_breaks_the_briefs_never_rules_is_dropped(self):
        from unittest import mock
        block = ("CAMERA AND MOTION (the director's plan for S1, \"Idea\"):\nCamera: S1.1: front, hold.\n"
                 "Beat by beat, each one moving: B1 lifts the crust off the skin; B2 the camera pushes in.")
        pr = PROMPT.replace("CAMERA AND MOTION (the director's plan for S1, \"Idea\"):\nCamera: S1.1: front, hold.", block)
        cm = {"scenes": {"S1": {"motion": {"beats": [{"id": "B1", "do": "lifts the crust off the skin"},
                                                      {"id": "B2", "do": "the camera pushes in"}]}}}}
        (self.run / "clips" / "camera-motion.json").write_text(json.dumps(cm))
        (self.run / "brief.md").write_text("```json\n" + json.dumps({"cast": [{"id": "lead"}, {"id": "friend"}],
            "world": [{"description": "A render. Never skin being removed or erased."}]}) + "\n```\n")

        def ask(q, pics):
            if not pics:
                self.assertIn("Never skin being removed", q)
                return {"breaks": [{"beat": "B1", "why": "skin being removed"}]}
            return self.ask(q, pics)
        self.plan([self.call("C1", "S1-F1", talking=False, people=["friend"], prompt=pr)])
        CR.apply(self.run, ask=ask)
        c = json.loads((self.run / "clips" / "plan.json").read_text())["calls"][0]
        self.assertNotIn("lifts the crust off the skin", c["prompt"])
        self.assertIn("the camera pushes in", c["prompt"])
        self.assertIn(CR.NEVER_MARK, c["prompt"])
        self.assertEqual(c["dropped_beats"][-1]["beat"], "B1")

    def test_14_a_product_scene_whose_picture_shows_no_product_is_flagged(self):
        self.plan([self.call("C1", "S1-F1", talking=False, people=["friend"],
                             image_refs=[{"file": "runs/x/products/p/model/product-sheet.png", "job": "the real p"}])])
        added = CR.apply(self.run, ask=self.ask)
        self.assertTrue(any("RULE 14" in x and "product" in x for x in added), added)
        self.reads[b"S1-F1"] = dict(self.reads[b"S1-F1"], products_seen=["the tube"])
        (self.run / "clips" / "picture-reads.json").unlink()                          # a new read of the picture
        self.plan([self.call("C1", "S1-F1", talking=False, people=["friend"],
                             image_refs=[{"file": "runs/x/products/p/model/product-sheet.png", "job": "the real p"}])])
        self.assertFalse(any("RULE 14" in x and "shows it" in x for x in CR.apply(self.run, ask=self.ask)))



class RenderNamesNoBody(unittest.TestCase):
    """brief-0380 G04-C1-B: a flesh-coloured cut-away plus "skin" lines read as a body and the model refused it (nsfw)."""
    def test_a_render_prompt_carries_no_body_words(self):
        p = CR.render_prompt("CAMERA AND MOTION (S5):\nB1: the salt dissolves across the rough skin surface; the epidermis "
                             "layers shift.")
        self.assertIsNone(CR.BODY_WORDS.search(p), p)
        for w in ("No body", "no hands", "no face"):
            self.assertNotIn(w, p)
        self.assertIn("layered material", p)
        self.assertIn("surface surface", p)        # skin said as the model's surface

if __name__ == "__main__":
    unittest.main()
