#!/usr/bin/env python3
"""python3 machine/test_vp1_pack_gates.py — from any cwd. Stdlib unittest only.

SI-156 (video pack gates): a talking clip counts toward its line, only the
passing parity word ships (a cut-off line never does), and the board opens
the plan the runner wrote. Offline, temp runs only."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


preflight = load("preflight")
board = load("board")


def run_cli(mod, argv) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = mod.main(argv)
    return code, buf.getvalue()


class TempRun(unittest.TestCase):
    """A run with one line and one talking clip that claims it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-packgates-"))
        self.run = self.tmp / "sample-run"
        (self.run / "batches").mkdir(parents=True)
        (self.run / "lines.json").write_text(json.dumps({"L1": "this cream changed my skin"}))
        (self.run / "batches" / "batch-1.json").write_text(json.dumps({"items": [
            {"id": "T1", "kind": "talking", "lines": ["L1"]}]}))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def parity(self, word: str) -> None:
        preflight.verdict(self.run, "T1", "parity",
                          {"verdict": word, "heard": "this cream changed", "match": 0.8})


class TalkingCoversItsLine(TempRun):
    def test_talking_item_claims_its_line(self):
        reg = preflight.platform.registry()
        items = preflight.other_batches(self.run)
        self.assertEqual(preflight.claims_in(items, reg), {"L1": ["T1"]})

    def test_talking_pass_covers_and_ships(self):
        self.parity("PASS")
        uncovered, dupes, not_shippable, concept_weak = preflight.coverage(self.run)
        self.assertEqual((uncovered, dupes, not_shippable, concept_weak), ([], [], [], []))
        code, out = run_cli(preflight, ["coverage", "--run", str(self.run)])
        self.assertEqual(code, 0, out)

    def test_talking_with_no_parity_is_not_shippable(self):
        uncovered, _, not_shippable, _ = preflight.coverage(self.run)
        self.assertEqual(uncovered, [])
        self.assertEqual(not_shippable, ["not shippable: no parity verdict — run lineparity (T1)"])


class OnlyPassShips(TempRun):
    def test_cut_off_without_order_names_the_remake_skill(self):
        self.parity("CUT_OFF")
        uncovered, _, not_shippable, _ = preflight.coverage(self.run)
        self.assertEqual(uncovered, [])
        self.assertEqual(not_shippable,
                         ["not shippable: line cut off — run the remake-clip skill (T1)"])
        self.assertIn("remake", not_shippable[0])

    def test_cut_off_names_the_newest_remake_order(self):
        self.parity("CUT_OFF")
        remakes = self.run / "remakes"
        remakes.mkdir()
        for n in (1, 2, 10):
            (remakes / f"T1-r{n}.json").write_text("{}")
        (remakes / "T10-r99.json").write_text("{}")   # another item's order
        _, _, not_shippable, _ = preflight.coverage(self.run)
        self.assertEqual(not_shippable,
                         [f"not shippable: line cut off — remake ({remakes / 'T1-r10.json'}) (T1)"])
        code, out = run_cli(preflight, ["coverage", "--run", str(self.run)])
        self.assertEqual(code, 2, out)
        self.assertIn("line cut off — remake", out)

    def test_unknown_word_is_not_shippable(self):
        self.parity("MAYBE")
        _, _, not_shippable, _ = preflight.coverage(self.run)
        self.assertEqual(not_shippable, ["not shippable: parity verdict MAYBE (T1)"])

    def test_missing_word_is_not_shippable(self):
        preflight.verdict(self.run, "T1", "parity", {"heard": "x", "match": 1.0})
        _, _, not_shippable, _ = preflight.coverage(self.run)
        self.assertEqual(not_shippable, ["not shippable: parity verdict None (T1)"])

    def test_flag_keeps_its_message(self):
        self.parity("FLAG")
        _, _, not_shippable, _ = preflight.coverage(self.run)
        self.assertEqual(not_shippable,
                         ["not shippable: says other words (heard: 'this cream changed') (T1)"])


class BoardOpensTheRunnersPlan(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-board-"))
        self.saved = board.RUN
        board.RUN = self.tmp

    def tearDown(self):
        board.RUN = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_runner_shaped_run(self):
        (self.tmp / "plan.json").write_text(json.dumps({"brand": "x"}))
        self.assertEqual(board.plan_path(), self.tmp / "plan.json")
        self.assertEqual(board.load(), {"brand": "x"})

    def test_run_plan_wins_over_old_layout(self):
        (self.tmp / "out").mkdir()
        (self.tmp / "out" / "plan.json").write_text("{}")
        (self.tmp / "plan.json").write_text("{}")
        self.assertEqual(board.plan_path(), self.tmp / "plan.json")

    def test_old_run_falls_back_to_out(self):
        (self.tmp / "out").mkdir()
        (self.tmp / "out" / "plan.json").write_text("{}")
        self.assertEqual(board.plan_path(), self.tmp / "out" / "plan.json")


if __name__ == "__main__":
    unittest.main()
