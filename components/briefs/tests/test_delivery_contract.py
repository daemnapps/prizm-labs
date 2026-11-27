import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import delivery_contract as D
sys.path.insert(0, str(HERE.parent / 'meta-upload'))
import delivery_gate as G


class ContractTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.folder = self.root / 'runs/handoffs/graphic-designer/acme/acme_product_brief-0001'
        self.folder.mkdir(parents=True)
        (self.folder / 'BRIEF.md').write_text('# Brief\n')
        D.pack(self.folder, record={'variations': [{'id': 'v1'}, {'id': 'v2'}]})

    def tearDown(self):
        self.tmp.cleanup()

    def submission(self):
        state = D.read(self.folder / D.STATE)
        sub = D.read(D.template(self.folder))
        sub.update(submitted_by='maker', submitted_at=D.now())
        for check in sub['checks'].values():
            check.update(checked=True, by='reviewer', at=D.now(), evidence='Inspected finished image')
        for i, item in enumerate(sub['items']):
            f = self.folder / ('image%d.png' % i)
            f.write_bytes(bytes([i + 1]))
            item.update(file=f.name, sha256=D.sha(f), creative_changes='Alternative wording')
        path = self.folder / 'returned' / state['revision_id'] / D.SUBMISSION
        D.write(path, sub)
        return sub, path

    @patch.object(D, 'media_info', return_value=(1080, 1920))
    def test_missing_and_unchecked_are_held(self, _):
        with self.assertRaisesRegex(D.Incomplete, 'Missing completed submission'):
            D.validate(self.folder)
        sub, path = self.submission()
        sub['items'].pop()
        D.write(path, sub)
        with self.assertRaisesRegex(D.Incomplete, 'every required slot'):
            D.validate(self.folder)
        sub, path = self.submission()
        sub['checks']['facts']['checked'] = False
        D.write(path, sub)
        with self.assertRaisesRegex(D.Incomplete, 'Unchecked criterion: facts'):
            D.validate(self.folder)

    @patch.object(D, 'media_info', return_value=(1080, 1920))
    def test_complete_alternative_passes_but_changed_and_duplicate_files_fail(self, _):
        sub, path = self.submission()
        self.assertEqual(len(D.validate(self.folder)['rows']), 2)
        (self.folder / 'image0.png').write_bytes(b'changed')
        with self.assertRaisesRegex(D.Incomplete, 'File changed'):
            D.validate(self.folder)
        sub, path = self.submission()
        sub['items'][1].update(file=sub['items'][0]['file'], sha256=sub['items'][0]['sha256'])
        D.write(path, sub)
        with self.assertRaisesRegex(D.Incomplete, 'same file'):
            D.validate(self.folder)

    @patch.object(D, 'media_info', return_value=(1080, 1920))
    def test_revision_keeps_history_idempotent_and_rejects_old_submission(self, _):
        sub, oldpath = self.submission()
        request = D.request_revision(self.folder, 'Fix missing items', 'owner', 'return-1')
        self.assertTrue(request['revision_id'].endswith('-R01'))
        self.assertEqual(request, D.request_revision(self.folder, 'Fix missing items', 'owner', 'return-1'))
        self.assertTrue(oldpath.exists())
        with self.assertRaisesRegex(D.Incomplete, 'stale revision'):
            D.validate(self.folder, oldpath)
        with self.assertRaisesRegex(D.Incomplete, 'already open'):
            D.request_revision(self.folder, 'Again', 'owner', 'return-2')
        self.submission()
        state = D.read(self.folder / D.STATE)
        state['state'] = 'ready-for-review'
        D.write(self.folder / D.STATE, state)
        request2 = D.request_revision(self.folder, 'Adjust scene', 'owner', 'return-2')
        self.assertTrue(request2['revision_id'].endswith('-R02'))
        self.assertNotEqual(request['batch'], request2['batch'])

    @patch.object(D, 'media_info', return_value=(1080, 1920))
    def test_gate_rejects_partial_filing_and_path_escape(self, _):
        self.submission()
        with self.assertRaisesRegex(D.Incomplete, 'complete validated'):
            D.gate('acme', 'brief-0001', 'product', [self.folder / 'image0.png'], None, repo=self.root)
        with self.assertRaises(D.Incomplete):
            D.inside(self.folder, '../../outside.png')
        with self.assertRaisesRegex(D.Incomplete, 'no issued handoff'):
            D.gate('acme', 'brief-0002', 'product', [], None, {'tool': 'video-editor'}, self.root)

    def test_video_contract_requires_all_openings_and_covers(self):
        f = self.root / 'runs/handoffs/video-editor/acme/acme_product_brief-0002'
        f.mkdir(parents=True)
        (f / 'BRIEF.md').write_text('**Opening 1 · Control**\n**Opening 2 · Alternate**\n')
        req = D.pack(f)
        self.assertEqual(len(req['slots']), 2)
        self.assertTrue(all(x['cover_required'] for x in req['slots']))

    @patch.object(D, 'media_info', return_value=(1080, 1920))
    def test_video_without_cover_is_held(self, _):
        req = D.read(self.folder / D.CONTRACT)
        req['slots'][0].update(kind='video', cover_required=True)
        D.write(self.folder / D.CONTRACT, req)
        self.submission()
        with self.assertRaisesRegex(D.Incomplete, 'relative path'):
            D.validate(self.folder)

    def test_ledger_shows_revision_and_preserves_other_briefs(self):
        import ledger
        request = D.request_revision(self.folder, 'Finish all versions', 'owner', 'ledger-return')
        queue = self.root / 'runs/queue'
        queue.mkdir(parents=True)
        D.write(queue / 'brief-ledger.json', {'briefs': [
            {'key': self.folder.name, 'id': '0001', 'brand': 'acme', 'type': 'image', 'status': 'Production',
             'handoff': str(self.folder.relative_to(self.root))},
            {'key': 'unrelated', 'id': '0002', 'brand': 'acme', 'status': 'Live'}]})
        result = ledger.refresh_delivery_states(self.root)['briefs']
        self.assertEqual(result[0]['status'], 'Back for revision')
        self.assertEqual(result[0]['revision_id'], request['revision_id'])
        self.assertEqual(result[1]['status'], 'Live')
        self.assertIn('R01', (queue / 'BRIEF-LEDGER.md').read_text())

    def test_unresolved_scope_is_held_and_can_be_issued_once_defined(self):
        f = self.root / 'runs/handoffs/video-editor/acme/acme_product_brief-0003'
        f.mkdir(parents=True)
        req = D.pack(f)
        self.assertEqual(req['state'], 'needs-scope')
        with self.assertRaisesRegex(D.Incomplete, 'scope is unresolved'):
            D.validate(f)
        req = D.pack(f, record={'deliver': ['control.mp4']})
        self.assertEqual(req['state'], 'ready')

    def test_approval_rejects_missing_receipt(self):
        card = {'brand': 'acme', 'brief_id': 'brief-0001', 'product': 'product', 'made_by': {'tool': 'graphic-designer'}}
        with patch.object(G, 'ROOT', self.root):
            check = G.check(self.root, card)['delivery_complete']
        self.assertFalse(check['ok'])


if __name__ == '__main__':
    unittest.main()
