"""shot_route follows SHOT-ROUTES.md: REAL first, then SWAP when the motion is the point, else AI."""
import unittest

import shot_route as R


class Routes(unittest.TestCase):
    def test_owned_footage_is_real_and_free(self):
        self.assertEqual(R.route({"owned_footage": True, "talks_to_camera": True, "seconds": 5})[:1], ("REAL",))
        self.assertEqual(R.route({"owned_footage": True})[2], 0.0)

    def test_talking_to_camera_is_ai_even_when_motion_matters(self):
        r = R.route({"talks_to_camera": True, "motion_is_the_point": True, "swipe_shot": "K1",
                     "clean_single_shot": True, "seconds": 5})
        self.assertEqual(r[0], "AI")

    def test_motion_with_a_clean_swipe_shot_is_a_swap(self):
        r = R.route({"motion_is_the_point": True, "swipe_shot": "K14", "clean_single_shot": True, "seconds": 4.2})
        self.assertEqual(r[0], "SWAP")
        self.assertGreater(r[2], 0)

    def test_no_swap_across_a_cut_or_without_a_product_slot(self):
        base = {"motion_is_the_point": True, "swipe_shot": "K2", "seconds": 4}
        self.assertEqual(R.route(dict(base, clean_single_shot=False))[0], "AI")
        self.assertEqual(R.route(dict(base, clean_single_shot=True, needs_product=True))[0], "AI")
        self.assertEqual(R.route(dict(base, clean_single_shot=True, needs_product=True,
                                      product_slot_in_swipe=True))[0], "SWAP")

    def test_simple_setup_is_ai_and_long_takes_cost_more(self):
        self.assertEqual(R.route({"seconds": 5})[0], "AI")
        self.assertGreater(R.ai_cost(20), R.ai_cost(10))

    def test_label_totals(self):
        res = R.label([{"id": "a", "owned_footage": True, "seconds": 3},
                       {"id": "b", "seconds": 5},
                       {"id": "c", "motion_is_the_point": True, "swipe_shot": "K1", "clean_single_shot": True, "seconds": 4}])
        s = res["summary"]
        self.assertEqual((s["REAL"]["shots"], s["AI"]["shots"], s["SWAP"]["shots"]), (1, 1, 1))
        self.assertAlmostEqual(s["total_usd"], s["AI"]["cost_usd"] + s["SWAP"]["cost_usd"], places=2)


if __name__ == "__main__":
    unittest.main()
