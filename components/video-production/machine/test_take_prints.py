#!/usr/bin/env python3
"""Finished 3D set prints are taken as a run's start pictures: nothing generated, nothing spent (2026-11-20)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import take_prints as TP  # noqa: E402


class TakePrints(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="takeprints_"))
        self.ho = self.tmp / "handoff"
        (self.ho / "returned").mkdir(parents=True)
        (self.ho / "RUN.md").write_text(
            "### Step 1 · `b_asset-01.png` · start picture for S1-shot-1\n"
            "### Step 2 · `b_asset-02.mp4` · clip for S1-shot-1 · talking\n"
            "### Step 3 · `b_asset-03-shot-2.png` · start picture for S1-shot-2\n"
            "### Step 4 · `b_asset-09.png` · start picture for S6\n"
            "### Step 5 · `b_asset-11.png` · start picture for S7-shot-1\n")
        for name, job in (("b_asset-01.png", "3d-print"), ("b_asset-03-shot-2.png", "3d-print"),
                          ("b_asset-09.png", "3d-print"), ("b_asset-11.png", "hand-made")):
            (self.ho / "returned" / name).write_bytes(name.encode())
            (self.ho / "returned" / (name + ".made.json")).write_text(json.dumps({"job": job}))
        self.run = self.tmp / "run"
        self.run.mkdir()

    def test_prints_become_start_frames_and_the_rest_is_refused_or_listed(self):
        res = TP.take(self.run, self.ho)
        self.assertEqual(sorted(res["taken"]), ["S1-F1", "S6-F1"])                 # a one-shot scene has no -shot-N
        self.assertIn("b_asset-11.png", res["refused"])                              # not a 3D print: refused
        self.assertEqual(res["extra"]["S1"][0]["shot"], "S1.2")
        shots = json.loads((self.run / "shot-pictures.json").read_text())
        self.assertEqual(shots["S1"][0]["shot"], "S1.2")                            # the later shot keeps its own print
        self.assertEqual(Path(shots["S1"][0]["file"]).read_bytes(), b"b_asset-03-shot-2.png")
        made = json.loads((self.run / "direct.json").read_text())
        self.assertEqual(made["S1-F1"]["door"], "3d-print")
        self.assertEqual((self.run / "media" / "S1-F1.png").read_bytes(), b"b_asset-01.png")

    def test_a_different_picture_already_made_is_kept(self):
        (self.run / "media").mkdir()
        other = self.run / "media" / "S1-F1.png"
        other.write_bytes(b"made by the run")
        (self.run / "direct.json").write_text(json.dumps({"S1-F1": {"file": str(other)}}))
        res = TP.take(self.run, self.ho)
        self.assertIn("S1-F1", res["kept"])
        self.assertEqual(other.read_bytes(), b"made by the run")

    def test_the_clip_plan_sends_each_later_shot_its_own_print(self):
        import clips_run as CR
        from unittest import mock
        TP.take(self.run, self.ho)
        with mock.patch.object(CR, "HERE", Path(str(self.tmp)) / "a" / "b" / "c"):   # workspace root = tmp
            sp = CR.shot_pictures_of(self.run, ["S1", "S9"])
        self.assertEqual([x["shot"] for x in sp], ["S1.2"])
        self.assertTrue(sp[0]["file"].startswith("run/media/"))

    def test_a_dry_run_writes_nothing(self):
        TP.take(self.run, self.ho, dry=True)
        self.assertEqual(list(self.run.iterdir()), [])


class PastedProduct(unittest.TestCase):
    def test_every_product_of_the_scene_is_pasted_and_recorded(self):
        from unittest import mock
        run = Path(tempfile.mkdtemp(prefix="paste_"))
        (run / "media").mkdir()
        pic = run / "media" / "S1-F1.png"
        pic.write_bytes(b"drawn")
        cr = mock.MagicMock()
        cr.product_ids.return_value = ["p"]
        cr.brand_of.return_value = "b"
        calls = []

        def paste(picture, kit, out=None, what=""):
            calls.append((Path(kit).name, what))
            Path(out).write_bytes(b"real")
            return {"ok": True, "angle": 30, "overlap": 0.8}
        with mock.patch.object(TP, "_load", lambda n: cr):
            rec = TP.paste_products(run, pic, "S1", paste=paste)
        self.assertEqual(rec["p"]["angle"], 30)
        self.assertEqual(calls[0][0], "p")
        self.assertEqual(pic.read_bytes(), b"real")
        self.assertEqual((run / "media" / "versions" / "S1-F1-before-paste.png").read_bytes(), b"drawn")
        saved = json.loads((run / "media" / "S1-F1.paste.json").read_text())
        self.assertEqual(saved["picture_sha"], TP._sha(pic))



class TakeSets(unittest.TestCase):
    """brief-0380: 18 sets filed kept and the picture step generated six stills over them."""
    def setUp(self):
        import tempfile
        from unittest import mock
        self.t = Path(tempfile.mkdtemp())
        self.run = self.t / "b_x_brief-0001"; (self.run / "media").mkdir(parents=True)
        self.sets = self.t / "sets"; self.reqs = self.t / "set-requests"; self.reqs.mkdir()
        for name, note in (("s1-f1", "kept: right"), ("s2-shot-2", "kept: right"), ("s3-f1", "wrong: x")):
            d = self.sets / f"b-x-brief-0001-{name}"; d.mkdir(parents=True)
            (d / "print-v1.png").write_bytes(name.encode())
        (self.run / "media" / "S1-F1.png").write_bytes(b"generated")
        sg = mock.MagicMock()
        sg.kept_print.side_effect = lambda b, n: (self.sets / n / "print-v1.png") if not n.endswith("s3-f1") else None
        sg.is_kept_print.return_value = False
        p = mock.patch.object(TP, "_set_gate", lambda: sg); p.start(); self.addCleanup(p.stop)

    def test_kept_prints_become_the_pictures_and_a_generated_one_is_set_aside(self):
        r = TP.take_sets(self.run, "b", sets_root=self.sets)
        self.assertEqual((self.run / "media" / "S1-F1.png").read_bytes(), b"s1-f1")
        self.assertEqual((self.run / "media" / "S2-shot-2.png").read_bytes(), b"s2-shot-2")
        self.assertIn("S1-F1", r["set_aside"])
        self.assertTrue(Path(r["set_aside"]["S1-F1"]).read_bytes() == b"generated")
        self.assertEqual(r["waiting"], ["b-x-brief-0001-s3-f1"])
        made = json.loads((self.run / "direct.json").read_text())
        self.assertEqual(made["S1-F1"]["door"], "3d-print")
        self.assertIn("S2", json.loads((self.run / "shot-pictures.json").read_text()))

    def test_a_dry_run_moves_and_copies_nothing(self):
        TP.take_sets(self.run, "b", dry=True, sets_root=self.sets)
        self.assertEqual((self.run / "media" / "S1-F1.png").read_bytes(), b"generated")

    def test_the_print_record_names_the_print_the_picture_now_is(self):
        side = self.run / "media" / "S1-F1.png.print.json"
        side.write_text(json.dumps({"print": "old/print-v0.png"}))
        TP.take_sets(self.run, "b", sets_root=self.sets)
        want = str(self.sets / "b-x-brief-0001-s1-f1" / "print-v1.png")
        self.assertEqual(json.loads(side.read_text())["print"], want)
        side.write_text(json.dumps({"print": "old/print-v0.png"}))      # already taken: the record is still put right
        TP.take_sets(self.run, "b", sets_root=self.sets)
        self.assertEqual(json.loads(side.read_text())["print"], want)

if __name__ == "__main__":
    unittest.main()
