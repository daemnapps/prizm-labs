"""Revalidation supplies only its own run's historical section receipts."""
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock
import test_writing_revalidate as T
V, complete = T.V, T.complete

class CacheWiring(unittest.TestCase):
    setUp = T.Revalidation.setUp
    def test_public_revalidation_passes_same_run_receipt_folders(self):
        old = self.d / 'revalidation/earlier/snapshot/section-fit-revalidation'
        old.mkdir(parents=True)
        other = self.d.parent / (self.d.name + '-peer')
        seen = []
        def checker(d, st, out, section_cache_dirs):
            seen.append(section_cache_dirs)
            return complete(d, st, out)
        with mock.patch.object(V, 'check_final', side_effect=checker):
            V.revalidate(self.d)
        self.assertIn(self.d.resolve() / 'section-fit', seen[0])
        self.assertIn(old.resolve(), seen[0])
        self.assertTrue(all(self.d.resolve() in p.parents for p in seen[0]))
        self.assertNotIn(other, seen[0])

    def test_final_checker_forwards_receipts_to_section_gate(self):
        doc = {'scenes': [{'id': 'S1', 'section': 'proof', 'voice': 'A source account.'}]}
        out = self.d / 'brief-cache-test.md'; out.write_text('```json\n' + json.dumps(doc) + '\n```\n')
        seen = []
        modules = {'slotfill': SimpleNamespace(holes_of=lambda doc: []),
                   'scenes': SimpleNamespace(json_block=lambda text: (doc, None)),
                   'sectionfit': SimpleNamespace(plan_of=lambda path: doc,
                       check=lambda plan, **kw: seen.append(kw) or {'pass': False, 'scenes': [{'id': 'S1'}]})}
        folders = [self.d / 'section-fit']
        with mock.patch.object(V, 'module', side_effect=lambda c, n: modules[n]), \
                mock.patch.object(V, 'claims_check', return_value={'passed': True}):
            checks = V.check_final(self.d, {}, out, section_cache_dirs=folders)
            next(checks); next(checks); next(checks); checks.close()
        self.assertEqual(seen[0]['cache_dirs'], folders)

if __name__ == '__main__': unittest.main()
