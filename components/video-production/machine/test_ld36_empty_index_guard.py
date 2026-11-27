#!/usr/bin/env python3
"""LD-36 (empty index guard) — a REAL run on a brand with no footage index
refuses before any still or clip is made; generating every B-roll scene is
said out loud with --generate-all-broll. No network, no spend: the footage
module is a fake, no key is found, and the run is stopped right after the
footage step (the first thing past it, the run's clip-model check, raises).

    /usr/bin/python3 machine/test_ld36_empty_index_guard.py
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
BRIEF = FIX / "brief-v15.md"
BRAND = "_fixture"
SENTINEL = "ld36-past-the-footage-step"
NO_INDEX = "no footage index on this machine"


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"test_ld36_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


run = load("run")
footage = load("footage")


class PastFootage(Exception):
    """Raised by the first check after the footage step — the run got past it."""


def fake_footage(indexed: bool, raises: Exception | None = None):
    """The footage module's gate/report surface, deciding nothing from disk."""
    calls = {"gate": 0}

    def gate(plan, brand, **kw):
        calls["gate"] += 1
        if raises is not None:
            raise raises
        res = {"cut": [], "generate": [], "presenter": [], "other": [], "indexed": indexed}
        for s in plan.get("scenes") or []:
            role = footage.role_of(s)
            if role == "presenter":
                res["presenter"].append(s["id"])
            elif role == "broll":
                res["generate"].append(s["id"])
            else:
                res["other"].append(s["id"])
        return res

    return types.SimpleNamespace(gate=gate, report=footage.report, calls=calls)


@contextlib.contextmanager
def env():
    saved = dict(os.environ)
    saved_mod = sys.modules.get("daemn_keys")
    sys.modules["daemn_keys"] = types.SimpleNamespace(key=lambda name, required=False: "")
    os.environ["HOME"] = tempfile.mkdtemp(prefix="vp_ld36_nokeys_")
    os.environ["KEYS_NO_FALLBACK"] = "1"
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(saved)
        if saved_mod is None:
            sys.modules.pop("daemn_keys", None)
        else:
            sys.modules["daemn_keys"] = saved_mod


class EmptyIndexGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-ld36-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        cast = self.tmp / "cast" / "the-speaker"
        cast.mkdir(parents=True)
        shutil.copy2(FIX / "cast-root" / "lead" / "voice.json", cast / "voice.json")
        self.past = {"n": 0}

        def model_fault(pick, station):
            if pick == SENTINEL:
                self.past["n"] += 1
                raise PastFootage()
            return None
        self.addCleanup(setattr, run.mi, "model_fault", run.mi.model_fault)
        run.mi.model_fault = model_fault
        self.addCleanup(setattr, run, "_load", run._load)
        self.real_load = run._load

    def use(self, fake):
        real = self.real_load
        run._load = lambda name: fake if name == "footage" else real(name)
        return fake

    def args(self, *extra):
        return run.build_parser().parse_args([
            "start", str(BRIEF), "--brand", BRAND, "--format", "fixture-format",
            "--label", "ld36", "--bank", str(FIX / "bank.json"),
            "--runs-root", str(self.tmp / "runs"), "--cast-root", str(self.tmp / "cast"),
            "--banks", str(FIX / "banks"), "--provider", "higgsfield-ui", "--yes",
            "--composed", "--clip-model", SENTINEL, *extra])

    def start(self, *extra):
        out, err = io.StringIO(), io.StringIO()
        code = None
        with env(), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = run.cmd_start(self.args(*extra))
            except PastFootage:
                code = "past"
        return code, out.getvalue(), err.getvalue()

    def made(self):
        r = self.tmp / "runs" / "video-production" / BRAND / "ld36"
        batches = sorted((r / "batches").glob("*.json")) if (r / "batches").is_dir() else []
        media = [p for p in (r / "media").rglob("*") if p.is_file()] if (r / "media").is_dir() else []
        return batches, media, (r / "direct.json").exists()

    # (a)
    def test_empty_index_real_run_is_refused_and_nothing_is_made(self):
        fake = self.use(fake_footage(indexed=False))
        code, out, err = self.start()
        self.assertEqual(code, 2, out + err)
        self.assertEqual(fake.calls["gate"], 1)
        self.assertEqual(self.past["n"], 0, "the run went past the footage step")
        self.assertIn("REFUSED", err)
        self.assertIn(BRAND, err)
        self.assertIn(f"runs/asset-index/{BRAND}/", err)
        self.assertIn("--generate-all-broll", err)
        self.assertIn("S2", err)                         # the B-roll scene it would have generated
        self.assertIn("nothing was made", err)
        self.assertEqual(self.made(), ([], [], False))

    # (b)
    def test_empty_index_with_generate_all_broll_proceeds_past_the_footage_step(self):
        self.use(fake_footage(indexed=False))
        code, out, err = self.start("--generate-all-broll")
        self.assertEqual(code, "past", out + err)
        self.assertNotIn("REFUSED", err)
        self.assertIn("--generate-all-broll", out)
        self.assertIn(NO_INDEX, out)

    # (c)
    def test_an_indexed_brand_is_unchanged(self):
        self.use(fake_footage(indexed=True))
        code, out, err = self.start()
        self.assertEqual(code, "past", out + err)
        self.assertNotIn("REFUSED", err)
        self.assertNotIn("--generate-all-broll", out + err)
        self.assertNotIn(NO_INDEX, out)
        self.assertIn("footage: 0 B-roll scene(s) CUT from our footage", out)

    def test_an_empty_index_with_no_broll_to_make_is_not_refused(self):
        fake = fake_footage(indexed=False)
        gate = fake.gate
        fake.gate = lambda plan, brand, **kw: {**gate(plan, brand), "generate": []}
        self.use(fake)
        code, out, err = self.start()
        self.assertEqual(code, "past", out + err)
        self.assertNotIn("REFUSED", err)

    def test_no_footage_keeps_meaning_what_it_means(self):
        fake = self.use(fake_footage(indexed=False))
        code, out, err = self.start("--no-footage")
        self.assertEqual(code, "past", out + err)
        self.assertEqual(fake.calls["gate"], 0)
        self.assertNotIn("REFUSED", err)

    # (d)
    def test_dry_run_on_an_empty_index_passes_with_the_line_printed(self):
        self.use(fake_footage(indexed=False))
        code, out, err = self.start("--dry-run")
        self.assertEqual(code, "past", out + err)
        self.assertNotIn("REFUSED", err)
        self.assertIn(NO_INDEX, out)
        self.assertIn("a real run REFUSES here", out)
        self.assertIn("--generate-all-broll", out)

    # (e)
    def test_a_footage_step_that_raises_on_a_real_run_is_refused(self):
        self.use(fake_footage(indexed=False, raises=RuntimeError("drive not mounted")))
        code, out, err = self.start()
        self.assertEqual(code, 2, out + err)
        self.assertEqual(self.past["n"], 0)
        self.assertIn("the footage step could not run (RuntimeError: drive not mounted)", err)
        self.assertIn(f"runs/asset-index/{BRAND}/", err)
        self.assertIn("--generate-all-broll", err)
        self.assertEqual(self.made(), ([], [], False))

    def test_a_footage_step_that_raises_with_generate_all_broll_proceeds(self):
        self.use(fake_footage(indexed=False, raises=RuntimeError("drive not mounted")))
        code, out, err = self.start("--generate-all-broll")
        self.assertEqual(code, "past", out + err)
        self.assertNotIn("REFUSED", err)


class TheDoor(unittest.TestCase):
    def test_the_flag_is_on_start_and_the_door_says_it(self):
        a = run.build_parser().parse_args(["start", str(BRIEF), "--brand", BRAND, "--format", "f",
                                           "--label", "x", "--generate-all-broll"])
        self.assertTrue(a.generate_all_broll)
        a = run.build_parser().parse_args(["start", str(BRIEF), "--brand", BRAND, "--format", "f",
                                           "--label", "x"])
        self.assertFalse(a.generate_all_broll)
        self.assertTrue(a.footage)
        door = json.loads((HERE / "lab_door.json").read_text())
        self.assertEqual(door["bool_flags"]["generate_all_broll"], "--generate-all-broll")
        self.assertEqual(door["bool_flags"]["dry_run"], "--dry-run")


if __name__ == "__main__":
    unittest.main()
