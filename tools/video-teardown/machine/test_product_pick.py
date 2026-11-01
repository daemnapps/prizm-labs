"""v2 product decision: lane declared, paid keeps in-use funnels, ties stop."""
import json
import tempfile
import unittest
from pathlib import Path

import product_pick as P


def brand(root, products, funnels, heroes=None):
    b = root / "brands" / "b"
    (b / "products").mkdir(parents=True)
    (b / "web" / "funnels").mkdir(parents=True)
    for p in products:
        (b / "products" / f"{p}.md").write_text(p)
    (b / "web" / "funnels" / "funnels.json").write_text(json.dumps({"funnels": funnels}))
    if heroes is not None:
        (b / "products" / "heroes.json").write_text(json.dumps(heroes))


class Pick(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.old = P.REPO
        P.REPO = Path(self.t.name)

    def tearDown(self):
        P.REPO = self.old
        self.t.cleanup()

    def test_no_lane_stops(self):
        brand(P.REPO, ["a", "b"], [])
        self.assertIsNone(P.decide("b", None)[0])

    def test_paid_keeps_only_in_use_funnel(self):
        brand(P.REPO, ["a", "b"], [{"product": "a", "status": "in use"}, {"product": "b", "status": "off"}])
        self.assertEqual(P.decide("b", "paid")[0], "a")

    def test_paid_tie_is_decided_by_the_ad(self):
        brand(P.REPO, ["x-face", "x-body"], [{"product": "x-face", "status": "in use"},
                                              {"product": "x-body", "status": "in use"},
                                              {"product": "x-body", "status": "in use"}])
        run = P.REPO / "run"
        (run / "stages").mkdir(parents=True)
        (run / "stages" / "1b-audience.md").write_text("dark spots on her face, face routine, face")
        self.assertEqual(P.decide("b", "paid", run)[0], "x-face")      # the ad is about the face
        self.assertEqual(P.decide("b", "paid")[0], "x-body")           # no ad text: more live funnels wins

    def test_lane_never_changes_the_product(self):
        # V1 (2026-10-20): organic and paid are the same video — the lane changes only the ask.
        # Replaces the 2026-10-18 test that organic took the brand's organic_hero instead.
        brand(P.REPO, ["a", "b"], [{"product": "a", "status": "in use"}], heroes={"organic_hero": "b"})
        self.assertEqual(P.decide("b", "paid")[0], "a")
        self.assertEqual(P.decide("b", "organic")[0], "a")

    def test_no_live_funnel_falls_to_the_heroes_on_both_lanes(self):
        brand(P.REPO, ["a", "b"], [], heroes={"heroes": ["b"]})
        self.assertEqual(P.decide("b", "organic")[0], "b")
        self.assertEqual(P.decide("b", "paid")[0], "b")
        (P.REPO / "brands" / "b" / "products" / "heroes.json").write_text("{}")
        self.assertIsNone(P.decide("b", "organic")[0])

    def test_lane_of(self):
        brand(P.REPO, ["a"], [])
        self.assertEqual(P.lane_of("b", "organic")[0], "organic")
        self.assertIsNone(P.lane_of("b", None)[0])


if __name__ == "__main__":
    unittest.main()
