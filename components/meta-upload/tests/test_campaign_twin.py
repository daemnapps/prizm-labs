"""A card whose campaign was renamed on the live side goes into the live campaign, never a new one."""
import sys, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "naming"))
import upload as U


class LiveTwin(unittest.TestCase):
    def live(self, names):
        return mock.patch.multiple(U, known_ids=lambda b: (None, {"campaigns": {}}), spending_campaigns=lambda b: set(names))

    def test_renamed_funnel_goes_to_the_live_campaign(self):
        with self.live(["campaign_acme_us_scrub_scrub-cpk-subscribe_purchase_cbo", "campaign_acme_us_face_face-cpk_purchase_cbo"]):
            self.assertEqual(U.live_twin("acme", "campaign_acme_us_scrub_scrub-cpk_purchase_cbo", "scrub-cpk"),
                             "campaign_acme_us_scrub_scrub-cpk-subscribe_purchase_cbo")

    def test_two_candidates_decide_nothing(self):
        with self.live(["campaign_acme_us_scrub_scrub-cpk-a_purchase_cbo", "campaign_acme_us_scrub_scrub-cpk-b_purchase_cbo"]):
            self.assertIsNone(U.live_twin("acme", "campaign_acme_us_scrub_scrub-cpk_purchase_cbo", "scrub-cpk"))

    def test_another_product_is_never_a_twin(self):
        with self.live(["campaign_acme_us_face_scrub-cpk-subscribe_purchase_cbo"]):
            self.assertIsNone(U.live_twin("acme", "campaign_acme_us_scrub_scrub-cpk_purchase_cbo", "scrub-cpk"))


if __name__ == "__main__":
    unittest.main()
