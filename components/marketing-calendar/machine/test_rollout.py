#!/usr/bin/env python3
"""What the rollout added, proven without a model, a network or a real run.

    python3 machine/test_rollout.py

    1  the dry run makes ZERO model calls and writes NOTHING
    2  a blocked brand makes the dry run exit non-zero
    3  a type that is in neither the element library nor the brand's own
       catalogue is a BREAK that names the real ids; a brand's own type passes
    4  a failing gate is RECORDED in check.json and never raised
    5  the miner's stop words come from the brand being mined, not from this code
    6  the repo-root filing copies text only, a scratch run never reaches it,
       and a month already at its home is never filed again
    7  both thinking layers take the `designs` tier; --model still forces one;
       an out-of-usage refusal stops with one line and is not retried

No brand is named here: the dry run is rehearsed on whichever brand folder in
this checkout can run the chain, found at run time.
"""
import calendar as _stdlib_calendar      # noqa: F401 — cached BEFORE machine/ joins the path,
import importlib.util                    # because this folder has a calendar.py of its own
import io
import json
import os
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path

MACHINE = Path(__file__).resolve().parent
CHECKOUT = next((d for d in MACHINE.parents if (d / ".git").exists()), None)
if CHECKOUT and not os.environ.get("AI_WORKSPACE"):
    os.environ["AI_WORKSPACE"] = str(CHECKOUT)     # a worktree must read ITSELF
sys.path.insert(0, str(MACHINE))

import chain as CH                       # noqa: E402
import gates as G                        # noqa: E402
import moments_mine as M                 # noqa: E402
import paths as P                        # noqa: E402
import runner as R                       # noqa: E402
import dryrun as DRY                     # noqa: E402

_spec = importlib.util.spec_from_file_location("mc_calendar", MACHINE / "calendar.py")
CAL = importlib.util.module_from_spec(_spec)
sys.modules["mc_calendar"] = CAL          # under its own name — never over the stdlib's
_spec.loader.exec_module(CAL)


def runnable_brand():
    root = P.WORKSPACE / "brands"
    for d in sorted(root.iterdir()) if root.is_dir() else []:
        if d.is_dir() and not any(L["verdict"] == "blocked" for L in CH.readiness(d)) \
                and (d / "calendar" / "moments.json").is_file():
            return d.name
    return None


def snapshot(folder):
    folder = Path(folder)
    return sorted((str(p), p.stat().st_mtime_ns) for p in folder.rglob("*")) if folder.exists() else None


class Spy:
    """Stands where the model call is. Counts, and would fail loudly."""
    def __init__(self):
        self.calls = 0

    def __call__(self, *a, **k):
        self.calls += 1
        raise AssertionError("a model call was attempted")


