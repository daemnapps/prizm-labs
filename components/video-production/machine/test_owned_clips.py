#!/usr/bin/env python3
"""Our own footage reaches the edit as a file (the logic layer, 2026-11-18). No network, no Drive, no ffmpeg: the
source read and the cut are fakes, the run folder is a temp folder.

    /usr/bin/python3 machine/test_owned_clips.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str, path: Path = None):
    spec = importlib.util.spec_from_file_location(f"test_oc_{name}", path or HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


OC = load("owned_clips")
footage = load("footage")
route_facts = load("route_facts")
budget = load("budget")
KIT = HERE.parents[1] / "video-edit" / "machine"
sys.path.insert(0, str(KIT))
kit_from_run = load("kit_from_run", KIT / "kit_from_run.py")


def cut_scene(sid="S3", **over):
    s = {"id": sid, "kind": "broll", "type": "B", "to_camera": False, "section": "proof", "voice": "it reaches every corner",
         "source_plan": "cut", "owned_file": "Shared Assets/brands/x/footage/clip-a.mp4", "owned_in": 2.0,
         "owned_out": 5.5, "owned_clip": "clip-a", "footage_why": "cut from our footage: clip clip-a scores 0.61 against a bar of 0.42",
         "owned_evidence": {"clip": "clip-a", "score": 0.61, "bar": 0.42}}
    s.update(over)
    return s


class Place(unittest.TestCase):
    def setUp(self):
        self.run = Path(tempfile.mkdtemp(prefix="oc_run_"))
        self.cuts, self.verdicts = [], []
        self.src = self.run / "source.mov"
        self.src.write_bytes(b"real footage")

    def cutter(self, src, t_in, t_out, dst):
        self.cuts.append((str(src), t_in, t_out))
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b"cut")

    def verdict(self, run, sid, layer, payload):
        self.verdicts.append((sid, layer, payload))
        p = Path(run) / "verdicts.json"
        d = json.loads(p.read_text()) if p.exists() else {}
        d.setdefault(sid, {})[layer] = payload
        p.write_text(json.dumps(d))

    def place(self, plan, **kw):
        return OC.place(self.run, plan, "x", fetch=lambda ref: self.src, cutter=self.cutter, verdict=self.verdict, **kw)

    def test_a_cut_scene_is_laid_at_its_times_with_its_verdict_rows(self):
        plan = {"scenes": [cut_scene(), {"id": "S1", "kind": "talking", "to_camera": True, "type": "A"}]}
        res = self.place(plan)
        self.assertEqual(res["placed"], ["S3"])
        self.assertTrue((self.run / "media" / "S3.mp4").is_file())
        self.assertEqual(self.cuts, [(str(self.src), 2.0, 5.5)])
        self.assertEqual(sorted(l for _, l, _ in self.verdicts), ["director", "motion"])
        for _sid, _layer, row in self.verdicts:
            self.assertEqual(row["verdict"], "PASS")
            self.assertTrue(row["owned"], "the row says it is our own footage, never a judged AI take")
            self.assertEqual((row["in"], row["out"]), (2.0, 5.5))
        self.assertEqual(plan["scenes"][0]["owned_media"]["file"], "media/S3.mp4")

    def test_the_edit_join_takes_it_as_an_approved_clip(self):
        """THE BREAK, CLOSED: the kit from this run carries the owned scene as an approved B-roll clip, not 'unmade'."""
        plan = {"scenes": [cut_scene()]}
        (self.run / "run.json").write_text(json.dumps({"brand": "x", "label": "x_p_brief-0001", "format": "narrator-montage"}))
        (self.run / "vo").mkdir()
        (self.run / "vo" / "S3.mp3").write_bytes(b"voice")
        self.place(plan)
        (self.run / "plan.json").write_text(json.dumps(plan))
        kit, notes = kit_from_run.build(self.run)
        row = next(c for c in kit["clips"] if c["id"] == "S3")
        self.assertTrue(row["approved"], notes)
        self.assertEqual(row["roll"], "b")
        self.assertTrue(str(row["src"]).endswith("media/S3.mp4"))
        self.assertEqual(kit["unmade"], [])
        self.assertEqual((row["owned"]["in"], row["owned"]["out"]), (2.0, 5.5), "the clip says it is our own footage")
        self.assertIn("scores 0.61", row["owned"]["why"])

    def test_the_kit_carries_each_clips_route_and_productions_trail(self):
        plan = {"scenes": [cut_scene(route="REAL", route_why="we own real footage of this: clip clip-a scores 0.61")]}
        (self.run / "run.json").write_text(json.dumps({"brand": "x", "label": "l", "trail": [
            {"stage": "production", "decision": "each scene's route", "choice": "REAL 1 · SWAP 0 · AI 0", "why": "one rule", "by": "the route rule"}]}))
        (self.run / "vo").mkdir()
        (self.run / "vo" / "S3.mp3").write_bytes(b"voice")
        self.place(plan)
        (self.run / "plan.json").write_text(json.dumps(plan))
        kit, _notes = kit_from_run.build(self.run)
        self.assertEqual((kit["clips"][0]["made_as"], kit["clips"][0]["made_why"][:27]), ("REAL", "we own real footage of this"))
        self.assertEqual(kit["trail"][0]["decision"], "each scene's route")

    def test_before_this_step_the_same_run_had_no_clip(self):
        plan = {"scenes": [cut_scene()]}
        (self.run / "run.json").write_text(json.dumps({"brand": "x", "label": "l"}))
        (self.run / "plan.json").write_text(json.dumps(plan))
        kit, notes = kit_from_run.build(self.run)
        self.assertEqual(kit["clips"], [])
        self.assertEqual(kit["unmade"], ["S3: broll clip not made"])

    def test_a_captioned_clip_is_never_laid_in(self):
        plan = {"scenes": [cut_scene(owned_tier="B", owned_marks=["caption"])]}
        res = self.place(plan)
        self.assertEqual(res["placed"], [])
        self.assertIn("words are burned into the clip", res["skipped"]["S3"])
        self.assertFalse((self.run / "media" / "S3.mp4").exists())
        self.assertEqual(self.cuts, [])

    def test_a_clean_marked_clip_is_laid(self):
        res = self.place({"scenes": [cut_scene(owned_tier="A", owned_marks=["clean"])]})
        self.assertEqual(res["placed"], ["S3"])

    def test_one_clip_section_is_never_laid_on_two_scenes(self):
        plan = {"scenes": [cut_scene("S3"), cut_scene("S4")]}
        res = self.place(plan)
        self.assertEqual(res["placed"], ["S3"])
        self.assertIn("already laid on S3", res["skipped"]["S4"])

    def test_a_clip_that_cannot_be_read_is_named_and_nothing_stops(self):
        def gone(ref):
            raise FileNotFoundError("not on the Drive")
        plan = {"scenes": [cut_scene()]}
        res = OC.place(self.run, plan, "x", fetch=gone, cutter=self.cutter, verdict=self.verdict)
        self.assertEqual(res["placed"], [])
        self.assertIn("could not be read or cut", res["skipped"]["S3"])
        self.assertEqual(plan["scenes"][0]["source_plan"], "cut", "the decision stands")
        self.assertEqual(self.verdicts, [], "no verdict is written for a clip that was not laid")

    def test_running_it_again_keeps_what_is_laid_and_recuts_a_changed_decision(self):
        plan = {"scenes": [cut_scene()]}
        self.place(plan)
        res = self.place(plan)
        self.assertEqual((res["placed"], res["kept"]), ([], ["S3"]))
        self.assertEqual(len(self.cuts), 1)
        plan["scenes"][0]["owned_in"] = 3.0
        res = self.place(plan)
        self.assertEqual(res["placed"], ["S3"])
        self.assertTrue(list((self.run / "media" / "versions").glob("S3-before-owned-*.mp4")), "the earlier cut is kept")

    def test_rows_that_cannot_be_written_never_lose_the_clip_and_are_written_next_time(self):
        def broken(run, sid, layer, payload):
            raise OSError("the record is locked")
        plan = {"scenes": [cut_scene()]}
        res = OC.place(self.run, plan, "x", fetch=lambda ref: self.src, cutter=self.cutter, verdict=broken)
        self.assertEqual(res["placed"], ["S3"])
        self.assertTrue((self.run / "media" / "S3.mp4").is_file())
        self.assertFalse(plan["scenes"][0]["owned_media"]["verdicts"])
        self.assertIn("verdict rows could not be written", " ".join(res["said"]))
        res = self.place(plan)                                  # the next run writes them, and cuts nothing again
        self.assertTrue(plan["scenes"][0]["owned_media"]["verdicts"])
        self.assertEqual(len(self.cuts), 1)
        self.assertEqual(sorted(l for _, l, _ in self.verdicts), ["director", "motion"])

    def test_a_dry_run_lays_nothing(self):
        res = self.place({"scenes": [cut_scene()]}, dry_run=True)
        self.assertEqual(res["placed"], [])
        self.assertFalse((self.run / "media").exists())
        self.assertIn("would be cut", " ".join(res["said"]))

    def test_generated_and_presenter_scenes_are_left_alone(self):
        plan = {"scenes": [{"id": "S1", "source_plan": "generate"}, {"id": "S2", "source_plan": "presenter"},
                           {"id": "S5", "source_plan": "swap"}]}
        self.assertEqual(self.place(plan), {"placed": [], "kept": [], "skipped": {}, "said": []})


class OneFootageRule(unittest.TestCase):
    """The reasoned route decides; the match score is its evidence; the budget and the run agree."""

    def hit(self, **over):
        h = {"clip_id": "c1", "score": 0.6, "shared_path": "Shared Assets/x/c1.mp4", "in": 1.0, "out": 4.0,
             "action_match": 0.7, "action_words": 3, "shows": "a hand wipes the table"}
        h.update(over)
        return h

    def test_the_decision_writes_what_it_was_judged_on(self):
        s = {"id": "S3", "to_camera": False, "kind": "broll", "happens": "a hand wipes the table"}
        self.assertEqual(footage._decide(s, [self.hit()]), "cut")
        self.assertEqual(s["owned_evidence"]["score"], 0.6)
        self.assertEqual(s["owned_evidence"]["bar"], footage.CONFIDENT)
        self.assertTrue(s["footage_why"].startswith("cut from our footage: clip c1 scores 0.60"))
        s2 = {"id": "S4", "to_camera": False, "kind": "broll"}
        self.assertEqual(footage._decide(s2, [self.hit(score=0.3)]), "generate")
        self.assertIn("under the bar", s2["footage_why"])
        s3 = {"id": "S5", "to_camera": False, "kind": "broll"}
        self.assertEqual(footage._decide(s3, []), "generate")
        self.assertEqual(s3["footage_why"], "generated: no clip of ours comes close")

    def test_the_route_gives_the_evidence_as_its_reason(self):
        s = {"id": "S3", "to_camera": False, "kind": "broll", "happens": "a hand wipes the table"}
        footage._decide(s, [self.hit()])
        res = route_facts.route_plan(Path(tempfile.mkdtemp()), {"scenes": [s]}, None)
        row = res["rows"][0]
        self.assertEqual(row["route"], "REAL")
        self.assertIn("scores 0.60 against a bar of 0.42", row["why"])
        self.assertEqual(s["route_by"], route_facts.RULE)

    def test_a_scene_that_is_not_real_says_why_no_clip_stands_in(self):
        s = {"id": "S4", "to_camera": False, "kind": "broll", "happens": "a hand wipes the table"}
        footage._decide(s, [self.hit(score=0.3)])
        row = route_facts.route_plan(Path(tempfile.mkdtemp()), {"scenes": [s]}, None)["rows"][0]
        self.assertEqual(row["route"], "AI")
        self.assertIn("our footage: our nearest clip c1 scores 0.30, under the bar", row["why"])

    def test_no_captioned_clip_and_no_clip_twice_before_the_decision(self):
        used = set()
        keep, aside = footage.usable([self.hit(text_marks=["caption"]), self.hit(clip_id="c2", shared_path="b.mp4",
                                                                                 text_marks=["clean"])], "x", used)
        self.assertEqual([h["clip_id"] for h in keep], ["c2"])
        self.assertIn("words burned in", aside[0]["why"])
        used.add(("b.mp4", 1.0, 4.0))
        keep, aside = footage.usable([self.hit(clip_id="c2", shared_path="b.mp4", text_marks=["clean"])], "x", used)
        self.assertEqual(keep, [])
        self.assertIn("already on an earlier scene", aside[0]["why"])

    def test_routing_twice_decides_again_and_keeps_a_brief_named_route(self):
        run = Path(tempfile.mkdtemp())
        s = {"id": "S3", "to_camera": False, "kind": "broll", "happens": "a hand wipes the table"}
        named = {"id": "S9", "kind": "broll", "route": "AI"}
        plan = {"scenes": [s, named]}
        footage._decide(s, [self.hit(score=0.3)])
        route_facts.route_plan(run, plan, None)
        self.assertEqual((s["route"], named["route_why"]), ("AI", route_facts.NAMED))
        footage._decide(s, [self.hit()])                          # the footage match changed
        res = route_facts.route_plan(run, plan, None)
        self.assertEqual(s["route"], "REAL", "a route the rule wrote is decided again, never read back as the brief's")
        self.assertEqual(next(r for r in res["rows"] if r["id"] == "S9")["why"], route_facts.NAMED)

    def test_the_budget_and_the_run_agree(self):
        """The budget used to read keys nothing sets, so it called a scene AI that the run cut from our footage."""
        run = Path(tempfile.mkdtemp())
        s = {"id": "S3", "to_camera": False, "kind": "broll", "happens": "a hand wipes the table", "seconds": 4}
        other = {"id": "S4", "to_camera": False, "kind": "broll", "happens": "he smiles", "seconds": 4}
        plan = {"scenes": [s, other]}
        footage._decide(s, [self.hit()])
        footage._decide(other, [])
        ran = route_facts.route_plan(run, plan, None)
        (run / "plan.json").write_text(json.dumps(plan))
        brief_scenes = [{"id": "S3", "to_camera": False, "kind": "broll", "happens": "a hand wipes the table", "seconds": 4},
                        {"id": "S4", "to_camera": False, "kind": "broll", "happens": "he smiles", "seconds": 4}]
        priced = budget.routes(brief_scenes, run)
        self.assertEqual({r["id"]: r["route"] for r in priced["rows"]}, {r["id"]: r["route"] for r in ran["rows"]})
        self.assertEqual({r["id"]: r["route"] for r in priced["rows"]}, {"S3": "REAL", "S4": "AI"})
        self.assertEqual({r["id"]: r["why"] for r in priced["rows"]}, {r["id"]: r["why"] for r in ran["rows"]})
        self.assertAlmostEqual(priced["ai_share"], 0.5)
        self.assertIn("the run's own routes", priced["from"])

    def test_before_the_run_the_budget_previews_by_the_same_rule(self):
        priced = budget.routes([{"id": "S1", "to_camera": True, "voice": "a line", "seconds": 5}], None)
        self.assertEqual(priced["rows"][0]["route"], "AI")
        self.assertEqual(priced["ai_share"], 1.0)
        self.assertIn("a preview by the same rule", priced["from"])


if __name__ == "__main__":
    unittest.main()
