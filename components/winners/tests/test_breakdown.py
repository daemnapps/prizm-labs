"""breakdown.py: a winner's breakdown is whole, in the fixed order, filed beside the bank and onto the board.
Offline, a scratch root. The step is held for review: nothing in the line calls it.

    /usr/bin/python3 components/winners/tests/test_breakdown.py
"""
import json, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import bank  # noqa: E402
import breakdown as BD  # noqa: E402
from test_bank import audit, row, w  # noqa: E402

REC = {"hook": {"said": "Why did no one tell me", "shown": "THIS causes it", "does": "names a hidden cause"},
       "lead": {"quote": "Nine in ten have these", "tone": "plain"}, "offer": {"quote": "none", "parts": []},
       "mechanism": {"quote": "it calms the overactive part"}, "outcome": {"quote": "clearer in a month"},
       "features_benefits": [{"feature": "four plants", "benefit": "no benefit said"}],
       "guarantee": {"quote": "sixty days"}, "ask": {"quote": "tap below", "at": "0:58"},
       "sound_off": [{"scene": 1, "on_screen": "a close-up", "words_on_screen": "THIS causes it",
                      "clear_without_sound": True}],
       "type": "Skin close-up", "angle": {"claim": "the cause is hidden", "id": "none on the list"},
       "what_to_change": [{"change": "a new opening on the same body", "keep": "the body and the close"},
                          {"change": "the same message as a picture", "keep": "the body and the close"}]}


class Check(unittest.TestCase):
    def test_a_whole_record_in_order_passes(self):
        self.assertEqual(BD.check(REC), [])

    def test_a_missing_part_is_named(self):
        self.assertEqual(BD.check({k: v for k, v in REC.items() if k != "guarantee"}), ["missing guarantee"])

    def test_parts_out_of_order_are_refused(self):
        moved = {"lead": REC["lead"], **{k: v for k, v in REC.items() if k != "lead"}}
        self.assertIn("out of order", BD.check(moved)[0])

    def test_it_must_end_with_what_to_change(self):
        self.assertIn("what_to_change is empty", BD.check(dict(REC, what_to_change=[]))[0])


class File(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        a1 = audit(self.root, "2025", "2025-01-01", "2026-11-02", [row(1, "Script 30", ["111", "112"], 1000, 50, 1500)])
        bank.main(["--brand", "acme", "--root", str(self.root), "--audit", str(a1)])

    def tearDown(self):
        self._t.cleanup()

    def test_files_the_record_and_a_page_in_the_same_order(self):
        wrote = BD.file(self.root, "acme", "acme-111", REC)
        doc = json.loads(wrote[0].read_text())
        self.assertEqual(wrote[0], self.root / "runs/winners/acme/breakdown/acme-111.json")
        self.assertEqual([k for k in doc if k in BD.ORDER], list(BD.ORDER))
        md = wrote[1].read_text()
        heads = [md.index("## " + BD.TITLES[k]) for k in BD.ORDER]
        self.assertEqual(heads, sorted(heads))

    def test_fills_the_boards_own_breakdown_for_the_winner_that_carries_the_ad(self):
        board = self.root / "board.json"
        w(self.root, "board.json", {"acme": {"winners": [{"rank": 1, "ads": [{"ad_id": "999"}]},
                                                         {"rank": 2, "ads": [{"ad_id": "112"}],
                                                          "breakdown": {"why_it_works": ["kept"], "proof": "p",
                                                                        "flags": ["a rule"], "hook": "old"}}]}})
        BD.file(self.root, "acme", "acme-111", REC, board)
        winners = json.loads(board.read_text())["acme"]["winners"]
        self.assertNotIn("breakdown", winners[0])
        bd = winners[1]["breakdown"]
        self.assertEqual(sorted(bd), ["flags", "format", "hook", "keep", "message", "proof", "vary", "why_it_works"])
        self.assertEqual((bd["why_it_works"], bd["proof"], bd["flags"]), (["kept"], "p", ["a rule"]))  # merged
        self.assertNotEqual(bd["hook"], "old")
        self.assertEqual((bd["message"], bd["format"], bd["keep"]), ("the cause is hidden", "Skin close-up", "the body and the close"))
        self.assertEqual(bd["vary"], ["a new opening on the same body", "the same message as a picture"])

    def test_bad_input_is_refused_and_writes_nothing(self):
        with self.assertRaises(ValueError):
            BD.file(self.root, "acme", "acme-999", REC)
        with self.assertRaises(ValueError):
            BD.file(self.root, "acme", "acme-111", dict(REC, what_to_change=[]))
        self.assertFalse((self.root / "runs/winners/acme/breakdown").exists())


if __name__ == "__main__":
    unittest.main()
