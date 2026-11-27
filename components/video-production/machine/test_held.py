#!/usr/bin/env python3
"""Changes held for review are written and not live (the logic layer, 2026-11-18): every switch is off, every item
shows a before and an after, and the held code acts on nothing while its switch is off.

    /usr/bin/python3 machine/test_held.py
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"test_hd_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


H = load("held")
HV = load("hook_variations")

PLAN = {"hooks": [{"id": "Opening 1", "take": "control", "text": "It used to look like this.", "opener_scene": "S1"}],
        "scenes": [{"id": "S1", "to_camera": True, "opens": True, "voice": "It used to look like this."},
                   {"id": "S2", "to_camera": True, "voice": "And then I found out why."},
                   {"id": "S3", "to_camera": True, "voice": "You don't have the problem you think you have. It is something else."},
                   {"id": "S4", "to_camera": False, "voice": "Three weeks later it was gone."},
                   {"id": "S5", "to_camera": True, "voice": "I tried four of them before this one worked."},
                   {"id": "S6", "to_camera": True, "kind": "endcard", "voice": "You can get yours now."}]}


class Held(unittest.TestCase):
    def test_nothing_held_is_live(self):
        self.assertEqual(set(H.items()), {"hooks-from-the-body", "cast-by-audience", "lessons-into-prompts"})
        for name, row in H.items().items():
            self.assertFalse(H.on(name), name)
            self.assertIsNone(row["ruled"], name)

    def test_every_item_shows_a_before_and_an_after(self):
        for name, row in H.items().items():
            for k in ("decision", "code", "before", "after", "source"):
                self.assertTrue(str(row.get(k) or "").strip(), f"{name}.{k}")
            self.assertNotEqual(row["before"], row["after"])

    def test_an_item_nobody_listed_is_off(self):
        self.assertFalse(H.on("something-else"))
        self.assertEqual(H.item("something-else"), {})


class HooksFromTheBody(unittest.TestCase):
    def test_lines_that_can_open_the_ad_are_proposed_in_the_opening_shape(self):
        rows = HV.body_openings(PLAN)
        self.assertEqual([r["opener_scene"] for r in rows], ["S3", "S5"])
        self.assertEqual(rows[0]["text"], "You don't have the problem you think you have.", "the first sentence, word for word")
        for r in rows:
            self.assertTrue(r["from_body"])
            self.assertEqual(r["take"], "a line already in the body, moved to the front")
            self.assertIn("stands on its own", r["why"])
            self.assertTrue(r["id"].startswith("Body opening "))

    def test_what_never_qualifies(self):
        got = {r["opener_scene"] for r in HV.body_openings(PLAN, limit=9)}
        self.assertNotIn("S1", got, "the control's own opening")
        self.assertNotIn("S2", got, "a line that leans on the one before it")
        self.assertNotIn("S4", got, "a line nobody says on camera has no clip of its own to move")
        self.assertNotIn("S6", got, "an end card is not a line")

    def test_the_plan_is_only_read(self):
        before = json.dumps(PLAN, sort_keys=True)
        HV.body_openings(PLAN)
        self.assertEqual(json.dumps(PLAN, sort_keys=True), before)

    def test_writing_them_into_a_run_is_refused_while_held(self):
        run = Path(tempfile.mkdtemp())
        (run / "plan.json").write_text(json.dumps(PLAN))
        with self.assertRaises(ValueError) as e:
            HV.apply_body_openings(run)
        self.assertIn("held for review", str(e.exception))
        self.assertEqual(json.loads((run / "plan.json").read_text()), PLAN, "nothing was written")


if __name__ == "__main__":
    unittest.main()
