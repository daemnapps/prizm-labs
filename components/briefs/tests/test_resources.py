import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
import resources


class ResourcesTest(unittest.TestCase):
    def setUp(self):
        self.queue = {'workforce': [{'id': 'maker', 'name': 'Maker', 'roles': []},
                                    {'id': 'reviewer', 'name': 'Reviewer', 'roles': []}],
                      'items': [], 'backlog': []}
        self.now = datetime(2026, 11, 19, tzinfo=timezone.utc)

    def project(self, dev):
        return resources.project(self.queue, dev, now=self.now)

    def test_every_identity_stays_visible_even_with_no_work(self):
        out = self.project({})
        self.assertEqual([p['id'] for p in out['resources']], ['maker', 'reviewer', None])
        self.assertEqual([p['total'] for p in out['resources']], [0, 0, 0])

    def test_no_assignment_inferred_from_builder_and_reviews_are_separate(self):
        out = self.project({'cards': [
            {'id': 'build', 'title': 'Build', 'state': 'up-next', 'developer': 'maker', 'assignee': None},
            {'id': 'review', 'title': 'Review', 'state': 'shipped', 'developer': 'maker',
             'review': [{'person': 'maker', 'understood': True}, {'person': 'reviewer', 'understood': None}],
             'merged': {'at': '2026-11-18T00:00:00Z'}}]})
        maker, reviewer, unassigned = out['resources']
        self.assertEqual(maker['total'], 0)
        self.assertEqual(reviewer['counts']['review'], 1)
        self.assertEqual(reviewer['queue'][0]['elapsed_hours'], 24)
        self.assertEqual(unassigned['queue'][0]['work_id'], 'build')

    def test_private_completed_and_duplicate_acts_excluded(self):
        issue = {'id': 'follow', 'title': 'Follow up', 'kind': 'follow-up', 'state': 'raised', 'assignees': ['maker']}
        out = self.project({'cards': [{'id': 'private', 'private': True, 'state': 'up-next', 'assignee': 'maker'},
                                     {'id': 'done', 'state': 'shipped', 'review': [{'person': 'maker', 'understood': True}]}],
                            'issues': [issue, dict(issue, id='closed', state='done')], 'acts': [issue]})
        self.assertEqual(out['resources'][0]['total'], 1)
        self.assertEqual(out['resources'][0]['queue'][0]['work_id'], 'follow')

    def test_creative_nonbrief_backlog_and_unresolved_are_not_hidden(self):
        self.queue['items'] = [{'id': 'email-month', 'title': 'Email', 'who': 'Maker', 'stage': 'making',
                               'workflow': {'person_id': 'maker', 'queue_elapsed_hours': 5}},
                              {'id': 'live', 'stage': 'live'},
                              {'id': 'unknown', 'who': 'Unmapped', 'stage': 'brief', 'workflow': {}}]
        self.queue['backlog'] = [{'id': 'later', 'stage': 'idea', 'workflow': {'person_id': 'maker'}}]
        out = self.project({})
        self.assertEqual(out['resources'][0]['counts']['active'], 1)
        self.assertEqual(out['resources'][0]['counts']['backlog'], 1)
        self.assertEqual(out['resources'][-1]['queue'][0]['unresolved_assignment'], 'Unmapped')

    def test_role_handoffs_join_actual_task_state_not_old_manifest(self):
        roles = {'tasks': [
            {'id': 'new-promo', 'title': 'Prepare promo', 'status': 'todo', 'assignees': ['maker'],
             'priority': 1, 'due': '2026-11-28', 'role': 'project-manager', 'card': 'runs/role-handoffs/promo/START.md', 'handoff': 'Finish the preview'},
            {'id': 'closed', 'title': 'Already done', 'status': 'done', 'assignees': ['maker']} ]}
        out = resources.project(self.queue, {}, now=self.now, role_view=roles)
        row = out['resources'][0]['queue'][0]
        self.assertEqual(out['resources'][0]['total'], 1)
        self.assertEqual(row['source'], 'role-handoffs')
        self.assertEqual(row['due'], '2026-11-28')
        self.assertEqual(row['handoff'], 'Finish the preview')
        self.assertEqual(row['priority'], 'urgent')

    def test_role_handoff_source_error_is_not_empty_workload_claim(self):
        out = resources.project(self.queue, {}, role_view={'error': 'Unavailable'})
        self.assertEqual(out['role_handoffs_error'], 'Unavailable')

    def test_held_work_and_source_failures_visible(self):
        out = self.project({'error': 'Source unavailable', 'cards': [{'id': 'held', 'title': 'Held', 'state': 'up-next',
                            'assignee': 'maker', 'pending': 'held'}]})
        self.assertEqual(out['development_error'], 'Source unavailable')
        self.assertEqual(out['resources'][0]['counts']['blocked'], 1)
        self.assertIsNone(out['resources'][0]['queue'][0]['elapsed_hours'])


if __name__ == '__main__':
    unittest.main()
