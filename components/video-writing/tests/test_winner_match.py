"""winner_match: ranking from teardown files only, and a switch run that carries the teardown and nothing written."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(ws):
    os.environ["DAEMN_WORKSPACE"] = str(ws)
    os.environ.pop("VIDEO_STUDIO_WRITING", None)
    sp = importlib.util.spec_from_file_location("winner_match_t", HERE.parent / "machine" / "winner_match.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def run(ws, slug, brand, runtime, words, fmt, delivery, humor="none", written=False):
    d = ws / "runs" / "video-teardown" / "_work" / slug
    (d / "stages").mkdir(parents=True)
    (d / "stages" / "0-triage.md").write_text(f"RUNTIME: {runtime}\nSOUND FORM: SPOKEN\nFORMAT: {fmt} — x\nONE LINE: x\n")
    (d / "stages" / "1-teardown.md").write_text("teardown")
    (d / "stages" / "2-spec.md").write_text("spec")
    (d / "transcript.json").write_text(json.dumps([{"speaker": "S1", "text": " ".join(["word"] * words)}]))
    (d / "doctrine.json").write_text(json.dumps({"format": fmt, "delivery": {"delivery_style": delivery, "humor": humor}}))
    (d / "run.json").write_text(json.dumps({"slug": slug, "brand": brand, "format_id": fmt, "state": "done",
                                            "stages": {"stage2": {"status": "done"}, "stage3": {"status": "done"}},
                                            "writing_lane": {"lane": "winner", "winner": "brand-core-01"}}))
    if written:
        (d / "stages" / "3-injection.md").write_text("written")
        (d / "writing-result.json").write_text("{}")


class WinnerMatch(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())
        (self.ws / "brands" / "acme").mkdir(parents=True)
        (self.ws / "brands" / "acme" / "winner.json").write_text(json.dumps({"winner": "brand-core-01", "label": "Core 1"}))
        run(self.ws, "brand-core-01", "acme", "00:14", 30, "demonstration", "hype")
        run(self.ws, "brand-core-02-skit", "acme", "01:30", 400, "comedy-skit", "deadpan", humor="absurd")
        run(self.ws, "other-core-03", "other", "01:30", 400, "comedy-skit", "deadpan", humor="absurd")
        run(self.ws, "swipe-a", "acme", "01:40", 420, "comedy-skit", "deadpan", humor="dry", written=True)
        self.m = load(self.ws)

    def test_rank_puts_the_closer_format_first_and_marks_the_one_in_use(self):
        r = self.m.rank("swipe-a")
        names = [x["winner"] for x in r["winners"]]
        self.assertEqual(names, ["brand-core-02-skit", "brand-core-01"])        # other brand's run not banked here
        self.assertTrue(r["winners"][1]["current"])
        self.assertTrue(any("length" in f for f in r["winners"][0]["facts"]))

    def test_switch_carries_the_teardown_and_nothing_written(self):
        slug, new = self.m.prepare("swipe-a", "brand-core-02-skit", "closest format")
        d = self.ws / "runs" / "video-teardown" / "_work" / slug
        self.assertTrue(new)
        self.assertTrue((d / "stages" / "2-spec.md").is_file())
        self.assertFalse((d / "stages" / "3-injection.md").exists())
        self.assertFalse((d / "writing-result.json").exists())
        rec = json.loads((d / "run.json").read_text())
        self.assertEqual(rec["writing_lane"]["winner"], "brand-core-02-skit")
        self.assertNotIn("stage3", rec["stages"])
        self.assertNotIn("state", rec)
        pick = json.loads((d / "winner-pick.json").read_text())
        self.assertEqual((pick["swipe_run"], pick["why"], pick["rank"]), ("swipe-a", "closest format", 1))
        self.assertEqual(self.m.source_run(slug), "swipe-a")                     # ranking a switched run reads the swipe
        self.assertEqual(self.m.prepare(slug, "brand-core-02-skit")[1], False)   # same switch again opens nothing new


if __name__ == "__main__":
    unittest.main()
