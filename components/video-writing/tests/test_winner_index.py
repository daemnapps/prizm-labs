"""winner_index + the trait matrix: a record per winner with its proof and call, copies folded, the swipe and the
winner read from their own teardowns on the same traits, and a ranking that never picks."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(ws, name):
    os.environ["DAEMN_WORKSPACE"] = str(ws)
    os.environ.pop("VIDEO_STUDIO_WRITING", None)
    sp = importlib.util.spec_from_file_location(name + "_t", HERE.parent / "machine" / (name + ".py"))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def run(ws, slug, runtime, fmt, aware_in, aware_out, framework, secs, speakers=1, url=None):
    d = ws / "runs" / "video-teardown" / "_work" / slug
    (d / "stages").mkdir(parents=True)
    (d / "stages" / "0-triage.md").write_text(
        f"RUNTIME: {runtime}\nSOUND FORM: SPOKEN\nSTYLE: phone-ugc — x\nFORMAT: {fmt} — x\nONE LINE: x\n")
    (d / "stages" / "1-teardown.md").write_text("teardown")
    (d / "stages" / "1c-doctrine.md").write_text(
        f"**FRAMEWORK:** {framework}\n\n**CROSSWALK ROW:** {framework}\n\n**SECTIONS CARRIED:** "
        + " · ".join(f"{s} 0:0{i}–0:0{i + 1}" for i, s in enumerate(secs))
        + f"\n\n**AWARENESS ENTRY:** {aware_in}. x\n\n**AWARENESS EXIT:** {aware_out}. x\n\n"
          "**SOPHISTICATION SIGNATURE:** a mechanism. x\n\n**MASS DESIRE:** x\n")
    tr = [{"speaker": f"S{i % speakers}", "text": "why does this keep happening to me every day " * 8}
          for i in range(max(2, speakers))]
    (d / "transcript.json").write_text(json.dumps(tr))
    (d / "run.json").write_text(json.dumps({"slug": slug, "brand": "acme", "post_url": url}))


class WinnerIndex(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())
        (self.ws / "brands" / "acme").mkdir(parents=True)
        reg = {"snapshot": "2026-11-03", "rows": [
            {"id": "acme-paid-core30-01", "rank": 1, "name": "Story Ad", "purchases": 900, "cpa_usd": 50, "roas": 1.4,
             "ran": "2025-01 to 2026-10", "core_message": "the story", "offer": "the offer", "hook": "why?",
             "run": "runs/video-teardown/_work/core30-01-story/"},
            {"id": "acme-paid-core30-02", "rank": 2, "name": "Old Demo", "purchases": 400, "cpa_usd": 60, "roas": 1.2,
             "ran": "2024-01 to 2025-03", "run": "runs/video-teardown/_work/core30-02-demo/"}]}
        (self.ws / "team").mkdir()
        (self.ws / "team" / "registry.json").write_text(json.dumps(reg))
        (self.ws / "runs" / "winners" / "acme").mkdir(parents=True)
        (self.ws / "runs" / "winners" / "acme" / "bank.json").write_text(json.dumps({"rows": [
            {"name": "Story Ad", "source": {"registry": "team/registry.json#acme-paid-core30-01"},
             "snapshots": [{"spend": 45000, "purchases": 900, "cpa": 50, "roas": 1.4, "first": "2025-01",
                            "last": "2026-10"}]}]}))
        story = ["hook", "problem", "root-cause", "unique-mechanism", "proof", "call-to-action"]
        run(self.ws, "core30-01-story", "01:20", "micro-drama", "problem-aware", "solution-aware",
            "Story / testimonial (life · tried · found · now)", story, speakers=3)
        run(self.ws, "core30-01-story-creator", "01:20", "micro-drama", "problem-aware", "solution-aware",
            "Story / testimonial (life · tried · found · now)", story, speakers=3)
        run(self.ws, "core30-02-demo", "00:15", "demonstration", "product-aware", "most-aware",
            "Direct offer (most-aware)", ["hook", "offer", "call-to-action"])
        run(self.ws, "swipe-b", "01:10", "micro-drama", "problem-aware", "solution-aware",
            "Story / testimonial (life · tried · found · now)", story, speakers=2)
        self.wi = load(self.ws, "winner_index")

    def test_every_winner_gets_a_record_with_its_proof_and_call(self):
        idx = self.wi.build("acme")
        by = {r["run"]: r for r in idx["winners"]}
        self.assertEqual(set(by), {"core30-01-story", "core30-01-story-creator", "core30-02-demo"})
        s = by["core30-01-story"]
        self.assertEqual((s["proof"]["purchases"], s["proof"]["spend"], s["proof"]["last_ran"]), (900, 45000, "2026-10"))
        self.assertEqual(s["argument"], "the story")
        self.assertEqual((s["traits"]["aware_in"], s["traits"]["framework"]), ("problem-aware", "Story / testimonial"))
        self.assertEqual(s["retire"]["call"], "keep")
        self.assertEqual(by["core30-01-story-creator"]["copy_of"], "core30-01-story")
        self.assertEqual(by["core30-01-story-creator"]["retire"]["call"], "fold")
        self.assertEqual(by["core30-02-demo"]["retire"]["call"], "keep")            # age retires nothing
        self.assertTrue((self.ws / "runs" / "winners" / "acme" / "winner-index.md").is_file())

    def test_rank_uses_the_matrix_folds_copies_and_never_picks(self):
        self.wi.build("acme")
        wm = load(self.ws, "winner_match")
        r = wm.rank("swipe-b", "acme")
        self.assertIsNone(r["pick"])
        self.assertEqual(r["folded"], 1)
        names = [x["winner"] for x in r["winners"]]
        self.assertEqual(names, ["core30-01-story", "core30-02-demo"])
        top = r["winners"][0]
        for k in ("aware_in", "aware_out", "format", "cast", "framework", "sections", "length"):
            self.assertIn(k, top["matrix"])
        self.assertEqual(top["matrix"]["aware_in"]["mark"], "same")
        self.assertEqual(r["winners"][1]["matrix"]["aware_in"]["mark"], "different")
        self.assertTrue(top["reason"].startswith("same "))
        self.assertEqual(top["proof"]["purchases"], 900)
        self.assertGreater(top["score"], r["winners"][1]["score"])


class WinnerMatchOnChain(WinnerIndex):
    """Stage 2w: every swipe is ranked before writing; the winner lane waits for a person's pick."""

    def _lane(self, lane, winner=None, **kw):
        f = self.ws / "runs" / "video-teardown" / "_work" / "swipe-b" / "run.json"
        st = json.loads(f.read_text())
        st["writing_lane"] = dict({"lane": lane, "winner": winner}, **kw)
        f.write_text(json.dumps(st))
        return st

    def test_the_winner_lane_holds_until_the_owner_picks(self):
        wm = load(self.ws, "winner_match")
        st = self._lane("winner")
        go, why = wm.on_chain(wm.RUNS / "swipe-b", st)
        self.assertFalse(go)
        self.assertIn("waiting for the winner pick", why)
        self.assertEqual(st["stages"]["stage2w"]["status"], "done")
        self.assertIsNone(st["stages"]["stage2w"]["picked"])
        m = json.loads((wm.RUNS / "swipe-b" / "winner-match.json").read_text())
        self.assertIsNone(m["pick"])
        self.assertEqual(m["winners"][0]["winner"], "core30-01-story")

    def test_the_brand_default_is_not_a_pick(self):
        (self.ws / "brands" / "acme" / "winner.json").write_text(json.dumps({"winner": "core30-02-demo"}))
        wm = load(self.ws, "winner_match")
        go, _ = wm.on_chain(wm.RUNS / "swipe-b", self._lane("winner", "core30-02-demo"))
        self.assertFalse(go)

    def test_a_pick_sets_the_lane_and_the_writing_may_go(self):
        wm = load(self.ws, "winner_match")
        st = self._lane("winner")
        wm.on_chain(wm.RUNS / "swipe-b", st)
        (wm.RUNS / "swipe-b" / "run.json").write_text(json.dumps(st))
        got = wm.pick_winner("swipe-b", "core30-01-story", "closest shape")
        self.assertEqual(got, {"run": "swipe-b", "new": False})
        st = json.loads((wm.RUNS / "swipe-b" / "run.json").read_text())
        self.assertEqual(st["writing_lane"]["picked_by"], "owner")
        self.assertNotIn("waiting_for", st)
        self.assertEqual(json.loads((wm.RUNS / "swipe-b" / "winner-pick.json").read_text())["why"], "closest shape")
        go, _ = wm.on_chain(wm.RUNS / "swipe-b", st)
        self.assertTrue(go)

    def test_a_from_scratch_piece_is_never_matched_or_held(self):
        wm = load(self.ws, "winner_match")
        st = self._lane("swipe", why="from scratch: no swipe, no winner")
        go, _ = wm.on_chain(wm.RUNS / "swipe-b", st)
        self.assertTrue(go)
        self.assertEqual(st["stages"]["stage2w"]["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
