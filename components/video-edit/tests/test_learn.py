"""The edit's declared learn step, run by the machine (the logic layer, 2026-11-18). No model: the reply is a fake
through run-kit's runner seam. Everything is written under the test's own runs root; the component's hand-kept rules
file is never written."""
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

MACHINE = Path(__file__).resolve().parents[1] / "machine"
TOOL = MACHINE.parent
sys.path.insert(0, str(MACHINE))
import learn as L  # noqa: E402


def at(minutes):
    """A change's time, this many minutes from now: the step marks how far it learned by the clock, so fixed dates
    would fall behind it."""
    import datetime as dt
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=minutes)).isoformat(timespec="seconds")


def reply(rows, promote=(), observations=()):
    return json.dumps({"rows": rows, "promote": list(promote), "observations": list(observations)})


def row(rid, stage="edit", rule="B-roll comes in a beat before the word it shows.", words="", scope="this format"):
    return {"id": rid, "what_changed": "B-roll at 12.1s moved to 11.6s", "his_words": words, "rule": rule, "stage": stage,
            "scope": scope, "seen": 1, "conflicts_with": ""}


class Learn(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ve_learn_")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = self.tmp / "runs" / "video-edit"
        self.run = self.root / "b" / "b_p_brief-0001"
        self.run.mkdir(parents=True)
        (self.run / "run.json").write_text(json.dumps({"brand": "b", "brief": "brief-0001"}))
        (self.run / "cutsheet-v1.json").write_text(json.dumps({"meta": {"format": "single-presenter"}}))
        self.sent = []
        self.kept_before = hashlib.sha256((TOOL / "learned.json").read_bytes()).hexdigest()

    def tearDown(self):
        self.assertEqual(hashlib.sha256((TOOL / "learned.json").read_bytes()).hexdigest(), self.kept_before,
                         "the rules kept by hand are never written by the machine")

    def change(self, at, asked="B-roll a beat earlier", why="", stop="timeline"):
        with (self.run / "changes.jsonl").open("a") as f:
            f.write(json.dumps({"at": at, "stop": stop, "asked": asked, "why": why, "from": "cutsheet-v1.json",
                                "to": "cutsheet-v2.json"}) + "\n")

    def runner(self, answer):
        def run(prompt, model):
            self.sent.append((prompt, model))
            return 0, answer, ""
        return run

    def bank(self):
        return L._jl(self.root / "_lessons" / "lessons.jsonl")

    def handover(self):
        return json.loads((self.root / "_lessons" / "learned.json").read_text())

    def test_no_change_means_no_model_call_and_nothing_written(self):
        got = L.safe(self.run, runner=self.runner("never asked"))
        self.assertEqual((got["state"], got["lessons"]), ("done", 0))
        self.assertEqual(self.sent, [])
        self.assertFalse((self.root / "_lessons").exists())

    def test_a_change_becomes_a_lesson_banked_with_its_stage(self):
        self.change(at(60), why="it lands before he says the word")
        got = L.safe(self.run, runner=self.runner(reply([row("broll-leads-its-word")], observations=["broll-leads-its-word"])))
        self.assertEqual((got["state"], got["lessons"]), ("done", 1))
        self.assertEqual(len(self.sent), 1)
        b = self.bank()[0]
        self.assertEqual((b["id"], b["stage"], b["standing"], b["seen"]), ("broll-leads-its-word", "edit", "observation", 1))
        self.assertEqual((b["brief"], b["brand"], b["format"]), ("brief-0001", "b", "single-presenter"))
        self.assertNotIn("his_words", b, "what is banked is direction only; the typed words stay in the change log")
        doc = self.handover()
        self.assertEqual([o["id"] for o in doc["stages"]["edit"]["observations"]], ["broll-leads-its-word"])
        self.assertEqual(doc["stages"]["edit"]["rules"], [])
        self.assertIn("Written by machine", doc["_what"])

    def test_the_prompt_carries_the_changes_the_ad_and_what_is_on_file(self):
        self.change(at(60), asked="lose the pause after the hook")
        L.safe(self.run, runner=self.runner(reply([row("x")])))
        prompt, model = self.sent[0]
        self.assertIn("lose the pause after the hook", prompt)
        self.assertIn('"brief": "brief-0001"', prompt)
        self.assertIn("headline-on-frame-one", prompt, "the rules kept by hand are on file for the count")
        for slot in ("{changes}", "{feedback}", "{learned}", "{ad}"):
            self.assertNotIn(slot, prompt)
        self.assertIn("sonnet", model)

    def test_seen_twice_is_a_rule_the_cut_reads(self):
        self.change(at(60))
        L.safe(self.run, runner=self.runner(reply([row("broll-leads-its-word")])))
        self.assertNotIn("broll-leads-its-word", [r["id"] for r in L.for_cut(self.root)])
        self.change(at(120))
        got = L.safe(self.run, runner=self.runner(reply([row("broll-leads-its-word")])))
        self.assertEqual(got["to_cut"], ["broll-leads-its-word"])
        rule = next(r for r in L.for_cut(self.root) if r["id"] == "broll-leads-its-word")
        self.assertEqual(rule["from"], "the edit's learn step")
        self.assertEqual(self.handover()["stages"]["edit"]["rules"][0]["seen"], 2)

    def test_a_rule_stated_as_one_binds_at_once(self):
        self.change(at(60), why="never cover the product with a caption")
        got = L.safe(self.run, runner=self.runner(reply(
            [row("captions-off-the-product", "captions", "A caption never covers the product.", "never cover the product with a caption",
                 "every edit")], promote=["captions-off-the-product"])))
        self.assertEqual(got["rules"], ["captions-off-the-product"])
        self.assertTrue(self.bank()[0]["stated"])
        self.assertEqual(self.handover()["stages"]["captions"]["rules"][0]["scope"], "every edit")

    def test_a_lesson_for_a_stage_upstream_is_handed_over_and_never_binds_the_cut(self):
        self.change(at(60), why="always name the product in the first line")
        got = L.safe(self.run, runner=self.runner(reply(
            [row("name-the-product-early", "brief", "The first line names the product.", "always name the product in the first line")],
            promote=["name-the-product-early"])))
        self.assertEqual(got["upstream"], ["brief"])
        self.assertEqual(got["to_cut"], [])
        self.assertNotIn("name-the-product-early", [r["id"] for r in L.for_cut(self.root)])
        self.assertIn("The first line names the product.", L.block("brief", self.root))
        self.assertEqual(L.block("teardown", self.root), "NONE")

    def test_the_cut_reads_the_hand_kept_rules_first_then_the_machines(self):
        hand = [r["id"] for r in json.loads((TOOL / "learned.json").read_text())["rules"]]
        self.assertEqual([r["id"] for r in L.for_cut(self.root)], hand)
        self.change(at(60), why="always")
        L.safe(self.run, runner=self.runner(reply([row("a-new-rule", words="always do this")], promote=["a-new-rule"])))
        self.assertEqual([r["id"] for r in L.for_cut(self.root)], hand + ["a-new-rule"])

    def test_nothing_is_learned_twice(self):
        self.change(at(60))
        L.safe(self.run, runner=self.runner(reply([row("x")])))
        got = L.safe(self.run, runner=self.runner(reply([row("x")])))
        self.assertEqual(got["lessons"], 0)
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(len(self.bank()), 1)

    def test_times_written_two_ways_are_still_read_in_order(self):
        """One tool writes UTC, another a local offset: the moment decides, never the text."""
        self.assertTrue(L.after("2026-11-18T17:30:00+07:00", "2026-11-18T10:00:00+00:00"))    # 10:30 UTC, after
        self.assertFalse(L.after("2026-11-18T16:30:00+07:00", "2026-11-18T10:00:00+00:00"))   # 09:30 UTC, before
        self.assertTrue(L.after("2026-11-18T10:00:01Z", "2026-11-18T10:00:00+00:00"))
        self.assertTrue(L.after("anything at all", ""))

    def test_a_reply_that_will_not_parse_is_said_and_the_changes_stay_unlearned(self):
        self.change(at(60))
        got = L.safe(self.run, runner=self.runner("I could not do that."))
        self.assertEqual(got["state"], "not run")
        self.assertIn("could not run", got["note"])
        self.assertFalse((self.run / ".learned-upto").exists())
        got = L.safe(self.run, runner=self.runner(reply([row("x")])))
        self.assertEqual(got["lessons"], 1, "read again next time")

    def test_a_dry_run_says_what_it_would_read(self):
        self.change(at(60))
        got = L.safe(self.run, runner=self.runner("never asked"), dry_run=True)
        self.assertEqual((got["state"], got["changes"]), ("dry run", 1))
        self.assertEqual(self.sent, [])

    def test_the_hand_over_is_rebuilt_whole_from_the_bank(self):
        self.change(at(60))
        L.safe(self.run, runner=self.runner(reply([row("x"), row("y", "production-clip", "Hands stay in frame.")])))
        (self.root / "_lessons" / "learned.json").unlink()
        doc = L.rebuild(self.root)
        self.assertEqual(doc["lessons"], 2)
        self.assertEqual([o["id"] for o in doc["stages"]["production-clip"]["observations"]], ["y"])
        self.assertEqual(set(doc["stages"]), set(L.STAGES))

    def test_the_declared_step_names_its_runner(self):
        steps = {s["id"]: s for s in json.loads((MACHINE / "steps.json").read_text())["steps"]}
        self.assertIn("machine/learn.py", steps["learn"]["runs"])
        self.assertEqual(L.prompt_file().parent.name, "stage-9-learn")


if __name__ == "__main__":
    unittest.main()
