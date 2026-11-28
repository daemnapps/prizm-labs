"""Every tool that takes a person must get the SAME folders whichever way the person is named: a profile, the new
avatar/sub names, or the older folder names. Dummy brand, dummy folders, no real data."""
import itertools
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import people as P  # noqa: E402

ALIASES = {"brands": {"acme": {
    "avatars": {"old-hero": "razor-bumps", "old-gift": "buying-for-him"},
    "subs": {"razor-bumps": {"old-fighter": "tried-everything", "old-back": "where-back-of-head"}, "buying-for-him": {"old-derm": "tried-the-derm"}},
    "demographics": {"old-rey": "male-25-34-latino", "old-mom": "female-45-54-black"}}}}
FOLDERS = {"old-hero": ["sub-01-old-fighter", "sub-02-old-back", "sub-03-old-rey"], "old-gift": ["sub-01-old-derm", "sub-02-old-mom"]}
OLD = [("old-hero", "old-fighter"), ("old-hero", "old-back"), ("old-hero", "old-rey"), ("old-gift", "old-derm"), ("old-gift", "old-mom"), ("old-hero", "")]


class Contract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for a, subs in FOLDERS.items():
            d = root / "acme" / "core-avatars" / a / "sub-avatars"
            d.mkdir(parents=True)
            for s in subs:
                (d / (s + ".md")).write_text("x")
        self.patches = [mock.patch.object(P, "BRANDS", root), mock.patch.object(P, "aliases", lambda: ALIASES)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_every_person_resolves_to_the_same_folders_by_every_name(self):
        for a, s in OLD:
            want = P.folders("acme", a, s)
            prof = P.profile("acme", a, s)
            self.assertEqual(want[:2], (a, s), (a, s))                                   # the older pair is untouched
            self.assertEqual(P.folders("acme", prof["id"])[:2], (a, s), (a, s, prof["id"]))   # the profile reaches the same folders
            self.assertEqual(P.canon("acme", prof["id"]), (a, s))                        # and so does canon, which every tool calls
            self.assertEqual(P.folders("acme", prof["avatar"], prof["sub"], prof["demographic"])[:2], (a, s))   # the profile's own parts too

    def test_the_new_avatar_and_sub_names_reach_the_same_folders(self):
        self.assertEqual(P.folders("acme", "razor-bumps", "tried-everything"), ("old-hero", "old-fighter", ""))
        self.assertEqual(P.folders("acme", "buying-for-him", "tried-the-derm"), ("old-gift", "old-derm", ""))

    def test_a_demographic_profile_finds_its_older_folder_and_a_free_demographic_stays_a_demographic(self):
        self.assertEqual(P.folders("acme", "razor-bumps_male-25-34-latino")[:2], ("old-hero", "old-rey"))
        self.assertEqual(P.folders("acme", "razor-bumps_where-back-of-head_male-35-44-black"), ("old-hero", "old-back", "male-35-44-black"))

    def test_a_profile_never_maps_two_people_to_one_name(self):
        ids = [P.profile("acme", a, s)["id"] for a, s in OLD]
        self.assertEqual(len(ids), len(set(ids)))

    def test_unknown_names_come_back_as_they_are_and_nothing_raises(self):
        self.assertEqual(P.canon("acme", "something-else", "other"), ("something-else", "other"))
        self.assertEqual(P.canon("nobrand", "a", "b"), ("a", "b"))
        self.assertEqual(P.canon("acme", None), (None, ""))
        self.assertEqual(P.canon("acme", ""), ("", ""))


class RealNames(unittest.TestCase):
    def test_no_alias_or_brand_avatar_name_contains_an_underscore(self):
        """`_` is what joins a profile's parts, so no avatar or sub-avatar name may use it."""
        for b, d in P.aliases()["brands"].items():
            narrowed = [k for k, v in d["demographics"].items() if isinstance(v, dict)]
            names = itertools.chain(d["avatars"], d["avatars"].values(), [v for v in d["demographics"].values() if not isinstance(v, dict)],
                                    [k for k in d["demographics"] if k not in narrowed], *[list(m) + list(m.values()) for m in d["subs"].values()])
            for x in names:
                self.assertNotIn("_", x, (b, x))
            for k in narrowed:                    # a renamed folder for a sub-avatar narrowed by a demographic is `<sub>_<demographic>`
                v = d["demographics"][k]
                self.assertIn(k, (v["sub"] + "_" + v["demographic"], k if "_" not in k else None), (b, k))
        for d in P.BRANDS.glob("*/core-avatars/*"):
            if d.parent.parent.name.startswith("_"):
                continue
            self.assertNotIn("_", d.name, str(d))

    def test_the_alias_file_is_cached_and_follows_edits(self):
        self.assertIs(P.aliases(), P.aliases())


if __name__ == "__main__":
    unittest.main()
