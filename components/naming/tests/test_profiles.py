"""A profile is one unit (avatar + sub-avatar + demographic) with one name, and every point inside it has an address."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import people as P  # noqa: E402


class Profile(unittest.TestCase):
    def test_old_and_new_spellings_name_the_same_profile(self):
        old = P.profile("brand_a", "fed-up-king", "ingrown-fighter")
        new = P.profile("brand_a", "razor-bumps", "tried-everything")
        self.assertEqual(old["id"], "razor-bumps_tried-everything")
        self.assertEqual(old["id"], new["id"])
        self.assertEqual(old["old"], {"avatar": "fed-up-king", "sub": "ingrown-fighter"})

    def test_an_older_demographic_name_is_read_as_its_sub_avatar_plus_that_demographic(self):
        x = P.profile("brand_a", "fed-up-king", "el-rey-cansado")
        self.assertEqual((x["avatar"], x["sub"], x["demographic"]), ("razor-bumps", "when-fresh-cut", "male-25-34-latino"))
        self.assertEqual(x["id"], "razor-bumps_when-fresh-cut_male-25-34-latino")
        self.assertEqual(P.folders("brand_a", x["id"]), ("fed-up-king", "el-rey-cansado", ""))
        self.assertEqual(P.folders("brand_a", "razor-bumps_when-fresh-cut"), ("fed-up-king", "barbershop-regular", ""))

    def test_a_chosen_demographic_joins_the_profile_and_the_label_reads_plainly(self):
        x = P.profile("brand_a", "razor-bumps", "where-back-of-head", "male/35-44/black")
        self.assertEqual(x["id"], "razor-bumps_where-back-of-head_male-35-44-black")
        self.assertEqual(x["label"], "Razor bumps · Back of head · Black man 35–44")

    def test_an_avatar_alone_is_a_profile(self):
        self.assertEqual(P.profile("brand_a", "face-back")["id"], "wrinkles")

    def test_parse_reads_a_name_back(self):
        self.assertEqual(P.parse("razor-bumps_where-back-of-head_male-35-44-black/desire-x-1a2b"),
                         {"avatar": "razor-bumps", "sub": "where-back-of-head", "demographic": "male-35-44-black", "point": "desire-x-1a2b"})
        self.assertEqual(P.parse("razor-bumps_male-25-34-latino")["sub"], "")
        self.assertEqual(P.parse("razor-bumps_male-25-34-latino")["demographic"], "male-25-34-latino")

    def test_sub_labels(self):
        self.assertEqual(P.sub_label("where-back-of-head"), "Back of head")
        self.assertEqual(P.sub_label("tried-every-wash"), "Tried every wash")
        self.assertEqual(P.sub_label("feels-scared-to-scrub"), "Feels scared to scrub")


class Folders(unittest.TestCase):
    def test_a_profile_resolves_to_the_folders_every_tool_reads(self):
        self.assertEqual(P.folders("brand_a", "razor-bumps_tried-everything"), ("fed-up-king", "ingrown-fighter", ""))
        self.assertEqual(P.folders("brand_a", "fed-up-king", "ingrown-fighter"), ("fed-up-king", "ingrown-fighter", ""))      # the older pair still works
        self.assertEqual(P.folders("brand_a", "razor-bumps", "tried-everything"), ("fed-up-king", "ingrown-fighter", ""))

    def test_a_profile_that_is_an_avatar_plus_a_demographic_finds_the_older_folder(self):
        self.assertEqual(P.folders("brand_a", "razor-bumps_male-25-34-latino")[:2], ("fed-up-king", "el-rey-cansado"))

    def test_a_demographic_joins_when_no_older_name_holds_it(self):
        self.assertEqual(P.folders("brand_a", "razor-bumps_where-back-of-head_male-35-44-black"), ("fed-up-king", "bald-bumps-guy", "male-35-44-black"))

    def test_canon_takes_a_profile_id_too(self):
        self.assertEqual(P.canon("brand_a", "razor-bumps_tried-everything"), ("fed-up-king", "ingrown-fighter"))


class Points(unittest.TestCase):
    def test_a_point_has_a_stable_address(self):
        a = P.point_id("desire", "I want my neck to still look clean two days after the barber lines me up")
        self.assertEqual(a, P.point_id("desire", "  I want my neck to still look clean two days after the barber lines me up "))
        self.assertTrue(a.startswith("desire-i-want-my-neck-to-still-"))

    def test_a_different_point_is_a_different_address_even_with_the_same_opening(self):
        a = P.point_id("desire", "I want my neck clean now and later tonight")
        b = P.point_id("desire", "I want my neck clean now and later tomorrow")
        self.assertNotEqual(a, b)
        self.assertNotEqual(P.point_id("belief", "x y z"), P.point_id("desire", "x y z"))

    def test_an_element_is_the_profile_and_the_point(self):
        e = P.element("razor-bumps_tried-everything", "doubt", "does it work")
        self.assertTrue(e.startswith("razor-bumps_tried-everything/doubt-does-it-work-"))


if __name__ == "__main__":
    unittest.main()
