"""The finished-ads index carries who each brief is for beside the card's own fields, and is built the same without it."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ads_index as AI  # noqa: E402


class Fake:
    def __init__(self, a):
        self.a = a

    def of(self, key):
        if isinstance(self.a, Exception):
            raise self.a
        return self.a


ROW = {"brief": "b1_p_brief-0001", "number": "0001", "avatar": "man", "sub_avatar": "card-sub", "face": "card-face"}
AIM = {"avatar": "man", "sub": "s", "demographic": "d", "desire": "want", "awareness": "unaware", "doubt": "for-me"}
CARD_ONLY = {"sub": "card-sub", "demographic": "card-face", "desire": None, "awareness": None, "doubt": None}


class AimColumns(unittest.TestCase):
    def test_the_briefs_aim(self):
        self.assertEqual(AI._aim_columns(ROW, Fake(AIM)), {k: AIM[k] for k in AI.AIM})

    def test_the_card_fills_what_the_brief_does_not_say(self):
        got = AI._aim_columns(ROW, Fake(dict(AIM, sub=None, demographic=None)))
        self.assertEqual((got["sub"], got["demographic"], got["desire"]), ("card-sub", "card-face", "want"))

    def test_another_avatar_no_aim_and_a_failure_leave_the_card_alone(self):
        for fake in (Fake(dict(AIM, avatar="woman")), None, Fake(ValueError("x"))):
            self.assertEqual(AI._aim_columns(ROW, fake), CARD_ONLY)
        self.assertEqual(AI._aim_columns(dict(ROW, number=None), Fake(AIM)), CARD_ONLY)

    def test_the_front_page_has_the_columns(self):
        md = AI.front("b1", [dict(ROW, names=["n"], lanes=["video"], state="3-live", cards=[{"folder": "f", "state": "3-live"}], **AIM)], "now")
        head = next(x for x in md.splitlines() if x.startswith("| Brief"))
        row = next(x for x in md.splitlines() if x.startswith("| 0001"))
        self.assertIn("| Live | Sub-avatar | Demographic | Desire | Awareness | Doubt |", head)
        self.assertTrue(row.endswith("| s | d | want | unaware | for-me |"), row)
        self.assertEqual(head.count("|"), row.count("|"))


if __name__ == "__main__":
    unittest.main()
