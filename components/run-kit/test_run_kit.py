#!/usr/bin/env python3
"""python3 test_run_kit.py — stdlib unittest, no network, no model call."""
import sys
import tempfile
import json
import shutil
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_kit import filing, index, model, paths, pool, prompts, stage   # noqa: E402
from run_kit.stage import DRY, Chain                     # noqa: E402

STEPS = [{"key": "stage1", "name": "Read", "tier": "reads", "label": "record"},
         {"key": "stage2", "name": "Write", "tier": "designs", "label": "draft", "depends": ["stage1"]}]


class Kit(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.pr = self.tmp / "prompts"
        self.pr.mkdir()
        (self.pr / "stage1-read-v1-x.md").write_text("Read this: {source}")
        (self.pr / "stage2-write-v2-x.md").write_text("OLD {record}")
        (self.pr / "stage2-write-v10-x.md").write_text("Write from: {record}")
        self.calls = []

    def runner(self, reply="ok"):
        def r(prompt, m):
            self.calls.append((m, prompt))
            return 0, reply, ""
        return r

    def chain(self, **kw):
        return Chain("tool", "brand", "label", self.tmp / "run", self.pr, STEPS,
                     echo=lambda *_: None, **kw)

    def test_v10_beats_v2(self):
        self.assertEqual(prompts.latest(self.pr, "stage2").name, "stage2-write-v10-x.md")

    def test_unfilled_field_is_refused(self):
        with self.assertRaises(prompts.PromptError):
            prompts.fill("needs {this} and {that}", {"this": 1})

    def test_dry_run_spends_nothing(self):
        c = self.chain(dry=True, runner=self.runner())
        self.assertEqual(c.run("stage1", source="s"), DRY)
        self.assertEqual(self.calls, [])
        self.assertTrue((self.tmp / "run" / "stage1--sent.md").is_file())

    def test_dry_run_still_refuses_unfilled(self):
        with self.assertRaises(prompts.PromptError):
            self.chain(dry=True).run("stage1")

    def test_tiers_and_escalation(self):
        self.assertEqual(model.pick("reads", 10)[0], model.TIERS["reads"])
        self.assertEqual(model.pick("reads", model.SMALL_WINDOW_CHARS + 1)[0], model.TIERS["designs"])
        self.assertEqual(model.pick("reads", 10, forced="m")[0], "m")

    def test_rerun_keeps_done_steps_and_invalidates_dependents(self):
        c = self.chain(runner=self.runner("first"))
        rec = c.run("stage1", source="s")
        c.run("stage2", record=rec)
        self.assertEqual(len(self.calls), 2)
        c2 = self.chain(runner=self.runner("second"))
        c2.run("stage1", source="s")
        c2.run("stage2", record=rec)
        self.assertEqual(len(self.calls), 2, "nothing changed — both steps are kept")
        (self.pr / "stage1-read-v2-x.md").write_text("Read this, again: {source}")
        c3 = self.chain(runner=self.runner("third"))
        c3.run("stage1", source="s")
        c3.run("stage2", record="x")
        self.assertEqual(len(self.calls), 4, "stage1's prompt changed, so stage2 (which reads it) reruns too")

    def test_rerun_from(self):
        c = self.chain(runner=self.runner())
        c.run("stage1", source="s"); c.run("stage2", record="r")
        c2 = self.chain(runner=self.runner(), rerun_from="stage2")
        c2.run("stage1", source="s"); c2.run("stage2", record="r")
        self.assertEqual(len(self.calls), 3)

    def test_usage_limit_is_its_own_error(self):
        def r(p, m):
            return 1, "You've hit your monthly spend limit · your weekly usage limit resets", ""
        with self.assertRaises(model.UsageLimit):
            model.call("x", "m", runner=r)

    def test_bad_answer_is_not_retried(self):
        n = []
        def r(p, m):
            n.append(1)
            return 1, "", "invalid request"
        with self.assertRaises(model.StageFailed):
            model.call("x", "m", runner=r, wait=0)
        self.assertEqual(len(n), 1)

    def test_transient_is_retried(self):
        n = []
        def r(p, m):
            n.append(1)
            return (1, "", "503 overloaded") if len(n) < 3 else (0, "fine", "")
        self.assertEqual(model.call("x", "m", runner=r, wait=0), "fine")
        self.assertEqual(len(n), 3)

    def test_paths_find_the_repo(self):
        self.assertTrue((paths.repo() / "brands").is_dir())
        self.assertTrue(paths.component("run-kit").is_dir())

    def test_pool_stops_on_usage_limit_and_survives_a_failure(self):
        def fn(label, payload):
            if payload == "boom":
                raise ValueError("broke")
            return payload
        out = pool.run_all([("a", 1), ("b", "boom")], fn, workers=2)
        self.assertEqual(out["a"], ("done", 1))
        self.assertEqual(out["b"][0], "failed")



class TestChainDelivers(unittest.TestCase):
    """The chain files its own deliverable. On the chain rather than in each
    machine — machine-by-machine is how 110 briefs ended up unfindable."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="runkit-chain-"))
        self.prompts = self.tmp / "prompts"; self.prompts.mkdir()
        (self.prompts / "stage1-read-v1-damon.md").write_text("read {x}")
        (self.prompts / "stage2-brief-v1-damon.md").write_text("brief {x}")
        self.steps = [{"key": "stage1", "name": "Read", "tier": "checks", "label": "read"},
                      {"key": "stage2", "name": "Brief", "tier": "designs", "label": "brief"}]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def chain(self):
        return stage.Chain("t", "acme", "run-1", self.tmp / "out", self.prompts,
                           self.steps, echo=lambda *a: None)

    def test_with_no_argument_it_delivers_the_last_stage_written(self):
        c = self.chain()
        (c.out / "stage1--read.md").write_text("the read")
        (c.out / "stage2--brief.md").write_text("the brief")
        got = c.deliver()
        self.assertEqual([p.name for p in got], ["stage2--brief.md"])
        self.assertEqual((c.out / "deliverable" / "stage2--brief.md").read_text(), "the brief")

    def test_it_takes_a_named_file_and_a_name(self):
        c = self.chain()
        (c.out / "stage2--brief.md").write_text("the brief")
        c.deliver(c.out / "stage2--brief.md", name="06-brief.md")
        self.assertTrue((c.out / "deliverable" / "06-brief.md").is_file())

    def test_a_chain_with_nothing_to_deliver_says_so_in_its_record(self):
        c = self.chain()
        self.assertEqual(c.deliver(), [])
        self.assertIn("nothing to deliver", json.loads(
            (c.out / "run.json").read_text())["deliverable"]["why"])

    def test_the_record_names_what_was_delivered(self):
        c = self.chain()
        (c.out / "stage2--brief.md").write_text("x")
        c.deliver()
        rec = json.loads((c.out / "run.json").read_text())
        self.assertEqual(rec["deliverable"]["files"], ["deliverable/stage2--brief.md"])


class TestIndexAndDeliver(unittest.TestCase):
    """The runs plane read as one thing — and the brief put where the standard
    says. Added 2026-09-23 after an index over every run found 198 runs and
    three briefs actually filed in `deliverable/`; a tool that wanted briefs had
    reached into another machine's folders instead, and deleting that machine
    nearly took six briefs with it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="runkit-index-"))
        r = self.tmp / "runs" / "image-teardown" / "acme" / "run-one"
        (r / "out").mkdir(parents=True)
        (r / "out" / "06-brief.md").write_text("# the brief\n")
        (r / "prompts").mkdir()
        (r / "prompts" / "5-brief.md").write_text("# the PROMPT, not the brief\n")
        (r / "run.json").write_text(json.dumps({"state": "filed"}))
        self.run = r

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_brief_outside_deliverable_is_reported_as_misfiled(self):
        rows = index.scan(self.tmp / "runs")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["briefs"], [])
        self.assertIn("out/06-brief.md", rows[0]["briefs_misfiled"])

    def test_the_prompt_as_sent_is_never_counted_as_a_brief(self):
        rows = index.scan(self.tmp / "runs")
        self.assertNotIn("prompts/5-brief.md", rows[0]["briefs_misfiled"])

    def test_deliver_puts_it_where_the_standard_says_and_keeps_the_original(self):
        filing.deliver(self.run, [self.run / "out" / "06-brief.md"])
        self.assertTrue((self.run / "deliverable" / "06-brief.md").is_file())
        self.assertTrue((self.run / "out" / "06-brief.md").is_file())
        rows = index.scan(self.tmp / "runs")
        self.assertEqual(rows[0]["briefs"], ["deliverable/06-brief.md"])
        self.assertEqual(rows[0]["briefs_misfiled"], [])

    def test_health_counts_the_column_that_matters(self):
        h = index.health(self.tmp / "runs")
        self.assertEqual(h["image-teardown"]["misfiled"], 1)
        filing.deliver(self.run, [self.run / "out" / "06-brief.md"])
        h = index.health(self.tmp / "runs")
        self.assertEqual((h["image-teardown"]["misfiled"], h["image-teardown"]["with_brief"]), (0, 1))

    def test_briefs_answers_by_brand_without_knowing_any_machine(self):
        filing.deliver(self.run, [self.run / "out" / "06-brief.md"])
        got = index.briefs(brand="acme", root=self.tmp / "runs")
        self.assertEqual(len(got), 1)
        self.assertTrue(got[0]["filed"])
        self.assertEqual(index.briefs(brand="nobody", root=self.tmp / "runs"), [])

if __name__ == "__main__":
    unittest.main(verbosity=1)
