"""A consumed session hand uses the normal persisted audit retry budget, without fake calls."""
import hashlib
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

COMP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COMP / 'machine'))
sys.path.insert(0, str(COMP.parent / 'video-teardown/machine'))
import writing_v2 as W
import run as R


class HandAuditRetry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        for name in ('stages', 'hand', 'prompts'):
            (self.d / name).mkdir()
        self.st = {'brand': 'fixture', 'slug': 'fixture', 'production_route': 'ai',
                   'writing_lane': {'lane': 'swipe'}, 'stages': {},
                   'writing_retry_budget': {'limit': 2, 'used': 0, 'pending': [], 'history': []}}
        self.save()
        self.plan = [{'key': k, 'id': k, 'name': k, 'splits': None}
                     for k in ('stage3', 'stage4e')]
        self.audit_attempts = 0

    def save(self):
        (self.d / 'run.json').write_text(json.dumps(self.st))

    def audit(self, current, identity='original'):
        prompt = 'Full configured audit input: ' + identity
        answer = 'VERDICT: RE-RUN INJECTION\nRepair the real source finding. ' + identity
        (self.d / 'hand/4f-audit.prompt.md').write_text(prompt)
        (self.d / 'prompts/4f-audit.md').write_text(prompt)
        (self.d / 'hand/4f-audit.md').write_text(answer)
        (self.d / 'stages/4f-audit.md').write_text(answer)
        current['stages']['stage4e'] = {'status': 'held', 'model': 'session-hand',
                                       'out': 'stages/4f-audit.md', 'sent': 'prompts/4f-audit.md'}

    def execute(self, *, new_audits=False, historical=False, paid=False):
        def attempt(d, current, p, extras, redo=False):
            if p['key'] == 'stage3':
                current['stages']['stage3'] = {'status': 'done'}
                R.save(d, current)
                return True
            self.audit_attempts += 1
            if not historical:
                self.audit(current, str(self.audit_attempts) if new_audits else 'original')
            if paid:
                current['stages']['stage4e']['model'] = 'configured-writer'
                W._CURRENT['calls'] = [{'stage': 'stage4e', 'cost_usd': 0, 'api_seconds': 0}]
            R.save(d, current)
            return False
        with ExitStack() as stack:
            for name, value in [('apply_call', lambda d, st: st), ('format_approved', lambda st: True),
                                ('keep_controls_preset', lambda *a: None), ('run_inputs', lambda st: {}),
                                ('declared_layers', lambda st: ''), ('plan', lambda *a: self.plan)]:
                stack.enter_context(patch.object(W, name, side_effect=value))
            stack.enter_context(patch.object(W, '_HAND', [str(self.d / 'hand')]))
            stack.enter_context(patch.object(R, 'run_stage', side_effect=attempt))
            stack.enter_context(patch.object(R, 'say'))
            stack.enter_context(patch.object(R, 'claude'))
            self.assertFalse(W.run_writing(self.d, self.st, {}))
        self.st = json.loads((self.d / 'run.json').read_text())

    def test_fresh_hand_rerun_reserves_once_without_paid_calls(self):
        self.execute()
        self.assertEqual(self.st['writing_retry_budget']['used'], 1)
        self.assertEqual(len(self.st['writing_retry_budget']['hand_audits']), 1)
        receipt = self.st['writing_retry_budget']['hand_audits'][0]
        self.assertEqual(receipt['answer_sha256'], hashlib.sha256(
            (self.d / 'hand/4f-audit.md').read_bytes()).hexdigest())
        self.assertFalse(self.st.get('writing_v2_calls'))
        self.assertEqual(self.st['stages']['stage4e']['calls'], [])

    def test_legacy_held_audit_recovers_once_and_repeated_resume_adds_no_budget(self):
        self.audit(self.st)
        self.save()
        self.execute(historical=True)
        self.assertEqual(self.st['writing_retry_budget']['used'], 1)
        before = self.st['writing_retry_budget'].copy()
        self.execute(historical=True)
        self.assertEqual(self.st['writing_retry_budget'], before)
        self.assertEqual(len(self.st['writing_retry_budget']['hand_audits']), 1)

    def test_stripped_lead_comment_cannot_reserve_same_audit_again(self):
        self.execute()
        answer = self.d / 'hand/4f-audit.md'
        answer.write_text('<!-- Cosmetic provenance note, not audit content. -->\n\n' + answer.read_text())
        self.execute(historical=True)
        self.assertEqual(self.st['writing_retry_budget']['used'], 1)
        self.assertEqual(len(self.st['writing_retry_budget']['hand_audits']), 1)

    def test_distinct_real_audits_stop_at_two_then_resume_cannot_allocate(self):
        self.execute(new_audits=True)
        self.assertEqual(self.st['writing_retry_budget']['used'], 2)
        self.assertEqual(len(self.st['writing_retry_budget']['hand_audits']), 2)
        self.assertEqual(self.audit_attempts, 3)
        # repairs spent: the audit's findings ride on as notes and the line goes on (owner ruling, 2026-11-20)
        self.assertTrue(self.st['stages']['stage4e']['audit_spent'])
        self.assertIn('Repair the real source finding', self.st['writing_notes']['audit'][-1]['words'])
        attempts = self.audit_attempts
        self.execute(new_audits=True)
        self.assertEqual(self.audit_attempts, attempts)
        self.assertEqual(self.st['writing_retry_budget']['used'], 2)

    def test_preexisting_exhausted_budget_goes_on_with_the_audit_as_a_note(self):
        self.st['writing_retry_budget']['used'] = 2
        self.audit(self.st)
        self.save()
        self.execute(historical=True)
        self.assertEqual(self.st['writing_retry_budget']['used'], 2)
        self.assertFalse(self.st['writing_retry_budget'].get('hand_audits'))
        self.assertTrue(self.st['stages']['stage4e']['audit_spent'])
        self.assertNotIn('error', self.st['stages']['stage4e'])
        self.assertEqual(self.audit_attempts, 1)
        attempts = self.audit_attempts
        self.execute(historical=True)                   # resume: the spent audit is never asked again
        self.assertEqual(self.audit_attempts, attempts)

    def test_normal_writer_keeps_the_existing_two_attempt_path(self):
        self.execute(new_audits=True, paid=True)
        self.assertEqual(self.st['writing_retry_budget']['used'], 2)
        self.assertEqual(self.audit_attempts, 3)
        self.assertFalse(self.st['writing_retry_budget'].get('hand_audits'))
        self.assertEqual(len(self.st['writing_v2_calls']), 3)

    def test_unmatched_or_unconsumed_hand_cannot_recover_audit(self):
        self.audit(self.st)
        with patch.object(W, '_HAND', [str(self.d / 'hand')]):
            self.assertIsNotNone(W.unhandled_hand_audit(self.d, self.st))
            (self.d / 'hand/4f-audit.prompt.md').write_text('different configured request')
            self.assertIsNone(W.unhandled_hand_audit(self.d, self.st))
            self.audit(self.st)
            (self.d / 'hand/4f-audit.md').write_text('changed unconsumed answer')
            self.assertIsNone(W.unhandled_hand_audit(self.d, self.st))
            self.audit(self.st)
            self.st['stages']['stage4e']['model'] = 'other-writer'
            self.assertIsNone(W.unhandled_hand_audit(self.d, self.st))


if __name__ == '__main__':
    unittest.main()