class DryRun(unittest.TestCase):
    def setUp(self):
        self.spy, self.sub = Spy(), Spy()
        self._claude, self._run = R.claude, R.subprocess.run
        R.claude, R.subprocess.run = self.spy, self.sub

    def tearDown(self):
        R.claude, R.subprocess.run = self._claude, self._run

    def test_zero_calls_and_nothing_written(self):
        brand = runnable_brand()
        if not brand:
            self.skipTest("no brand in this checkout can run the chain")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "runs"
            real_before = snapshot(P.RUNS)
            filed_before = snapshot(G.repo_home(brand, "2026-11"))
            argv, sys.argv = sys.argv, ["calendar.py", "2026-11", "--brand", brand,
                                        "--dry-run", "--out", str(out)]
            buf = io.StringIO()
            try:
                with redirect_stdout(buf), self.assertRaises(SystemExit) as stop:
                    CAL.main()
            finally:
                sys.argv = argv
            said = buf.getvalue()
            self.assertEqual(stop.exception.code, 0, said)
            self.assertEqual(self.spy.calls, 0)
            self.assertEqual(self.sub.calls, 0)
            self.assertFalse(out.exists(), "the dry run made the month's folder")
            self.assertEqual(list(Path(tmp).iterdir()), [])
            self.assertEqual(snapshot(P.RUNS), real_before)
            self.assertEqual(snapshot(G.repo_home(brand, "2026-11")), filed_before)
            # both prompts resolved, every field reported, none left open
            for key in ("cells", "concepts"):
                self.assertIn(R.latest_prompt(CH.BY_KEY[key]["prompt"]).name, said)
            self.assertIn("{skeleton}  OK", said)
            self.assertIn("{techniques}  OK", said)
            self.assertNotIn("MISSING", said)
            self.assertIn("0 model calls", said)

    def test_the_short_flag_is_the_same_flag(self):
        brand = runnable_brand()
        if not brand:
            self.skipTest("no brand in this checkout can run the chain")
        args = types.SimpleNamespace(month="2026-11", brand=brand, model=None)
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            self.assertEqual(DRY.run(args, CAL, Path(tmp) / "runs"), 0)
        self.assertEqual(self.spy.calls + self.sub.calls, 0)

    def test_a_blocked_brand_exits_non_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "brands" / "empty-brand").mkdir(parents=True)
            keep, DRY.WORKSPACE = DRY.WORKSPACE, Path(tmp)
            buf = io.StringIO()
            try:
                args = types.SimpleNamespace(month="2026-11", brand="empty-brand", model=None)
                with redirect_stdout(buf):
                    code = DRY.run(args, CAL, Path(tmp) / "runs")
            finally:
                DRY.WORKSPACE = keep
            self.assertEqual(code, 2)
            self.assertIn("BLOCKED", buf.getvalue())
            self.assertFalse((Path(tmp) / "runs").exists())
        self.assertEqual(self.spy.calls + self.sub.calls, 0)

    def test_an_unfilled_field_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            keep, R.PROMPTS = R.PROMPTS, Path(tmp)
            # numeric, not alphabetical: v10 beats v9
            (Path(tmp) / "cal3-cells-v9-damon.md").write_text("old {month}")
            (Path(tmp) / "cal3-cells-v10-damon.md").write_text("{month} {state} {nobody_fills_this}")
            try:
                lines, problems = DRY.prompt_report("cells", {"month": "2026-11", "state": ""})
            finally:
                R.PROMPTS = keep
        text = "\n".join(lines)
        self.assertIn("cal3-cells-v10-damon.md", text)
        self.assertIn("{nobody_fills_this}  MISSING", text)
        self.assertIn("{state}  EMPTY", text)
        self.assertEqual(len(problems), 1)


class Elements(unittest.TestCase):
    def brand(self, tmp, keys=("house-special",)):
        root = Path(tmp) / "brands" / "test-brand"
        (root / "email-sms").mkdir(parents=True)
        (root / "email-sms" / "email-types.json").write_text(json.dumps(
            {"types": [{"key": k, "well": "ask", "role": "asks"} for k in keys]}))
        return root

    def test_unknown_in_both_is_a_break_naming_real_ids(self):
        lib = G.library_ids()
        self.assertTrue(lib, "the element library has no email formats to check against")
        real = sorted(lib)[0]
        with tempfile.TemporaryDirectory() as tmp:
            root = self.brand(tmp)
            breaks, warns, picked = G.type_problems(
                [real, real, "house-special", "coined-on-the-spot"], root,
                dropped=["another-invention", sorted(lib)[1]])
        self.assertEqual(len(breaks), 2)
        joined = "\n".join(breaks)
        self.assertIn("`coined-on-the-spot`", joined)
        self.assertIn("`another-invention`", joined)
        self.assertIn(real, joined)                      # the real ids are named
        self.assertIn("house-special", joined)           # …the brand's own among them
        self.assertEqual(picked[real], {"from": "library", "sends": 2})
        self.assertEqual(picked["house-special"]["from"], "brand")
        self.assertEqual(picked["coined-on-the-spot"]["from"], "unknown")
        # a real format the brand does not carry was dropped: a warning, not a break
        self.assertTrue(any(sorted(lib)[1] in w for w in warns))

    def test_a_clean_month_has_no_breaks(self):
        lib = sorted(G.library_ids())
        with tempfile.TemporaryDirectory() as tmp:
            breaks, _, _ = G.type_problems(lib[:3] + ["house-special"], self.brand(tmp))
        self.assertEqual(breaks, [])

    def test_a_held_gate_is_recorded_and_never_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(G.record("elements", ["`x` is not an email format"], tmp), "HELD")
            self.assertEqual(G.record("inputs", [], tmp, notes=["layer 4 runs with less"]), "pass")
            got = json.loads((Path(tmp) / "check.json").read_text())
        self.assertEqual(got["elements"], {"result": "HELD",
                                           "problems": ["`x` is not an email format"]})
        self.assertEqual(got["inputs"]["result"], "pass")
        self.assertEqual(got["inputs"]["notes"], ["layer 4 runs with less"])

    def test_the_inputs_gate_reads_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "brand"
            empty.mkdir()
            self.assertEqual(G.inputs_gate(CH.readiness(empty), Path(tmp) / "month"), "HELD")
            got = json.loads((Path(tmp) / "month" / "check.json").read_text())
        self.assertTrue(got["inputs"]["problems"])


