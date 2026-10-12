#!/usr/bin/env python3
"""Status words in image-production's models.json — SI-74 (alternate model routed).

    python3 tools/image-production/tests/test_model_status.py

Components rule 6 (the developer, 2026-10-07, triage page 15, Option A): `status`
holds only draft / approved / deprecated; any other meaning gets its own
field. `gemini-image-object` was `status: alternate`; it is now
`status: approved` plus `routed: false`, and the route still never picks it
unless a caller forces it by name. Stdlib `unittest`; no key, no network, no
imaging library, nothing written.
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent))                  # APPEND — never insert at 0
import image_production as IP                      # noqa: E402

RULE_6 = {"draft", "approved", "deprecated"}
UNROUTED = "gemini-image-object"


class TestModelStatus(unittest.TestCase):

    def setUp(self):
        self.t = IP.route.table()

    def test_every_status_is_a_rule_6_word(self):
        entries = list(self.t["models"].items()) + [("judge", self.t["judge"])]
        for name, entry in entries:
            self.assertIn(entry["status"], RULE_6, name)

    def test_the_alternate_is_approved_and_not_routed(self):
        entry = self.t["models"][UNROUTED]
        self.assertEqual(entry["status"], "approved")
        self.assertIs(entry["routed"], False)

    def test_no_route_row_names_an_unrouted_model(self):
        for row in self.t["route"]:
            if row["model"] == "@forced":
                continue
            self.assertIsNot(self.t["models"][row["model"]].get("routed", True), False, row["model"])

    def test_unforced_requests_never_reach_the_unrouted_model(self):
        reqs = ({}, {"people": True}, {"people": False}, {"from_image": "/x.png"})
        for req in reqs:
            for people in (True, False, "maybe", None):
                name, _e, _w = IP.route.pick(req, {"purpose": {"id": "ad", "people": people}}, self.t)
                self.assertIsNot(self.t["models"][name].get("routed", True), False,
                                 "%r with purpose people=%r went to %s" % (req, people, name))
                self.assertNotEqual(name, UNROUTED)

    def test_a_forced_unrouted_model_still_resolves(self):
        name = IP.route.pick({"model": UNROUTED}, {"purpose": {"id": "ad", "people": None}}, self.t)[0]
        self.assertEqual(name, UNROUTED)


if __name__ == "__main__":
    unittest.main()
