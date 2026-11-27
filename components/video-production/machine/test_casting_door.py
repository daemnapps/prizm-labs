#!/usr/bin/env python3
"""Production asks the casting door who plays a role before it binds or makes anyone (the logic layer, 2026-11-18).
No model, no network: the door's answer is a fake, the workspace a temp folder.

    /usr/bin/python3 machine/test_casting_door.py
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_sp = importlib.util.spec_from_file_location("t_cd_auto_elements", HERE / "auto_elements.py")
AE = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(AE)


def answer(covered, pid=None, why="the record says expert", near=()):
    return {"covered": covered, "person": {"id": pid} if pid else None, "why": why,
            "gap": None if covered else {"near": list(near)}, "problems": []}


class Asking(unittest.TestCase):
    def test_the_role_is_the_briefs_own_words(self):
        self.assertEqual(AE.role_words({"role": "the expert who explains the routine", "name": "LEAD"}),
                         "the expert who explains the routine")
        self.assertEqual(AE.role_words({"name": "LEAD", "identity_block": "An expert in their forties. Short hair; kind eyes."}),
                         "LEAD An expert in their forties")

    def test_the_door_is_asked_with_that_role(self):
        seen = {}

        def who(brand, role, start=None):
            seen.update(brand=brand, role=role)
            return answer(True, "person-a")
        got = AE.ask_casting("x", {"role": "expert"}, who_plays=who)
        self.assertEqual(seen, {"brand": "x", "role": "expert"})
        self.assertTrue(got["covered"])
        self.assertEqual(got["person"]["id"], "person-a")

    def test_a_door_that_cannot_answer_never_stops_the_step(self):
        def broken(brand, role, start=None):
            raise SystemExit("no cast bank for this brand")
        got = AE.ask_casting("x", {"role": "expert"}, who_plays=broken)
        self.assertFalse(got["covered"])
        self.assertIn("could not answer", got["problem"])
        self.assertEqual(AE.cast_from(got, "x")[0], None)


class Acting(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp(prefix="cd_ws_"))
        self.saved = (AE.WS, AE.CALLS, AE._complete)
        AE.WS = self.ws
        AE.CALLS = self.ws / "runs" / "decisions" / "calls.jsonl"

    def tearDown(self):
        AE.WS, AE.CALLS, AE._complete = self.saved

    def folder(self, pid):
        d = AE.EP.casting_home("x", pid, self.ws)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def test_a_covered_role_with_a_ready_sheet_is_cast_from_the_bank(self):
        self.folder("person-a")
        AE._complete = lambda folder, kind: True
        got, why = AE.cast_from({"asked": "expert", "covered": True, "person": {"id": "person-a"}, "why": "Person A (roster) — the record says expert"}, "x")
        self.assertEqual(got, "person-a")
        self.assertIn("the casting door", why)

    def test_a_covered_role_whose_person_is_not_ready_is_flagged_and_the_run_carries_on(self):
        self.folder("person-a")
        AE._complete = lambda folder, kind: False
        got, why = AE.cast_from({"asked": "expert", "covered": True, "person": {"id": "person-a"}, "why": ""}, "x")
        self.assertIsNone(got)
        self.assertIn("not ready for production", why)
        self.assertIn("carries on as before", why)

    def test_nobody_banked_says_so_with_the_nearest(self):
        got, why = AE.cast_from({"asked": "expert", "covered": False, "person": None, "why": "",
                                 "gap": {"near": ["Person B (roster) — only its describing fields say expert"]}}, "x")
        self.assertIsNone(got)
        self.assertIn("nobody in the bank is recorded as playing this role", why)
        self.assertIn("Person B", why)


class TheStepAsksFirst(unittest.TestCase):
    """The automatic elements step: the door before the same-swipe match, and before a new face is ever made."""

    def setUp(self):
        self.ws = Path(tempfile.mkdtemp(prefix="cd_step_"))
        self.saved = {k: getattr(AE, k) for k in ("WS", "CALLS", "is_auto", "match_banked", "make_person", "_complete", "best_look")}
        self.saved_ec = (AE.EC.sheet, AE.EC.bind, AE.EC.resolve_teardown, AE.EC.teardown_of)
        AE.WS, AE.CALLS = self.ws, self.ws / "runs" / "decisions" / "calls.jsonl"
        AE.is_auto = lambda: True
        self.calls = []
        AE.match_banked = lambda brand, it, td: (self.calls.append("match") or (None, ""))
        AE.make_person = lambda *a, **k: (self.calls.append("make") or "new-face")
        AE._complete = lambda folder, kind: True
        AE.best_look = lambda folder, want: (None, 0.0)
        self.td = self.ws / "td"
        self.td.mkdir()
        self.brief = self.ws / "brief.md"
        doc = {"cast": [{"id": "LEAD", "name": "LEAD", "bank_id": "NEW", "role": "expert", "identity_block": "An expert."}],
               "scenes": [], "world": []}
        self.brief.write_text("# b\n\n```json\n" + json.dumps(doc) + "\n```\n")
        item = {"kind": "person", "id": "LEAD", "bank_id": "person-a", "folder": "runs/ai-elements/x/casting/person-a",
                "scenes": [], "speaks": [], "looks": [], "missing": ["NEW"]}
        self.sheets = [{"to_make": [item], "items": [item], "brief_gaps": []}, {"to_make": [], "items": [item], "brief_gaps": []}]
        AE.EC.sheet = lambda *a, **k: self.sheets.pop(0) if len(self.sheets) > 1 else self.sheets[0]
        self.bound = {}
        AE.EC.bind = lambda brief, pairs: self.bound.update(pairs)
        AE.EC.resolve_teardown = lambda p: self.td
        AE.EC.teardown_of = lambda *a: self.td
        (AE.EP.casting_home("x", "person-a", self.ws)).mkdir(parents=True)
        self.run = self.ws / "runs" / "video-production" / "x" / "x_p_brief-0001"

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(AE, k, v)
        AE.EC.sheet, AE.EC.bind, AE.EC.resolve_teardown, AE.EC.teardown_of = self.saved_ec

    def go(self, who):
        return AE.run(self.brief, "x", self.run, manifest=lambda *a: (True, []), confirm=lambda run, by: {"fingerprint": "f"},
                      who_plays=who)

    def test_a_role_the_bank_covers_never_gets_a_new_face(self):
        res = self.go(lambda brand, role, start=None: answer(True, "person-a", "Person A (roster) — the record says expert"))
        self.assertEqual(self.bound, {"LEAD": "person-a"})
        self.assertEqual(self.calls, [], "neither the same-swipe match nor a new face was reached")
        self.assertEqual(res["made"], [])
        trail = json.loads((self.run / "run.json").read_text())["trail"]
        self.assertEqual(trail[0]["decision"], "who plays LEAD")
        self.assertEqual(trail[0]["by"], "the casting door")
        self.assertIn("`person-a` from the cast bank", trail[0]["choice"])

    def test_a_gap_runs_the_steps_as_before_and_the_doors_answer_is_kept(self):
        res = self.go(lambda brand, role, start=None: answer(False, near=["nobody close"]))
        self.assertEqual(self.calls, ["match", "make"])
        self.assertEqual(self.bound, {"LEAD": "new-face"})
        self.assertEqual(res["made"], ["person new-face"])
        trail = json.loads((self.run / "run.json").read_text())["trail"]
        self.assertIn("nobody banked for the role", trail[0]["choice"])
        self.assertIn("nobody in the bank is recorded as playing this role", trail[0]["why"])


class HeldForReview(unittest.TestCase):
    """Cast by audience is written and not live: off, the step behaves exactly as it does without it."""

    def test_the_switch_is_off(self):
        self.assertFalse(AE.held_on("cast-by-audience"))
        self.assertFalse(AE.held_on("no-such-item"))

    def test_the_lead_is_whoever_opens_the_ad_else_whoever_is_in_most_of_it(self):
        items = [{"kind": "person", "id": "A", "scenes": ["S2", "S3", "S4"]}, {"kind": "person", "id": "B", "scenes": ["S1"]},
                 {"kind": "prop", "id": "jar", "scenes": ["S1", "S2", "S3", "S4"]}]
        self.assertEqual(AE.lead_of(items, {"scenes": [{"id": "S1", "opens": True}]}), "B")
        self.assertEqual(AE.lead_of(items, {"scenes": [{"id": "S1"}]}), "A")
        self.assertIsNone(AE.lead_of([], {}))

    def test_the_audience_answer_names_the_lead_and_the_authority_on_file(self):
        def fa(brand, avatar, start=None):
            return {"roster": [{"id": "person-c", "name": "Person C"}, {"id": "person-d", "name": "Person D"}], "authority": [{"id": "person-a"}],
                    "covered": True, "why": "1 authority, 2 roster"}
        got = AE.audience_cast("x", {"piece": {"avatar": "the-avatar"}}, for_avatar=fa)
        self.assertTrue(got["covered"])
        self.assertEqual(got["person"]["id"], "person-c")
        self.assertEqual(got["authority"], ["person-a"])
        self.assertIn("someone who looks like the audience", got["why"])
        self.assertIn("figures of authority on file for the same avatar: person-a", got["why"])

    def test_no_avatar_or_nobody_for_it_is_a_gap_not_a_guess(self):
        self.assertFalse(AE.audience_cast("x", {"piece": {}})["covered"])
        got = AE.audience_cast("x", {"piece": {"avatar": "a"}}, for_avatar=lambda b, a, s=None: {"roster": [], "authority": [], "why": "nobody"})
        self.assertFalse(got["covered"])
        self.assertIsNone(got["person"])


if __name__ == "__main__":
    unittest.main()
