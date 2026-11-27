"""A picture the judge never looked at is said, never silent (the team, 2026-10-28: Brand-B nov-04's two pictures were
thrown away on 2026-10-21 because the judge had no credits, and the slots sat empty for a week with no reason given).

    /usr/bin/python3 test_unjudged.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gaps as G  # noqa: E402
import line  # noqa: E402

NO_CREDITS = "judge did not run: RuntimeError: judge error 402: Your prepayment credits are depleted"


class Unjudged(unittest.TestCase):
    def test_the_reason_is_found_in_any_shape_the_engine_returns(self):
        for held in ([NO_CREDITS], [[NO_CREDITS]], [{"fails": [NO_CREDITS]}], NO_CREDITS):
            self.assertTrue(line.unjudged(held).startswith("judge did not run"), held)

    def test_a_judge_that_looked_is_not_unjudged(self):
        self.assertIsNone(line.unjudged([["the tube is lying down"]]))
        self.assertIsNone(line.unjudged(None))


class MissingList(unittest.TestCase):
    def run_with(self, pictures, ok=()):
        d = Path(tempfile.mkdtemp())
        (d / "design").mkdir()
        (d / "klaviyo").mkdir()
        (d / "design" / "email.json").write_text(json.dumps(
            {"sections": [{"s": "photo_card", "picture": p} for p in pictures]}))
        (d / "klaviyo" / "card.json").write_text(json.dumps({"sections_ok": list(ok)}))
        return [g["why"] for g in G.find(d)["gaps"]]

    def test_a_picture_thrown_away_for_no_judge_says_why_and_how_to_retry(self):
        why = self.run_with([{"todo": "a woman at her sink", "unjudged": NO_CREDITS}])
        self.assertEqual(len(why), 1)
        self.assertIn("could not run", why[0])
        self.assertIn("402", why[0])
        self.assertIn("Make the missing parts", why[0])

    def test_a_picture_placed_without_the_judge_asks_eve_to_look(self):
        why = self.run_with([{"photo": "run:media/x.png", "alt": "a woman", "unchecked": NO_CREDITS}])
        self.assertEqual(len(why), 1)
        self.assertIn("look at it yourself", why[0])

    def test_once_the_part_is_marked_right_it_is_no_longer_listed(self):
        self.assertEqual(self.run_with([{"photo": "run:media/x.png", "alt": "a woman", "unchecked": NO_CREDITS}], ok=[0]), [])

    def test_a_plain_missing_picture_reads_as_before(self):
        self.assertEqual(self.run_with([{"todo": "a woman at her sink"}]), ["picture not made yet"])


class PersonInFrame(unittest.TestCase):
    """The engine hands the brand's cast only when told a person is in the picture (the team, 2026-10-28)."""
    def test_tomorrows_briefs_read_right(self):
        cases = [
            ({"todo": "A woman in her late fifties at her kitchen table", "brief": "No product in this frame."}, True),
            ({"todo": "Wash going onto the brush", "brief": "hand of a man holding the brush. No face, no result."}, True),
            ({"todo": "A debate board", "brief": "no people, no skin, the CRUSH tube alone"}, False),
            ({"todo": "A barber station counter", "brief": "WAR Face Wash and PRIME Face Quench, no hands, no text"}, None),
            ({"todo": "A quote card", "brief": "No face, no portrait, no person in the frame"}, False),
            ({"todo": "A gift box", "use": "gift", "brief": "a man unwrapping it"}, False),
            ({"todo": "A woman at the sink", "people": False}, False),
        ]
        for p, want in cases:
            self.assertEqual(line.in_frame(p), want, p)


class FillPicturesOnly(unittest.TestCase):
    def test_the_page_fill_leaves_words_prices_and_promises_alone(self):
        """the team, 2026-10-28: Make the missing parts makes pictures and nothing else."""
        d = Path(tempfile.mkdtemp())
        (d / "design").mkdir()
        spec = {"sections": [{"s": "letter", "text": "[UNFILLED: the headline]"}, {"s": "product", "name": "X", "price": ""}]}
        (d / "design" / "email.json").write_text(json.dumps(spec))
        out = G.fill(d, brand="nobrand", lk={}, make_pictures=False, redesign=True, pictures_only=True)
        self.assertEqual(out["filled"], [])
        self.assertEqual(json.loads((d / "design" / "email.json").read_text()), spec)
        self.assertTrue(all("the team's to settle" in g["ask"] for g in out["open"]))


if __name__ == "__main__":
    unittest.main()
