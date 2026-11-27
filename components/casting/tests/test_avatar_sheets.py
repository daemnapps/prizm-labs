"""avatar_sheets: a customer's picture never gets past the door, and the sheet layout is the one core layout."""
import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
import avatar_sheets as A  # noqa: E402

CARD = {"id": "testman", "name": "Testman", "handle": None, "kind": "ai-character", "role": "customer", "gender": "male",
        "ethnic-appearance": "latino", "ethnic-appearance-source": "stated", "age-band": "25-34", "age-band-source": "stated",
        "avatars-fit": [], "sub-avatars-fit": [], "source": "invented", "notes": [], "missing": [], "casting-sheet": "yes", "status": "current"}


def avatar(file="../world.jpg", frm="the swipe"):
    return {"id": "testman", "brand": "x", "group": "a group", "card": CARD,
            "real_references": [{"file": file, "from": frm}]}


class Door(unittest.TestCase):
    def test_clean_avatar_passes(self):
        self.assertEqual(A.refused(avatar()), [])

    def test_customer_picture_refused_by_path(self):
        self.assertTrue(A.refused(avatar(file="runs/x/proof/intake-before-after-finals-someone.jpg")))

    def test_customer_picture_refused_by_source(self):
        self.assertTrue(A.refused(avatar(frm="a customer review photo")))

    def test_group_is_required(self):
        a = avatar()
        del a["group"]
        self.assertTrue(A.refused(a))

    def test_bad_card_refused(self):
        a = avatar()
        a["card"] = {**CARD, "ethnic-appearance": "unknown-word"}
        self.assertTrue(A.refused(a))

    def test_core_layout_says_invented(self):
        c = A.core_json({"id": "testman", "group": "a group"})
        self.assertTrue(c["not_a_real_customer"])
        self.assertEqual(c["headshot"], "sheets/headshot.jpg")


if __name__ == "__main__":
    unittest.main()
