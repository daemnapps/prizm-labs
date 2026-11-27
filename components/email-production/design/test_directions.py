"""Wireframe directions: three heroes that differ, checked against the brand's recent emails.

    /usr/bin/python3 test_directions.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import directions as DR  # noqa: E402


def email(h, grounds=("#FFFFFF",), todo="a still life"):
    return {"date": "2026-11-20", "sections": [{"s": "fg_hero", "photo_h": h, "picture": {"todo": todo, "alt": "x"}}] +
            [{"s": "fg_block", "bg": g, "items": []} for g in grounds]}


class Directions(unittest.TestCase):
    def test_the_three_heroes_have_different_bands(self):
        bands = [d["band"] for d in DR.DIRECTIONS]
        self.assertEqual(len(DR.DIRECTIONS), 3)
        self.assertEqual(len({d["id"] for d in DR.DIRECTIONS}), 3)
        self.assertEqual(len(set(bands)), 3)

    def test_a_repeat_of_the_last_hero_height_is_flagged(self):
        rec = [{"label": "e1", "date": "2026-11-19", "hero_h": 1000, "hero_words": "", "grounds": ["#FFFFFF"]}]
        d = DR.DIRECTIONS[0]                                    # band 880 to 1000
        self.assertTrue(any("repeats e1" in p for p in DR.problems(email(990), d, rec)))
        self.assertFalse(any("repeats" in p for p in DR.problems(email(900, ("#F4EDDA",)), d, rec)))

    def test_a_hero_outside_its_band_and_same_colours_are_flagged(self):
        rec = [{"label": "e1", "date": "2026-11-19", "hero_h": None, "hero_words": "", "grounds": ["#FFFFFF"]}]
        probs = DR.problems(email(600), DR.DIRECTIONS[0], rec)
        self.assertTrue(any("outside its band" in p for p in probs))
        self.assertTrue(any("same section colours" in p for p in DR.problems(email(900), DR.DIRECTIONS[0], rec)))

    def test_recent_reads_other_emails_newest_first_and_skips_the_one_being_laid_out(self):
        with tempfile.TemporaryDirectory() as t:
            for name, date, h in (("b-nov-1", "2026-11-01", 900), ("b-nov-2", "2026-11-02", 1000), ("b-nov-3", "2026-11-03", 800)):
                p = Path(t) / "runs/email-production/b" / name / "design"
                p.mkdir(parents=True)
                e = email(h)
                e["date"] = date
                (p / "email.json").write_text(json.dumps(e))
            r = DR.recent("b", t, exclude="b-nov-3", n=5)
            self.assertEqual([x["label"] for x in DR.recent("b", t, before="2026-11-02")], ["b-nov-1"])
            self.assertEqual([x["label"] for x in r], ["b-nov-2", "b-nov-1"])
            self.assertIn("hero 1000 px", DR.recent_text(r))

    def test_every_direction_has_its_own_structure_and_alike_layouts_are_caught(self):
        self.assertTrue(all(d.get("structure") for d in DR.DIRECTIONS))
        self.assertEqual(len({d["structure"] for d in DR.DIRECTIONS}), 3)
        a = {"sections": [{"s": "fg_header"}, {"s": "fg_block", "items": [{"t": "headline"}, {"t": "body"}, {"t": "button"}]}, {"s": "fg_foot"}]}
        b = {"sections": [{"s": "fg_header"}, {"s": "fg_block", "items": [{"t": "mosaic"}, {"t": "zigzag"}]}, {"s": "fg_foot"}]}
        self.assertEqual(DR.similarity(a, a), 1.0)
        self.assertGreater(DR.similarity(a, a), DR.TOO_ALIKE)
        self.assertLess(DR.similarity(a, b), DR.TOO_ALIKE)
        self.assertIn("STRUCTURE:", DR.direction_text(DR.DIRECTIONS[1], []))

    def test_single_layout_instructions_and_repeat_check(self):
        rec = [{"label": "e1", "date": "2026-11-19", "hero_h": 1000, "hero_words": "x", "grounds": ["#FFFFFF"], "diagram": "infographic", "diagram_all": ["infographic"]}]
        txt = DR.single_text(rec)
        self.assertIn("weigh three structures privately", txt)
        self.assertIn("infographic", txt)
        self.assertIn("never one fixed style", txt)
        self.assertTrue(DR.repeat_problems(email(980), rec))
        self.assertFalse(DR.repeat_problems(email(700, ("#F4EDDA",)), rec))
        spec = email(900)
        spec["sections"].append({"s": "fg_block", "items": [{"t": "curvepanel"}, {"t": "steps"}, {"t": "infographic"}]})
        self.assertEqual(DR.diagram_of(spec), ["curvepanel", "steps"])


if __name__ == "__main__":
    unittest.main()
