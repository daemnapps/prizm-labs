#!/usr/bin/env python3
"""image-teardown — the parts that must hold without a model.

    python3 tests/test_image_teardown.py

No network, no model, nothing spent. Every test that goes near a runner
replaces `subprocess.run` with something that fails the test if it is called.
Runs live in a temp folder: no test touches a real run or the real runs/.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

LANE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LANE / "tools"))

import paths as P                     # noqa: E402
import run as R                       # noqa: E402
import elements_label as EL           # noqa: E402
import gates as G                     # noqa: E402


def no_calls(*a, **k):
    raise AssertionError(f"a subprocess was started during a dry run: {a[0] if a else k}")


def quiet(fn, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        out = fn(*a, **k)
    return out, buf.getvalue()


def good_answer():
    """A canned labelling answer built from whatever the library holds today,
    so the test follows the library instead of pinning rows that may move."""
    E = EL.library()
    return {EL.key(el, asset): {"id": E.rows(el, asset)[0]["id"],
                                "why": "the record describes it", "proposed": None}
            for el, asset in EL.LISTS}


def fenced(answer):
    return "Here you go.\n\n```ELEMENTS\n" + json.dumps(answer, indent=1) + "\n```\n"


class PromptSort(unittest.TestCase):
    def test_v10_beats_v2(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for n in (1, 2, 9, 10):
                (d / f"stage1-image-teardown-v{n}-damon.md").write_text(str(n))
            self.assertEqual(R.prompt_for("1", d).name, "stage1-image-teardown-v10-damon.md")

    def test_subfolders_never_compete(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "superseded").mkdir()
            (d / "superseded/stage1-image-teardown-v99-damon.md").write_text("old")
            (d / "stage1-image-teardown-v3-damon.md").write_text("live")
            self.assertEqual(R.prompt_for("1", d).name, "stage1-image-teardown-v3-damon.md")

    def test_every_stage_has_a_live_prompt(self):
        for s in R.STAGES:
            self.assertTrue(R.prompt_for(s).is_file(), s)

    def test_no_stale_model_id(self):
        for s in R.STAGES:
            model, _ = R.model_for(s)
            self.assertNotEqual(model, "claude-opus-4-6")
        sys.path.insert(0, str(P.RUN_KIT))
        from run_kit import model as M
        if not R.CLAUDE:
            self.assertEqual(R.model_for("6")[0], M.TIERS["designs"])
            self.assertEqual(R.model_for("2b")[0], M.TIERS["checks"])


class Paths(unittest.TestCase):
    def test_found_by_walking_up(self):
        self.assertTrue((P.REPO / "components").is_dir() and (P.REPO / "brands").is_dir())
        self.assertEqual(P.LANE, LANE)
        self.assertEqual(P.LAB, LANE.parent)
        self.assertEqual(P.BRANDS, P.REPO / "brands")
        self.assertEqual(P.RECORDS, P.REPO / "runs" / "image-teardown")

    def test_every_exported_name_still_there(self):
        for name in ("LANE LAB SWIPE SWIPE_ORGANIC BRANDS DOCTRINE ADCOPY PROMPTS TOOLS RUNS "
                     "REFERENCE DRIVE GEMINI_TEXT CLAUDE_TEXT GEMINI_IMAGE COMPOSE LANGUAGE FAL "
                     "LEXICON brand avatar_profile product").split():
            self.assertTrue(hasattr(P, name), name)
        for f in (P.CLAUDE_TEXT, P.GEMINI_TEXT, P.GEMINI_IMAGE, P.LANGUAGE):
            self.assertTrue(f.is_file(), f)
        self.assertTrue(P.DOCTRINE.is_dir())
        self.assertTrue((P.ELEMENTS / "machine/elements.py").is_file())
        self.assertTrue((P.QUALITY / "quality_checks").is_dir())

    def test_nothing_counts_parents_to_find_the_workspace(self):
        for f in (LANE / "tools/paths.py", LANE / "tools/run.py", LANE / "chain.py",
                  LANE / "tools/gates.py", LANE / "tools/elements_label.py"):
            self.assertNotRegex(f.read_text(), r"parents\[\d\]", f.name)

    def test_a_run_with_no_brand_on_it_is_an_error_not_a_default(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit) as e:
                P.brand_of_run(d)
            self.assertIn("--brand", str(e.exception))
            self.assertEqual(P.brand_of_run(d, "anything"), "anything")


class DryRun(unittest.TestCase):
    def test_makes_no_calls_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            run = Path(d) / "not-opened-yet"
            with mock.patch("subprocess.run", no_calls), mock.patch("subprocess.Popen", no_calls):
                code, out = quiet(R.dry_run, [run], list(R.STAGES), "no-such-brand", "nobody", "nothing")
            self.assertFalse(run.exists(), "a dry run opened a run folder")
            self.assertEqual(list(Path(d).iterdir()), [])
            self.assertIn("DRY RUN", out)
            for s in R.STAGES:
                self.assertIn(f"stage {s}:", out)
            # a brand that does not exist cannot resolve — and it says so, per stage
            self.assertEqual(code, 1)
            self.assertIn("MISSING", out)
            self.assertIn("offer_file", out)

    def test_inputs_an_earlier_stage_makes_are_not_missing(self):
        with tempfile.TemporaryDirectory() as d:
            run = Path(d) / "r"
            with mock.patch("subprocess.run", no_calls):
                bad, _ = quiet(R.dry_stage, run, "2", "b", None, None, ["1", "2"])
                self.assertEqual(bad, [])
                alone, _ = quiet(R.dry_stage, run, "2", "b", None, None, ["2"])
                self.assertEqual(alone, ["teardown_record"])

    def test_the_labelling_stage_resolves(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("subprocess.run", no_calls):
                bad, out = quiet(R.dry_stage, Path(d) / "r", "2b", "b", None, None, ["1", "2", "2b"])
            self.assertEqual(bad, [], out)

    def test_entry_script_takes_the_flag(self):
        src = (LANE / "chain.py").read_text()
        self.assertIn('"--dry-run"', src)
        self.assertIn("--dry-run", (LANE / "tools/run.py").read_text())

    def test_stage_list(self):
        self.assertEqual(R.stage_list("all"), list(R.STAGES))
        self.assertEqual(R.stage_list("6,3"), ["3", "6"])
        self.assertEqual(R.stage_list("2b"), ["2b"])
        with self.assertRaises(Exception):
            R.stage_list("9")


class Elements(unittest.TestCase):
    def test_candidates_come_from_the_library(self):
        text = EL.candidates()
        E = EL.library()
        for el, asset in EL.LISTS:
            self.assertIn(f"### {el}/{asset}", text)
            for r in E.rows(el, asset):
                self.assertIn(f"`{r['id']}`", text)

    def test_a_clean_answer_passes(self):
        rec, problems = EL.validate(EL.parse(fenced(good_answer())))
        self.assertEqual(problems, [])
        self.assertEqual(set(rec["labels"]), {EL.key(*l) for l in EL.LISTS})
        self.assertEqual(rec["refused"], [])

    def test_an_unknown_id_is_refused_and_recorded_never_guessed(self):
        a = good_answer()
        a["format/image"]["id"] = "a-format-nobody-ever-filed"
        rec, problems = EL.validate(a)
        self.assertNotIn("format/image", rec["labels"])
        self.assertEqual(rec["refused"][0]["id"], "a-format-nobody-ever-filed")
        self.assertEqual(rec["refused"][0]["list"], "format/image")
        self.assertTrue(any("REFUSED" in p for p in problems))
        # the other three still stand
        self.assertEqual(len(rec["labels"]), 3)

    def test_an_id_from_the_wrong_list_is_refused(self):
        a = good_answer()
        a["style/image"]["id"] = a["framework/all"]["id"]
        rec, problems = EL.validate(a)
        self.assertEqual([r["list"] for r in rec["refused"]], ["style/image"])

    def test_none_fits_needs_a_proposed_row(self):
        a = good_answer()
        a["style/image"] = {"id": "none-fits", "why": "x",
                            "proposed": "new-look — New look — a register no row describes"}
        rec, problems = EL.validate(a)
        self.assertEqual(problems, [])
        self.assertEqual(rec["labels"]["style/image"], "none-fits")
        self.assertIn("New look", rec["proposed"]["style/image"])
        a["style/image"]["proposed"] = None
        _, problems = EL.validate(a)
        self.assertTrue(any("no proposed row" in p for p in problems))

    def test_a_missing_label_and_an_unreadable_answer(self):
        a = good_answer()
        del a["doctrine/awareness"]
        _, problems = EL.validate(a)
        self.assertTrue(any("doctrine/awareness" in p for p in problems))
        with self.assertRaises(ValueError):
            EL.parse("I labelled it, all four fit nicely.")

    def test_read_writes_elements_json_and_the_gate_holds(self):
        Held = G.quality().Held
        with tempfile.TemporaryDirectory() as d:
            run = Path(d) / "r"
            (run / "out").mkdir(parents=True)
            a = good_answer()
            a["framework/all"]["id"] = "not-a-framework"
            (run / "out" / EL.ANSWER).write_text(fenced(a))
            rec, problems = EL.read(run, "stage2b-image-elements-v1-damon.md")
            on_disk = json.loads((run / "out/elements.json").read_text())
            self.assertEqual(on_disk["refused"][0]["id"], "not-a-framework")
            with self.assertRaises(Held):
                quiet(G.elements_gate, run, problems, "hold")
            self.assertIn("elements", G.held(run))
            self.assertIn("not-a-framework", " ".join(G.held(run)["elements"]))
            # warn: same verdict on file, the run carries on
            ok, _ = quiet(G.elements_gate, run, problems, "warn")
            self.assertFalse(ok)
            # and a clean answer clears it
            (run / "out" / EL.ANSWER).write_text(fenced(good_answer()))
            _, problems = EL.read(run)
            quiet(G.elements_gate, run, problems, "hold")
            self.assertEqual(G.held(run), {})

    def test_the_prompt_is_guarded_and_names_no_brand(self):
        t = R.prompt_for("2b").read_text()
        self.assertTrue(t.lstrip().startswith("**No example in this prompt is an answer.**"))
        self.assertEqual(R.wants_of("2b"), {"teardown_record", "element_candidates"})
        low = t.lower()
        for d in P.BRANDS.iterdir():
            if d.is_dir() and not d.name.startswith(("_", ".")):
                self.assertNotIn(d.name.lower(), low)


BANK = """# offers