class StopWords(unittest.TestCase):
    def test_they_come_from_the_brand(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "zephyrine-labs"
            (root / "products").mkdir(parents=True)
            (root / "products" / "store.json").write_text(json.dumps({
                "brand": "Zephyrine", "site": "https://www.zephyrine.example/",
                "products": [{"handle": "the-quillon-set", "title": "Quillon™ Balm"}]}))
            got = M.brand_stop_words("zephyrine-labs", root)
            for w in ("zephyrine", "labs", "quillon", "balm"):
                self.assertIn(w, got)
            M.use_brand("zephyrine-labs", root)
            try:
                seen = M.words("Zephyrine Quillon spring restock", "harvest")
            finally:
                M._BRAND_STOP.clear()
        self.assertEqual(seen, {"spring", "restock", "harvest"})
        # …and once the brand is put down, its words are words again
        self.assertIn("quillon", M.words("quillon"))

    def test_a_brand_with_no_store_file_gives_its_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(M.brand_stop_words("plain-brand", Path(tmp)), {"plain", "brand", "plain-brand"})

    def test_no_brand_folder_name_is_typed_into_the_code(self):
        root = P.WORKSPACE / "brands"
        for d in (root.iterdir() if root.is_dir() else []):
            if d.is_dir():
                self.assertNotIn(d.name.lower(), M.STOP, f"{d.name} is hard-coded in the stop words")


class Filing(unittest.TestCase):
    def month(self, tmp):
        run = Path(tmp) / "scratch" / "test-brand" / "2026-11"
        (run / "3-cells").mkdir(parents=True)
        (run / "5-concepts").mkdir()
        (run / "run.json").write_text(json.dumps({"brand": "Test Brand", "month": "2026-11"}))
        (run / "slots.json").write_text("[]\n")
        (run / "checks.md").write_text("# The month, checked\n")
        (run / "check.json").write_text("{}\n")
        (run / "review.json").write_text("{}\n")                 # the human's layer: stays put
        (run / "board.html").write_text("<html></html>")
        (run / "3-cells" / "prompt-sent.md").write_text("the prompt, as sent")
        (run / "3-cells" / "cells.json").write_text("{}")
        (run / "5-concepts" / "reasoning.md").write_text("the answer")
        (run / "5-concepts" / "picture.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
        (run / "5-concepts" / "not-text.md").write_bytes(b"\xff\xfe\x00\x9f\x92")
        (run / "5-concepts" / "huge.md").write_text("x" * (G.MAX_BYTES + 1))
        return run

    def test_text_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, repo = self.month(tmp), Path(tmp) / "repo"
            dest, copied, left_out = G.file_month(run, repo)
            self.assertEqual(dest, repo / "runs" / "marketing-calendar" / "test-brand" / "2026-11")
            have = sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file())
            self.assertEqual(have, ["3-cells/cells.json", "3-cells/prompt-sent.md",
                                    "5-concepts/reasoning.md", "check.json", "checks.md",
                                    "run.json", "slots.json"])
            self.assertEqual(len(left_out), 2)
            self.assertTrue((run / "slots.json").is_file(), "the month was moved, not copied")
            # filing twice is quiet and changes nothing
            again = G.file_month(run, repo)
            self.assertEqual(again[1], copied)

    def test_a_scratch_month_never_reaches_the_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.month(tmp)
            before = snapshot(G.repo_home("test-brand", "2026-11"))
            self.assertIsNone(G.file_after_run(run))
            self.assertEqual(snapshot(G.repo_home("test-brand", "2026-11")), before)

    def test_a_month_already_home_is_not_filed_again(self):
        # one home, no second copy (SI-22 (calendar months home)): a month that
        # calendar.py wrote at runs/marketing-calendar/<brand>/<month>/ IS home
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            src = self.month(tmp)
            dest, _, _ = G.file_month(src, repo)
            before = snapshot(repo)
            self.assertIsNone(G.file_after_run(dest, repo))
            self.assertEqual(snapshot(repo), before)

    def test_no_brand_no_shelf(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.month(tmp)
            (run / "run.json").write_text("{}")
            with self.assertRaises(ValueError):
                G.file_month(run, Path(tmp) / "repo")


class Tiers(unittest.TestCase):
    def test_both_thinking_layers_design(self):
        self.assertEqual(sorted(R.LAYER_TIERS), sorted(CH.AI_KEYS))
        for key in CH.AI_KEYS:
            model, why = R.pick_model(key, 1000)
            self.assertEqual((model, why), (R.DEFAULT_MODEL, "designs"))

    def test_a_forced_model_wins(self):
        self.assertEqual(R.pick_model("cells", 1000, "some-other-model"),
                         ("some-other-model", "forced"))

    def test_out_of_usage_stops_once(self):
        calls = []

        def refused(*a, **k):
            calls.append(1)
            return types.SimpleNamespace(returncode=1, stdout="", stderr="Claude usage limit reached")
        keep, R.subprocess.run = R.subprocess.run, refused
        try:
            with self.assertRaises(SystemExit) as stop:
                R.claude("a prompt", "a-model")
        finally:
            R.subprocess.run = keep
        self.assertEqual(len(calls), 1)
        self.assertIn("out of usage", str(stop.exception.code))

    def test_a_long_answer_that_says_limit_is_an_answer(self):
        body = "the usage limit of this offer is one per person. " * 40
        keep = R.subprocess.run
        R.subprocess.run = lambda *a, **k: types.SimpleNamespace(returncode=0, stdout=body, stderr="")
        try:
            self.assertEqual(R.claude("a prompt", "a-model"), body.strip())
        finally:
            R.subprocess.run = keep


class LinkedCoolDown(unittest.TestCase):
    """FOLD Y5 (2026-09-23): a peer LINKED as an ask's cool-down carries the
    ask's offer, the same as a generated one. Proof in the run it came from:
    oct-03 bundle with glow-duo-bundle, then oct-05 guarantee with none."""

    CAT = {"types": [
        {"key": "bundle", "role": "asks", "well": "ask",
         "arc": {"warm_up": [], "cool_down": ["guarantee"]}},
        {"key": "guarantee", "role": "closes", "well": "ask"},
    ]}

    def move(self, type_, date, offer):
        return {"cell": {"segment": "Core | Buyers"}, "type": type_,
                "preferred_date": date, "offer": offer, "occasion": "october"}

    def test_a_linked_cool_down_takes_the_asks_offer(self):
        ask = self.move("bundle", "2026-10-03", "glow-duo-bundle")
        close = self.move("guarantee", "2026-10-05", "none")
        out, added = CAL.expand_arcs([ask, close], self.CAT)
        self.assertEqual(added, 0)                       # linked, not generated
        self.assertEqual(close["arc_for"], ask["_arc"])
        self.assertEqual(close["offer"], "glow-duo-bundle")

    def test_a_linked_cool_down_keeps_its_own_offer(self):
        ask = self.move("bundle", "2026-10-03", "glow-duo-bundle")
        close = self.move("guarantee", "2026-10-05", "free-shipping")
        CAL.expand_arcs([ask, close], self.CAT)
        self.assertEqual(close["offer"], "free-shipping")


class WholeArcs(unittest.TestCase):
    """2026-09-23: layer 9 used to drop an arc's warm-up and push its close
    past the moment when a window was full. broken_arcs() names every arc
    that did not come out whole — fit_month() cuts until it names none."""

    CAT = {"types": [
        {"key": "bundle", "role": "asks", "arc": {"warm_up": ["stack"], "cool_down": ["guarantee"]}},
        {"key": "stack", "role": "earns"},
        {"key": "guarantee", "role": "recovers"},
    ]}
    WIN = {"reset": [("2026-09-14", "2026-10-15")]}

    def arc(self, warm, ask, close, warm_dropped=False):
        w = {"arc_for": "C1", "type": "stack", "role": "earns", "occasion": "reset", "_date": warm}
        if warm_dropped:
            w = dict(w, _date=None, _dropped_arc=True)
        return [w,
                {"_arc": "C1", "type": "bundle", "role": "asks", "occasion": "reset", "_date": ask},
                {"arc_for": "C1", "type": "guarantee", "role": "recovers", "occasion": "reset",
                 "_date": close}]

    def test_a_whole_arc_is_not_broken(self):
        self.assertEqual(CAL.broken_arcs(self.arc("2026-10-08", "2026-10-11", "2026-10-13"),
                                         self.CAT, "2026-10", self.WIN), [])

    def test_a_dropped_warm_up_breaks_it(self):
        self.assertEqual(CAL.broken_arcs(self.arc(None, "2026-10-11", "2026-10-13", True),
                                         self.CAT, "2026-10", self.WIN), ["C1"])

    def test_a_close_past_the_moment_breaks_it(self):
        self.assertEqual(CAL.broken_arcs(self.arc("2026-10-08", "2026-10-11", "2026-10-17"),
                                         self.CAT, "2026-10", self.WIN), ["C1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
