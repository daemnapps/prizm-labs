"""image-writing — the parts that must hold without a model.

    /usr/bin/python3 -m unittest discover -s tools/image-writing/tests

No network, no model, nothing spent. Runs live in a temp folder: no test touches a real run.
Proves: the writing prompts live here and the teardown holds none; the teardown loads its writing steps from here and
every writing prompt's {slots} have a source; the command refuses what is not a writing step and a run that does not
exist; the variations record holds its shape (the approved picture + exactly 5, the rows image-edit reads); stage 5
writes it and sends a broken one back once; the hook ledger opens in the run, never under brands/.
"""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOME / "tools"))
import writing as W            # noqa: E402  — puts the teardown's tools on the path
import variation_rows as VR    # noqa: E402
import paths as P              # noqa: E402
import run as R                # noqa: E402  — the teardown's engine

TEARDOWN = P.LANE


def quiet(fn, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        out = fn(*a, **k)
    return out, buf.getvalue()


# The model: the first five rows of the hand-written grandma example (2026-10-27), ids made v1..v5.
FIVE = [
    {"id": "v1", "label": "Headline 1 · A package deal", "words": ["SPOTS? NOT / A PACKAGE DEAL"],
     "picture": "The three dark spots are grouped tight and touching, so they read as one set"},
    {"id": "v2", "label": "Headline 2 · Splitting the mirror", "words": ["MY SPOTS? WE'RE NOT / SPLITTING THE MIRROR"],
     "picture": "The phone's reflection shows as a hard, bright rectangle in the largest spot"},
    {"id": "v3", "label": "Headline 3 · 8 years", "words": ["8 YEARS? WE'RE NOT / CELEBRATING IT"],
     "picture": "The spots are staged by age: the biggest and darkest in front, two smaller ones behind it"},
    {"id": "v4", "label": "Headline 4 · Covered up", "words": ["COVERED UP? WE'RE NOT / DOING JULY AGAIN"],
     "picture": "The fur is pulled up across her throat to the cheekbone, covering everything but the spots"},
    {"id": "v5", "label": "Headline 5 · A new face", "words": ["12 STEPS? WE'RE NOT / GOING TO 13"],
     "picture": "A woman of 62 in her place, same pose and crop", "people": "made-up",
     "person": {"who": "the spot-hider", "age": "62", "look": "freckled, ash-blonde going grey", "wardrobe": "the same fur"},
     "swap": [{"from": "A woman, roughly 50", "to": "A woman of 62, freckled", "kind": "drawn"}]},
]


def answer(rows):
    return ("v1 · Headline 1 · ...\n\n**THE VARIATIONS RECORD**\n\n```json\n"
            + json.dumps({"variations": rows}, indent=1) + "\n```\n")


def make_run(root, t5=""):
    run = Path(root) / "r"
    (run / "out").mkdir(parents=True)
    (run / "vars").mkdir()
    (run / "out" / VR.ANSWER).write_text(t5)
    return run


class Home(unittest.TestCase):
    def test_the_writing_prompts_live_here_and_the_teardown_holds_none(self):
        for s in W.STAGES:
            for route, form in (("ai", "single"), ("ai", "sequence"), ("creator", "single")):
                g = W.glob_for(s, route, form)
                self.assertTrue(list(W.PROMPTS.glob(g)), g)
                self.assertFalse(list((TEARDOWN / "prompts").rglob(g)), f"{g} still in the teardown")
        self.assertTrue((W.PROMPTS / "swaps-reader-v1-owner.md").is_file())
        self.assertFalse((TEARDOWN / "tools" / "swaps.py").exists())

    def test_the_teardown_runs_its_writing_steps_from_here(self):
        for s in W.STAGES:
            self.assertEqual(R.prompts_dir(s), W.PROMPTS)
            self.assertEqual(R.prompt_for(s).parent, W.PROMPTS)
            self.assertIn(s, R.STAGES)
        for s in R.RECORDS:
            if s == "1k":                       # the culture read moved to components/culture, 2026-10-27
                self.assertEqual(R.prompts_dir(s), P.REPO / "components" / "culture" / "prompts")
                continue
            self.assertEqual(R.prompts_dir(s), P.PROMPTS)
        self.assertEqual(list(R.STAGES), ["1", "1k", "2", "2b", "3", "4", "5", "6"])

    def test_every_writing_prompt_asks_only_for_what_is_supplied(self):
        import preflight as PF
        self.assertEqual([m for m in PF.placeholders() if m[0] in W.STAGES], [])

    def test_the_live_stage5_writes_the_record_and_stage6_lists_it(self):
        s5 = R.prompt_for("5").read_text()
        self.assertEqual(R.prompt_for("5").name, "stage4e-image-variations-v9-owner.md")
        self.assertIn("FORMAT HEADLINE", s5)                # v6: the headline is a format, the video hook step's rule
        self.assertIn("THE VARIATIONS RECORD", s5)
        self.assertIn("{approved_words}", s5)        # v4: the five vary the words on the approved picture
        self.assertIn("{spice_bank}", s5)            # v5: the avatar's spice rows
        self.assertIn("{spice_bank}", R.prompt_for("4").read_text())
        self.assertIn("{swaps_record}", s5)
        self.assertIn("exactly five", s5)
        s6 = R.prompt_for("6").read_text()
        self.assertIn("{variation_rows}", s6)
        self.assertIn("{brief_standard}", s6)
        self.assertIn("section 6, the variations", s6)


class Command(unittest.TestCase):
    def door(self, *args):
        return subprocess.run([sys.executable, str(HOME / "run.py"), *args], capture_output=True, text=True)

    def test_help(self):
        r = self.door("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("steps 3 to 6", r.stdout)

    def test_a_record_step_is_refused(self):
        r = self.door("any-run", "1,3", "--brand", "x")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not a writing step", r.stderr)

    def test_a_run_that_does_not_exist_is_refused(self):
        r = self.door("no-such-run-anywhere", "--brand", "x", "--product", "y")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no run at", r.stderr)


class Record(unittest.TestCase):
    def test_five_rows_one_change_each_pass(self):
        self.assertEqual(VR.validate({"variations": FIVE}), [])

    def test_the_batch_is_exactly_five(self):
        self.assertTrue(any("exactly 5" in p for p in VR.validate({"variations": FIVE[:4]})))
        self.assertTrue(any("exactly 5" in p for p in VR.validate({"variations": FIVE + [dict(FIVE[0], id="v6")]})))

    def test_a_row_needs_an_id_a_label_and_a_change(self):
        rows = [dict(r) for r in FIVE]
        rows[0] = {"id": "v1", "label": "nothing"}
        self.assertTrue(any("changes nothing" in p for p in VR.validate({"variations": rows})))
        rows[0] = {"label": "x", "words": ["A"]}
        self.assertTrue(any("no id" in p for p in VR.validate({"variations": rows})))

    def test_only_the_keys_image_edit_reads(self):
        rows = [dict(r) for r in FIVE]
        rows[1]["headline"] = "x"
        self.assertTrue(any("does not take: headline" in p for p in VR.validate({"variations": rows})))
        rows = [dict(r) for r in FIVE]
        rows[4] = dict(rows[4], people="somebody")
        self.assertTrue(any("people must be" in p for p in VR.validate({"variations": rows})))
        rows[4] = dict(FIVE[4], person={"who": "x", "height": "tall"})
        self.assertTrue(any("person carries height" in p for p in VR.validate({"variations": rows})))

    def test_words_are_one_string_per_zone(self):
        rows = [dict(r) for r in FIVE]
        rows[0] = dict(rows[0], words="ONE STRING")
        self.assertTrue(any("words must be a list" in p for p in VR.validate({"variations": rows})))

    def test_ids_are_unique(self):
        rows = [dict(r) for r in FIVE]
        rows[1] = dict(rows[1], id="v1")
        self.assertTrue(any("used twice" in p for p in VR.validate({"variations": rows})))

    def test_the_row_keys_are_the_ones_vary_recipe_takes(self):
        # tools/image-edit vary_recipe passes these through as the change; nothing else is read
        self.assertEqual(set(VR.CHANGES), {"words", "picture", "swap", "stays_drop", "people", "person"})
        self.assertEqual(VR.COUNT, 5)


class StageFive(unittest.TestCase):
    def test_the_record_is_read_from_the_last_json_block(self):
        with tempfile.TemporaryDirectory() as d:
            run = make_run(d, "```\nv1 · readable line\n```\n" + answer(FIVE))
            rec, bad = VR.from_stage5(run)
            self.assertEqual(bad, [])
            self.assertEqual([v["id"] for v in rec["variations"]], ["v1", "v2", "v3", "v4", "v5"])
            self.assertEqual(rec["source"], "stage5")

    def test_after_stage5_writes_variations_json_without_a_model(self):
        with tempfile.TemporaryDirectory() as d:
            run = make_run(d, answer(FIVE))
            pf = W.PROMPTS / "stage4e-image-variations-v3-owner.md"
            cmd = [sys.executable, "-c", "raise SystemExit('a model was called')", "--prompt-file", str(pf)]
            quiet(W.after, R, run, "5", pf, cmd, "x", "y")
            self.assertEqual(VR.load(run)["variations"], FIVE)

    def test_a_broken_record_is_sent_back_once_and_never_written(self):
        with tempfile.TemporaryDirectory() as d:
            run = make_run(d, answer(FIVE[:3]))
            pf = W.PROMPTS / "stage4e-image-variations-v3-owner.md"
            mark = Path(d) / "called"
            cmd = [sys.executable, "-c", f"open({str(mark)!r}, 'a').write('x')", "--prompt-file", str(pf)]
            _, out = quiet(W.after, R, run, "5", pf, cmd, "x", "y")
            self.assertEqual(mark.read_text(), "x")                      # re-made once
            self.assertIn("exactly 5", (run / "vars" / "_prompt-5-rows.md").read_text())
            self.assertIsNone(VR.load(run))
            self.assertIn("no variations record", out)

    def test_a_hand_written_record_is_kept_beside_the_new_one(self):
        with tempfile.TemporaryDirectory() as d:
            run = make_run(d, answer(FIVE))
            (run / "out" / VR.FILE).write_text(json.dumps({"written": "by hand", "variations": FIVE[:2]}))
            rec, _ = VR.from_stage5(run)
            VR.write(run, rec)
            self.assertEqual(json.loads((run / "out" / "variations.by-hand.json").read_text())["written"], "by hand")
            self.assertEqual(VR.load(run)["source"], "stage5")


class HookLedger(unittest.TestCase):
    """A brand with no hook ledger gets one in the run, never in brands/ (SI-24). Moved here from the teardown's tests
    with open_ledger, 2026-10-27."""

    def test_missing_brand_ledger_opens_in_the_run(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "brands/fx").mkdir(parents=True)
            run = d / "r"
            run.mkdir()
            f, _ = quiet(W.open_ledger, run, "fx", d / "brands/fx/ads/hooks/hook-ledger.md")
            self.assertEqual(f, run / "vars" / "hook-ledger.md")
            self.assertTrue(f.is_file())
            self.assertIn("| verbatim | hook | status | run |", f.read_text())
            self.assertFalse((d / "brands/fx/ads").exists(), "a ledger was opened under brands/")

    def test_existing_brand_ledger_is_used_and_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            ledger = d / "brands/fx/ads/hooks/hook-ledger.md"
            ledger.parent.mkdir(parents=True)
            ledger.write_text("kept\n")
            run = d / "r"
            run.mkdir()
            f, _ = quiet(W.open_ledger, run, "fx", ledger)
            self.assertEqual(f, ledger)
            self.assertEqual(ledger.read_text(), "kept\n")
            self.assertFalse((run / "vars" / "hook-ledger.md").exists())


class NoBrand(unittest.TestCase):
    def test_no_brand_named_in_the_code_or_the_prompts(self):
        names = {d.name.lower() for d in P.BRANDS.iterdir() if (d / "products").is_dir()} if P.BRANDS.is_dir() else set()
        live = [HOME / "run.py", *(HOME / "tools").glob("*.py"), *W.PROMPTS.glob("*.md"), *(HOME / "templates").glob("*.md")]
        import re
        for f in live:
            words = set(re.findall(r"[a-z0-9-]+", f.read_text().lower()))
            self.assertFalse(names & words, f"{f.name} names {names & words}")



class HeadlineFormat(unittest.TestCase):
    """Stage 5 v6: the approved headline as a FORMAT with [BLANKS]; every row keeps every fixed word (video-teardown
    hook_format's own check, no model)."""

    FMT = "FORMAT HEADLINE: [PROBLEM]? YOU AND ME / ARE NOT A [PAIR]\n"
    ROWS = [{"id": f"v{i}", "label": f"Headline {i} · x", "words": [w]} for i, w in enumerate(
        ["BROWN SPOTS? YOU AND ME / ARE NOT A MATCHING SET", "MY SPOTS? YOU AND ME / ARE NOT A DOUBLE ACT",
         "8 YEARS OF SPOTS? YOU AND ME / ARE NOT AN ITEM", "SPOTS IN JULY? YOU AND ME / ARE NOT A SUMMER PAIR",
         "12 STEPS FOR 3 SPOTS? YOU AND ME / ARE NOT A FAIR TRADE"], 1)]

    def run_with(self, d, rows, fmt=None):
        run = make_run(d, (fmt or self.FMT) + answer(rows))
        (run / "out" / "approved-words.md").write_text("- Zone 1: `DARK SPOTS? YOU AND ME / ARE NOT A PACKAGE DEAL`\n")
        return run

    def test_rows_that_keep_the_fixed_words_pass(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(VR.format_problems(self.run_with(d, self.ROWS), {"variations": self.ROWS}), [])

    def test_a_row_that_writes_a_different_sentence_is_named(self):
        rows = [dict(r) for r in self.ROWS]
        rows[2] = dict(rows[2], words=["8 YEARS? WE'RE NOT / CELEBRATING IT"])
        with tempfile.TemporaryDirectory() as d:
            got = VR.format_problems(self.run_with(d, rows), {"variations": rows})
            self.assertTrue(any(p.startswith("v3 breaks the format") for p in got))

    def test_a_format_that_is_not_the_approved_headline_is_named(self):
        with tempfile.TemporaryDirectory() as d:
            run = self.run_with(d, self.ROWS, fmt="FORMAT HEADLINE: [PROBLEM]? WE'RE NOT / [GROWING OLD TOGETHER]\n")
            self.assertTrue(any("not the approved headline's own" in p for p in VR.format_problems(run, {"variations": self.ROWS})))

    def test_a_break_is_sent_back_once_and_recorded(self):
        rows = [dict(r) for r in self.ROWS]
        rows[0] = dict(rows[0], words=["COVERED UP? WE'RE NOT / DOING JULY AGAIN"])
        with tempfile.TemporaryDirectory() as d:
            run = self.run_with(d, rows)
            pf = W.PROMPTS / "stage4e-image-variations-v6-owner.md"
            mark = Path(d) / "called"
            cmd = [sys.executable, "-c", f"open({str(mark)!r}, 'a').write('x')", "--prompt-file", str(pf)]
            quiet(W.after, R, run, "5", pf, cmd, "x", "y")
            self.assertEqual(mark.read_text(), "x")                      # sent back once
            self.assertTrue(VR.load(run).get("format_breaks"))           # still broken: written, flagged for the sign-off

if __name__ == "__main__":
    unittest.main()
