"""Every door calls the matrix: no row no start, the swipe's format decides, the finished picture is read back (no model)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

W = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(W / "components" / "creative-diversity"))
import creative_matrix as X  # noqa: E402
from test_matrix import V, row  # noqa: E402


class Wired(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.run_ = Path(self.t.name) / "run-1"
        self.run_.mkdir()
        self.m = [mock.patch.dict(os.environ, {"CREATIVE_PLAN_ROOT": self.t.name}), mock.patch.object(X.PL, "running", lambda b: ([], None)),
                  mock.patch.object(X, "values", lambda b, k="image": V), mock.patch.object(X, "person_text", lambda b, s: s)]
        for m in self.m:
            m.start()
        self.ask = lambda p: "```json\n" + json.dumps({"rows": [dict(row("x")["moves"], picture="a")]}) + "\n```"

    def tearDown(self):
        for m in self.m:
            m.stop()
        self.t.cleanup()

    def test_a_run_with_no_row_gets_one_fitted_to_its_swipe(self):
        r = X.start(self.run_, "acme", "sub-01-p", pin={"format": "f3"}, ask=self.ask, say=lambda m: None)
        self.assertEqual(r["moves"]["format"], "f3")
        self.assertIn("run-1", X.PL.ledger("acme"))
        self.assertEqual(X.start(self.run_, "acme", "p", pin={"format": "f3"}, ask=None, say=lambda m: None)["id"], "run-1")

    def test_a_row_moves_to_its_swipe_only_while_the_grid_holds(self):
        X.save("acme", "b", [row("p-1")], "image", [])
        X.lock("acme", "b")
        X.cell("acme", "b", "p-1", self.run_)
        self.assertEqual(X.start(self.run_, "acme", "p", pin={"format": "f2"}, say=lambda m: None)["moves"]["format"], "f2")
        X.PL.claim("acme", "other", dict(row("y")["moves"], format="f4", angle="a2"))
        with self.assertRaises(ValueError):
            X.start(self.run_, "acme", "p", pin={"format": "f4"}, say=lambda m: None)

    def test_no_fitting_row_stops_the_start(self):
        X.PL.claim("acme", "taken", dict(row("y")["moves"], format="f3"))
        with self.assertRaises(ValueError):
            X.start(self.run_, "acme", "p", pin={"format": "f3"}, ask=self.ask, say=lambda m: None)

    def test_the_finished_picture_is_kept_beside_its_row_and_compared_from_then_on(self):
        X.PL.claim("acme", "a", row("a")["moves"], brief="brief-0001")
        got = X.finished("acme", "brief-0001", dict(row("a")["moves"], look="l2", setting="s2"))
        self.assertEqual((got["as_planned"], got["seen_off"]), (5, 2))
        self.assertEqual(X.PL.ledger("acme")["a"]["made"]["look"], "l2")
        self.assertIsNone(X.finished("acme", "brief-9999", {}))

    def test_the_doors(self):
        c = W / "components"
        for f, x in (("image-teardown/tools/run.py", "W.matrix_start(run, brand, avatar, gates)"), ("image-writing/tools/writing.py", "MX.start(run, brand"),
                     ("video-writing/machine/writing_v2.py", "matrix_start(d, st)"), ("video-writing/machine/writing_v2.py", "matrix_written(d, st)"),
                     ("meta-upload/to_check.py", "read_back(p, brand, kw[\"brief\"])")):
            self.assertIn(x, (c / f).read_text(), f)


if __name__ == "__main__":
    unittest.main()
