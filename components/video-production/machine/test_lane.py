#!/usr/bin/env python3
"""How the whole ad is made: one rule, with its reason, and one answer for every reader (the logic layer, 2026-11-18).

    /usr/bin/python3 machine/test_lane.py
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"test_ln_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


L = load("lane")


def footage(**plans):
    return {"scenes": {k: {"plan": v} for k, v in plans.items()}}


class Default(unittest.TestCase):
    def test_a_creator_route_is_a_creator_piece(self):
        got = L.default("single-presenter", "creator", footage(S1="cut"), "phone-ugc")
        self.assertEqual(got["lane"], "creator")
        self.assertIn("a person films it", got["why"])

    def test_a_format_made_one_way_by_its_own_definition(self):
        got = L.default("text-thread", "ai", footage(S1="cut"), "phone-ugc")
        self.assertEqual(got["lane"], "ai")
        self.assertIn("drawn in code", got["why"])

    def test_a_style_that_is_not_filmed_is_made_whatever_we_own(self):
        got = L.default("song-ad", "ai", footage(S1="cut", S2="cut"), "family-3d")
        self.assertEqual(got["lane"], "ai")
        self.assertIn("family-3d", got["why"])

    def test_the_footage_decision_picks_between_made_mixed_and_ours(self):
        self.assertEqual(L.default("narrator-montage", "ai", footage(S1="generate", S2="generate"), "phone-ugc")["lane"], "ai")
        mix = L.default("narrator-montage", "ai", footage(S1="cut", S2="generate", S3="made"), "phone-ugc")
        self.assertEqual(mix["lane"], "mix")
        self.assertIn("passed 1 of 2 shot(s)", mix["why"])
        self.assertEqual(L.default("narrator-montage", "ai", footage(S1="cut", S2="cut"), None)["lane"], "real")

    def test_someone_talking_to_camera_is_never_all_ours(self):
        got = L.default("single-presenter", "ai", footage(S1="cut", S2="presenter"), "phone-ugc")
        self.assertEqual(got["lane"], "mix")
        self.assertIn("never the library's", got["why"])

    def test_no_footage_decision_is_said_not_assumed(self):
        got = L.default("narrator-montage", "ai", None, "phone-ugc")
        self.assertEqual(got["lane"], "ai")
        self.assertIn("no footage decision is on file", got["why"])

    def test_every_call_carries_a_reason_and_who_made_it(self):
        for args in ((None, None, None, None), ("x", "creator", None, None), ("x", "ai", footage(S1="cut"), None)):
            got = L.default(*args)
            self.assertIn(got["lane"], L.lanes())
            self.assertTrue(got["why"].strip())
            self.assertEqual(got["by"], L.BY)

    def test_read_off_the_writing_run(self):
        w = Path(tempfile.mkdtemp())
        (w / "stages").mkdir()
        (w / "run.json").write_text(json.dumps({"format_id": "narrator-montage", "production_route": "ai", "style_id": "phone-ugc"}))
        (w / "stages" / "storyboard-footage.json").write_text(json.dumps(footage(S1="cut", S2="generate")))
        got = L.for_writing(w)
        self.assertEqual(got["lane"], "mix")
        self.assertEqual(got["inputs"]["footage"], {"cut": 1, "make": 1, "presenter": 0, "other": 0})


class OneAnswerForEveryReader(unittest.TestCase):
    """The pack read "ai" and the Studio's next-step tools read "real" for the same production with no lane."""

    def test_a_recorded_lane_stands_with_who_chose_it(self):
        self.assertEqual(L.of({"lane": "mix"}), {"lane": "mix", "why": "picked at Produce", "by": L.PICKED})
        got = L.of({"lane": "ai", "lane_why": "the footage decision passed none", "lane_by": L.BY})
        self.assertEqual((got["why"], got["by"]), ("the footage decision passed none", L.BY))

    def test_a_production_with_no_lane_gets_one_answer(self):
        for brief in ({}, None, {"lane": None}, {"lane": "nonsense"}):
            got = L.of(brief)
            self.assertEqual(got["lane"], "real")
            self.assertIn("before the way of making was recorded", got["why"])

    def test_a_persons_pick_wins_and_the_chains_call_rides_beside_it(self):
        w = Path(tempfile.mkdtemp())
        (w / "run.json").write_text(json.dumps({"production_route": "ai"}))
        got = L.chosen("real", w)
        self.assertEqual((got["lane"], got["by"]), ("real", L.PICKED))
        self.assertEqual(got["chain_call"]["lane"], "ai")
        self.assertEqual(L.chosen(None, w)["by"], L.BY)
        self.assertNotIn("chain_call", L.chosen("ai", w))

    def test_the_settings_are_draft_and_name_no_brand(self):
        s = L.settings()
        self.assertEqual(s["status"], "draft")
        self.assertEqual(set(s["lanes"]), {"ai", "mix", "real", "creator"})
        for row in (v for k, v in s["by_format"].items() if not k.startswith("_")):
            self.assertIn(row["lane"], s["lanes"])
            self.assertEqual(row["status"], "draft")


if __name__ == "__main__":
    unittest.main()
