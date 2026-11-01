"""The brief follows the element (2026-10-01): a brief whose words describe a
person differently from their banked element is a MISMATCH, with no model."""
import json, tempfile, unittest
from pathlib import Path
from unittest import mock
import element_match as em


class BriefFollows(unittest.TestCase):
    def test_her_hand_on_a_man_is_caught(self):
        doc = {"cast": [{"id": "PRO", "bank_id": "NEW", "identity_block": "a man in his 50s"},
                        {"id": "GUEST", "bank_id": "NEW", "identity_block": "a woman in her 40s"}],
               "scenes": [{"id": "S1", "who": "PRO", "composition": "GUEST centred; PRO behind her, only her right hand in frame"}]}
        rows = em.brief_follows("", doc, "nobrand-test")
        self.assertEqual([r["id"] for r in rows], ["D-S1"])
        doc["scenes"][0]["composition"] = "GUEST centred; PRO behind her, only his right hand on her cheek"
        self.assertEqual(em.brief_follows("", doc, "nobrand-test"), [])


if __name__ == "__main__":
    unittest.main()
