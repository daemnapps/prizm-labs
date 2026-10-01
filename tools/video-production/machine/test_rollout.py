#!/usr/bin/env python3
"""
test_rollout.py — what the 2026-09-20 rollout added, held in place.

    python3 machine/test_rollout.py

  · preflight rule 13: the run's format is asked of the element library —
    a library row is accepted, an unknown one is refused WITH the real ids,
    a row that is only a name (`[TO DEFINE`) is refused as not defined yet;
    `style_id` and the scene delivery dials are asked the same way
  · the old path is untouched: a run on another bank, naming no library, is
    checked exactly as it was before
  · promptify's cast folder follows the run's brand, and no brand is assumed
  · the live offer and A-roll prompts carry no price, link or brand, open
    with the shape guard, and send the SAME shape block as the ones they replace

Standard library only. No network, no model, nothing spent.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
LIB = FIX / "element-library"
BANK = FIX / "bank.json"
PROMPTS = HERE.parent / "prompts"
sys.path.insert(0, str(HERE))


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


preflight = _load("vm_preflight_rollout", "preflight.py")
library_check = preflight.library_check
prompt = _load("vm_prompt_rollout", "prompt.py")


def rule13(fails):
    return [f for f in fails if f.startswith("[rule 13]")]


class RunCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-rollout-"))
        self.run = self.tmp / "sample-run"
        shutil.copytree(FIX / "sample-run", self.run)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def set_run(self, **fields):
        p = self.run / "run.json"
        d = json.loads(p.read_text())
        d.update(fields)
        p.write_text(json.dumps(d))

    def check(self, library=LIB, bank=BANK):
        return preflight.check(FIX / "batch-good.json", self.run, "higgsfield-ui", bank, library)


class LibraryFormat(RunCase):
    def test_library_format_accepted(self):
        fails, _ = self.check()
        self.assertEqual(fails, [])

    def test_unknown_format_refused_with_real_ids(self):
        self.set_run(format="no-such-format")
        r13 = rule13(self.check()[0])
        self.assertEqual(len(r13), 1, r13)
        self.assertIn("'no-such-format' is not a format/video row", r13[0])
        # the real ids are named — and only the ones a run may actually use
        self.assertIn("fixture-format", r13[0])
        self.assertIn("fixture-second", r13[0])
        self.assertNotIn("fixture-named-only", r13[0])
        self.assertNotIn("fixture-retired", r13[0])

    def test_to_define_draft_refused(self):
        self.set_run(format="fixture-named-only")
        r13 = rule13(self.check()[0])
        self.assertEqual(len(r13), 1, r13)
        self.assertIn("named but not defined yet", r13[0])
        self.assertIn("fixture-format", r13[0])

    def test_in_the_bank_but_not_the_library_says_rebuild(self):
        bank = self.tmp / "bank.json"
        bank.write_text(json.dumps({"formats": [{"id": "fresh-format"}]}))
        self.set_run(format="fresh-format")
        fails, _ = self.check(bank=bank)
        self.assertEqual(len(fails), 1, fails)
        self.assertIn("older than the bank", fails[0])
        self.assertIn("elements.py build", fails[0])

    def test_style_id_asked(self):
        self.set_run(style_id="fixture-look")
        self.assertEqual(self.check()[0], [])
        self.set_run(style_id="fixture-look-named-only")
        self.assertIn("named but not defined yet", rule13(self.check()[0])[0])
        self.set_run(style_id="no-such-look")
        r13 = rule13(self.check()[0])
        self.assertIn("is not a style/video row", r13[0])
        self.assertIn("fixture-look", r13[0])

    def test_old_path_untouched_without_a_library(self):
        """Another bank and no --library: exactly the check it always was."""
        self.set_run(format="fixture-format", style_id="no-such-look")
        fails, warns = self.check(library=None)
        self.assertEqual(fails, [])
        self.assertFalse([w for w in warns if "rule 13" in w])

    def test_cli_takes_library(self):
        self.set_run(format="fixture-named-only")
        code = preflight.main(["check", str(FIX / "batch-good.json"), "--run", str(self.run),
                               "--provider", "higgsfield-ui", "--bank", str(BANK),
                               "--library", str(LIB)])
        self.assertEqual(code, 2)


class DeliveryDials(unittest.TestCase):
    def ask(self, plan):
        doc = json.loads((FIX / plan).read_text())
        return library_check.problems({"format": "fixture-format"}, doc, LIB)

    def test_good_plan_is_clean(self):
        self.assertEqual(self.ask("plan-library-good.json"), [])

    def test_bad_plan_names_each_wrong_value_and_the_real_ones(self):
        bad = self.ask("plan-library-bad.json")
        text = "\n".join(f"{i}: {w} → {t}" for i, w, t in bad)
        self.assertEqual(len(bad), 3, text)
        self.assertIn("style_id 'fixture-look-named-only' is named but not defined yet", text)
        self.assertIn("brief S1: delivery.humor 'slapstick' is not a delivery/humor row → use one of: none, dry", text)
        self.assertIn("brief S2: delivery.register 'one-breath' is not a delivery/register row", text)


class RealLibrary(unittest.TestCase):
    """The real lists, read and never written. Nothing here names a row."""

    def test_every_format_in_the_real_bank_is_a_defined_library_row(self):
        lib = library_check.load()
        for fid in preflight.load_bank_names(preflight.DEFAULT_BANK):
            self.assertEqual(library_check.problems({"format": fid}, lib=lib), [], fid)

    def test_the_real_library_refuses_its_own_named_only_rows(self):
        lib = library_check.load()
        named_only = [r["id"] for r in lib.rows("format", "video")
                      if str(r.get("what") or "").startswith(library_check.TO_DEFINE)]
        for fid in named_only:
            bad = library_check.problems({"format": fid}, lib=lib)
            self.assertEqual(len(bad), 1, fid)
            self.assertIn("named but not defined yet", bad[0][1])

    def test_a_fixture_library_never_leaks_into_a_real_check(self):
        library_check.problems({"format": "fixture-format"}, library_dir=LIB)
        real = library_check.problems({"format": "fixture-format"})
        self.assertEqual(len(real), 1)


class CastPerBrand(unittest.TestCase):
    def setUp(self):
        self.pm = _load("vm_promptify_rollout", "promptify.py")
        self.pm.WORKSPACE = FIX / "cast-workspace"
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-rollout-cast-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cast_file_resolves_per_brand(self):
        a = self.pm.use_brand("_fixture-a")
        self.assertEqual(a, FIX / "cast-workspace/brands/_fixture-a/core-avatars/casting")
        self.assertEqual(self.pm.elements()["lead-a"], "00000000-0000-4000-8000-0000000000a1")
        self.pm.use_brand("_fixture-b")
        got = self.pm.elements()
        self.assertEqual(got["lead-b"], "00000000-0000-4000-8000-0000000000b1")
        self.assertNotIn("lead-a", got)

    def test_brand_comes_from_the_run(self):
        (self.tmp / "run.json").write_text(json.dumps({"brand": "_fixture-b"}))
        self.assertEqual(self.pm.brand_of(self.tmp), "_fixture-b")
        self.assertEqual(self.pm.brand_of(self.tmp, "_fixture-a"), "_fixture-a")   # the flag wins

    def test_brand_from_the_plan_when_run_json_has_none(self):
        (self.tmp / "out").mkdir()
        (self.tmp / "out" / "plan.json").write_text(json.dumps({"brand": "_fixture-a"}))
        self.assertEqual(self.pm.brand_of(self.tmp), "_fixture-a")

    def test_no_brand_is_an_error_that_says_so(self):
        with self.assertRaises(SystemExit) as e:
            self.pm.brand_of(self.tmp)
        self.assertIn("does not name a brand", str(e.exception))
        with self.assertRaises(SystemExit):
            _load("vm_promptify_unset", "promptify.py").elements()

    def test_no_brand_is_written_into_the_module(self):
        src = (HERE / "promptify.py").read_text()
        self.assertIsNone(re.search(r"brands/(?!<)[a-z0-9_-]+/", src))


def _shape_of(path: Path) -> str:
    return re.search(r"```shape\n(.*?)```", path.read_text(), re.S).group(1)


class LivePrompts(unittest.TestCase):
    OFFER = PROMPTS / "stage-4-offer" / "stage4-offer-v2-damon.md"
    AROLL = PROMPTS / "stage-2-aroll" / "stage2-aroll-v2-damon.md"
    GUARD = "**Everything named in this prompt as an example is an example of a SHAPE, not"

    def test_offer_v2_carries_no_price_and_no_link(self):
        text = self.OFFER.read_text()
        for pat in (r"\$\d", r"https?://", r"\.com"):
            self.assertIsNone(re.search(pat, text), pat)
        for token in ("<price from the brief>", "<guarantee line from the brief, verbatim>",
                      "<the brief's link>"):
            self.assertIn(token, text)

    def test_both_open_with_the_shape_guard(self):
        for f in (self.OFFER, self.AROLL):
            self.assertTrue(f.read_text().startswith(self.GUARD), f.name)

    def test_neither_names_a_brand_or_a_price(self):
        brands = [p.name for p in (HERE.parents[3] / "brands").iterdir()
                  if p.is_dir() and not p.name.startswith(("_", "."))]
        for f in (self.OFFER, self.AROLL):
            text = f.read_text()
            for b in brands:
                self.assertIsNone(re.search(rf"(?<![A-Za-z]){re.escape(b)}(?![a-z])", text, re.I),
                                  f"{f.name} names {b}")
            self.assertIsNone(re.search(r"\d+\.\d\d", text), f"{f.name} carries a price")

    def test_the_machine_is_pinned_to_v2_and_the_files_exist(self):
        self.assertTrue(prompt.STAGE_PROMPT["offer"].endswith("stage4-offer-v2-damon.md"))
        self.assertTrue(prompt.STAGE_PROMPT["aroll"].endswith("stage2-aroll-v2-damon.md"))
        for stage in prompt.STAGE_PROMPT:
            self.assertTrue((PROMPTS / prompt.STAGE_PROMPT[stage]).is_file(), stage)
            prompt.shape(stage)

    def test_what_is_sent_did_not_change(self):
        """The side-by-side proof: v2 changed the words AROUND the shape, for
        the person reading. The shape block — the only part the machine sends —
        is byte-for-byte the one it replaced."""
        for new in (self.OFFER, self.AROLL):
            old = new.parent / "archive" / new.name.replace("-v2-", "-v1-")
            self.assertEqual(_shape_of(new), _shape_of(old), new.name)


if __name__ == "__main__":
    unittest.main()
