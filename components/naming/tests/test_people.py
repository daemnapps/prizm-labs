"""PEOPLE.md's rules, and every name on file follows them."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import people as P  # noqa: E402


class People(unittest.TestCase):
    def test_good_names(self):
        for layer, n in (("avatar", "razor-bumps"), ("avatar", "acne"), ("sub", "where-back-of-head"), ("sub", "tried-every-wash"), ("demographic", "male-35-44-black"), ("demographic", "male-35-44-latino-spanish"), ("demographic", "female-65-plus-east-asian")):
            self.assertEqual(P.check(layer, n), [], n)

    def test_refused(self):
        for layer, n in (("avatar", "fed-up-king"), ("avatar", "spot-hider"), ("sub", "bald-bumps-guy"), ("sub", "ingrowns"), ("sub", "tried-every-wash-kid"), ("demographic", "male-40-49-black"), ("demographic", "el-jefe"), ("avatar", "Razor Bumps")):
            self.assertTrue(P.check(layer, n), n)

    def test_address_joins_and_reads_the_older_spelling(self):
        self.assertEqual(P.address("razor-bumps", "where-back-of-head", "male/35-44/black"), "razor-bumps_where-back-of-head_male-35-44-black")
        self.assertEqual(P.demographic("male/25-34/south-asian")["ethnicity"], "south-asian")

    def test_every_new_name_on_file_follows_the_rules_and_is_unique(self):
        for b, d in P.aliases()["brands"].items():
            self.assertEqual(len(set(d["avatars"].values())), len(d["avatars"]), b)
            for n in d["avatars"].values():
                self.assertEqual(P.check("avatar", n), [], n)
            for av, subs in d["subs"].items():
                self.assertIn(av, d["avatars"].values())
                self.assertEqual(len(set(subs.values())), len(subs))
                for n in subs.values():
                    self.assertEqual(P.check("sub", n), [], n)
            for n in d["demographics"].values():
                dm = n["demographic"] if isinstance(n, dict) else n           # a card is a sub-avatar narrowed by a signed demographic (2026-11-27)
                self.assertEqual(P.check("demographic", dm), [], dm)
                if isinstance(n, dict):
                    self.assertEqual(P.check("sub", n["sub"]), [], n["sub"])


class Aliases(unittest.TestCase):
    def test_either_name_reads_the_same_folder(self):
        for b, d in P.aliases()["brands"].items():
            for old, new in d["avatars"].items():
                self.assertEqual(P.canon(b, new)[0], P.canon(b, old)[0])
                for o, n in (d["subs"].get(new) or {}).items():
                    self.assertEqual(P.canon(b, new, n), P.canon(b, old, o))
                    self.assertEqual(P.new_names(b, old, o), (new, n))


if __name__ == "__main__":
    unittest.main()
