"""The effects read v2: names from one list, one name per group, the picture as evidence, keys that fall through.
No network, no spend.  python3 -m unittest tests/test_effects.py"""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import effects as EF  # noqa: E402
import gemini as G  # noqa: E402

EVENTS = [{"at": 2.26, "until": None, "kind": "hit", "group": 2, "stands_out": 1.5},
          {"at": 3.76, "until": None, "kind": "hit", "group": 2, "stands_out": 2.0},
          {"at": 6.02, "until": None, "kind": "hit", "group": 3, "stands_out": 1.6},
          {"at": 7.63, "until": 7.97, "kind": "soft", "group": 4, "stands_out": 1.9}]


class Names(unittest.TestCase):
    def test_names_snap_onto_the_one_list(self):
        self.assertEqual(EF.snap("Camera Shutter"), "camera shutter")
        self.assertEqual(EF.snap("woosh"), "whoosh")
        self.assertEqual(EF.snap("reverse cymbal swell"), "reverse cymbal")   # the longest list value it holds
        self.assertEqual(EF.snap("keyboard typing"), "typewriter")
        self.assertIsNone(EF.snap(None))
        self.assertTrue(EF.snap("kazoo").startswith("other: "))

    def test_every_name_files_under_a_real_category_and_bank_ids_exist(self):
        cats = set(EF.LISTS["ucs_category"])
        for n in EF.NAMES:
            self.assertIn(EF.ucs_of(n), cats)
        self.assertEqual(EF.BANK_OF["camera shutter"], "shutter")


class OneNamePerSound(unittest.TestCase):
    def test_a_group_is_named_once_and_every_member_carries_it(self):
        heard = {"groups": [{"group": 2, "added": True, "name": "Click", "sure": "high", "job": "caption-pop",
                             "ucs_category": "USER INTERFACE", "in_the_edit": True},
                            {"group": 3, "added": False}],
                 "missed": [{"at": 6.2, "name": "click", "sure": "medium", "job": "caption-pop"}]}
        rows = EF.apply(EVENTS, heard)
        self.assertEqual([(r["at"], r["name"]) for r in rows], [(2.26, "click"), (3.76, "click"), (6.2, "click")])
        self.assertEqual(rows[2]["found"], "ear only")
        self.assertEqual(rows[0]["bank"], "click")

    def test_only_at_keeps_just_the_moments_named(self):
        heard = {"groups": [{"group": 2, "added": True, "only_at": [3.76], "name": "pop"}]}
        self.assertEqual([r["at"] for r in EF.apply(EVENTS, heard)], [3.76])

    def test_a_missed_moment_near_a_timed_one_takes_the_measured_second(self):
        rows = EF.apply(EVENTS, {"missed": [{"at": 2.37, "name": "whoosh"}]})
        self.assertEqual((rows[0]["at"], rows[0]["found"], rows[0]["group"]), (2.26, "tool + ear", 2))

    def test_a_missed_soft_sound_is_kept_soft(self):
        rows = EF.apply([], {"missed": [{"at": 11.9, "until": 14.9, "name": "riser"}]})
        self.assertEqual(rows[0]["kind"], "soft")

    def test_the_listing_groups_and_marks_soft_rises(self):
        text = EF.listing(EVENTS)
        self.assertIn("group 2 (sharp hit): 2.26s, 3.76s", text)
        self.assertIn("group 4 (soft rise): 7.63s-7.97s", text)
        self.assertNotIn("loop", text)                                     # the ear is not steered by a number

    def test_picture_moments_are_listed_or_said_missing(self):
        self.assertIn("2.37s · punch-in", EF.picture_lines([{"at": 2.37, "what": "punch-in"}]))
        self.assertEqual(EF.picture_lines(None), "- (not given)")


class KeysFallThrough(unittest.TestCase):
    def test_a_spent_key_hands_over_to_the_backup(self):
        calls = []

        def fake(model, audio, text, cap, name):
            calls.append(name)
            if name == "GEMINI_API_KEY":
                raise RuntimeError('{"error": {"code": 402, "message": "Your prepayment credits are depleted"}}')
            return {"ok": True}
        with mock.patch.object(G, "_one", fake), mock.patch.object(G, "key", lambda n: "k-" + n):
            got, model, tried = G.ask("x.mp3", "q", models=[("m", 5)])
        self.assertEqual(got, {"ok": True})
        self.assertEqual(calls, ["GEMINI_API_KEY", "GEMINI_API_KEY_PERSONAL"])

    def test_a_bad_answer_does_not_spend_the_backup(self):
        calls = []

        def fake(model, audio, text, cap, name):
            calls.append((model, name))
            raise RuntimeError("no answer")
        with mock.patch.object(G, "_one", fake), mock.patch.object(G, "key", lambda n: "k"):
            with self.assertRaises(RuntimeError):
                G.ask("x.mp3", "q", models=[("a", 5), ("b", 5)])
        self.assertEqual(calls, [("a", "GEMINI_API_KEY"), ("b", "GEMINI_API_KEY")])


if __name__ == "__main__":
    unittest.main()
