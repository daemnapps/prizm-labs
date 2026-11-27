#!/usr/bin/env python3
"""One source for how many takes a clip gets and which take is kept (the logic layer, 2026-11-18).

    /usr/bin/python3 machine/test_takes.py
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"test_tk_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


T = load("takes")
REG = json.loads((HERE / "providers.json").read_text())
V2 = json.loads((HERE / "v2.json").read_text())


class OneCount(unittest.TestCase):
    def test_the_number_is_stated_in_one_place(self):
        route = REG["direct"]["clip_route"]
        self.assertIn("attempts", route)
        self.assertNotIn("takes", route, "the route's own copy is gone")
        self.assertNotIn("max_tries", route)
        self.assertNotIn("takes", V2["clips"], "v2.json no longer states a take count")
        self.assertNotIn("max_tries", V2["clips"])

    def test_one_paid_take_on_a_press_and_in_the_automatic_run(self):
        # owner ruling 2026-11-20: one paid take per clip, never an automatic second take
        self.assertEqual(T.counts("press"), {"takes": 1, "max_tries": 1})
        self.assertEqual(T.counts("automatic"), {"takes": 1, "max_tries": 1})
        self.assertEqual(T.expected(), {"low": 1.0, "likely": 1.0, "high": 1.0})
        with mock.patch.object(T, "ONE_PAID_TAKE", False):                         # the registry's own numbers
            self.assertEqual(T.counts("automatic"), {"takes": 1, "max_tries": 3})   # VIDEO-RULINGS V34
        with self.assertRaises(ValueError):
            T.counts("whenever")

    def test_every_reader_gets_the_same_numbers(self):
        oc = load("clips_run")
        cfg = oc.route_cfg()
        self.assertEqual((cfg["takes"], cfg["max_tries"]), (1, 1))                  # a press on the board
        budget = load("budget")
        self.assertEqual(budget.CLIP_TRIES, {k: T.expected()[k] for k in ("low", "likely", "high")})
        self.assertEqual(load("shot_route").RETRY, T.expected()["likely"])
        self.assertEqual(T.expected()["high"], float(T.counts("automatic")["max_tries"]),
                         "the budget's high figure is the cap, not a number of its own")

    def test_the_automatic_run_lays_its_count_over_the_route(self):
        rv2 = load("run_v2")
        m = rv2._patch_clips(load("clips_run"))
        c = m.route_cfg()
        self.assertEqual((c["takes"], c["max_tries"]), (1, 1))                      # one paid take (2026-11-20)

    def test_a_registry_with_no_block_is_refused_by_name(self):
        with self.assertRaises(SystemExit) as e:
            T.rule({"direct": {"clip_route": {}}})
        self.assertIn("clip_route.attempts", str(e.exception))

    def test_an_older_registry_keeps_meaning_what_it_said(self):
        old = {"direct": {"clip_route": {"takes": 1, "max_tries": 2}}}
        with mock.patch.object(T, "ONE_PAID_TAKE", False):
            self.assertEqual(T.counts("press", old), {"takes": 1, "max_tries": 2})

    @mock.patch.object(T, "ONE_PAID_TAKE", False)
    def test_likely_is_the_runs_own_average_once_it_has_clips(self):
        run = Path(tempfile.mkdtemp())
        (run / "clips").mkdir()
        self.assertNotIn("measured", T.expected(run))
        led = {f"G0{i}-C1": {"status": "done", "takes": [{}] * n} for i, n in enumerate((1, 2, 3), 1)}
        (run / "clips" / "ledger.json").write_text(json.dumps(led))
        got = T.expected(run)
        self.assertTrue(got["measured"])
        self.assertEqual(got["likely"], 2.0)


class OneKeepRule(unittest.TestCase):
    def take(self, n, score, ok, stop=0.0, file=None):
        return {"take": n, "score": score, "pass": ok, "stop_power": stop, "file": file}

    def test_a_passing_take_wins_the_highest_score_then_stop_power_then_the_earlier(self):
        a, b, c = self.take(1, 8.0, True, 3), self.take(2, 8.0, True, 5), self.take(3, 9.5, False)
        self.assertIs(T.pick([a, b, c]), b)
        self.assertIs(T.pick([self.take(1, 8.0, True), self.take(2, 8.0, True)])["take"], 1)
        self.assertIsNone(T.pick([c]))

    def test_none_passed_keeps_the_best_attempt_flagged_a_tie_to_the_later(self):
        d = Path(tempfile.mkdtemp())
        f1, f2 = d / "t1.mp4", d / "t2.mp4"
        f1.write_bytes(b"x"); f2.write_bytes(b"x")
        a, b = self.take(1, 6.0, False, file=str(f1)), self.take(2, 6.0, False, file=str(f2))
        kept, below = T.keep([a, b])
        self.assertIs(kept, b)
        self.assertTrue(below)
        self.assertEqual(T.keep([self.take(1, 6.0, False)]), (None, True), "no attempt made a file: nothing to keep")
        kept, below = T.keep([a, self.take(2, 7.0, True, file=str(f2))])
        self.assertFalse(below)

    def test_the_clip_runner_keeps_by_this_rule(self):
        oc = load("clips_run")
        d = Path(tempfile.mkdtemp())
        f = d / "t1.mp4"
        f.write_bytes(b"x")
        takes = [self.take(1, 7.0, True, 2), self.take(2, 7.0, True, 4), self.take(3, 5.0, False, file=str(f))]
        self.assertEqual(oc.pick(takes), T.pick(takes))
        self.assertEqual(oc.best_attempt(takes), T.best_attempt(takes))

    def test_the_rule_reads_as_one_sentence(self):
        self.assertIn("one paid take of every clip, never sent again on its own", T.said("automatic"))
        with mock.patch.object(T, "ONE_PAID_TAKE", False):
            self.assertIn("another only when one fails, 3 at most", T.said("automatic"))
            self.assertIn("one per press", T.said("press"))


if __name__ == "__main__":
    unittest.main()
