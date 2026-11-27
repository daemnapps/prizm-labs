"""The creative matrix: rules by code, values by list, rows that ride with their run (made-up brand; no model)."""
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

V = {"awareness": ["problem-aware", "solution-aware"], "argument": ["a1", "a2"], "format": ["f1", "f2", "f3", "f4"], "face": ["none", "male/25-34/black"], "setting": ["s1", "s2", "s3"], "look": ["l1", "l2"], "_text": {"argument": "- `a1`: x\n- `a2`: y", "setting": "- `s1`: x\n- `s2`: y\n- `s3`: z"}}


def row(i, **k):
    return {"id": i, "moves": dict({"who": "p", "awareness": "problem-aware", "argument": "a1", "format": "f1", "face": "none", "setting": "s1", "look": "l1"}, **k)}


class Matrix(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.m = [mock.patch.dict(os.environ, {"CREATIVE_PLAN_ROOT": self.t.name}), mock.patch.object(X.PL, "running", lambda b: ([], None)),
                  mock.patch.object(X, "values", lambda b, k="image": V), mock.patch.object(X, "person_text", lambda b, s: s)]
        for m in self.m:
            m.start()

    def tearDown(self):
        for m in self.m:
            m.stop()
        self.t.cleanup()

    def test_three_apart_is_not_enough_when_nothing_seen_moved(self):
        self.assertTrue(X.problems([row("a"), row("b", awareness="solution-aware", argument="a2", who="q")]))
        self.assertFalse(X.problems([row("a"), row("b", argument="a2", format="f2", setting="s2")]))

    def test_one_look_never_fills_the_batch(self):
        rows = [row("a"), row("b", format="f2", setting="s2", face="male/25-34/black"), row("c", format="f3", setting="s3", argument="a2"), row("d", format="f4", awareness="solution-aware", setting="s9", who="q")]
        self.assertTrue(any("fills" in b for b in X.problems(rows)))

    def test_off_list_is_refused_and_outside_counts(self):
        self.assertTrue(any("not on the list" in b for b in X.problems([row("a", look="invented")], V)))
        self.assertTrue(any("too close" in b for b in X.problems([row("a")], V, [("live", row("x")["moves"])])))

    def test_a_grid_that_breaks_a_rule_is_sent_back_then_passes_and_locks(self):
        asked = []
        good = [dict(row("x")["moves"]), dict(row("y", argument="a2", format="f2", setting="s2")["moves"])]
        answers = [[good[0], dict(good[0])], good]

        def ask(p):
            asked.append(p)
            return "```json\n" + json.dumps({"rows": answers[len(asked) - 1]}) + "\n```"
        rows, bad = X.fill("acme", [("p", 2)], ask=ask)
        self.assertEqual((bad, len(asked)), ([], 2))
        self.assertIn("YOUR LAST GRID BROKE", asked[1])
        X.save("acme", "b1", rows, "image", bad)
        self.assertEqual(X.lock("acme", "b1"), 2)
        self.assertEqual(set(X.PL.ledger("acme")), {"b1/p-1", "b1/p-2"})
        f = X.cell("acme", "b1", "p-2", self.t.name)
        self.assertIn("f2", json.loads(f.read_text())["text"])

    def test_a_grid_that_does_not_pass_is_never_locked(self):
        X.save("acme", "b2", [row("a"), row("b")], "image", ["x"])
        with self.assertRaises(SystemExit):
            X.lock("acme", "b2")

    def test_read_back(self):
        self.assertEqual(X.back(row("a")["moves"], row("a", look="l2")["moves"])[1], [("look", "l1", "l2")])
        self.assertEqual(X.back(row("a")["moves"], {"look": "unclear"})[0], 7)

    def test_every_kind_and_every_brand_has_its_lists(self):
        for m in self.m[2:3]:
            m.stop()
        for b in sorted(p.name for p in (W / "brands").iterdir() if (p / "strategy" / "settings.json").is_file()):
            for k in X.KINDS:
                v = X.values(b, k)
                for c in ("awareness", "argument", "format", "setting", "look"):
                    self.assertGreater(len(v[c]), 3 if c != "look" else 1, (b, k, c))
        for m in self.m[2:3]:
            m.start()


if __name__ == "__main__":
    unittest.main()
