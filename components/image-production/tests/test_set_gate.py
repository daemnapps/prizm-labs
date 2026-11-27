#!/usr/bin/env python3
"""GATE-4 (2026-11-10): every picture is made from a filed 3D set print, or it is refused before any door. No exceptions;
one switch per lane rolls it back.

    python3 components/image-production/tests/test_set_gate.py

Stdlib `unittest`, Python 3.9. No network, no model, no key: a temp workspace (AI_WORKSPACE) holds the sets and casting
files; the Drive is switched off.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent))                  # APPEND — never insert at 0
os.environ.pop("PICTURE_GATE_OFF", None)            # this file tests the gate itself
from image_production import engine as E, plain as PL, providers as PV, set_gate as SG, set_queue as Q   # noqa: E402
import cast_board as CB                            # noqa: E402
import picture_sets as PS                          # noqa: E402

TABLE = {"gate": {"set_required": {"on": True, "lanes": {}}}}
VIDEO_STILL = {"people": "maybe", "safe_zone": True}


def png(path, colour=(200, 120, 40)):
    from PIL import Image
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (60, 100), colour).save(path)
    return Path(path)


class Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "brands" / "b").mkdir(parents=True)
        (self.root / "components").mkdir()
        self._env = os.environ.get("AI_WORKSPACE")
        os.environ["AI_WORKSPACE"] = str(self.root)
        self._roots = SG._drive_roots
        SG._drive_roots = lambda: []

    def tearDown(self):
        SG._drive_roots = self._roots
        if self._env is None:
            os.environ.pop("AI_WORKSPACE", None)
        else:
            os.environ["AI_WORKSPACE"] = self._env
        self.tmp.cleanup()

    def file_set(self, name="beach", kept=True):
        d = self.root / "runs" / "image-production" / "b" / "sets" / name
        pr = png(d / "print-v1.png")
        (d / "set.json").write_text(json.dumps({"project": {"id": "p"}, "prints": [
            {"file": "print-v1.png", "note": ("kept: six on the beach" if kept else "faces off")}]}))
        return pr

    def req(self, **k):
        return {"brand": "b", "purpose": "video-still", "direction": "six people on a beach", "out": str(self.root / "o"), **k}


class EngineRefuses(Workspace):
    def test_the_10_nov_request_is_refused(self):
        """video-still, an AI start picture as from_image, twelve casting references, no set: refused, naming the process."""
        ai = png(self.root / "start.png")
        ai.with_suffix(".recipe.json").write_text("{}")
        refs = [str(png(self.root / f"cast-{i}.jpg")) for i in range(12)]
        with self.assertRaises(SG.SetRefused) as ex:
            SG.engine_gate(self.req(from_image=str(ai), references=refs), VIDEO_STILL, TABLE)
        self.assertIn("3D Jutsu", str(ex.exception))
        self.assertIn("Nothing was sent", str(ex.exception))

    def test_resolve_refuses_before_any_door(self):
        with self.assertRaises(E.BadRequest) as ex:
            E.resolve(self.req(people=True))
        self.assertIn("no filed 3D set", str(ex.exception))

    def test_an_ad_with_people_is_refused(self):
        with self.assertRaises(SG.SetRefused):
            SG.engine_gate(self.req(purpose="ad", people=True), {"people": "maybe"}, TABLE)

    def test_no_people_is_no_exception(self):
        with self.assertRaises(SG.SetRefused):
            SG.engine_gate(self.req(people=False), VIDEO_STILL, TABLE)

    def test_every_purpose_is_gated(self):
        for purpose in ("email-hero", "product-shot", "page-section"):
            with self.assertRaises(SG.SetRefused):
                SG.engine_gate(self.req(purpose=purpose, people=False), {}, TABLE)

    def test_a_rolled_back_lane_passes_and_others_hold(self):
        off = {"gate": {"set_required": {"on": True, "lanes": {"email": False}}}}
        self.assertIsNone(SG.engine_gate(self.req(purpose="email-hero"), {}, off))
        with self.assertRaises(SG.SetRefused):
            SG.engine_gate(self.req(purpose="ad"), {}, off)

    def test_the_master_switch_and_the_machine_switch(self):
        self.assertIsNone(SG.engine_gate(self.req(), {}, {"gate": {"set_required": {"on": False}}}))
        os.environ["PICTURE_GATE_OFF"] = "video"
        try:
            self.assertIsNone(SG.engine_gate(self.req(), {}, TABLE))
            with self.assertRaises(SG.SetRefused):
                SG.engine_gate(self.req(purpose="ad"), {}, TABLE)
        finally:
            os.environ.pop("PICTURE_GATE_OFF", None)

    def test_a_set_with_no_kept_print_is_refused(self):
        self.file_set(kept=False)
        with self.assertRaises(SG.SetRefused) as ex:
            SG.engine_gate(self.req(set="beach"), VIDEO_STILL, TABLE)
        self.assertIn("no kept print", str(ex.exception))

    def test_a_kept_print_is_the_base(self):
        pr = self.file_set()
        self.assertEqual(SG.engine_gate(self.req(set="beach"), VIDEO_STILL, TABLE), pr)
        self.assertEqual(SG.engine_gate(self.req(set=str(pr)), VIDEO_STILL, TABLE), pr)    # named by its print

    def test_another_picture_as_the_base_is_refused(self):
        self.file_set()
        other = png(self.root / "ai.png", (1, 2, 3))
        with self.assertRaises(SG.SetRefused) as ex:
            SG.engine_gate(self.req(set="beach", from_image=str(other)), VIDEO_STILL, TABLE)
        self.assertIn("not from set", str(ex.exception))

    def test_a_masked_patch_is_refused(self):
        self.file_set()
        with self.assertRaises(SG.SetRefused) as ex:
            SG.engine_gate(self.req(set="beach", region=[10, 10, 40, 40]), VIDEO_STILL, TABLE)
        self.assertIn("patch", str(ex.exception))

    def test_a_picture_we_made_as_a_reference_is_refused(self):
        self.file_set()
        ours = png(self.root / "made.png")
        ours.with_suffix(".recipe.json").write_text("{}")
        with self.assertRaises(SG.SetRefused):
            SG.engine_gate(self.req(set="beach", references=[str(ours)]), VIDEO_STILL, TABLE)

    def test_the_real_table_turns_every_lane_on(self):
        cfg = SG.config()
        self.assertTrue(cfg.get("on"))
        self.assertTrue(all(cfg["lanes"].get(lane) for lane in SG.LANES))


class PlainRefuses(Workspace):
    def test_cast_photos_without_a_print_are_refused(self):
        swipe = png(self.root / "swipe.png")
        with self.assertRaises(SG.SetRefused):
            SG.plain_gate("b", [swipe], ref_says={1: "the face of the host"}, t=TABLE)

    def test_plain_make_stops_before_the_door(self):
        swipe = png(self.root / "swipe.png")
        with self.assertRaises(SG.SetRefused):
            PL.make("b", "six on a beach", self.root / "o.png", references=[swipe], people="cast",
                    recipe={"x": {"na": "test"}}, kind="picture")

    def test_a_kept_print_or_its_copy_as_image_1_passes(self):
        pr = self.file_set()
        copy = self.root / "plate.png"
        copy.write_bytes(pr.read_bytes())
        SG.plain_gate("b", [pr], people="cast", t=TABLE)
        SG.plain_gate("b", [copy], people_lines=["the host"], t=TABLE)

    def test_undeclared_people_count_as_people(self):
        swipe = png(self.root / "swipe.png")
        with self.assertRaises(SG.SetRefused):
            SG.plain_gate("b", [swipe], t=TABLE)

    def test_a_slide_with_people_is_refused(self):
        swipe = png(self.root / "swipe.png")
        with self.assertRaises(SG.SetRefused):
            SG.plain_gate("b", [swipe], kind="slide", people="lookalike", t=TABLE)

    def test_no_people_is_no_exception(self):
        swipe = png(self.root / "swipe.png")
        with self.assertRaises(SG.SetRefused):
            SG.plain_gate("b", [swipe], people=False, t=TABLE)

    def test_the_email_lane_rolls_back_alone(self):
        swipe = png(self.root / "swipe.png")
        off = {"gate": {"set_required": {"on": True, "lanes": {"email": False}}}}
        SG.plain_gate("b", [swipe], lane="email", t=off)
        with self.assertRaises(SG.SetRefused):
            SG.plain_gate("b", [swipe], lane="statics", t=off)

    def test_the_no_people_prompt_says_so(self):
        got = PL.prompt("a brush on a counter", [], [], True, people=False)
        self.assertIn("no person in the picture", got)
        self.assertNotIn("LOOKALIKE", got)


class MachineDoors(Workspace):
    def test_undeclared_is_refused(self):
        with self.assertRaises(SG.SetRefused):
            SG.door_gate([png(self.root / "frame.png")], t=TABLE)

    def test_no_people_and_cast_sheets_are_no_exception(self):
        f = png(self.root / "frame.png")
        for kw in ({"people": False}, {"cast_sheet": True}):
            with self.assertRaises(SG.SetRefused):
                SG.door_gate([f], t=TABLE, **kw)

    def test_a_named_kept_print_passes_a_finishing_pass(self):
        pr = self.file_set()
        SG.door_gate([png(self.root / "made.png")], from_print=pr, t=TABLE)

    def test_the_cast_lane_rolls_back_alone(self):
        f = png(self.root / "frame.png")
        SG.door_gate([f], cast_sheet=True, t={"gate": {"set_required": {"on": True, "lanes": {"cast": False}}}})

    def test_the_picture_door_itself_refuses_an_uncleared_call(self):
        with self.assertRaises(SG.SetRefused):
            PV.generate({"provider": "higgsfield"}, "a picture", [png(self.root / "frame.png")], self.root / "o.png", "9:16")

    def test_a_cleared_call_passes_the_door_gate(self):
        with SG.cleared():
            SG.provider_gate([png(self.root / "frame.png")])

    def test_a_kept_print_first_passes(self):
        SG.door_gate([self.file_set()], people=True, t=TABLE)

    def test_the_openai_door_itself_refuses(self):
        import importlib.util
        f = HERE.parents[1] / "video-production" / "machine" / "direct_openai.py"
        spec = importlib.util.spec_from_file_location("t_door_gen", f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with self.assertRaises(SystemExit) as ex:
            mod.generate("six people on a beach", [png(self.root / "frame.png")], self.root / "o.png", dry_run=True)
        self.assertIn("3D", str(ex.exception))


class SessionHook(unittest.TestCase):
    """The team workspace's PreToolUse guard: Higgsfield's picture tools and picture jobs by hand are blocked."""
    def run_hook(self, event):
        import subprocess
        hook = HERE.parents[2] / ".claude" / "hooks" / "people-picture-guard.py"
        if not hook.is_file():
            self.skipTest("the workspace hook is not beside this checkout")
        return subprocess.run([sys.executable, str(hook)], input=json.dumps(event), capture_output=True, text=True).returncode

    def test_blocks_and_passes(self):
        self.assertEqual(self.run_hook({"tool_name": "mcp__x__generate_image", "tool_input": {}}), 2)
        self.assertEqual(self.run_hook({"tool_name": "Bash", "tool_input": {
            "command": "higgsfield --json generate create gpt_image_2_5 --prompt a"}}), 2)
        self.assertEqual(self.run_hook({"tool_name": "mcp__x__scene_builder_3d_generate_angles", "tool_input": {}}), 0)
        self.assertEqual(self.run_hook({"tool_name": "Bash", "tool_input": {
            "command": "higgsfield --json generate create seedance_2_5 --prompt a"}}), 0)


class RawDoorsRefuse(unittest.TestCase):
    """The video line's two direct still doors refuse a picture by hand unless it says --no-people."""
    def door(self, name):
        import importlib.util
        f = HERE.parents[1] / "video-production" / "machine" / name
        spec = importlib.util.spec_from_file_location("t_" + name[:-3], f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_openai_door_refuses_people(self):
        d = self.door("direct_openai.py")
        self.assertEqual(d.main(["six people on a beach", "--out", "x.png", "--dry-run"]), 2)

    def test_google_door_refuses_people(self):
        d = self.door("direct_google.py")
        self.assertEqual(d.main(["edit", "six people on a beach", "--image", "a.png", "--out", "x.png", "--dry-run"]), 2)


class CastBoard(Workspace):
    def cast(self, element, colour):
        d = self.root / "runs" / "ai-elements" / "b" / "casting" / element
        png(d / "sheets" / "headshot.jpg", colour)
        png(d / "sheets" / "look-1-beach.jpg", colour)
        (d / "looks.json").write_text(json.dumps({"looks": {"look-1-beach": {"sheet": "sheets/look-1-beach.jpg"}}}))
        return d

    def test_board_records_every_file_in_standing_order(self):
        self.cast("host", (10, 10, 10))
        self.cast("rater", (90, 90, 90))
        rec = CB.build("b", ["host", "rater:look-1-beach"], self.root / "board" / "b.png")
        self.assertEqual(rec["order"], ["host", "rater"])
        self.assertEqual([(f["element"], f["file"]) for f in rec["picture_from"]],
                         [("host", "sheets/headshot.jpg"), ("host", "sheets/look-1-beach.jpg"),
                          ("rater", "sheets/headshot.jpg"), ("rater", "sheets/look-1-beach.jpg")])
        self.assertTrue(all(len(f["sha256"]) == 64 for f in rec["picture_from"]))
        self.assertIn("casting sheet", rec["print_reference"])    # picture_sets' kept-print check accepts it
        self.assertEqual(CB.check(rec), [])

    def test_a_missing_file_refuses_the_board(self):
        d = self.cast("host", (10, 10, 10))
        (d / "sheets" / "headshot.jpg").unlink()
        with self.assertRaises(CB.BoardRefused):
            CB.build("b", ["host"], self.root / "board" / "b.png")

    def test_put_writes_picture_from_and_refuses_a_stale_board(self):
        d = self.cast("host", (10, 10, 10))
        CB.build("b", ["host"], self.root / "board" / "b.png")
        pr = png(self.root / "print.png")
        PS.put("b", "beach", printed=pr, note="kept: the host", cast_board=self.root / "board" / "b.json")
        self.assertEqual([f["element"] for f in PS.picture_from("b", "beach")], ["host", "host"])
        self.assertTrue((PS.home("b", "beach") / "cast-board.png").is_file())
        png(d / "sheets" / "headshot.jpg", (250, 0, 0))                     # the casting element changed
        with self.assertRaises(ValueError):
            PS.put("b", "beach", printed=pr, note="kept: again", cast_board=self.root / "board" / "b.json")


class TheQueue(Workspace):
    """A refusal files the picture into the 3D print queue; the 3d-print skill clears it (plan, put, done, resume)."""
    def test_an_engine_refusal_is_queued_with_its_resume(self):
        with self.assertRaises(E.BadRequest) as ex:
            E.make(self.req(people=True, label="beach-six"))
        self.assertIn("Queued for the 3D print as beach-six", str(ex.exception))
        r = Q.read("b", "beach-six")
        self.assertEqual(r["state"], "open")
        self.assertEqual(r["resume"]["tool"], "make.py")
        self.assertEqual(r["resume"]["request"]["direction"], "six people on a beach")

    def test_a_dry_run_queues_nothing(self):
        with self.assertRaises(E.BadRequest):
            E.resolve(self.req(label="dry-one"))
        self.assertIsNone(Q.read("b", "dry-one"))

    def test_a_plain_refusal_is_queued(self):
        swipe = png(self.root / "swipe.png")
        with self.assertRaises(SG.SetRefused) as ex:
            PL.make("b", "a brush on a counter", self.root / "out" / "counter-1.png", references=[swipe],
                    recipe={"x": {"na": "test"}})
        self.assertIn("Queued for the 3D print as counter-1", str(ex.exception))
        self.assertEqual(Q.read("b", "counter-1")["resume"]["tool"], "plain.make")

    def test_a_board_refusal_is_one_request_per_run_with_its_people(self):
        swipe = png(self.root / "swipe.png")
        for stamp in ("20261110-180231", "20261110-180955"):
            with self.assertRaises(SG.SetRefused):
                PL.make("b", "a man, four panels", self.root / "pb" / f"ig-run-{stamp}.png", references=[swipe],
                        recipe={"x": {"na": "test"}})
        self.assertEqual([r["id"] for r in Q.open_requests("b")], ["ig-run"])
        r = Q.read("b", "ig-run")
        self.assertEqual(r["resume"]["run"], "ig-run")
        self.assertTrue(r["people_in_it"])
        pl = Q.plan("b", "ig-run")
        self.assertIn("--run ig-run", pl["file_it"])
        self.assertNotIn("No people", pl["print"]["words"])
        self.assertNotIn("studio photographs of the product", pl["print"]["words"])

    def test_the_plan_gives_the_print_and_the_cast_board(self):
        Q.file("b", "two people on a beach", name="beach-two", cast=["host", "rater"])
        pl = Q.plan("b", "beach-two")
        self.assertEqual(pl["print"]["tool"], "scene_builder_3d_generate_angles")
        self.assertIn("cast_board.py build b", pl["cast_board"]["command"])
        self.assertIn("host rater", pl["cast_board"]["command"])
        self.assertTrue(pl["print"]["references"][0].endswith("beach-two-cast-board.png"))
        self.assertIn("picture_sets.py put b beach-two", pl["file_it"])

    def test_done_refuses_while_the_set_has_no_kept_print(self):
        Q.file("b", "six on a beach", name="six")
        self.file_set("six", kept=False)
        with self.assertRaises(SystemExit):
            Q.done("b", "six", "six")
        self.assertEqual(Q.read("b", "six")["state"], "open")

    def test_done_closes_it_and_gives_the_step_to_run_again(self):
        Q.file("b", "six on a beach", name="six", resume={"tool": "make.py", "request": {"brand": "b", "purpose": "ad"}})
        self.file_set("six")
        res = Q.done("b", "six", "six")
        self.assertIn("make.py --request", res["command"])
        self.assertEqual(Q.read("b", "six")["state"], "done")
        self.assertEqual(json.loads((Q.home("b") / "six.resume-request.json").read_text())["set"], "six")
        self.assertEqual(Q.open_requests("b"), [])


class PlanWords(Workspace):
    """The plan carries what the kit knows into the print: true size, how it rests, what it never does, no invented letters."""
    def kit(self):
        k = self.root / "runs" / "ai-elements" / "b" / "products" / "egg-brush"
        png(k / "model" / "product-sheet.png")
        png(k / "sources" / "rest-1.jpg")
        (k / "kit.json").write_text(json.dumps({"what": "the black egg brush", "label_words": [],
            "size_cm": {"height": 11.15, "width": 6.98, "how": "measured"},
            "behaviour": {"rests": [{"how": "sits leaning back in its cradle", "pictures": [{"kit": "sources/rest-1.jpg"}]}],
                          "cannot": ["cannot stand upright on its own"]},
            "always": [{"line": "its light glowing", "status": "approved"}]}))
        (self.root / "runs" / "ai-elements" / "b" / "products" / "egg-case").mkdir(parents=True)
        return k

    def test_the_words_carry_the_kit(self):
        self.kit()
        import image_production.product3d as P3
        old = P3.bank
        P3.bank = lambda: self.root / "runs" / "ai-elements"
        try:
            Q.file("b", "the brush on a bathroom counter", name="egg", products=["egg-brush"])
            pl = Q.plan("b", "egg")
        finally:
            P3.bank = old
        w = pl["print"]["words"]
        self.assertIn("11.15 cm", w)
        self.assertNotIn("{", w)
        self.assertIn("leaning back in its cradle", w)
        self.assertIn("cannot stand upright", w)
        self.assertIn("never add letters", w)
        self.assertIn("Always: the black egg brush, its light glowing", w)        # the kit's `always` lines travel
        # the casting sheet is the product's only reference (owner, 2026-11-23): the kit's rest picture never rides along
        self.assertEqual(len(pl["print"]["references"]), 1)
        self.assertTrue(pl["print"]["references"][0].endswith("model/product-sheet.png"))
        self.assertIsNone(pl["reference_board"])
        self.assertNotIn("rest-1.jpg", json.dumps(pl["print"]))

    def test_a_reference_board_is_one_picture(self):
        import cast_board as CB
        rec = CB.ref_board([png(self.root / "a.png"), png(self.root / "b.png")], self.root / "board.png")
        self.assertTrue((self.root / "board.png").is_file())
        self.assertEqual(len(rec["from"]), 2)

    def test_worlds_put_the_named_room_first(self):
        w = self.root / "runs" / "ai-elements" / "b" / "worlds"
        for wid, room in (("the-gym", "locker room"), ("family-house", "bathroom")):
            (w / wid).mkdir(parents=True)
            (w / wid / "world.json").write_text(json.dumps({"id": wid, "name": wid, "rooms": [{"id": room.replace(" ", "-"), "name": room}]}))
        got = Q.worlds("b", "the brush by the bathroom sink")
        self.assertEqual(got[0]["id"], "family-house")
        self.assertEqual(got[0]["match"], ["bathroom"])



EDITS = {"gate": {"set_required": {"on": True, "lanes": {}, "edits": {"on": True}}}}


class EditLane(Workspace):
    """2026-11-10: the 3D rule is for new production; an approved or live picture is changed by a masked edit on it."""
    def original(self, name="beach"):
        live = png(self.root / "live-store-photo.jpg", (9, 9, 9))
        d = PS.put("b", name, original=str(live), note="approved: live store picture")
        return d / "original-v1.jpg"

    def test_an_original_needs_an_approved_note(self):
        live = png(self.root / "live.png")
        with self.assertRaises(ValueError):
            PS.put("b", "beach", original=str(live), note="kept: no")

    def test_a_masked_edit_of_an_approved_original_passes(self):
        self.file_set()
        o = self.original()
        self.assertEqual(SG.engine_gate(self.req(set="beach", from_image=str(o), region=[60, 50, 95, 95]), VIDEO_STILL, EDITS), o)

    def test_a_masked_edit_of_the_kept_print_passes(self):
        pr = self.file_set()
        self.assertEqual(SG.engine_gate(self.req(set="beach", from_image=str(pr), region=[1, 1, 9, 9]), VIDEO_STILL, EDITS), pr)

    def test_an_original_set_with_no_print_still_edits(self):
        o = self.original("store-5pack")
        self.assertEqual(SG.engine_gate(self.req(set="store-5pack", from_image=str(o), region=[1, 1, 9, 9]), VIDEO_STILL, EDITS), o)

    def test_an_unfiled_picture_is_refused(self):
        self.file_set()
        other = png(self.root / "ai.png", (1, 2, 3))
        with self.assertRaises(SG.SetRefused) as ex:
            SG.engine_gate(self.req(set="beach", from_image=str(other), region=[1, 1, 9, 9]), VIDEO_STILL, EDITS)
        self.assertIn("approved original", str(ex.exception))

    def test_a_whole_picture_redraw_of_an_original_is_refused(self):
        self.file_set()
        o = self.original()
        with self.assertRaises(SG.SetRefused) as ex:
            SG.engine_gate(self.req(set="beach", from_image=str(o)), VIDEO_STILL, EDITS)
        self.assertIn("masked edit", str(ex.exception))

    def test_rolled_back_the_patch_is_refused_again(self):
        self.file_set()
        o = self.original()
        with self.assertRaises(SG.SetRefused):
            SG.engine_gate(self.req(set="beach", from_image=str(o), region=[1, 1, 9, 9]), VIDEO_STILL, TABLE)
        os.environ["PICTURE_GATE_OFF"] = "edits"
        try:
            with self.assertRaises(SG.SetRefused):
                SG.engine_gate(self.req(set="beach", from_image=str(o), region=[1, 1, 9, 9]), VIDEO_STILL, EDITS)
        finally:
            os.environ.pop("PICTURE_GATE_OFF", None)

    def test_the_real_table_keeps_the_edit_lane_off(self):
        self.assertFalse(SG.edits_on())               # switched off by the owner, 10 Nov: edits are 3D rebuilds too

if __name__ == "__main__":
    unittest.main(verbosity=1)
