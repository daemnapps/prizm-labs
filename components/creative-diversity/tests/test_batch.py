"""A batch is scored against itself before anything is made (made-up ads, no library, no model)."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check  # noqa: E402

A = {"profile": "p1", "awareness": "problem-aware", "angle": "a1", "format": "list", "face": "f1", "setting": "s1", "look": "l1"}


class Batch(unittest.TestCase):
    def go(self, *ads):
        with mock.patch.object(check, "score", lambda b, m: {"verdict": "unscored"}):
            return check.batch("acme", list(ads))

    def test_one_thing_changed_is_the_same_creative(self):
        r = self.go({"id": "a", "moves": A}, {"id": "b", "moves": dict(A, setting="s2")})
        self.assertFalse(r["passes"])
        self.assertEqual(r["same"][0]["ads"], ["a", "b"])

    def test_three_moves_apart_passes(self):
        self.assertTrue(self.go({"id": "a", "moves": A}, {"id": "b", "moves": dict(A, profile="p2", angle="a2", look="l2")})["passes"])

    def test_every_move_is_named(self):
        with self.assertRaises(SystemExit):
            self.go({"id": "a", "moves": dict(A, look="")})


if __name__ == "__main__":
    unittest.main()
