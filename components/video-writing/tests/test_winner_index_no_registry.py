"""A brand with no winner registry still gets proof: each Core teardown run reaches its bank row through the audit
video it tore down; a partial second run of the same video folds under the finished one; the variation proof gate
and the winner lane read the same tie."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def load(ws, name, path):
    os.environ["DAEMN_WORKSPACE"] = str(ws)
    os.environ.pop("VIDEO_STUDIO_WRITING", None)
    sp = importlib.util.spec_from_file_location(name + "_nr", path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def teardown(ws, slug, video, finished=True):
    d = ws / "runs" / "video-teardown" / "_work" / slug
    (d / "stages").mkdir(parents=True)
    (d / "stages" / "0-triage.md").write_text("RUNTIME: 00:40\nSOUND FORM: SPOKEN\nSTYLE: phone-ugc — x\n"
                                              "FORMAT: single-presenter — x\nONE LINE: x\n")
    (d / "stages" / "1-teardown.md").write_text("## 6. THE CORE MESSAGE\nCore message: it works.\n")
    (d / "stages" / "1-transcript.md").write_text("why does this keep happening to me every day")
    if finished:
        for f in ("1c-doctrine.md", "1k-culture.md", "2-spec.md"):
            (d / "stages" / f).write_text("x")
    (d / "run.json").write_text(json.dumps({"slug": slug, "brand": "acme", "video": video}))


class NoRegistry(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())
        (self.ws / "brands" / "acme").mkdir(parents=True)
        home = self.ws / "runs" / "winners" / "acme"
        home.mkdir(parents=True)
        win = "audit/2025-01-01_2026-11-02"
        (home / "bank.json").write_text(json.dumps({"bar": {}, "rows": [
            {"id": "acme-111", "name": "Script 30", "core": True, "format": "Video",
             "source": {"audit": win, "teardown": win + "/teardowns/01-script-30/teardown.md", "registry": None},
             "snapshots": [{"spend": 1700, "purchases": 26, "cpa": 65.4, "roas": 1.3, "first": "2025-02", "last": "2026-10"}]},
            {"id": "acme-222", "name": "Script 86", "core": True, "format": "Video",
             "source": {"audit": win, "teardown": win + "/teardowns/02-script-86/teardown.md", "registry": None},
             "snapshots": [{"spend": 900, "purchases": 10, "cpa": 90, "roas": 0.9, "first": "2025-03", "last": "2026-09"}]}]}))
        vid = "runs/creative-audit/acme/2025-01-01_2026-11-02/videos/%s.mp4"
        teardown(self.ws, "acme-core8-01", vid % "01-script-30", finished=False)
        teardown(self.ws, "acme-core8-01-flash", vid % "01-script-30")
        teardown(self.ws, "acme-core8-02-flash", vid % "02-script-86")
        self.wi = load(self.ws, "winner_index", REPO / "components/video-writing/machine/winner_index.py")

    def test_proof_reaches_the_bank_through_the_audit_video(self):
        idx = self.wi.build("acme")
        by = {r["run"]: r for r in idx["winners"]}
        one = by["acme-core8-01-flash"]
        self.assertEqual((one["proof"]["purchases"], one["proof"]["spend"], one["proof"]["source"]), (26, 1700, "bank"))
        self.assertEqual(one["bank_id"], "acme-111")
        self.assertEqual(one["label"], "Winner #1 · script 30")
        self.assertEqual(one["retire"]["call"], "keep")
        self.assertEqual(by["acme-core8-02-flash"]["retire"]["call"], "watch")      # return under 1.0x
        self.assertEqual(by["acme-core8-01"]["copy_of"], "acme-core8-01-flash")     # the partial run folds
        self.assertEqual(by["acme-core8-01"]["retire"]["call"], "fold")

    def test_the_proof_gate_reads_the_same_tie(self):
        self.wi.build("acme")
        sys.path.insert(0, str(REPO / "components/video-teardown/machine"))
        try:
            import proven
        finally:
            sys.path.pop(0)
        old = proven.C.WS
        proven.C.WS = self.ws
        self.addCleanup(setattr, proven.C, "WS", old)
        ok, proof, _ = proven.check("acme", "acme-core8-01-flash")
        self.assertTrue(ok)
        self.assertEqual(proof[0]["name"], "Script 30")
        ok, proof, _ = proven.check("acme", "acme-core8-01")                      # a copy reads its original
        self.assertTrue(ok)
        self.assertFalse(proven.check("acme", "some-swipe-999")[0])


class ShapeInTheLane(unittest.TestCase):
    """The winner lane carries the winner's story shape as its section plan, and keeps the founder out as teller."""

    def test_shape_block(self):
        w2 = load(REPO, "writing_v2", REPO / "components/video-writing/machine/writing_v2.py")
        ws = Path(tempfile.mkdtemp())
        (ws / "runs/winners/acme/shapes").mkdir(parents=True)
        (ws / "runs/winners/acme/shapes/shapes.json").write_text(json.dumps({"winners": [
            {"run": "acme-core8-01-flash", "folded_copies": ["acme-core8-01"], "arc": "person-in-a-hole",
             "arc_fit": "clear", "arc_why": "fall then rise", "arc_beats": ["Fine", "Falls in", "Rock bottom"],
             "devices": ["the-confession"], "teller": "founder"}]}))
        old = w2.WS
        w2.WS = ws
        self.addCleanup(setattr, w2, "WS", old)
        got = w2.winner_shape("acme", "acme-core8-01")                  # a folded copy reads its original's call
        self.assertIn("WINNER SHAPE: person-in-a-hole (clear fit). fall then rise", got)
        self.assertIn("Fine → Falls in → Rock bottom", got)            # no controls file here: the call's own beats
        self.assertIn("never the founder as teller", got)
        self.assertEqual(w2.winner_shape("acme", "no-such-run"), "")
        self.assertEqual(w2.winner_shape("other", "acme-core8-01"), "")
        w2.WS = old
        live = w2.winner_shape("brand_a", "core30-01-hi-res-product-focus")
        if live:                                                        # on this checkout: beats carry their sections
            self.assertRegex(live, r"\[[a-z-]+\]")


if __name__ == "__main__":
    unittest.main()
