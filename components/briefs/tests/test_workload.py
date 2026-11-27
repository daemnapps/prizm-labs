import copy
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

spec = importlib.util.spec_from_file_location('workload', Path(__file__).parents[1] / 'workload.py')
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class WorkloadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.put('team/people/maker/identity.json', {'person': 'maker', 'emails': ['private'], 'slack_id': 'private'})
        self.put('components/image-edit/delivery.json', {'roles': {'video-editor': {'filled_by': 'Maker'}}})
        self.key = 'acme_product_brief-0001'
        self.folder = 'runs/handoffs/video-editor/acme/' + self.key
        self.row = {'id': self.key, 'who': 'Maker', 'created': '2026-11-01T10:00:00',
                    'history': [{'stage': 'making', 'at': '2026-11-02T10:00:00'}],
                    'pack': {'role': 'video-editor', 'returned': 3}}
        self.now = datetime(2026, 11, 3, 3, tzinfo=timezone.utc)

    def put(self, path, data):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data))

    def read(self, row=None, **kwargs):
        return w.enrich({'items': [self.row if row is None else row], 'removed': []}, self.root,
                        legacy_offset_minutes=420, now=self.now, **kwargs)

    def test_uploads_are_not_completion_and_usage_is_unknown(self):
        out = self.read()
        flow = out['items'][0]['workflow']
        self.assertIsNone(flow['completed_at'])
        self.assertIsNone(flow['tokens'])
        self.assertEqual(flow['maker_elapsed_hours'], 24)
        self.assertEqual(flow['queue_elapsed_hours'], 48)
        self.assertNotIn('emails', str(out))
        self.assertNotIn('slack_id', str(out))
        self.assertNotIn('workflow', self.row)

    def test_revisions_do_not_reset_original_clock_or_restore_archives(self):
        self.put(self.folder + '/delivery-state.json', {'state': 'back-for-revision', 'round': 2,
                 'revision_id': self.key + '-R02', 'updated_at': '2026-11-03T02:00:00Z'})
        out = w.enrich({'items': [], 'removed': [self.row]}, self.root, 420, self.now)
        flow = out['removed'][0]['workflow']
        self.assertEqual(out['items'], [])
        self.assertEqual(flow['revision_round'], 2)
        self.assertEqual(flow['revision_elapsed_hours'], 1)
        self.assertEqual(flow['maker_elapsed_hours'], 24)
        self.assertEqual(flow['person_id'], 'maker')

    def test_checked_completion_freezes_elapsed_and_clear_assignment_stays_clear(self):
        self.put(self.folder + '/delivery-state.json', {'state': 'ready-for-review',
                 'updated_at': '2026-11-02T15:00:00Z'})
        row = copy.deepcopy(self.row)
        row['who'] = ''
        flow = self.read(row)['items'][0]['workflow']
        self.assertEqual(flow['maker_elapsed_hours'], 12)
        self.assertEqual(flow['assignment_state'], 'unassigned')
        self.assertIsNone(flow['person_id'])
        self.assertEqual(flow['role_default'], 'Maker')

    def test_missing_dates_remain_unknown(self):
        flow = self.read({'id': self.key})['items'][0]['workflow']
        self.assertIsNone(flow['queue_elapsed_hours'])
        self.assertIsNone(flow['maker_elapsed_hours'])


if __name__ == '__main__':
    unittest.main()
