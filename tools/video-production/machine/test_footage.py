#!/usr/bin/env python3
"""The footage step — our own clips first (the owner, 2026-10-05). No network, no
drive: the index, its Shared Assets map and the drive root are temp folders,
and the old search service is never asked.

    /usr/bin/python3 machine/test_footage.py
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
BRIEF = FIX / "brief-v15.md"


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"test_fo_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


footage = load("footage")
run = load("run")
shared_paths = sys.modules["shared_paths"]
sys.path.insert(0, str(HERE.parents[1] / "asset-index" / "machine"))
from test_index import make_record  # noqa: E402

MB = 1048576


def quiet(fn, *a, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = fn(*a, **kw)
    return code, buf.getvalue()


@contextlib.contextmanager
def env():
    saved = dict(os.environ)
    saved_mod = sys.modules.get("daemn_keys")
    sys.modules["daemn_keys"] = types.SimpleNamespace(key=lambda name, required=False: "")
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(saved)
        if saved_mod is None:
            sys.modules.pop("daemn_keys", None)
        else:
            sys.modules["daemn_keys"] = saved_mod


class Index(unittest.TestCase):
    """A brand `_fixture` with three clips on a fake Shared Assets drive."""

    BRAND = "_fixture"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-footage-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = self.tmp / "Shared Assets"
        self.work = self.tmp / "work"
        self.maps = self.work / "_maps"
        for attr, val in (("SHARED_ROOT", self.root), ("WORK", self.work), ("MAPS", self.maps)):
            self.addCleanup(setattr, shared_paths, attr, getattr(shared_paths, attr))
            setattr(shared_paths, attr, val)
        self.addCleanup(setattr, footage, "_service", footage._service)
        footage._service = lambda *a, **k: []          # the old service is never asked in a test
        files = []
        col = f"{self.BRAND}-creators"

        def clip(cid, visuals, spoken=None, **kw):
            p = self.root / "brands" / self.BRAND / "content-creators" / cid / "raw" / f"{cid}.MOV"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"")
            files.append({"path": str(p), "name": p.name, "bytes": 10 * MB})
            make_record(self.work, col, cid, filename=p.name, folder=cid, size_mb=10.0, duration=12.0,
                        scenes=[{"t_start": 2.0, "t_end": 7.5, "visuals": visuals, "spoken": spoken,
                                 "on_screen_text": None}], **kw)

        clip("shelf", "A hand reaches upward toward a wooden shelf in daylight.",
             subject="One hand and forearm", setting="Room with a shelf")
        clip("jaw", "Man runs fingertips along his jawline and neck, razor bumps visible.",
             spoken="it bumps up a day later", subject="Adult man", setting="Bathroom")
        clip("box", "Hands open a black product box and lift the lid.", subject="Hands", setting="Counter")
        shared_paths.build_map(self.work / col, files, self.root, self.maps)


# ---------------------------------------------------------------- the gate

def broll(sid, happens, subject, action, refs=None, **kw):
    return {"id": sid, "kind": "broll", "to_camera": False, "happens": happens,
            "frames": [{"role": "first", "subject": subject, "action": action,
                        "refs": list(refs or ["the style frame"])}], **kw}


class Gate(Index):
    def plan(self):
        return {"brand": self.BRAND, "cast": {"names": ["KEMAR"]}, "scenes": [
            # the presenter says the very words a clip shows — still never the library's
            {"id": "S1", "kind": "talking", "to_camera": True, "happens": "runs fingertips along his jawline",
             "frames": [{"role": "first", "subject": "KEMAR's jaw and neck, razor bumps", "action": "fingertips on jawline"}]},
            broll("S2", "runs his fingertips along the jawline", "KEMAR's jaw and the neck, razor bumps",
                  "the fingertips run along the jawline and neck"),
            broll("S3", "throws a ball through a hoop", "a basketball court at night",
                  "the ball drops through the net"),
            {"id": "S4", "kind": "card", "to_camera": False, "happens": "hand reaches upward to the shelf"},
            # a scene that does not say whether it is to camera is never handed to the library
            {"id": "S5", "happens": "runs fingertips along his jawline"},
            broll("S6", "opens the the device box and lifts the lid", "the the device™ box in two hands",
                  "the hands open the box and lift the lid"),
        ]}

    def test_cut_generate_presenter_and_made_are_decided_before_anything_is_made(self):
        plan = self.plan()
        res = footage.gate(plan, self.BRAND)
        by = {s["id"]: s for s in plan["scenes"]}
        self.assertTrue(res["indexed"])
        self.assertEqual(res["presenter"], ["S1", "S5"])
        self.assertEqual(res["cut"], ["S2"])
        self.assertEqual(sorted(res["generate"]), ["S3", "S6"])
        self.assertEqual(res["other"], ["S4"])
        # the cut carries our clip, its time range and its frame — a Shared Assets path, never another
        s2 = by["S2"]
        self.assertEqual(s2["source_plan"], "cut")
        self.assertEqual(s2["owned_clip"], "jaw")
        self.assertEqual((s2["owned_in"], s2["owned_out"]), (2.0, 7.5))
        self.assertTrue(s2["owned_file"].startswith(str(self.root)))
        self.assertTrue(s2["owned_frame"].endswith("frame_01.jpg"))
        self.assertNotIn("owned_file", by["S1"])
        self.assertEqual(by["S1"]["owned_candidates"], [])

    def test_a_clip_without_the_named_product_is_a_reference_not_a_cut(self):
        plan = self.plan()
        footage.gate(plan, self.BRAND)
        s6 = next(s for s in plan["scenes"] if s["id"] == "S6")
        self.assertEqual(s6["source_plan"], "generate")
        self.assertEqual(s6["footage_ref"]["clip"], "box")
        # the nearest real clip's frame rides along as a picture reference for the generator
        self.assertIn(s6["footage_ref"]["frame"], s6["frames"][0]["refs"])
        self.assertEqual(s6["frames"][0]["refs"][0], "the style frame")

    def test_a_cut_scene_makes_no_still_and_no_clip(self):
        plan = self.plan()
        footage.gate(plan, self.BRAND)
        ids = {it.get("for") or it.get("id") for it in run.scene_shape_items(plan, self.BRAND)}
        self.assertNotIn("S2", ids)

    def test_no_index_for_the_brand_means_every_broll_scene_is_generated(self):
        plan = self.plan()
        res = footage.gate(plan, "no-such-brand")
        self.assertFalse(res["indexed"])
        self.assertEqual(res["cut"], [])
        self.assertIn("S2", res["generate"])

    def test_an_older_plans_cutaways_go_through_the_same_gate(self):
        plan = {"scenes": [{"id": "A1", "line": "hello", "gesture": "hand reaches upward to the shelf"}],
                "cutaways": [{"id": "S2", "subject": "a hand reaching upward toward a wooden shelf",
                              "action": "a hand reaches upward toward the shelf"}]}
        res = footage.gate(plan, self.BRAND)
        self.assertEqual(res["presenter"], ["A1"])
        self.assertEqual(res["cut"], ["S2"])
        self.assertEqual(plan["cutaways"][0]["owned_clip"], "shelf")


class ClipPlannersSkipCutSections(unittest.TestCase):
    def test_a_section_entirely_cut_from_our_footage_gets_no_clip(self):
        by_id = {"S2": {"source_plan": "cut", "owned_file": "/x.mov"},
                 "S3": {"source_plan": "generate"}}
        for mod in (load("omni_clips"), load("clips_plan")):
            self.assertTrue(mod.cut_from_footage(["S2"], by_id))
            self.assertFalse(mod.cut_from_footage(["S2", "S3"], by_id))
            self.assertFalse(mod.cut_from_footage([], by_id))


# ---------------------------------------------------------------- run.py start

class StartRunsTheGate(Index):
    def setUp(self):
        super().setUp()
        cast = self.tmp / "cast" / "the-speaker"
        cast.mkdir(parents=True)
        shutil.copy2(FIX / "cast-root" / "lead" / "voice.json", cast / "voice.json")

    def args(self, *extra):
        return run.build_parser().parse_args([
            "start", str(BRIEF), "--brand", self.BRAND, "--format", "fixture-format",
            "--label", "footage", "--bank", str(FIX / "bank.json"),
            "--runs-root", str(self.tmp / "runs"), "--cast-root", str(self.tmp / "cast"),
            "--banks", str(FIX / "banks"), "--provider", "higgsfield-ui", "--yes", "--dry-run",
            "--composed", *extra])

    def items(self):
        r = self.tmp / "runs" / "video-production" / self.BRAND / "footage"
        return r, [it["id"] for bf in sorted((r / "batches").glob("*.json"))
                   for it in json.loads(bf.read_text())["items"]]

    def test_the_dry_run_cuts_the_fixtures_broll_scene_from_our_footage(self):
        with env():
            code, out = quiet(run.cmd_start, self.args())
        self.assertEqual(code, 0, out)
        self.assertIn("footage: 1 B-roll scene(s) CUT from our footage", out)
        self.assertIn("cut S2 from our footage", out)
        self.assertRegex(out, r"footage: 3 still\(s\)/clip\(s\) not made — ~[\d.]+ credits")
        r, ids = self.items()
        plan = json.loads((r / "plan.json").read_text())
        s2 = next(s for s in plan["scenes"] if s["id"] == "S2")
        self.assertEqual(s2["source_plan"], "cut")
        self.assertEqual(s2["owned_clip"], "shelf")
        self.assertNotIn("S2", ids)
        self.assertNotIn("S2-F1", ids)
        self.assertIn("S1-F1", ids)                    # the presenter is made as ever
        s1 = next(s for s in plan["scenes"] if s["id"] == "S1")
        self.assertEqual(s1["source_plan"], "presenter")

    def test_no_footage_skips_it(self):
        with env():
            code, out = quiet(run.cmd_start, self.args("--no-footage"))
        self.assertEqual(code, 0, out)
        self.assertNotIn("CUT from our footage", out)
        _, ids = self.items()
        self.assertIn("S2", ids)


# ---------------------------------------------------------------- the brief ledger

class BriefLedger(Index):
    def test_the_ledger_lands_where_it_is_told_and_never_touches_the_brief(self):
        before = BRIEF.read_text()
        out_dir = self.tmp / "ledger"
        out = footage.brief_pass(BRIEF, self.BRAND, out_dir=out_dir)
        self.assertEqual(BRIEF.read_text(), before)
        self.assertFalse((BRIEF.parent / "footage.json").exists())
        self.assertEqual((out["broll"], out["cut"], out["generate"]), (1, 1, 0))
        row = next(r for r in out["scenes"] if r["scene"] == "S2")
        self.assertEqual(row["plan"], "cut")
        self.assertEqual(row["candidates"][0]["clip_id"], "shelf")
        self.assertEqual((row["candidates"][0]["in"], row["candidates"][0]["out"]), (2.0, 7.5))
        md = (out_dir / "footage.md").read_text()
        self.assertIn("S2 — REAL CLIP", md)
        self.assertIn("2.0–7.5s", md)
        self.assertTrue(json.loads((out_dir / "footage.json").read_text())["indexed"])


if __name__ == "__main__":
    unittest.main()
