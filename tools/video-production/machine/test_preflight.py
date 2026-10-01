#!/usr/bin/env python3
"""python3 machine/test_preflight.py — from any cwd. Stdlib unittest only.

No provider or model slug is written here: every one is read out of
providers.json, so the registry test can hold this file to the same rule."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


platform = load("platform")
preflight = load("preflight")
REG = json.loads((HERE / "providers.json").read_text())

FALLBACK = next(n for n, r in REG["providers"].items() if not r["detect"])
KEYED = next(n for n, r in REG["providers"].items() if r["detect"].get("key_env"))
KEY_ENV = REG["providers"][KEYED]["detect"]["key_env"]
SESSION_ONLY = next(n for n, r in REG["providers"].items()
                    if r["detect"] == {"claudecode": True})
HF = REG["providers"][FALLBACK]["stations"]
MOTION = HF["motion"]
KEYED_MOTION = REG["providers"][KEYED]["stations"]["motion"]
PER_DOLLAR = REG["credits_per_dollar"][REG["providers"][FALLBACK]["family"]]

CLEAN_ENV = {k: v for k, v in os.environ.items()
             if k not in ("CLAUDECODE", KEY_ENV, "AI_VIDEO_PROVIDER", "AI_VIDEO_CONFIRM")}


@contextlib.contextmanager
def env(**extra):
    """A clean environment plus `extra`, and a vault that holds nothing —
    so no test ever touches a real Keychain."""
    saved = dict(os.environ)
    saved_mod = sys.modules.get("daemn_keys")
    os.environ.clear()
    os.environ.update(CLEAN_ENV)
    os.environ.update(extra)
    sys.modules["daemn_keys"] = types.SimpleNamespace(key=lambda name, required=False: "")
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(saved)
        if saved_mod is None:
            sys.modules.pop("daemn_keys", None)
        else:
            sys.modules["daemn_keys"] = saved_mod


def run_cli(mod, argv) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = mod.main(argv)
    return code, buf.getvalue()


class RunDir(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-preflight-"))
        self.run = self.tmp / "sample-run"
        shutil.copytree(FIX / "sample-run", self.run)
        self.bad_run = self.tmp / "unknown-format-run"
        shutil.copytree(FIX / "unknown-format-run", self.bad_run)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def check(self, batch: str, run: Path | None = None, provider: str = FALLBACK) -> tuple[int, str]:
        with env():
            return run_cli(preflight, ["check", str(FIX / batch), "--run", str(run or self.run),
                                       "--provider", provider, "--bank", str(FIX / "bank.json")])


class Check(RunDir):
    def test_bad_batch_names_every_rule(self):
        code, out = self.check("batch-bad.json")
        self.assertEqual(code, 2, out)
        for rule in (1, 2, 3, 4, 5, 6, 7, 8):
            self.assertIn(f"[rule {rule}]", out, f"rule {rule} missing:\n{out}")
        self.assertIn("[rule 1] S1:", out)
        self.assertIn("[rule 2] S2:", out)
        self.assertIn("[rule 3] S3:", out)
        self.assertIn("[rule 4] S4:", out)
        self.assertIn(f"over {MOTION}'s {REG['models'][MOTION]['max_seconds']}s cap", out)
        self.assertIn("unverified frame 00000000-0000-4000-8000-0000000000a2", out)
        self.assertIn("[rule 8] S6:", out)
        self.assertIn("line L1 claimed more than once", out)
        self.assertIn("says nothing about who/what is in it", out)
        self.assertFalse((self.run / "batches" / "batch-bad.json").exists())

    def test_bad_format_is_rule_9(self):
        code, out = self.check("batch-bad-format.json", self.bad_run)
        self.assertEqual(code, 2, out)
        self.assertIn("[rule 9]", out)
        self.assertIn("no-such-format", out)

    def test_missing_bank_is_rule_9(self):
        with env():
            code, out = run_cli(preflight, ["check", str(FIX / "batch-good.json"), "--run", str(self.run),
                                            "--provider", FALLBACK, "--bank", str(self.tmp / "nowhere.json")])
        self.assertEqual(code, 2)
        self.assertIn("[rule 9] run: format bank missing", out)

    def test_good_batch_is_green_and_copied(self):
        code, out = self.check("batch-good.json")
        self.assertEqual(code, 0, out)
        self.assertIn("WARNING [rule 7] lines still unclaimed after this batch: L3", out)
        self.assertTrue((self.run / "batches" / "batch-good.json").exists())
        # a second check of the same file must not see itself as a duplicate claim
        code, out = self.check("batch-good.json")
        self.assertEqual(code, 0, out)

    def test_good_batch_on_each_provider_family(self):
        # each good fixture is green on its own family and rule 8 on the other
        fal_models = {platform.item_model(i) for i in platform.load_batch(FIX / "batch-good-fal.json")}
        for m in fal_models:
            self.assertEqual(REG["models"][m]["provider"], REG["providers"][KEYED]["family"], m)
        code, out = self.check("batch-good-fal.json", provider=KEYED)
        self.assertEqual(code, 0, out)
        code, out = self.check("batch-good.json", provider=KEYED)
        self.assertEqual(code, 2, out)
        self.assertEqual(out.count("[rule 8]"), 3)
        self.assertIn("flip the provider or change the model", out)
        code, out = self.check("batch-good-fal.json", provider=FALLBACK)
        self.assertEqual(code, 2, out)
        self.assertEqual(out.count("[rule 8]"), 3)

    def test_cinema_bare_list_is_green(self):
        code, out = self.check("cinema-payloads.json")
        self.assertEqual(code, 0, out)

    def test_negated_post_effects_pass(self):
        code, out = self.check("batch-negation.json")
        self.assertEqual(code, 0, out)
        self.assertNotIn("[rule 3]", out)

    def test_post_effect_detector(self):
        hits = preflight.post_effect_hits
        self.assertEqual(hits("No subtitles. No captions. No title cards."), [])
        self.assertEqual(hits("NEGATIVES: captions, subtitles"), [])
        self.assertEqual(hits("a shot with no captions burnt in"), [])
        self.assertEqual([h.lower() for h in hits("add captions along the bottom")], ["captions"])
        self.assertEqual(hits("a pipe on the wall, a borderline case"), [])
        self.assertEqual([h.lower() for h in hits("slow push in, then a transition")], ["transition"])

    def test_no_cut_line_required_on_motion(self):
        missing = self.tmp / "no-cut-missing.json"
        missing.write_text(json.dumps({"items": [{
            "id": "S9", "kind": "motion",
            "params": {"model": MOTION, "prompt": "She looks up and away. Natural motion.", "duration": 5},
            "medias": [{"value": "00000000-0000-4000-8000-0000000000a1", "role": "start_image"}],
            "characters": [], "products": [], "lines": ["L9"]}]}))
        with env():
            code, out = run_cli(preflight, ["check", str(missing), "--run", str(self.run),
                                            "--provider", FALLBACK, "--bank", str(FIX / "bank.json")])
        self.assertEqual(code, 2, out)
        self.assertIn("[rule 11] S9: prompt carries no continuous-take line", out)
        self.assertIn("add the no-cut line: Single continuous take, no cuts or scene changes", out)

        present = self.tmp / "no-cut-present.json"
        present.write_text(json.dumps({"items": [{
            "id": "S9", "kind": "motion",
            "params": {"model": MOTION,
                       "prompt": "She looks up and away. Single continuous take, no cuts or scene changes.",
                       "duration": 5},
            "medias": [{"value": "00000000-0000-4000-8000-0000000000a1", "role": "start_image"}],
            "characters": [], "products": [], "lines": ["L9"]}]}))
        with env():
            code, out = run_cli(preflight, ["check", str(present), "--run", str(self.run),
                                            "--provider", FALLBACK, "--bank", str(FIX / "bank.json")])
        self.assertNotIn("[rule 11]", out)

    def test_missing_batch_is_bad_input(self):
        with env():
            code, _ = run_cli(preflight, ["check", str(self.tmp / "none.json"), "--run", str(self.run),
                                          "--provider", FALLBACK])
        self.assertEqual(code, 3)


class Coverage(RunDir):
    def test_coverage_after_good_batch(self):
        code, out = run_cli(preflight, ["coverage", "--run", str(self.run)])
        self.assertEqual(code, 2)
        for line in ("L1", "L2", "L3"):
            self.assertIn(f"uncovered: {line}", out)
        self.check("batch-good.json")
        code, out = run_cli(preflight, ["coverage", "--run", str(self.run)])
        self.assertEqual(code, 2, out)
        self.assertIn("uncovered: L3", out)
        self.assertNotIn("uncovered: L1", out)
        self.check("cinema-payloads.json")
        # every clip that will ship also needs its motion + director verdicts —
        # write both for every motion item across the batches before the pack is deliverable
        for iid in ("S3", "A1", "B1"):
            preflight.verdict(self.run, iid, "motion", {"pass": True})
            preflight.verdict(self.run, iid, "director", {"verdict": "PASS"})
        # S3 and A1 carry lines, so each also needs a parity verdict; B1 carries none
        for iid in ("S3", "A1"):
            preflight.verdict(self.run, iid, "parity", {"verdict": "PASS", "heard": "x", "match": 1.0})
        code, out = run_cli(preflight, ["coverage", "--run", str(self.run)])
        self.assertEqual(code, 0, out)
        self.assertIn("every line claimed exactly once", out)

    def test_duplicate_across_batches(self):
        self.check("batch-good.json")
        dup = self.tmp / "again.json"
        dup.write_text(json.dumps({"items": [{
            "id": "S9", "kind": "motion",
            "params": {"model": MOTION, "prompt": "She looks up.", "duration": 5},
            "medias": [{"value": "00000000-0000-4000-8000-0000000000a1", "role": "start_image"}],
            "characters": ["lead"], "products": [], "lines": ["L2"]}]}))
        with env():
            code, out = run_cli(preflight, ["check", str(dup), "--run", str(self.run),
                                            "--provider", FALLBACK, "--bank", str(FIX / "bank.json")])
        self.assertEqual(code, 2, out)
        self.assertIn("line L2 claimed more than once", out)


class Verdict(RunDir):
    def test_verdict_writes_and_merges(self):
        code, out = run_cli(preflight, ["verdict", "S3", "--run", str(self.run),
                                        "--layer", "motion", "--json", json.dumps({"pass": True})])
        self.assertEqual(code, 0, out)
        self.assertIn("motion: ", out)
        self.assertIn("director: none", out)
        data = json.loads((self.run / "verdicts.json").read_text())
        self.assertTrue(data["S3"]["motion"]["pass"])
        self.assertEqual(data["S3"]["motion"]["history"], [])
        self.assertIn("at", data["S3"]["motion"])

        # a second write to the same layer keeps the first write in history
        code, out = run_cli(preflight, ["verdict", "S3", "--run", str(self.run), "--layer", "motion",
                                        "--json", json.dumps({"pass": False, "problems": [
                                            {"what": "mouth static on the talking beat", "defect_class": "fixable"}]})])
        self.assertEqual(code, 0, out)
        data = json.loads((self.run / "verdicts.json").read_text())
        self.assertFalse(data["S3"]["motion"]["pass"])
        self.assertEqual(len(data["S3"]["motion"]["history"]), 1)
        self.assertTrue(data["S3"]["motion"]["history"][0]["pass"])

        # a different layer on the same item does not disturb the first
        code, out = run_cli(preflight, ["verdict", "S3", "--run", str(self.run), "--layer", "director",
                                        "--json", json.dumps({"verdict": "PASS"})])
        self.assertEqual(code, 0, out)
        self.assertIn("motion: ", out)
        self.assertIn('"verdict": "PASS"', out)
        data = json.loads((self.run / "verdicts.json").read_text())
        self.assertFalse(data["S3"]["motion"]["pass"])
        self.assertEqual(data["S3"]["director"]["verdict"], "PASS")

    def test_verdict_from_file(self):
        f = self.tmp / "verdict.json"
        f.write_text(json.dumps({"verdict": "FLAG", "notes": ["announces, does not show"]}))
        code, out = run_cli(preflight, ["verdict", "A1", "--run", str(self.run),
                                        "--layer", "director", "--file", str(f)])
        self.assertEqual(code, 0, out)
        data = json.loads((self.run / "verdicts.json").read_text())
        self.assertEqual(data["A1"]["director"]["verdict"], "FLAG")

    def test_bad_json_is_bad_input(self):
        code, _ = run_cli(preflight, ["verdict", "S3", "--run", str(self.run),
                                      "--layer", "motion", "--json", "{not json"])
        self.assertEqual(code, 3)


class Coverage2(RunDir):
    def test_coverage_fails_clip_without_verdicts_then_passes(self):
        self.check("batch-good.json")
        code, out = run_cli(preflight, ["coverage", "--run", str(self.run)])
        self.assertEqual(code, 2, out)
        self.assertIn("not shippable: no motion verdict (S3)", out)
        self.assertIn("not shippable: no director verdict (S3)", out)
        self.assertIn("not shippable: no parity verdict — run lineparity (S3)", out)

        preflight.verdict(self.run, "S3", "motion", {"pass": True})
        code, out = run_cli(preflight, ["coverage", "--run", str(self.run)])
        self.assertEqual(code, 2, out)
        self.assertNotIn("no motion verdict (S3)", out)
        self.assertIn("not shippable: no director verdict (S3)", out)

        preflight.verdict(self.run, "S3", "director", {"verdict": "PASS"})
        code, out = run_cli(preflight, ["coverage", "--run", str(self.run)])
        self.assertEqual(code, 2, out)
        self.assertNotIn("no director verdict", out)
        self.assertIn("not shippable: no parity verdict — run lineparity (S3)", out)

        preflight.verdict(self.run, "S3", "parity", {"verdict": "PASS", "heard": "first line second line",
                                                       "match": 1.0})
        code, out = run_cli(preflight, ["coverage", "--run", str(self.run)])
        self.assertEqual(code, 2, out)  # L3 still uncovered by this fixture alone
        self.assertNotIn("not shippable: no", out)

    def test_parity_flag_is_not_shippable(self):
        self.check("batch-good.json")
        preflight.verdict(self.run, "S3", "motion", {"pass": True})
        preflight.verdict(self.run, "S3", "director", {"verdict": "PASS"})
        preflight.verdict(self.run, "S3", "parity", {"verdict": "FLAG", "heard": "wrong words entirely",
                                                       "match": 0.1})
        code, out = run_cli(preflight, ["coverage", "--run", str(self.run)])
        self.assertEqual(code, 2, out)
        self.assertIn("not shippable: says other words (heard: 'wrong words entirely') (S3)", out)

    def test_second_director_flag_is_concept_weak(self):
        self.check("batch-good.json")
        preflight.verdict(self.run, "S3", "motion", {"pass": True})
        preflight.verdict(self.run, "S3", "director", {"verdict": "FLAG", "notes": ["announces, does not show"]})
        code, out = run_cli(preflight, ["coverage", "--run", str(self.run)])
        self.assertNotIn("concept weak", out)  # one FLAG alone is a normal rework, not concept-weak

        preflight.verdict(self.run, "S3", "director", {"verdict": "FLAG", "notes": ["still an arrangement, not an event"]})
        code, out = run_cli(preflight, ["coverage", "--run", str(self.run)])
        self.assertEqual(code, 2, out)
        self.assertIn("concept weak — rework the scene in the script (S3)", out)


class Verify(RunDir):
    def test_verify_writes_frame(self):
        uid = "00000000-0000-4000-8000-0000000000a2"
        code, out = run_cli(preflight, ["verify", uid, "--run", str(self.run), "--shot", "S5",
                                        "--by", "tester", "--note", "face matches the sheet"])
        self.assertEqual(code, 0, out)
        frames = json.loads((self.run / "frames.json").read_text())
        row = frames[uid]
        self.assertTrue(row["verified"])
        self.assertEqual(row["shot"], "S5")
        self.assertEqual(row["by"], "tester")
        self.assertIn("T", row["at"])
        self.assertEqual(row["note"], "face matches the sheet")
        self.assertIn("00000000-0000-4000-8000-0000000000a1", frames)

    def test_verify_rejects_non_uuid(self):
        code, _ = run_cli(preflight, ["verify", "https://x/y.png", "--run", str(self.run),
                                      "--shot", "S1", "--by", "t"])
        self.assertEqual(code, 3)


class Ledger(RunDir):
    def test_totals_match_registry_arithmetic(self):
        run = self.tmp / "fresh-run"
        rates = [r for r in REG["models"][MOTION]["rates"] if "credits_per_second" in r]
        self.assertGreaterEqual(len(rates), 2, "the motion default needs at least two per-second readings")
        base = ["ledger", "--run", str(run), "--model", MOTION, "--brand", "_fixture"]
        expected = []
        # one billed row per reading, the first two on the same shot (a re-roll)
        for i, r in enumerate(rates):
            args = base + ["--job", f"j{i}", "--seconds", "10", "--status", "done",
                           "--tier", r["tier"], "--shot", "S3" if i < 2 else f"S{i + 4}"]
            if r["resolution"]:
                args += ["--resolution", r["resolution"]]
            code, _ = run_cli(preflight, args)
            self.assertEqual(code, 0)
            expected.append(r["credits_per_second"] * 10)
        amb = rates[0]
        code, out = run_cli(preflight, base + ["--job", "jx", "--seconds", "5", "--status", "ip_detected",
                                               "--tier", amb["tier"], "--shot", "S9"])
        self.assertEqual(code, 0)

        rows = json.loads((run / "ledger.json").read_text())
        self.assertEqual(len(rows), len(rates) + 1)
        for row, want in zip(rows, expected):
            self.assertAlmostEqual(row["credits"], want, places=2)
            self.assertNotIn("billing", row)
        self.assertEqual(rows[-1]["billing"], "ambiguous")
        billed = sum(expected)
        t = preflight.totals(rows)
        self.assertAlmostEqual(t["billed_credits"], billed, places=2)
        self.assertAlmostEqual(t["billed_usd"], round(billed / PER_DOLLAR, 3), places=2)
        self.assertAlmostEqual(t["ambiguous_credits"], amb["credits_per_second"] * 5, places=2)
        self.assertEqual(t["rerolls"], 1)
        self.assertEqual(t["rerolled_shots"], ["S3"])
        self.assertIn("re-rolls   1", out)
        self.assertIn("ambiguous", out)

        seeded = json.loads((run / "run.json").read_text())
        self.assertEqual(seeded["machine"], "video-machine")
        self.assertEqual(seeded["brand"], "_fixture")
        self.assertEqual(seeded["label"], "fresh-run")
        self.assertIn("opened", seeded)

    def test_exact_resolution_beats_later_null(self):
        rates = REG["models"][MOTION]["rates"]
        exact = [r for r in rates if r.get("resolution")]
        if not exact:
            self.skipTest("no resolution-specific reading on the motion default")
        r = exact[0]
        # among readings at the same tier and resolution the latest read wins
        same = [x for x in exact if x["tier"] == r["tier"] and x["resolution"] == r["resolution"]]
        expected = max(same, key=lambda x: x["read"])
        picked = platform.pick_rate(REG["models"][MOTION], r["tier"], r["resolution"])
        self.assertEqual(picked, expected)
        later_null = [x for x in rates if x["tier"] == r["tier"] and x["resolution"] is None]
        if later_null:
            self.assertEqual(platform.pick_rate(REG["models"][MOTION], r["tier"], None),
                             max(later_null + [r], key=lambda x: x["read"]))

    def test_seed_never_overwrites(self):
        code, _ = run_cli(preflight, ["ledger", "--run", str(self.run), "--model", MOTION,
                                      "--job", "j1", "--seconds", "8", "--status", "done", "--brand", "other"])
        self.assertEqual(code, 0)
        rj = json.loads((self.run / "run.json").read_text())
        self.assertEqual(rj["brand"], "_fixture")
        self.assertEqual(rj["format"], "fixture-format")

    def test_unknown_model_is_bad_input(self):
        code, _ = run_cli(preflight, ["ledger", "--run", str(self.run), "--model", "not_a_model",
                                      "--job", "j", "--seconds", "1", "--status", "done"])
        self.assertEqual(code, 3)


class Provider(unittest.TestCase):
    def test_clean_env_falls_back(self):
        with env():
            name, _, why = platform.resolve_provider()
        self.assertEqual(name, FALLBACK)
        self.assertIn("no conditions — the fallback", why)

    def test_claudecode_and_key_is_keyed_provider(self):
        with env(CLAUDECODE="1", **{KEY_ENV: "x"}):
            name, _, why = platform.resolve_provider()
        self.assertEqual(name, KEYED)
        self.assertIn(f"{KEY_ENV} in env", why)

    def test_claudecode_only_is_session_provider(self):
        with env(CLAUDECODE="1"):
            name, _, _ = platform.resolve_provider()
        self.assertEqual(name, SESSION_ONLY)

    def test_vault_key_counts(self):
        with env(CLAUDECODE="1"):
            sys.modules["daemn_keys"] = types.SimpleNamespace(key=lambda name, required=False: "secret")
            name, _, why = platform.resolve_provider()
        self.assertEqual(name, KEYED)
        self.assertIn(f"{KEY_ENV} in vault", why)

    def test_flag_beats_env(self):
        with env(CLAUDECODE="1", AI_VIDEO_PROVIDER=SESSION_ONLY, **{KEY_ENV: "x"}):
            self.assertEqual(platform.resolve_provider()[0], SESSION_ONLY)
            self.assertEqual(platform.resolve_provider(FALLBACK)[0], FALLBACK)

    def test_unknown_forced_provider_is_bad_input(self):
        with env(AI_VIDEO_PROVIDER="nope"):
            code, _ = run_cli(platform, [])
        self.assertEqual(code, 3)

    def test_cli_plan_and_confirm(self):
        with env():
            code, out = run_cli(platform, ["--provider", FALLBACK, "--batch", str(FIX / "batch-good.json"), "--yes"])
            self.assertEqual(code, 0, out)
            self.assertIn(f"provider: {FALLBACK}", out)
            self.assertIn(f"S3 · motion · {MOTION} · fast/1080p", out)
            self.assertIn("TOTAL", out)
            code, out = run_cli(platform, ["--provider", FALLBACK, "--batch", str(FIX / "batch-good.json"),
                                           "--json", "--yes"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["plan"]["count"], 3)
            code, out = run_cli(platform, ["--provider", KEYED, "--batch", str(FIX / "batch-good.json"), "--yes"])
            self.assertEqual(code, 2, out)
            self.assertIn("REFUSED", out)
            code, out = run_cli(platform, ["--provider", KEYED, "--batch", str(FIX / "batch-good-fal.json"), "--yes"])
            self.assertEqual(code, 0, out)
            self.assertIn(f"motion · {KEYED_MOTION}", out)

    def test_confirm_off_never_asks(self):
        with env(), contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(platform.confirm({"confirm": False}, yes=False))
            self.assertFalse(platform.confirm({"confirm": True}, yes=False))
            self.assertTrue(platform.confirm({"confirm": True}, yes=True))
        with env(AI_VIDEO_CONFIRM="1"), contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(platform.confirm({"confirm": False}, yes=False))


class Registry(unittest.TestCase):
    def test_no_slugs_in_python(self):
        words = set(REG["models"]) | set(REG["providers"])
        for f in ("platform.py", "preflight.py", "test_preflight.py"):
            src = (HERE / f).read_text()
            for w in words:
                self.assertIsNone(re.search(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", src),
                                  f"{w} named in {f}")

    def test_defaults_are_real_models(self):
        for pname, prov in REG["providers"].items():
            for station, slug in prov["stations"].items():
                if slug is None:
                    continue
                self.assertIn(slug, REG["models"], f"{pname}.{station}")
                model = REG["models"][slug]
                # most models belong to one provider family; a pseudo-model
                # called directly on its own API lists every family allowed
                # to use it in "used_by" instead of matching family exactly
                allowed = {model["provider"], *model.get("used_by", [])}
                self.assertIn(prov["family"], allowed, f"{pname}.{station}")
                self.assertIn(station, REG["stations"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
