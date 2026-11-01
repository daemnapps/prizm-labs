import unittest
import body_check as B

class Verdict(unittest.TestCase):
    def test_empty_or_unanswered_verdict_cannot_pass(self):
        for response in ('', '{}', '{"ok": true}'):
            with self.assertRaises(ValueError): B.verdict(response)

    def test_extra_arm_overrides_positive_summary(self):
        self.assertFalse(B.verdict('{"ok": true, "people": [{"arms": 3, "hands": 2}]}')['ok'])

    def test_valid_body_verdict(self):
        self.assertTrue(B.verdict('{"ok": true, "people": [{"arms": 2, "hands": 2}]}')['ok'])

    def test_explicit_no_people_is_valid_for_product_shots(self):
        self.assertTrue(B.verdict('{"ok": true, "people": []}')['ok'])
