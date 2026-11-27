"""The self-reinforcing learnings loop (run_kit/learnings.py): capture, promotion, hand-off, checks.

    python3 test_learnings.py
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_kit import learnings as L  # noqa: E402


class Loop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        (self.repo / "runs" / "learnings").mkdir(parents=True)
        self._repo, self._seed = L.paths.repo, L.SEED
        L.paths.repo = lambda: str(self.repo)
        L.SEED = self.repo / "seed.jsonl"
        self.quotes = self.repo / "his-node" / "quotes.jsonl"
        os.environ["OWNER_QUOTES"] = str(self.quotes)
        self.run = self.repo / "runs" / "video-writing" / "b" / "r1"
        self.run.mkdir(parents=True)

    def tearDown(self):
        L.paths.repo, L.SEED = self._repo, self._seed
        os.environ.pop("OWNER_QUOTES", None)
        self.tmp.cleanup()

    def test_a_candidate_is_not_in_force_until_it_recurs(self):
        r = L.note("b", ["writing"], "Open on the problem", run="r1")
        self.assertFalse(r["promoted"])
        self.assertEqual(L.handed(self.run, "writing", "b"), "")
        r = L.note("b", ["writing"], "Open on the problem", run="r2")
        self.assertTrue(r["promoted"])
        self.assertIn("Open on the problem", L.handed(self.run, "writing", "b"))

    def test_a_stated_rule_is_in_force_at_once_and_his_words_stay_in_his_node(self):
        L.note(None, ["video"], "One front view only", said="his exact words", said_rule=True, run="r1")
        self.assertIn("One front view only", L.handed(self.run, "video", "b"))
        repo_text = "".join(f.read_text() for f in (self.repo / "runs").rglob("*.jsonl"))
        self.assertNotIn("his exact words", repo_text)
        self.assertIn("his exact words", self.quotes.read_text())

    def test_the_run_records_what_it_was_handed(self):
        r = L.note(None, ["writing"], "Time moves forward", said_rule=True)
        L.handed(self.run, "writing", "b")
        rec = json.loads((self.run / "learnings-handed.json").read_text())
        self.assertEqual(rec["writing"]["ids"], [r["id"]])

    def test_stations_and_formats_keep_rules_where_they_belong(self):
        L.note(None, ["video"], "Video only rule", said_rule=True)
        L.note(None, ["writing"], "Drama only rule", said_rule=True, formats=["micro-drama"])
        self.assertNotIn("Video only rule", L.handed(None, "writing", "b"))
        self.assertNotIn("Drama only rule", L.handed(None, "writing", "b", fmt="song-ad"))
        self.assertIn("Drama only rule", L.handed(None, "writing", "b", fmt="micro-drama"))
        self.assertEqual(L.block("b", ("picture",)), "(none yet)")     # an old reader is untouched

    def test_a_draft_that_breaks_a_rule_is_flagged(self):
        L.note(None, ["writing"], "No flashback", "never", said_rule=True, formats=["micro-drama"],
               check={"never": [r"\bflash[- ]?back\b"]})
        self.assertEqual(L.findings("He walks on.", "b", ("writing",), "micro-drama"), [])
        self.assertEqual(len(L.findings("FLASHBACK: the party.", "b", ("writing",), "micro-drama")), 1)
        self.assertEqual(L.findings("FLASHBACK: the party.", "b", ("writing",), "song-ad"), [])

    def test_a_request_check_reads_the_references(self):
        L.note(None, ["video"], "One view", "never", said_rule=True, check={"request_never": [r"seven[-_ ]?view"]})
        req = {"medias": [{"value": "product-seven-view.png"}]}
        self.assertEqual(len(L.findings(json.dumps(req), "b", ("video",), field="request")), 1)
        self.assertEqual(L.findings("seven-view", "b", ("video",)), [])          # words are not references

    def test_the_same_edit_in_two_runs_puts_it_in_force(self):
        made = L.capture("b", "writing", "He grabs a brush.\nShe laughs.", "He grabs the FLEX.\nShe laughs.", run="r1")
        self.assertEqual(len(made), 1)
        self.assertFalse(made[0]["promoted"])
        made = L.capture("b", "writing", "Use a brush now.", "Use the FLEX now.", run="r2")
        self.assertTrue(made[0]["promoted"])

    def test_an_overrule_and_a_take_finding_become_candidates(self):
        calls = [{"id": "c1", "brand": "b", "run": "r1", "gate": "audit", "kind": "audit:claim", "verdict": "overrule",
                  "note": "no", "item": {"element": "claim line"}},
                 {"id": "c2", "brand": "b", "run": "f1", "gate": "take", "item": {"element": "face drifts", "status": "identity"}}]
        made = L.harvest(calls=calls)
        self.assertEqual([m["stations"] for m in made], [["writing"], ["video"]])
        self.assertEqual(len(L.candidates()), 2)
        L.harvest(calls=[dict(calls[1], run="f2")])
        self.assertIn("face drifts", L.handed(None, "video", "b"))

    def test_the_seed_travels_with_the_code_and_is_read_once(self):
        L.SEED.write_text(json.dumps({"id": "LN-seed0001", "stations": ["writing"], "kind": "never", "stage": "writing",
                                      "rule": "Seeded rule", "status": "approved"}) + "\n")
        self.assertIn("Seeded rule", L.handed(None, "writing", "b"))
        L.note(None, ["writing"], "Seeded rule", "never", said_rule=True)
        self.assertEqual([r["rule"] for r in L.in_force(None)].count("Seeded rule"), 1)

    def test_a_one_off_edit_stays_a_candidate_even_when_it_recurs(self):
        for run in ("e1", "e2", "e3"):
            L.add("b", "copy", "do", 'In a offer section, "$69.99" became "$69.99 + Free Towel"', by="x", src=run)
        L.add("b", "picture", "do", "hero_bg picture (a tube on velvet): Remake on emerald", src="e1")
        L.add("b", "picture", "do", "hero_bg picture (a tube on velvet): Remake on emerald", src="e2")
        self.assertEqual(L.in_force("b"), [])
        self.assertTrue(all(c.get("one_off") for c in L.candidates()))
        L.add("b", "copy", "never", "Never promise a free gift the offer bank does not hold")   # a stated rule stays
        self.assertEqual(len(L.in_force("b")), 1)

    def test_a_kept_price_edit_never_goes_in_force_by_recurring(self):
        L.capture("b", "copy", "Only $19.99", "Only $19.99, buy 2 get 1", run="r1")
        made = L.capture("b", "copy", "Just $19.99", "Just $19.99, buy 2 get 1", run="r2")
        self.assertFalse(made[0]["promoted"])

    def test_a_temp_folder_is_not_a_real_run(self):
        self.assertTrue(L.real_run(self.run))
        self.assertFalse(L.real_run(tempfile.gettempdir()))


if __name__ == "__main__":
    unittest.main()