## thing-one — Thing One
Single: $29.00. Three: $75.00.

## thing-two — Thing Two
Single: $12.00.
"""


class CopyGate(unittest.TestCase):
    def test_unfilled_and_prices(self):
        self.assertEqual(G.copy_problems("Buy it for $29.00 today.", BANK, "thing-one"), [])
        probs = G.copy_problems("Buy it for $12.00. [UNFILLED: the proof line]", BANK, "thing-one")
        self.assertEqual(len(probs), 2)
        self.assertTrue(any("UNFILLED" in p for p in probs))
        self.assertTrue(any("$12.00" in p for p in probs))

    def test_document_three_is_not_our_copy(self):
        brief = ("## DOCUMENT ONE — THE BRIEF\nOurs is $29.00.\n\n"
                 "## DOCUMENT THREE — INTERNAL\nThe source ad says $300 a session.\n")
        self.assertEqual(G.copy_problems(brief, BANK, "thing-one"), [])

    def test_a_bank_keyed_differently_falls_back_to_the_whole_bank(self):
        self.assertEqual(G.copy_problems("Only $12.00.", BANK, "a-slug-the-bank-does-not-use"), [])
        self.assertTrue(G.copy_problems("Only $13.00.", BANK, "a-slug-the-bank-does-not-use"))


class Filing(unittest.TestCase):
    def test_every_run_files_its_record_and_never_media(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            run = d / "lane-runs" / "brandx-swipe-01-thing"
            for s in ("out", "assets"):
                (run / s).mkdir(parents=True)
            (run / "out/01-teardown.md").write_text("t")
            (run / "out/06-brief.md").write_text("b")
            (run / "out/elements.json").write_text("{}")
            (run / "out/.language-hooks.md").write_text("working file")
            (run / "assets/source.json").write_text("{}")
            (run / "assets/source.jpg").write_bytes(b"\xff\xd8")
            G.quality().hold("copy", [], run)
            with mock.patch.object(P, "RUNS", d / "lane-runs"), \
                 mock.patch.object(P, "RECORDS", d / "runs" / "image-teardown"):
                dst = G.file_record("brandx", run.name)
            self.assertEqual(dst, d / "runs/image-teardown/brandx" / run.name)
            self.assertEqual(sorted(p.name for p in dst.iterdir()),
                             ["01-teardown.md", "06-brief.md", "check.json", "elements.json",
                              "run.json", "source.json"])
            meta = json.loads((dst / "run.json").read_text())
            self.assertEqual((meta["machine"], meta["brand"], meta["state"]),
                             ("image-teardown", "brandx", "filed"))

    def test_a_held_run_says_why_in_its_record(self):
        Held = G.quality().Held
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            run = d / "lane-runs" / "r1"
            (run / "out").mkdir(parents=True)
            (run / "out/06-brief.md").write_text("x [UNFILLED]")
            with self.assertRaises(Held):
                G.quality().hold("copy", ["the brief still carries an UNFILLED note"], run)
            with mock.patch.object(P, "RUNS", d / "lane-runs"), \
                 mock.patch.object(P, "RECORDS", d / "runs" / "image-teardown"):
                dst = G.file_record("brandx", "r1")
            meta = json.loads((dst / "run.json").read_text())
            self.assertEqual(meta["state"], "held")
            self.assertIn("UNFILLED", meta["held"]["copy"][0])

    def test_one_run_files_even_when_a_gate_stops_it(self):
        Held = G.quality().Held
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            run = d / "lane-runs" / "r2"
            (run / "out").mkdir(parents=True)

            def fake_stage(run, s, *a):
                (run / "out/06-brief.md").write_text("x")
                G.quality().hold("copy", ["held for the test"], run)

            with mock.patch.object(P, "RUNS", d / "lane-runs"), \
                 mock.patch.object(P, "RECORDS", d / "runs" / "image-teardown"), \
                 mock.patch.object(P, "REPO", d), mock.patch.object(P, "LAB", d), \
                 mock.patch.object(R, "run_stage", fake_stage):
                with self.assertRaises(Held):
                    quiet(R.one_run, run, ["6"], "brandx", None, None, True)
            self.assertTrue((d / "runs/image-teardown/brandx/r2/check.json").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=1)
