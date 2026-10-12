"""edit_map: the timeline built from an Omni clip run — every line on its real length, no gaps or overlaps,
a clip's sound only over its scripted words. Runs on the Nova run when it is on this machine."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "machine"))
import edit_map as EM  # noqa: E402

RUN = Path(__file__).resolve().parents[3] / "runs" / "video-production" / "brand-a" / "an-earlier-run"


class NothingOfOneAdInTheCode(unittest.TestCase):
    """4 Oct 2026 (the owner: "ultra agnostic — product, brand, avatar, concept, everything"): a clip id, a price, a
    person or a look tied to one ad lives in that ad's decisions.json, never in the line's code."""

    def test_no_clip_fixes_in_code(self):
        self.assertFalse(hasattr(EM, "FIXES"))

    def test_the_tools_carry_no_ad(self):
        import re
        bad = re.compile(r"nova|brand-a|face.?scrub|hydroquinone|\$29|\bG\d\d-[CHK]\d|\bS\d\d\+?\b", re.I)
        for f in ("edit_map", "render_map", "listen", "mouths", "word_fix", "music_bed", "deliver", "sweep", "line"):
            code = [l for l in (HERE.parent / "machine" / f"{f}.py").read_text().splitlines()
                    if not l.strip().startswith("#")]
            hits = [l.strip() for l in code if bad.search(l) and '"""' not in l and "the owner" not in l]
            self.assertEqual(hits, [], f)

    def test_numbers_are_said_the_same_both_sides(self):
        import listen as LI
        self.assertEqual(LI.words_of("$400 apiece"), LI.words_of("four hundred dollars apiece"))
        self.assertEqual(LI.words_of("100% in 60 days"), LI.words_of("one hundred percent in sixty days"))
        self.assertEqual(LI.words_of("Café"), ["café"])


@unittest.skipUnless((RUN / "clips" / "plan.json").exists() and (RUN / "clips" / "omni-ledger.json").exists(), "the Nova run is not on this machine")
class OnTheNovaRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = EM.build(RUN)

    def test_the_picture_never_has_a_hole_or_an_overlap(self):
        pic = sorted(self.m["picture"], key=lambda p: p["a"])
        for x, y in zip(pic, pic[1:]):
            self.assertAlmostEqual(x["b"], y["a"], delta=0.2, msg=f"{x.get('clip')} → {y.get('clip')}")

    def test_lines_follow_one_breath_apart_in_script_order(self):
        ls = sorted(self.m["voice"] + self.m["sounds"], key=lambda l: l["a"])
        for x, y in zip(ls, ls[1:]):
            self.assertGreaterEqual(y["a"] - x["b"], -0.01)

    def test_a_clip_is_heard_only_on_its_scripted_words(self):
        for p in self.m["picture"]:
            if p.get("lip"):
                self.assertTrue(any(l["kind"] == "in clip" and l.get("clip") == p["clip"] for l in self.m["voice"]))


if __name__ == "__main__":
    unittest.main()


class FaceParts(unittest.TestCase):
    """4 Oct 2026 (the owner): a close-up frames the part being talked about — lips for lips, temples for temples —
    never the forehead at random."""

    def test_the_named_part_nearest_the_closeup_wins(self):
        import edit_map as E
        lines = [{"a": 0, "b": 4, "text": "I would definitely do your upper lip. Do you want", "section": "G07"}]
        self.assertEqual(E.part_named(lines, 2, 3, {})[0], "upper lip")
        lines = [{"a": 0, "b": 4, "text": "the dark spots on your cheeks and your temples.", "section": "G02"},
                 {"a": 4.2, "b": 5.5, "text": "That's hydroquinone.", "section": "G02"}]
        self.assertEqual(E.part_named(lines, 4.3, 5.0, {})[0], "temples")   # the section's last named part
        self.assertEqual(E.part_named([{"a": 0, "b": 2, "text": "Literally.", "section": "G11"}], 0, 2, {})[0], None)

    def test_mouth_shows_only_when_nothing_would_give_it_away(self):
        import edit_map as E
        covers = [{"a": 10, "b": 12, "why": "lips move, no words"}]
        self.assertTrue(E.hide_mouth(covers, [], 9, 13, {}))
        self.assertTrue(E.hide_mouth(covers, [{"a": 10.5, "b": 11.5}], 9, 13, {}))    # a mm-hmm doesn't excuse talking lips
        self.assertFalse(E.hide_mouth([], [], 9, 13, {}))
        self.assertTrue(E.others_talking([{"who": "DOCTOR", "kind": "own track", "a": 9, "b": 12}], "NOVA", 10, 11))
        self.assertTrue(E.hide_mouth([], [], 0, 1, {"scene": "S20+"}))               # a word added in her voice
