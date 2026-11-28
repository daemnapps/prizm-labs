"""The matrix says profile and angle; run files written in the old words (who, argument) still read."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import matrix as M  # noqa: E402

NEW = {"profile": "p1", "awareness": "problem-aware", "angle": "a1", "format": "list", "face": "f1", "setting": "s1", "look": "l1"}
OLD = {"who": "p1", "awareness": "problem-aware", "argument": "a1", "format": "list", "face": "f1", "setting": "s1", "look": "l1"}


class Words(unittest.TestCase):
    def test_matrix_file_says_profile_and_angle(self):
        d = json.loads((HERE / "dimensions.json").read_text())
        ids = [x["id"] for x in d["big"]]
        self.assertIn("profile", ids)
        self.assertIn("angle", ids)
        self.assertNotIn("who", ids)
        self.assertNotIn("argument", ids)
        self.assertEqual(d["matrix"]["said"], ["profile", "awareness", "angle"])
        self.assertEqual(M.BIG[:3], ["profile", "awareness", "angle"])

    def test_old_words_read_as_new(self):
        self.assertEqual(M.norm(OLD), NEW)
        self.assertEqual(M.norm(NEW), NEW)
        self.assertEqual(M.norm(dict(OLD, profile="p9"))["profile"], "p9")      # the new word wins

    def test_old_and_new_are_no_moves_apart(self):
        self.assertEqual(M.distance(OLD, NEW), (0, []))

    def test_old_plan_file_still_reads(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["CREATIVE_PLAN_ROOT"] = d
            try:
                import creative_plan as PL
                f = PL.file("acme")
                f.parent.mkdir(parents=True)
                f.write_text(json.dumps({"ads": {"x": {"moves": OLD, "state": "planned"}}}))
                self.assertEqual(PL.ledger("acme")["x"]["moves"], NEW)
                self.assertIn("p1", PL.short(PL.ledger("acme")["x"]["moves"]))
            finally:
                os.environ.pop("CREATIVE_PLAN_ROOT", None)

    def test_old_batch_and_cell_still_read(self):
        import creative_matrix as X
        with tempfile.TemporaryDirectory() as d:
            os.environ["CREATIVE_PLAN_ROOT"] = d
            try:
                f = X.file("acme", "b1")
                f.parent.mkdir(parents=True)
                f.write_text(json.dumps({"rows": [{"id": "r1", "moves": OLD}]}))
                self.assertEqual(X.load("acme", "b1")["rows"][0]["moves"], NEW)
                (Path(d) / "matrix-cell.json").write_text(json.dumps({"moves": OLD}))
                self.assertEqual(X.row_of(d)["moves"], NEW)
                self.assertEqual(X.back(OLD, NEW), (7, []))
            finally:
                os.environ.pop("CREATIVE_PLAN_ROOT", None)


if __name__ == "__main__":
    unittest.main()
