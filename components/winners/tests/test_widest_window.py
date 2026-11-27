import argparse, contextlib, io, json, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import audit as A  # noqa: E402
from test_bank import audit, row, w  # noqa: E402
from test_winners import run  # noqa: E402


class Widest(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        self.addCleanup(setattr, A, "REPO", A.REPO)
        A.REPO = self.root
        self.wide = "2025-01-01_2026-11-02"
        self.short = "2026-10-04_2026-11-03"
        audit(self.root, self.wide, "2025-01-01", "2026-11-02", [
            row(1, "All Time One", ["111"], 1000, 50, 1500), row(2, "All Time Two", ["221"], 800, 20, 900),
            row(3, "All Time Three", ["331"], 900, 5, 300)], core=2)
        self.dir = self.root / "runs/winners/acme"
        self.assertEqual(run(self.root, "bank", "--brand", "acme")[0], 0)
        self.assertEqual(run(self.root, "feed", "--brand", "acme")[0], 0)
        self.feed = (self.dir / "feed.md").read_text()
        self.core = self.cores()

    def tearDown(self):
        self._t.cleanup()

    def cores(self):
        return {r["id"]: r.get("core") for r in json.loads((self.dir / "bank.json").read_text())["rows"]}

    def bank_short(self):
        renamed = dict(row(1, "This Month's Name", ["221"], 90, 40, 300), headline="New words", format="Image", body="new")
        audit(self.root, self.short, "2026-10-04", "2026-11-03", [renamed, row(2, "Brand New", ["771"], 50, 30, 100),
                                                                 row(3, "All Time One", ["111"], 10, 1, 5)], core=2)
        self.assertEqual(run(self.root, "bank", "--brand", "acme", "--window", self.short)[0], 0)

    def test_a_30_day_audit_leaves_the_feed_and_core_alone(self):
        before = {r["id"]: r for r in json.loads((self.dir / "bank.json").read_text())["rows"]}
        self.bank_short()
        self.assertEqual(run(self.root, "feed", "--brand", "acme")[0], 0)
        self.assertEqual((self.dir / "feed.md").read_text(), self.feed)
        rows = {r["id"]: r for r in json.loads((self.dir / "bank.json").read_text())["rows"]}
        self.assertEqual({k: rows[k]["core"] for k in self.core}, self.core)
        self.assertFalse(rows["acme-771"]["core"])     # its rows still join the bank
        self.assertEqual(rows["acme-221"]["name"], "All Time Two")
        self.assertEqual(rows["acme-221"]["headline"], before["acme-221"]["headline"])
        self.assertEqual(len(rows["acme-221"]["snapshots"]), 2)   # and its snapshots
        self.assertIn("This Month's Name", rows["acme-221"]["ad_names"])

    def test_a_bar_reads_the_widest_window_too(self):
        run(self.root, "bar", "--brand", "acme", "--max-cpa", "50")
        run(self.root, "feed", "--brand", "acme")
        with_bar = (self.dir / "feed.md").read_text()
        self.bank_short()                              # row 221 now has a newest snapshot at a far lower CPA, 111 a worse one
        run(self.root, "feed", "--brand", "acme")
        self.assertEqual((self.dir / "feed.md").read_text(), with_bar)

    def test_a_wider_audit_takes_over(self):
        audit(self.root, "2024-01-01_2026-11-02", "2024-01-01", "2026-11-02", [row(1, "Older", ["881"], 100, 99, 500)], core=1)
        run(self.root, "bank", "--brand", "acme", "--window", "2024-01-01_2026-11-02")
        run(self.root, "feed", "--brand", "acme")
        self.assertIn("window 2024-01-01 to 2026-11-02", (self.dir / "feed.md").read_text())
        self.assertEqual([k for k, v in self.cores().items() if v], ["acme-881"])

    def test_a_tie_goes_to_the_newest(self):
        audit(self.root, "2025-01-02_2026-11-03", "2025-01-02", "2026-11-03", [row(1, "Same Length", ["991"], 100, 9, 500)], core=1)
        run(self.root, "bank", "--brand", "acme", "--window", "2025-01-02_2026-11-03")
        run(self.root, "feed", "--brand", "acme")
        self.assertIn("window 2025-01-02 to 2026-11-03", (self.dir / "feed.md").read_text())

    def test_feed_window_prints_and_writes_nothing(self):
        self.bank_short()
        code, out, _ = run(self.root, "feed", "--brand", "acme", "--window", self.short)
        self.assertEqual(code, 0)
        self.assertIn("window 2026-10-04 to 2026-11-03", out)
        self.assertIn("acme-771", out)
        self.assertEqual((self.dir / "feed.md").read_text(), self.feed)
        code, _, err = run(self.root, "feed", "--brand", "acme", "--window", "nope")
        self.assertEqual(code, 2)
        self.assertEqual(len(err.strip().splitlines()), 1)

    def cells(self, label):
        d = A.run_dir("acme", label)
        cells = [{"name": n, "month": "2026-10", "spend": s, "purchases": p, "value": s, "ids": [i]}
                 for n, s, p, i in (("Keeper", 100, 10, "1"), ("Copy Of Keeper", 50, 5, "2"), ("Other", 10, 1, "3"))]
        w(d, "cells.json", cells)
        return d

    def rank(self, label):
        with contextlib.redirect_stdout(io.StringIO()):
            A.rank(argparse.Namespace(brand="acme", label=label))
        return {r["name"]: r for r in A.load(A.run_dir("acme", label) / "ranked.json")["rows"]}

    def test_a_new_window_starts_from_the_widest_merges(self):
        w(self.dir / "audit" / self.wide, "merges.json", {"Copy Of Keeper": "Keeper"})
        self.cells(self.short)
        ranked = self.rank(self.short)
        self.assertEqual(ranked["Keeper"]["purchases"], 15)
        self.assertFalse((A.run_dir("acme", self.short) / "merges.json").exists())

    def test_a_window_with_its_own_merges_keeps_them(self):
        w(self.dir / "audit" / self.wide, "merges.json", {"Copy Of Keeper": "Keeper"})
        d = self.cells(self.short)
        w(d, "merges.json", {})
        self.assertEqual(self.rank(self.short)["Keeper"]["purchases"], 10)


if __name__ == "__main__":
    unittest.main()
