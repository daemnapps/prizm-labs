#!/usr/bin/env python3
"""The rollout's promises, checked without a model, a network or a real brand.

    python3 machine/test_rollout.py

A throwaway brand tree is built in a temp folder and both run homes are
pointed at temp folders, so nothing here reads a real brand or touches a
real run. `claude` is stubbed everywhere; any real call fails the test.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.modules.pop("copy", None)        # the stdlib module of the same name, if loaded
import copy as C                     # noqa: E402  this machine's runner
import context                       # noqa: E402
import paths as P                    # noqa: E402
import quality_checks as Q           # noqa: E402  (copy.py put it on the path)

BRAND = "testbrand"
OFFERS = "# Offers\n\n## core — The one offer\n- Price: **$49.00**\n- Subscribed: **$37.00**\n"


def quiet(fn, *a, **kw):
    """Run fn, return (result_or_SystemExit, printed text)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        try:
            got = fn(*a, **kw)
        except SystemExit as e:
            got = e
    return got, out.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="copy-rollout-"))
        tree = self.tmp / "tree"
        b = tree / "brands" / BRAND
        (b / "offers").mkdir(parents=True)
        (b / "products").mkdir()
        (b / "offers" / "offer-bank.md").write_text(OFFERS)
        (b / "products" / "thing.md").write_text("# The thing\nIt does a job.\n")
        self.tree, self.product = tree, str(b / "products" / "thing.md")
        self.source = self.tmp / "source.md"
        self.source.write_text("A piece of copy somebody else wrote. It has a hook and a close.\n")
        self.keep = (P.RUNS, P.RESULTS, C.WORKSPACE, context.WORKSPACE, C.claude,
                     C.subprocess.run, C.time.sleep, C._rebuild_board)
        P.RUNS, P.RESULTS = self.tmp / "runs" / P.TOOL, self.tmp / "results"
        C._rebuild_board = lambda: None
        C.RUN_TIERS.clear(); C.RUN_TIERS.update(C.TIERS)
        C.RERUN_FROM = C.DRY = None
        self.calls = []

    def tearDown(self):
        (P.RUNS, P.RESULTS, C.WORKSPACE, context.WORKSPACE, C.claude,
         C.subprocess.run, C.time.sleep, C._rebuild_board) = self.keep
        C.RERUN_FROM = C.DRY = None

    def forbid_calls(self):
        def no(*a, **kw):
            self.calls.append(a)
            raise AssertionError("a model call was attempted")
        C.claude = no
        C.subprocess.run = no

    def argv(self, *extra):
        return [str(self.source), "--brand", BRAND, "--product", self.product,
                "--brand-root", str(self.tree), "--label", "t-run", *extra]

    def files_written(self):
        return [p for p in self.tmp.rglob("*") if p.is_file()
                and self.tree not in p.parents and p != self.source]


class DryRun(Base):
    def test_dry_run_makes_no_call_and_writes_nothing(self):
        self.forbid_calls()
        code, text = quiet(C.main, self.argv("--dry-run"))
        self.assertEqual(code, 0, text)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.files_written(), [])
        self.assertIn("model calls made: 0", text)
        for stage in ("Triage", "Context scout", "Expansion", "Render", "Brief"):
            self.assertIn(stage, text)
        self.assertNotIn("UNFILLED ", text)          # every prompt field is handed over

    def test_dry_run_fails_on_a_missing_required_input(self):
        self.forbid_calls()
        args = self.argv("--dry-run")
        args[args.index("--product") + 1] = str(self.tmp / "no-such-product.md")
        code, _ = quiet(C.main, args)
        self.assertIsInstance(code, SystemExit)
        self.assertNotEqual(code.code, 0)
        self.assertEqual(self.calls, [])

    def test_a_prompt_field_nobody_hands_over_is_reported(self):
        C.DRY = []
        C.dry_stage("stage0", None, {"today": "x", "source": "y"})      # formats + avatars withheld
        missing = {n for n, status, _, _ in C.DRY[0]["fields"] if status == "UNFILLED"}
        self.assertEqual(missing, {"formats", "avatars"})


