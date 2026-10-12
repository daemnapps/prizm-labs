"""used="fresh": never-used rows first, a proven slice of used rows, and
the rows earlier runs were shown least come first (2026-10-05)."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from language_layer import engine as E


def rows(n):
    return [{"id": f"r{i}", "text": f"line number {i}", "use": ["problem-language"],
             "funnel": "prospect", "signal": {"likes": 1000 - i}} for i in range(n)]


class Fresh(unittest.TestCase):
    def setUp(self):
        self.rows = rows(60)
        self._load, self._used = E.load, E.used_ids
        E.load = lambda *a, **k: self.rows
        E.used_ids = lambda *a, **k: {f"r{i}" for i in range(10)}   # r0..r9 used before

    def tearDown(self):
        E.load, E.used_ids = self._load, self._used

    def ids(self, txt):
        import re
        return re.findall(r"\[(r\d+)\]", txt)

    def test_fresh_mixes_new_and_proven(self):
        got = self.ids(E.for_stage("b", "s", stage_use={"s": ["problem-language"]}, limit=20, used="fresh"))
        self.assertEqual(len(got), 20)
        proven = [i for i in got if int(i[1:]) < 10]
        self.assertEqual(len(proven), 5)                 # 25% of 20
        self.assertEqual(got[:15], [f"r{i}" for i in range(10, 25)])   # fresh first, by likes

    def test_least_shown_first(self):
        shown = {f"r{i}": 3 for i in range(10, 20)}      # r10..r19 shown three times already
        got = self.ids(E.for_stage("b", "s", stage_use={"s": ["problem-language"]}, limit=20,
                                   used="fresh", shown=shown))
        self.assertEqual(got[:10], [f"r{i}" for i in range(20, 30)])

    def test_default_unchanged(self):
        got = self.ids(E.for_stage("b", "s", stage_use={"s": ["problem-language"]}, limit=5))
        self.assertEqual(got, ["r0", "r1", "r2", "r3", "r4"])

    def test_thin_fresh_topped_up_by_proven(self):
        self.rows = rows(12)                              # 2 fresh, 10 used
        got = self.ids(E.for_stage("b", "s", stage_use={"s": ["problem-language"]}, limit=8, used="fresh"))
        self.assertEqual(len(got), 8)
        self.assertEqual(got[:2], ["r10", "r11"])


if __name__ == "__main__":
    unittest.main()
