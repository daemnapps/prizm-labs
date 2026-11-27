"""Stages from first principles and a brand's facts: unknown facts block, false facts drop, nothing is assumed."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import stages as S  # noqa: E402
import build as B  # noqa: E402

TPL = HERE.parents[2] / "brands" / "_TEMPLATE"


class Stages(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        shutil.copytree(TPL, self.root / "brands" / "_TEMPLATE")
        (self.root / "brands" / "acme" / "operations").mkdir(parents=True)

    def facts(self, **vals):
        v = json.loads((TPL / "operations" / "feedback-variables.json").read_text())
        for k, x in vals.items():
            v[k]["value"] = x
        (self.root / "brands/acme/operations/feedback-variables.json").write_text(json.dumps(v))
        return S.facts("acme", self.root)[0]

    def test_no_facts_means_every_form_waits(self):
        rows = S.derive(S.facts("acme", self.root)[0])
        self.assertTrue(all(s and s["status"] == "blocked" and s["blocked_by"].startswith("needs ") for _, s in rows))

    def test_facts_drive_triggers_waits_and_which_forms_exist(self):
        f = self.facts(store_platform="shopify", email_platform="klaviyo", has_email_signup=True, welcome_series_days=5,
                       checkout_recovery_days=2, time_to_first_result_days=21, buffer_days=1,
                       joined_list_event="Subscribed to List", checkout_started_event="Checkout Started",
                       order_placed_event=["Placed Order (store)", "Placed Order (checkout)"],
                       delivered_event="Delivered Shipment", refund_event="Refunded Order", sells_subscriptions=False)
        rows = {m["stage"]: s for m, s in S.derive(f)}
        self.assertIsNone(rows["subscriber"])
        self.assertIsNone(rows["churned-cancelled"])
        self.assertEqual(rows["new-customer"]["klaviyo"]["wait"], "21 days")
        self.assertEqual(rows["list-no-order"]["klaviyo"]["wait"], "6 days")
        self.assertEqual(rows["abandoned-checkout"]["klaviyo"]["trigger"]["metric"], "Checkout Started")
        self.assertIn("Refunded Order — zero times since starting this flow", rows["new-customer"]["klaviyo"]["flow_filters"])
        self.assertEqual(rows["post-support"]["status"], "blocked")
        self.assertIn("ticket_resolved_event", rows["post-support"]["blocked_by"])

    def test_event_names_are_the_brands_own(self):
        f = self.facts(email_platform="klaviyo", has_email_signup=True, welcome_series_days=3, buffer_days=1)
        rows = {m["stage"]: s for m, s in S.derive(f)}
        self.assertIn("joined_list_event", rows["list-no-order"]["blocked_by"])
        f = self.facts(email_platform="mailchimp")
        rows = {m["stage"]: s for m, s in S.derive(f)}
        self.assertIn("only klaviyo is built", rows["repeat-customer"]["blocked_by"])

    def test_two_order_sources_show_as_either(self):
        f = self.facts(email_platform="klaviyo", buffer_days=1, order_placed_event=["Placed Order (store)", "Placed Order (checkout)"])
        rows = {m["stage"]: s for m, s in S.derive(f)}
        self.assertEqual(rows["repeat-customer"]["klaviyo"]["trigger"]["metric"], "Placed Order (store) or Placed Order (checkout)")

    def test_proposal_drops_questions_for_dropped_forms_and_passes_check(self):
        self.facts(sells_subscriptions=False)
        _, _, _, st, q = S.proposal("acme", self.root)
        self.assertNotIn("subscriber", q["stages"])
        self.assertEqual(B.check(st, q), [])

    def test_starter_template_assumes_nothing(self):
        st = json.loads((TPL / "operations" / "feedback-stages.json").read_text())
        self.assertTrue(all(s["status"] == "blocked" for s in st["stages"]))


if __name__ == "__main__":
    unittest.main()
