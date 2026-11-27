"""A statics-sprint brief carries its round's sale (moment, offer, promo) to the copywriter (2026-11-27)."""
import json, tempfile, unittest
from pathlib import Path
import brief_words as B


class SprintRoundSale(unittest.TestCase):
    def test_round_found_and_unknown_empty(self):
        with tempfile.TemporaryDirectory() as t:
            old, B.WS = B.WS, Path(t)
            try:
                d = Path(t) / "runs/ad-variations/acme/xmas"
                d.mkdir(parents=True)
                (d / "briefs.json").write_text(json.dumps({"a": "brief-0901"}))
                (d / "sprint.json").write_text(json.dumps({"moment": "Christmas", "offer": "Widget from $9", "angle": "promo"}))
                self.assertEqual(B.sprint_round("acme", "brief-0901"),
                                 {"moment": "Christmas", "offer_lines": ["Widget from $9"], "promo": True})
                self.assertEqual(B.sprint_round("acme", "brief-0902"), {})
            finally:
                B.WS = old


if __name__ == "__main__":
    unittest.main()
