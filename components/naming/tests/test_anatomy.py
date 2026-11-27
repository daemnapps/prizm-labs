"""The body map: every part once, words that find it, the exact part before the near one."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import anatomy as A  # noqa: E402
import people as P  # noqa: E402


class Anatomy(unittest.TestCase):
    def test_each_part_once_and_its_words_compile(self):
        ids = [p for ps in A.groups().values() for p in ps]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertFalse(set(ids) & set(A.groups()) - {"torso"} & set(ids))
        for p in A.parts().values():
            re.compile(p["words"])
            self.assertIn(p["shaved"], ("no", "some", "often"))
            self.assertIn(p["covered"], ("no", "some", "yes"))

    def test_exact_before_near(self):
        self.assertEqual(A.find("bumps on the back of my neck"), ["nape"])
        self.assertEqual(A.find("the back of my head is a nightmare"), ["back-of-head"])
        self.assertIn("elbows", A.find("my elbows and my shins"))
        self.assertEqual(A.find("it smells great"), [])

    def test_a_place_is_a_part_or_a_group(self):
        self.assertEqual(A.open_("heels"), ["heels"])
        self.assertIn("shins", A.open_("legs"))
        self.assertEqual(A.open_("tail"), [])
        self.assertTrue(P.check("sub", "where-tail"))
        self.assertEqual(P.check("sub", "where-back-of-head"), [])


if __name__ == "__main__":
    unittest.main()
