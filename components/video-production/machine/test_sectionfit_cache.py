"""Exact section request receipts survive snapshot boundaries; no provider calls."""
import json
import os
from pathlib import Path
import tempfile
import unittest
import sectionfit as sf

PLAN = {'scenes': [{'id': 'S1', 'section': 'solution', 'voice': 'Here is the product in use.'}]}

def reply(fits):
    return json.dumps({'scenes': [{'id': 'S1', 'given': 'solution', 'fits': fits,
                                  'should_be': 'solution' if fits else 'product', 'why': 'Observed job'}], 'order': []})

class CompletedReceipts(unittest.TestCase):
    def test_first_complete_result_is_reused_including_failures_with_exact_evidence(self):
        for first_pass in (False, True):
            with self.subTest(first_pass=first_pass), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp); first, later, out = [base / n for n in ('first', 'later', 'snapshot')]
                expected = sf.check(PLAN, first, call=lambda _: reply(first_pass))
                sf.check(PLAN, later, call=lambda _: reply(not first_pass))
                os.utime(first / 'result.json', ns=(100, 100)); os.utime(later / 'result.json', ns=(200, 200))
                originals = {str(p): p.read_bytes() for d in (first, later) for p in d.iterdir()}
                actual = sf.check(PLAN, out, call=lambda _: self.fail('duplicate provider call'), cache_dirs=[later, first])
                self.assertEqual(actual, expected)
                self.assertEqual(actual['pass'], first_pass)
                receipt = json.loads((out / 'cache-reuse.json').read_text())
                self.assertEqual(receipt['source'], str(first.resolve()))
                for name in receipt['files']:
                    self.assertEqual((out / name).read_bytes(), (first / name).read_bytes())
                self.assertTrue(all(Path(p).read_bytes() == content for p, content in originals.items()))

    def test_existing_later_receipt_is_preserved_before_earlier_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, later = Path(tmp) / 'first', Path(tmp) / 'later'
            expected = sf.check(PLAN, first, call=lambda _: reply(False))
            sf.check(PLAN, later, call=lambda _: reply(True))
            os.utime(first / 'result.json', ns=(100, 100)); os.utime(later / 'result.json', ns=(200, 200))
            before = {p.name: p.read_bytes() for p in later.iterdir()}
            actual = sf.check(PLAN, later, call=lambda _: self.fail('duplicate call'), cache_dirs=[first])
            self.assertEqual(actual, expected)
            history = list((later / 'before-cache-reuse').iterdir())
            self.assertEqual(len(history), 1)
            self.assertTrue(all((history[0] / name).read_bytes() == content for name, content in before.items()))

    def test_changed_request_and_incomplete_receipts_cannot_reuse(self):
        for defect in ('changed request', 'missing read', 'wrong hash', 'incomplete count', 'malformed result'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp); cached, out = base / 'old', base / 'new'
                sf.check(PLAN, cached, call=lambda _: reply(True))
                rules = ''
                if defect == 'changed request': rules = 'New explicit section source.'
                elif defect == 'missing read': (cached / 'reply-3.md').unlink()
                elif defect == 'malformed result': (cached / 'result.json').write_text('[]')
                else:
                    rec = json.loads((cached / 'result.json').read_text())
                    rec['sent_hash' if defect == 'wrong hash' else 'reads'] = 'different' if defect == 'wrong hash' else 2
                    (cached / 'result.json').write_text(json.dumps(rec))
                calls = []
                actual = sf.check(PLAN, out, call=lambda p: calls.append(p) or reply(False),
                                  run_rulings=rules, cache_dirs=[cached])
                self.assertEqual(len(calls), 3)
                self.assertFalse(actual['pass'])
                self.assertFalse((out / 'cache-reuse.json').exists())

if __name__ == '__main__': unittest.main()