class Formats(Base):
    def test_an_unknown_write_as_is_refused_with_the_real_ids(self):
        self.forbid_calls()
        got, _ = quiet(C.main, self.argv("--write-as", "caption, billboard"))
        self.assertIsInstance(got, SystemExit)
        self.assertIn("billboard", str(got.code))
        self.assertIn("short-form", str(got.code))                      # the real list is named
        self.assertEqual(self.calls, [])
        self.assertEqual(self.files_written(), [])                      # refused before a run folder exists

    def test_known_formats_pass(self):
        ids, own, problems = C.check_formats("caption, short-form")
        self.assertEqual((ids, own, problems), (["caption", "short-form"], [], []))


class Tiers(Base):
    def models(self, *extra):
        self.forbid_calls()
        code, text = quiet(C.main, self.argv("--dry-run", *extra))
        self.assertEqual(code, 0, text)
        return {r["stage"]: r["model"] for r in C.DRY}

    def test_each_stage_gets_its_tiers_model(self):
        m = self.models()
        self.assertEqual(m["stage0"], C.TIERS["reads"])
        self.assertEqual(m["stage1"], C.TIERS["checks"])
        self.assertEqual(m["stage4"], C.TIERS["checks"])
        self.assertEqual(m["stage9"], C.TIERS["reads"])
        for k in ("stage2", "stage3", "stage5", "stage6", "stage7", "stage8"):
            self.assertEqual(m[k], C.TIERS["designs"], k)

    def test_model_forces_one_model_for_everything(self):
        self.assertEqual(set(self.models("--model", "one-model").values()), {"one-model"})

    def test_tier_flag_repoints_one_tier(self):
        m = self.models("--tier", "reads=other-reader")
        self.assertEqual((m["stage0"], m["stage1"]), ("other-reader", C.TIERS["checks"]))

    def test_a_prompt_past_a_small_window_escalates_and_is_recorded(self):
        seen = []
        C.claude = lambda prompt, model, label=None: seen.append(model) or "LANE: ORGANIC"
        state = {"stages": {}}
        out = self.tmp / "run"; out.mkdir()
        big = "x" * (C.SMALL_WINDOW_CHARS + 1)
        quiet(C.run_stage, "stage0", out, None, state, today="t", source=big, formats="f", avatars="a")
        self.assertEqual(seen, [C.TIERS["designs"]])
        rec = state["stages"]["stage0"]
        self.assertEqual((rec["model"], rec["tier"]), (C.TIERS["designs"], "reads"))
        self.assertTrue(rec["model_why"].startswith("escalated"))


class UsageLimit(Base):
    def fake(self, stdout, code=1):
        class R:
            returncode, stderr = code, ""
        R.stdout = stdout

        def run(*a, **kw):
            self.calls.append(a)
            return R
        C.subprocess.run = run
        C.time.sleep = lambda s: None

    def test_a_usage_limit_raises_once_and_is_not_retried(self):
        self.fake("You have hit your usage limit. It resets at 9pm.")
        with self.assertRaises(C.UsageLimit):
            quiet(C.claude, "prompt", "some-model", "stage3")
        self.assertEqual(len(self.calls), 1)

    def test_an_ordinary_failure_is_still_retried_three_times(self):
        self.fake("")
        got, _ = quiet(C.claude, "prompt", "some-model", "stage3")
        self.assertIsInstance(got, SystemExit)
        self.assertEqual(len(self.calls), 3)

    def test_the_run_stops_with_one_clear_line(self):
        def refuse(*a, **kw):
            raise C.UsageLimit("stage stage0 on m was refused: usage limit reached")
        C.claude = refuse
        got, _ = quiet(C.cli, self.argv("--no-gate"))
        self.assertIsInstance(got, SystemExit)
        self.assertTrue(str(got.code).startswith("USAGE LIMIT"))


def make_run(d, stages=("stage0", "stage1", "stage2", "stage1b", "stage3", "stage4",
                        "stage5", "stage7", "stage8")):
    d.mkdir(parents=True)
    rec = {}
    for k in stages:
        name = f"{k}--{C.SPEC[k]['label']}.md"
        (d / name).write_text("LANE: ALREADY AN AD\nFORMAT: caption\n" if k == "stage0" else f"saved {k}\n")
        rec[k] = {"status": "done", "out": name, "model": "earlier-model"}
    (d / "run.json").write_text(json.dumps({"slug": d.name, "label": d.name, "brand": BRAND, "stages": rec}))


