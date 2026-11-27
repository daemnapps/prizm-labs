#!/usr/bin/env python3
"""Tests for the moments pass and its query: a scene splits at its real cuts (index, measured, motion jumps), each
unbroken stretch keeps its busiest 1.5-3 s window, captioned scenes are never sent to the judge, labels past a clip's
real end make no moments, a second pass reads nothing, and find/place/look_at give back only clean moments of the
right length (no text, no blur or transition, not dead, the right product, our footage, one section per shot). The
chain's moments-first doors (shot_timing.placed, frame_look.looked) answer from the same rows. No network, no judge."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENTS = HERE.parents[1]


def load(runs: Path):
    os.environ["ASSET_INDEX_RUNS"] = str(runs)
    for k in ("library", "moments"):
        sys.modules.pop(k, None)
    sys.path.insert(0, str(HERE))
    sp = importlib.util.spec_from_file_location("moments", HERE / "moments.py")
    m = importlib.util.module_from_spec(sp)
    sys.modules["moments"] = m
    sp.loader.exec_module(m)
    return m


def fixture(runs: Path, brand="_fixture"):
    d = runs / brand / "library"
    d.mkdir(parents=True)
    (d / "brand-vocabulary.json").write_text(json.dumps({
        "products": {"gadget": ["gadget", "silicone brush"], "cream": ["cream"]},
        "looks": {"gadget": "GADGET: a black silicone brush", "cream": "CREAM: a white tube"}}))
    (d / "cuts.json").write_text(json.dumps({"c1": [6.5]}))
    rows = []
    for cid, n, a, b, marks, lab in [
            ("c1", 1, 0.0, 12.0, ["clean"], "Shared Assets/brands/_fixture/content-creators/a/raw/one.mov"),
            ("c1", 2, 12.0, 30.0, ["clean"], "Shared Assets/brands/_fixture/content-creators/a/raw/one.mov"),
            ("c2", 1, 0.0, 8.0, ["caption"], "Shared Assets/brands/_fixture/content-creators/b/raw/two.mp4"),
            ("c3", 1, 0.0, 9.0, ["clean"], "Shared Assets/brands/_fixture/archive/old/three.mp4"),
            ("c4", 1, 0.0, 6.0, ["clean"], "Shared Assets/brands/_fixture/content-creators/d/raw/four.mov"),
            ("c4", 2, 6.0, 40.0, ["clean"], "Shared Assets/brands/_fixture/content-creators/d/raw/four.mov")]:
        rec = runs / brand / "creators" / cid
        rec.mkdir(parents=True, exist_ok=True)
        (rec / "clip.json").write_text(json.dumps({"meta": {"duration_s": 20.0 if cid == "c4" else 60.0}}))
        rows.append({"clip": cid, "scene": n, "in": a, "out": b, "text_marks": marks, "label": lab,
                     "shows": "man uses the brush", "frame": "creators/%s/frame_01.jpg" % cid})
    return rows


class Pure(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.M = load(Path(self.t.name))

    def tearDown(self):
        self.t.cleanup()

    def test_stretches_split_at_cuts_and_pad(self):
        sp = self.M.stretches(0.0, 10.0, [4.0], clip_end=10.0)
        self.assertEqual(sp, [(0.0, 3.65), (4.35, 10.0)])
        self.assertEqual(self.M.stretches(0.0, 10.0, [1.0, 2.0], clip_end=20.0), [(2.35, 9.65)])   # 1 s bits dropped

    def test_jump_cuts_are_both_ends_of_a_spike(self):
        mv = [2.0] * 20
        mv[9] = 80.0
        self.assertEqual(self.M.jump_cuts(mv, 0.0, 10), [0.9, 1.0])
        self.assertEqual(self.M.jump_cuts([2.0] * 20, 0.0, 10), [])

    def test_windows_take_the_busiest_and_split_long_stretches(self):
        mv = [1.0] * 200
        for i in range(20, 40):
            mv[i] = 30.0
        ws = self.M.windows(mv, 0.0, [(0.0, 20.0)], 10)
        self.assertEqual(len(ws), 3)                      # 20 s in pieces of at most 8 s
        self.assertTrue(all(1.5 <= w["out"] - w["in"] <= 3.0 for w in ws))
        busy = max(ws, key=lambda w: w["motion"])
        self.assertTrue(1.0 <= busy["in"] <= 2.0, busy)
        short = self.M.windows([5.0] * 30, 0.0, [(0.0, 2.0)], 10)
        self.assertEqual(short[0]["out"] - short[0]["in"], 2.0)


class Pass(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        runs = Path(self.t.name)
        self.M = load(runs)
        rows = fixture(runs)
        self.M.LIB.rows_of = lambda brand: rows
        self.M.LIB.use_brand("_fixture")
        self.reads = []

        def read_scene(brand, r, a, b):
            self.reads.append((r["clip"], r["scene"]))
            n = int(round((b - a) * 10))
            mv = [3.0 + (i % 7) for i in range(n)]
            return {"mv": mv, "cuts": [round(a + 3.0, 2)] if r["clip"] == "c1" and r["scene"] == 2 else [],
                    "source": "proxy", "fps": 10}

        def strip(brand, r, at, w, out):
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"jpg")
            return out
        self.M.read_scene, self.M.strip = read_scene, strip
        self.asked = []

        def ask(q, pics):
            self.asked.append(len(pics))
            return {"moments": [{"n": i + 1, "product_in_use": True, "product": "gadget", "text_on_screen": False,
                                 "blur_or_transition": False, "dead": i % 3 == 2, "people": "one", "who": "man",
                                 "shows": "uses the brush", "why": ""} for i in range(len(pics))]}
        self.ask = ask

    def tearDown(self):
        self.t.cleanup()

    def test_pass_writes_moments_and_resumes(self):
        dry = self.M.run("_fixture", 5.0, dry=True)
        self.assertEqual(dry["scenes"], 5)                # the archive clip is not ours
        res = self.M.run("_fixture", 5.0, workers=2, ask=self.ask)
        self.assertEqual(res["scenes_read"], 5)
        self.assertNotIn(("c3", 1), self.reads)
        ms = {m["id"]: m for m in self.M._jsonl(self.M.mdir("_fixture") / "moments.jsonl")}
        cap = [m for m in ms.values() if m["clip"] == "c2"]
        self.assertTrue(cap and all(m["judge"]["text_on_screen"] and not m.get("judged_by") for m in cap))
        self.assertTrue(all(m["out"] <= 20.0 for m in ms.values() if m["clip"] == "c4"))   # clip is 20 s, labels say 40
        c1 = sorted((m for m in ms.values() if m["clip"] == "c1"), key=lambda m: m["in"])
        for m in c1:                                      # no moment crosses the index cut (6.5) or the measured one (15)
            self.assertFalse(m["stretch"][0] - 0.01 < 6.5 < m["stretch"][1] + 0.01, m)
            self.assertFalse(m["stretch"][0] - 0.01 < 15.0 < m["stretch"][1] + 0.01, m)
        self.assertTrue(all(n <= self.M.PER_ASK for n in self.asked))
        self.reads.clear()
        again = self.M.run("_fixture", 5.0, workers=2, ask=self.ask)
        self.assertEqual((again["scenes_read"], self.reads), (0, []))

    def test_budget_stops_the_judge_and_a_later_pass_finishes(self):
        self.M.run("_fixture", 0.0001, workers=1, ask=self.ask)
        left = [m for m in self.M._jsonl(self.M.mdir("_fixture") / "moments.jsonl") if m["needs_judge"] and not m["judge"]]
        self.assertTrue(left)
        self.M.run("_fixture", 5.0, workers=1, ask=self.ask)
        latest = {}
        for m in self.M._jsonl(self.M.mdir("_fixture") / "moments.jsonl"):
            latest[m["id"]] = m
        self.assertFalse([m for m in latest.values() if m["needs_judge"] and not m["judge"]])

    def test_queries_give_only_clean_moments(self):
        self.M.run("_fixture", 5.0, workers=2, ask=self.ask)

        class S:
            @staticmethod
            def search(words, brand="", per=0):
                return [{"clip_id": c, "shared_path": lab, "score": sc, "in": 0.0, "out": 12.0} for c, lab, sc in [
                    ("c3", "Shared Assets/brands/_fixture/archive/old/three.mp4", 0.9),
                    ("c2", "Shared Assets/brands/_fixture/content-creators/b/raw/two.mp4", 0.8),
                    ("c1", "Shared Assets/brands/_fixture/content-creators/a/raw/one.mov", 0.7),
                    ("c4", "Shared Assets/brands/_fixture/content-creators/d/raw/four.mov", 0.6)]]
        sys.modules["moments_search"] = S
        hits = self.M.find("_fixture", "man uses the brush", 2.5, need_product="GADGET Pro Brush")
        self.assertEqual([h["clip"] for h in hits], ["c1", "c4"])      # archive and captioned clips are out
        for h in hits:
            self.assertAlmostEqual(h["out"] - h["in"], 2.5)
            self.assertFalse(h["judge"]["dead"] or h["judge"]["text_on_screen"])
        self.assertEqual(self.M.find("_fixture", "x", 2.5, need_product="cream"), [])   # nobody uses the cream
        self.assertEqual([h["clip"] for h in self.M.find("_fixture", "x", 2.5, exclude=["c1"])], ["c4"])
        lab = "/Volumes/x/Shared Assets/brands/_fixture/content-creators/a/raw/one.mov"
        self.assertTrue(self.M.known("_fixture", lab))
        at, m = self.M.place("_fixture", lab, 0.0, 2.5, "gadget")
        self.assertTrue(m["stretch"][0] <= at and at + 2.5 <= m["stretch"][1])
        at2, m2 = self.M.place("_fixture", lab, 0.0, 2.5, "gadget", avoid=[(at, at + 2.5)])
        self.assertFalse(at2 < at + 2.5 and at < at2 + 2.5)            # one clip section per shot
        self.assertEqual(self.M.look_at("_fixture", lab, at, 2.5)["id"], m["id"])
        self.assertIsNone(self.M.place("_fixture", lab, 0.0, 15.0))    # no unbroken stretch that long
        self.assertFalse(self.M.known("_fixture", "Shared Assets/brands/_fixture/none.mov"))


class Chain(unittest.TestCase):
    """The chain's moments-first doors read the same rows (skipped where the chain files are not installed)."""

    def test_placed_and_looked(self):
        st = COMPONENTS / "video-edit" / "machine" / "shot_timing.py"
        fl = COMPONENTS / "video-production" / "machine" / "frame_look.py"
        if not (st.is_file() and fl.is_file()):
            self.skipTest("chain files not here")
        with tempfile.TemporaryDirectory() as t:
            M = load(Path(t))
            rows = fixture(Path(t))
            M.LIB.rows_of = lambda brand: rows
            M.LIB.use_brand("_fixture")
            M.read_scene = lambda brand, r, a, b: {"mv": [4.0] * int((b - a) * 10), "cuts": [], "source": "proxy", "fps": 10}
            M.strip = lambda brand, r, at, w, out: (out.parent.mkdir(parents=True, exist_ok=True), out.write_bytes(b"x"))[0] or out
            M.run("_fixture", 5.0, workers=1, ask=lambda q, p: {"moments": [
                {"n": i + 1, "product_in_use": True, "product": "cream", "text_on_screen": False,
                 "blur_or_transition": False, "dead": False} for i in range(len(p))]})
            sys.modules["chain_asset_index_moments"] = M
            specs = {}
            for name, f in (("t_shot_timing", st), ("t_frame_look", fl)):
                sp = importlib.util.spec_from_file_location(name, f)
                specs[name] = importlib.util.module_from_spec(sp)
                sp.loader.exec_module(specs[name])
            T, L = specs["t_shot_timing"], specs["t_frame_look"]
            lab = "Shared Assets/brands/_fixture/content-creators/a/raw/one.mov"
            known, at = T.placed("_fixture", lab, 0.0, 2.5)
            self.assertTrue(known and at is not None)
            self.assertEqual(T.placed("_fixture", "Shared Assets/x/new.mov", 0.0, 2.5), (False, None))
            self.assertEqual(T.placed("_fixture", lab, 0.0, 2.5, product="gadget"), (True, None))   # swap the clip
            ok, said = L.looked("_fixture", lab, at, 2.5, "the man uses the brush", {"product": "gadget"})
            self.assertFalse(ok)
            self.assertIn("another product", said)
            ok, said = L.looked("_fixture", lab, at, 2.5, "he smiles", {"product": "gadget"})
            self.assertTrue(ok and "moments index" in said)
            self.assertIsNone(L.looked("_fixture", "Shared Assets/x/new.mov", 0.0, 2.5, "x", {}))
            sys.modules.pop("chain_asset_index_moments", None)


if __name__ == "__main__":
    unittest.main()
