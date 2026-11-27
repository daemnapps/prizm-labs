#!/usr/bin/env python3
"""The checklist before every paid clip (clip_checklist.py): every picture's inventory and the clip model's input sheet,
filled per call; a ✗ goes into the plan's problems and the clip gate reads the same file. Nothing is called.

    python3 components/video-production/machine/test_clip_checklist.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clip_checklist as CK  # noqa: E402

PROMPT = ("Image 1 is the first frame. " + "word " * 30 + "\n\nCAMERA AND MOTION (the director's plan for S1, \"I\"):\n"
          "Camera: S1.1: hold.\n\nNothing is added that is not in Image 1.\n\nNo words, letters on screen.")


class Checklist(unittest.TestCase):
    def setUp(self):
        self.run = Path(tempfile.mkdtemp(prefix="ck_"))
        (self.run / "clips").mkdir()
        (self.run / "media").mkdir()
        self.pic = self.run / "media" / "S1-F1.png"
        self.pic.write_bytes(b"png")
        cr = mock.MagicMock()
        cr.person_refs.return_value = []
        cr.prop_refs.return_value = []
        cr.product_ids.return_value = []
        cr.named_products.return_value = ([], [])
        cr.model_of.return_value = "seedance-2.5"
        rules = mock.MagicMock(NEVER_MARK="NEVER", NO_TEXT_MARK="No words, letters",
                               NO_ADD_MARK="Nothing is added that is not in Image")
        rules.never_rules.return_value = []
        cp = mock.MagicMock()
        cp.picture_file.side_effect = lambda run, f: self.pic if f == "S1-F1" else None
        real = CK._load
        self.mods = {"clip_refs": cr, "clip_rules": rules, "clips_plan": cp}
        p = mock.patch.object(CK, "_load", lambda n: self.mods.get(n) or real(n))
        p.start()
        self.addCleanup(p.stop)

    def plan(self, **kw):
        c = {"id": "C1", "scenes": ["S1"], "start_frame": "S1-F1", "prompt": PROMPT, "talking": False,
             "image_refs": [], "duration": 5}
        c.update(kw)
        (self.run / "clips" / "plan.json").write_text(json.dumps({"calls": [c], "problems": []}))

    def review(self, sev="OK"):
        return lambda items: {i["id"]: {"severity": sev, "problems": [] if sev == "OK" else ["hands"]} for i in items}

    def test_a_clean_call_passes_and_the_gate_reads_it(self):
        self.plan()
        self.assertEqual(CK.build(self.run, review=self.review()), [])
        self.assertEqual(CK.passed(self.run, "C1"), (True, ""))

    def test_a_fix_finding_goes_on_the_fix_list_and_never_stops_the_call(self):
        # owner, 2026-11-21: "small miss, small fix" — a FIX finding is listed for adjustment, the paid run goes on
        self.plan()
        self.assertEqual(CK.build(self.run, review=self.review("FIX")), [])
        self.assertEqual(CK.passed(self.run, "C1"), (True, ""))
        fx = json.loads((self.run / "clips" / "fixes.json").read_text())
        self.assertEqual(fx["C1"]["fixes"], [{"picture": "S1-F1", "fix": "hands"}])
        self.assertEqual(fx["C1"]["scenes"], ["S1"])

    def test_a_blocker_the_inventory_finds_stops_the_call(self):
        self.plan()
        bad = CK.build(self.run, review=self.review("BLOCKER"))
        self.assertTrue(any("picture inventory · S1-F1" in b and "BLOCKER" in b for b in bad), bad)
        ok, why = CK.passed(self.run, "C1")
        self.assertFalse(ok)
        probs = json.loads((self.run / "clips" / "plan.json").read_text())["problems"]
        self.assertTrue(any(p.startswith("CHECKLIST") for p in probs))

    def accept(self, **kw):
        a = {"words": "only the product matters", "by": "owner", "at": "2026-11-21", "accepts": "people and pose"}
        a.update(kw)
        (self.run / "clips" / "accepted.json").write_text(json.dumps({"S1-F1": a}))

    def problems(self, sev, probs):
        return lambda items: {i["id"]: {"severity": sev, "problems": probs} for i in items}

    NO_KINDS = staticmethod(lambda run, name, pic, probs: {})

    def test_the_owners_acceptance_turns_people_findings_into_watch_notes(self):
        self.plan()
        self.accept()
        bad = CK.build(self.run, kind_ask=self.NO_KINDS, review=self.problems("BLOCKER", ["the left and right hands are swapped"]))
        self.assertEqual(bad, [])
        rows = json.loads((self.run / "clips" / "checklists.json").read_text())["C1"]["rows"]
        r = next(x for x in rows if x["line"] == "picture inventory · S1-F1")
        self.assertEqual(r["state"], "~")
        self.assertIn("only the product matters", r["value"])

    def test_a_product_finding_still_gates_under_the_acceptance(self):
        self.plan()
        self.accept()
        bad = CK.build(self.run, kind_ask=self.NO_KINDS, review=self.problems("FIX", ["hands swapped", "the product reads as a compact mirror"]))
        self.assertTrue(any("kept by the owner" in b and "compact mirror" in b for b in bad), bad)
        self.assertFalse(CK.passed(self.run, "C1")[0])

    def test_a_product_finding_the_owner_accepted_by_its_text_passes(self):
        self.plan()
        self.accept(lines=["The product sits at 40% width"])
        bad = CK.build(self.run, kind_ask=self.NO_KINDS, review=self.problems("FIX", ["The product sits at 40% width, not 50%"]))
        self.assertEqual(bad, [])

    def test_a_pose_finding_naming_the_product_is_accepted_by_its_kind(self):
        self.plan()
        self.accept()
        probs = ["the product is in his left hand, not his right", "the product's label is invented"]
        kinds = lambda run, name, pic, p: {probs[0]: "people", probs[1]: "product"}  # noqa: E731
        bad = CK.build(self.run, review=self.problems("FIX", probs), kind_ask=kinds)
        self.assertEqual(len(bad), 1)
        self.assertIn("label is invented", bad[0])
        self.assertNotIn("left hand", bad[0])

    def test_kinds_are_asked_only_where_the_owner_accepted(self):
        self.plan()
        CK.build(self.run, review=self.problems("BLOCKER", ["an invented label is printed on the jar"]),
                 kind_ask=lambda *a: self.fail("kinds asked without an acceptance"))

    def test_without_an_acceptance_the_rule_is_unchanged(self):
        self.plan()
        bad = CK.build(self.run, review=self.problems("BLOCKER", ["an invented label is printed on the jar"]))
        self.assertTrue(any("BLOCKER" in b for b in bad), bad)

    def test_a_product_name_is_matched_as_a_word(self):
        terms = ["product", "flex"]
        g, ok = CK.split_accepted(["his reflection is cut off", "the FLEX is a disc"], {"words": "x"}, terms)
        self.assertEqual(g, ["the FLEX is a disc"])
        self.assertEqual(ok, ["his reflection is cut off"])

    def test_the_inventory_is_read_once_per_picture(self):
        self.plan()
        CK.build(self.run, review=self.review())
        CK.build(self.run, review=lambda items: self.fail("read twice"))

    def test_a_named_products_texture_sheet_not_sent_is_a_cross(self):
        prod = CK.WS / "runs" / "ai-elements"          # a product folder that is not on disk is said "none banked"
        self.mods["clip_refs"].product_ids.return_value = ["p"]
        self.mods["clip_refs"].brand_of.return_value = "b"
        self.mods["clip_refs"].texture_sheet.return_value = None
        self.plan()
        CK.build(self.run, review=self.review())
        rows = json.loads((self.run / "clips" / "checklists.json").read_text())["C1"]["rows"]
        self.assertTrue(any(r["line"] == "product · p · casting sheet" and r["state"] == "~" for r in rows), rows)
        self.assertTrue(prod)

    def test_a_product_picture_without_the_real_product_pasted_is_a_cross(self):
        import hashlib
        self.mods["clip_refs"].product_ids.return_value = ["p"]
        self.mods["clip_refs"].brand_of.return_value = "b"
        self.mods["clip_refs"].texture_sheet.return_value = None
        self.plan()
        bad = CK.build(self.run, review=self.review())
        self.assertTrue(any("real product" in b and "no paste" in b for b in bad), bad)
        (self.run / "media" / "S1-F1.paste.json").write_text(json.dumps(
            {"picture_sha": hashlib.sha256(self.pic.read_bytes()).hexdigest(),
             "products": {"p": {"ok": True, "angle": 30}}}))
        bad = CK.build(self.run, review=self.review())
        self.assertFalse(any("real product" in b for b in bad), bad)

    def test_an_in_look_piece_asks_for_no_paste(self):
        self.mods["clip_refs"].product_ids.return_value = ["p"]
        self.mods["clip_refs"].brand_of.return_value = "b"
        self.mods["clip_refs"].texture_sheet.return_value = None
        self.mods["product_route"] = mock.MagicMock(**{"in_look.return_value": True})
        self.plan()
        bad = CK.build(self.run, review=self.review())
        self.assertFalse(any("real product" in b for b in bad), bad)
        rows = json.loads((self.run / "clips" / "checklists.json").read_text())["C1"]["rows"]
        self.assertTrue(any(r["line"].startswith("real product") and "in-look" in r["value"] for r in rows), rows)

    def test_a_dry_run_reads_no_picture_and_says_so(self):
        self.plan()
        CK.build(self.run, dry=True, review=lambda items: self.fail("a dry run read a picture"))
        rows = json.loads((self.run / "clips" / "checklists.json").read_text())["C1"]["rows"]
        self.assertTrue(any(r["line"].startswith("picture inventory") and r["state"] == "~" for r in rows))

    def test_a_prompt_without_its_camera_plan_is_a_cross(self):
        self.plan(prompt="Image 1 is x. " + "word " * 30)
        bad = CK.build(self.run, review=self.review())
        self.assertTrue(any("camera and motion plan" in b for b in bad))



class BodyFaultsConfirmed(unittest.TestCase):
    """brief-0380 openings: the one-read inventory gave clean prints "six toes" and "a melting hand"."""
    def setUp(self):
        self.run = Path(tempfile.mkdtemp())
        (self.run / "clips").mkdir()
        self.pic = self.run / "p.png"
        self.pic.write_bytes(b"png")

    def read(self, problems, body_ok):
        return CK.inventory(self.run, [("S1-F1", self.pic)],
                            review=lambda items: {"S1-F1": {"severity": "BLOCKER", "problems": problems}},
                            body=lambda run, f: {"ok": body_ok, "problems": [] if body_ok else ["six toes"]})["S1-F1"]

    def test_a_body_fault_the_body_check_does_not_find_is_a_fix(self):
        v = self.read(["left foot has six toes", "right hand melting into the plastic"], True)
        self.assertEqual(v["severity"], "FIX")
        self.assertTrue(v["problems"][0].startswith("not confirmed by the body check"))

    def test_a_body_fault_the_body_check_finds_still_stops(self):
        self.assertEqual(self.read(["left foot has six toes"], False)["severity"], "BLOCKER")

    def mixed(self, planned):
        return CK.inventory(self.run, [("S1-F1", self.pic)],
                            review=lambda items: {"S1-F1": {"severity": "BLOCKER", "problems": [
                                "a mangled hand", "liquid passes through the glass cylinder"]}},
                            body=lambda run, f: {"ok": True, "problems": []},
                            plan_ask=lambda run, n, f, probs, text: planned)["S1-F1"]

    def test_body_items_beside_a_planned_set_moment_are_a_fix(self):
        v = self.mixed({0})
        self.assertEqual(v["severity"], "FIX")
        self.assertTrue(v["problems"][1].startswith("the picture's own planned moment"))

    def test_a_set_item_the_judge_does_not_call_planned_still_stops(self):
        self.assertEqual(self.mixed(set())["severity"], "BLOCKER")

    def test_a_blocker_that_is_not_about_a_body_is_never_sent_to_the_body_check(self):
        v = CK.inventory(self.run, [("S1-F1", self.pic)],
                         review=lambda items: {"S1-F1": {"severity": "BLOCKER", "problems": ["the label is missing"]}},
                         body=lambda run, f: self.fail("asked the body check"))["S1-F1"]
        self.assertEqual(v["severity"], "BLOCKER")


class SheetWrittenAsADict(unittest.TestCase):
    def test_a_dict_sheet_reads_as_named_rows(self):
        ws = Path(tempfile.mkdtemp())
        (ws / "components" / "model-inputs" / "inputs").mkdir(parents=True)
        (ws / "components" / "model-inputs" / "inputs" / "m.json").write_text(
            json.dumps({"inputs": {"start_image": "the picture", "prompt": "the words"}}))
        with mock.patch.object(CK, "WS", ws), mock.patch.object(CK, "_load") as ld:
            ld.return_value.model_of.return_value = "m"
            rows = CK.sheet_inputs(ws)
        self.assertEqual([r["name"] for r in rows], ["start_image", "prompt"])


class InventoryKnowsItsSources(unittest.TestCase):
    def test_the_picture_words_and_references_go_with_it(self):
        run = Path(tempfile.mkdtemp())
        (run / "batches").mkdir(); (run / "media").mkdir()
        ref = run / "glove.png"; ref.write_bytes(b"g")
        kp = run / "kept.png"; kp.write_bytes(b"k")
        (run / "batches" / "01.json").write_text(json.dumps({"items": [{"id": "S1-F1", "params": {"prompt": "two gloves"},
                                                                        "medias": [{"role": "image_references", "value": str(ref)}]}]}))
        (run / "media" / "S1-F1.png.print.json").write_text(json.dumps({"print": str(kp)}))
        src = CK.sources_of(run, "S1-F1")
        self.assertTrue(src[0].endswith("two gloves"))
        self.assertEqual(src[1:], [str(kp), str(ref)])


class SourcesKeptAcrossPasses(unittest.TestCase):
    def test_a_picture_not_in_this_pass_keeps_its_sources_and_is_not_read_again(self):
        run = Path(tempfile.mkdtemp())
        (run / "batches").mkdir(); (run / "clips").mkdir(); (run / "media").mkdir()
        pic = run / "media" / "S1-F1.png"; pic.write_bytes(b"p")
        (run / "batches" / "01.json").write_text(json.dumps({"items": [{"id": "S1-F1", "params": {"prompt": "x"}}]}))
        CK.inventory(run, [("S1-F1", pic)], review=lambda items: {i["id"]: {"severity": "OK"} for i in items})
        (run / "batches" / "01.json").write_text(json.dumps({"items": []}))        # a later pass made other pictures
        CK.inventory(run, [("S1-F1", pic)], review=lambda items: self.fail("read again without its sources"))

if __name__ == "__main__":
    unittest.main()
