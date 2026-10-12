"""SI-140 (objection banks named): a brand's missing objection-bank files are
named, never skipped in silence — offline, stdlib unittest, a temp workspace
(python3 tests/test_bank_missing.py)."""
import sys, tempfile, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from marketing_chain_checks import viewer as V

B = "si140-test-brand"
CORE, CX, OFFERS = ("core-avatars/objection-bank.md", "customer-experience/objection-bank.md",
                    "offers/objection-answers.md")


class BankMissing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        self.patch = mock.patch.object(V, "WS", self.ws)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def keep(self, *names):
        for n in names:
            f = self.ws / "brands" / B / n
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(f'# {n}\n- "it burns" — answer for {n}\n')

    def test_one_of_three_names_the_other_two(self):
        self.keep(CORE)
        t = V.bank_text(B)
        self.assertIn(f"=== missing: brands/{B}/{CX} (not in this brand's folder) ===", t)
        self.assertIn(f"=== missing: brands/{B}/{OFFERS} (not in this brand's folder) ===", t)
        self.assertNotIn(f"missing: brands/{B}/{CORE}", t)
        self.assertIn(f"=== brands/{B}/{CORE} ===\n# {CORE}", t)      # the bank it has, as before
        self.assertEqual(V.bank_missing(B), [f"brands/{B}/{CX}", f"brands/{B}/{OFFERS}"])
        self.assertFalse((self.ws / "brands" / B / CX).exists())      # nothing created

    def test_all_three_no_missing_line(self):
        self.keep(CORE, CX, OFFERS)
        t = V.bank_text(B)
        self.assertNotIn("=== missing:", t)
        for n in (CORE, CX, OFFERS):
            self.assertIn(f"=== brands/{B}/{n} ===", t)
        self.assertEqual(V.bank_missing(B), [])

    def doubt(self):
        return [{"believe": "no", "doubt": "it would burn my skin"}]

    def test_the_match_record_carries_bank_missing(self):
        self.keep(CORE)
        sent = []
        ob = V.objections(self.doubt(), B, "si140-avatar",
                          caller=lambda text, *a: sent.append(text) or {"matches": [], "new_objections": []})
        self.assertEqual(ob["bank_missing"], [f"brands/{B}/{CX}", f"brands/{B}/{OFFERS}"])
        self.assertIn(f"=== missing: brands/{B}/{CX}", sent[0])      # the match is told it ran on part of the bank

    def test_no_bank_still_skips_and_names_all_three(self):
        called = []
        ob = V.objections(self.doubt(), B, "si140-avatar", caller=lambda *a: called.append(1) or {})
        self.assertEqual(ob["skipped"], "no objection bank on file")
        self.assertEqual(ob["bank_missing"], [f"brands/{B}/{n}" for n in (CORE, CX, OFFERS)])
        self.assertEqual(called, [])                                   # nothing refused, no model asked

    def test_the_rewrite_records_its_two_files(self):
        self.keep(CX)
        brief = 'Frame 9 text: old line\n'
        out = ('=== BRIEF ===\nFrame 9 text: new line\n=== END BRIEF ===\n'
               '=== CHANGES ===\n{"changes":[{"where":"Frame 9","was":"old line","now":"new line"}]}\n=== END CHANGES ===')
        _, ch = V.fix(brief, {"fix_at": "proof", "notes": "n"}, B, "si140-avatar", caller=lambda *a: out)
        self.assertEqual(ch["bank_missing"], [f"brands/{B}/{CORE}"])
        self.assertEqual(ch["changes"][0]["now"], "new line")


if __name__ == "__main__":
    unittest.main(verbosity=1)