class BothHomes(Base):
    def test_runs_are_found_in_both_homes(self):
        make_run(P.RUNS / BRAND / "new-run")
        make_run(P.RESULTS / "old-run")
        make_run(P.RESULTS / "archive-v1-chain" / "parked")
        self.assertEqual([d.name for d in P.all_runs()], ["new-run", "old-run"])
        self.assertEqual(P.find_run("new-run"), P.RUNS / BRAND / "new-run")
        self.assertEqual(P.find_run("old-run"), P.RESULTS / "old-run")
        self.assertIsNone(P.find_run("never-ran"))
        import board
        slugs = {r["slug"]: r["archived"] for r in board.collect()}
        self.assertEqual(slugs, {"new-run": False, "old-run": False, "parked": True})
        import research
        self.assertEqual(research._run_dir({"slug": "old-run", "brand": BRAND}), P.RESULTS / "old-run")
        self.assertEqual(research._run_dir({"slug": "fresh", "brand": BRAND}), P.RUNS / BRAND / "fresh")

    def test_rerun_from_carries_an_old_run_over_once_and_buys_only_what_is_left(self):
        make_run(P.RESULTS / "t-run")
        C.claude = lambda prompt, model, label=None: self.calls.append(label) or "the brief"
        code, text = quiet(C.main, self.argv("--rerun-from", "stage9", "--no-gate"))
        self.assertEqual(code, 0, text)
        self.assertEqual(self.calls, ["stage9"])                        # nothing earlier was bought again
        new = P.RUNS / BRAND / "t-run"
        st = json.loads((new / "run.json").read_text())
        self.assertTrue(st["stages"]["stage3"]["reused"])
        self.assertEqual(st["stages"]["stage3"]["model"], "earlier-model")
        self.assertEqual(st["stages"]["stage9"]["model"], C.TIERS["reads"])
        self.assertEqual(st["elements"]["format/copy"], ["short-form", "caption", "long-form", "social-proof"])
        self.assertTrue((P.RESULTS / "t-run" / "stage8--render.md").is_file())   # history is left alone


class Gate(Base):
    def test_a_price_the_offer_bank_does_not_sell_holds_the_copy(self):
        out = self.tmp / "run"; out.mkdir()
        with self.assertRaises(Q.Held) as held:
            C.copy_gate("Get it for $99 today.\n\n## CHECKS\nnothing here", OFFERS, out)
        self.assertIn("$99.00", str(held.exception))
        self.assertEqual(json.loads((out / "check.json").read_text())["copy"]["result"], "HELD")

    def test_a_listed_price_passes_however_it_is_written(self):
        out = self.tmp / "run"; out.mkdir()
        self.assertTrue(C.copy_gate("Just $49, or $37.00 subscribed.\n\n## CHECKS\n$5 is only a note", OFFERS, out))
        self.assertEqual(json.loads((out / "check.json").read_text())["copy"]["result"], "pass")

    def test_an_unfilled_note_in_the_copy_holds_it(self):
        with self.assertRaises(Q.Held):
            C.copy_gate("Hook. [UNFILLED: no proof row]\n", OFFERS)

    def test_a_held_run_saves_everything_and_does_not_write_the_brief(self):
        def fake(prompt, model, label=None):
            self.calls.append(label)
            return {"stage0": "LANE: ALREADY AN AD\nFORMAT: caption",
                    "stage8": "# FORMAT: `caption`\nOnly $12 this week.\n\n## CHECKS\nok"}.get(label, f"out {label}")
        C.claude = fake
        import research
        keep, research.text_for = research.text_for, lambda **kw: "no research in a test"
        try:
            got, text = quiet(C.main, self.argv())
        finally:
            research.text_for = keep
        self.assertIsInstance(got, SystemExit)
        self.assertEqual(got.code, 2)
        self.assertNotIn("stage9", self.calls)
        run = P.RUNS / BRAND / "t-run"
        self.assertTrue((run / "stage8--render.md").is_file())
        st = json.loads((run / "run.json").read_text())
        self.assertEqual(st["gate"]["copy"], "HELD")
        self.assertIn("$12.00", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
