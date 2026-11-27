"""A person named by profile must give every writing chain exactly what the older avatar/sub pair gave it (read-only, no model)."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "machine"))
sys.path.insert(0, str(HERE.parent / "naming"))
import who as W  # noqa: E402
import people as N  # noqa: E402


def pairs(brand):
    return [(a, s) for a in W.avatars(brand) for s in (W.subs(brand, a) or [""])]


class SamePersonEitherWay(unittest.TestCase):
    def test_every_person_of_every_brand_with_a_profile_reads_the_same(self):
        seen = 0
        for brand in ("brand_a", "brand_b"):
            try:
                ps = pairs(brand)
            except (Exception, SystemExit):
                continue
            for a, s in ps:
                pid = N.profile(brand, a, s)["id"]
                if pid in N.merges(brand):               # a merged profile reads as the one it was merged into (profiles/CREATE.md)
                    self.assertEqual(W.profile_args(brand, pid)[:2], W.profile_args(brand, N.merges(brand)[pid]["into"])[:2], pid)
                    continue
                a2, s2, d2 = W.profile_args(brand, pid)
                self.assertEqual((a2, s2), (a, s), "%s %s via %s" % (a, s, pid))
                self.assertEqual(W.block(brand, a2, s2 or None, d2 or None), W.block(brand, a, s or None, None), pid)
                seen += 1
        self.assertGreater(seen, 0)

    def test_the_cli_takes_a_profile_for_the_same_person(self):
        a, s, _ = W.profile_args("brand_a", "razor-bumps_tried-everything")
        self.assertEqual((a, s), ("fed-up-king", "ingrown-fighter"))

    def test_avatar_dir_takes_any_spelling_of_the_avatar(self):
        self.assertEqual(W.avatar_dir("brand_a", "razor-bumps"), W.avatar_dir("brand_a", "fed-up-king"))
        self.assertEqual(W.avatar_dir("brand_a", "razor-bumps_tried-everything"), W.avatar_dir("brand_a", "fed-up-king"))


if __name__ == "__main__":
    unittest.main()
