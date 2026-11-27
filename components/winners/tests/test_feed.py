import json, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
sys.path.insert(0, str(COMPONENT))
sys.path.insert(0, str(HERE))
import bank  # noqa: E402
import feed  # noqa: E402
from test_bank import TEARDOWN, audit, row, w  # noqa: E402


class T(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        rows = [row(1, "Script 30", ["111", "112"], 1000, 50, 1500),
                row(2, "Touch Face", ["221"], 800, 20, 900),
                row(3, "Plain", ["331"], 600, 10, 500),
                row(4, "Dud", ["441"], 900, 5, 300),
                row(5, "Tiny", ["551"], 50, 1, 40)]
        self.a1 = audit(self.root, "2025", "2025-01-01", "2026-11-02", rows)
        w(self.a1, "teardowns/01-script-30/teardown.md", TEARDOWN)
        self.feed_path = self.root / "runs/winners/acme/feed.md"
        self.bank_path = self.root / "runs/winners/acme/bank.json"

    def tearDown(self):
        self._t.cleanup()

    def run_bank(self, *args):
        return bank.main(["--brand", "acme", "--root", str(self.root), *args])

    def run_feed(self, *args):
        return feed.main(["--brand", "acme", "--root", str(self.root), *args])

    def test_feed_reads_bank(self):
        self.run_bank("--audit", str(self.a1))
        self.assertEqual(self.run_feed("--top", "8"), 0)
        md = self.feed_path.read_text()
        self.assertIn("Source: `runs/winners/acme/bank.json`", md)
        self.assertIn("window 2025-01-01 to 2026-11-02", md)
        self.assertIn("### W1 · `acme-111` · Script 30", md)
        self.assertIn("- Numbers: 50 purchases · spend $1,000 · CPA $20 · ROAS 1.50", md)
        self.assertIn('- Hook: Spoken: "Why did no one tell me', md)
        # median spend 800; above it: 1000 (CPA 20), 900 (CPA 180) -> Dud
        self.assertIn("### L1 · `acme-441` · Dud", md)
        self.assertLess(md.index("## Winners"), md.index("## Loser"))
        self.assertIn("Bar: OPEN", md)

    def test_feed_is_byte_stable(self):
        self.run_bank("--audit", str(self.a1))
        self.run_feed()
        first = self.feed_path.read_text()
        self.run_feed()
        self.assertEqual(self.feed_path.read_text(), first)

    def test_feed_bad_input(self):
        cmd = [sys.executable, str(COMPONENT / "feed.py"), "--root", str(self.root), "--brand", "acme"]
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 2)

    def test_with_a_bar_only_winners_and_it_says_so(self):
        self.run_bank("--audit", str(self.a1))
        b = bank.load_bank(self.bank_path, "acme")
        b["bar"]["max_cpa"] = 25
        bank.write(self.root, b)
        self.run_feed()
        md = self.feed_path.read_text()
        winners = md[md.index("## Winners"):md.index("## Loser")]
        self.assertIn("acme-111", winners)
        self.assertNotIn("acme-221", winners)
        self.assertIn("only rows that clear it are listed", md)

    def test_with_a_bar_nothing_clears(self):
        self.run_bank("--audit", str(self.a1))
        b = bank.load_bank(self.bank_path, "acme")
        b["bar"]["max_cpa"] = 1
        bank.write(self.root, b)
        self.assertEqual(self.run_feed(), 0)
        self.assertIn("No row clears the bar.", self.feed_path.read_text())

    def test_a_second_pull_of_one_window_keeps_every_row(self):
        self.run_bank("--audit", str(self.a1))
        win = json.loads((self.a1 / "window.json").read_text())
        win["pulled_at"] = "2026-11-03T09:00:00"
        (self.a1 / "window.json").write_text(json.dumps(win))
        ranked = json.loads((self.a1 / "ranked.json").read_text())
        ranked["rows"].append(row(6, "New one", ["661"], 40, 1, 20))
        (self.a1 / "ranked.json").write_text(json.dumps(ranked))
        self.run_bank("--audit", str(self.a1))
        self.assertEqual(self.run_feed(), 0)
        self.assertIn("acme-111", self.feed_path.read_text())


if __name__ == "__main__":
    unittest.main()
