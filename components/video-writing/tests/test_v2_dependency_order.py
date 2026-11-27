"""Actual v2 dependencies invalidate old writing without erasing artifacts or retry limits."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

COMP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COMP / 'machine'))
sys.path.insert(0, str(COMP.parent / 'video-teardown/machine'))
import writing_v2 as W
import run as R


class V2Dependencies(unittest.TestCase):
    def passes(self):
        return [{'key': p[0], 'splits': p[5]} for p in W.PASSES]

    def state(self):
        return {'brand': 'test-brand', 'slug': 'test-run',
                '_order': ['stage0', 'stage1b', 'stage2', 'stage3', 'stage4r', 'stage4b', 'stage5'],
                'stages': {k: {'status': 'done', 'out': 'stages/' + k + '.md'}
                           for k in ['stage0', 'stage1b', 'stage2', 'stage3', 'stage4i',
                                     'stage4v2a', 'stage4r', 'stage4b', 'stage4v2b', 'stage5']},
                'writing_retry_budget': {'limit': 2, 'used': 2, 'pending': [], 'history': []}}

    def test_existing_stale_injection_invalidates_legacy_idea_and_emitted_files(self):
        st = self.state()
        st['stages']['stage3']['status'] = 'stale'
        W.register_pass_order(st, self.passes())
        self.assertLess(st['_order'].index('stage3'), st['_order'].index('stage4i'))
        self.assertLess(st['_order'].index('stage4i'), st['_order'].index('stage4v2a'))
        for key in ['stage4i', 'stage4v2a', 'stage4r', 'stage4b', 'stage4v2b', 'stage5']:
            self.assertEqual(st['stages'][key]['status'], 'stale', key)
        self.assertEqual(st['writing_retry_budget']['used'], 2)

    def test_real_engine_spec_rewrite_invalidates_v2_only_idea(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / 'prompts').mkdir()
            prompt = d / 'template.md'
            prompt.write_text('Return the source specification.')
            st = self.state()
            W.register_pass_order(st, self.passes())
            (d / 'run.json').write_text(json.dumps(st))
            stage = {'key': 'stage2', 'id': '2', 'name': 'Spec', 'prompt': str(prompt),
                     'version': 1, 'engine': 'claude', 'vars': {}, 'per_run': [], 'role': 'stage'}
            def writer(text, out, model=None):
                out.write_text('Changed source specification with its source evidence.')
                return 'fake'
            with patch.object(R, 'claude', side_effect=writer), patch.object(R, 'creative_qc'), \
                 patch.object(R, 'record_time'), patch.object(R, 'TMP', d / 'tmp'), \
                 patch.object(R.C, 'chain_version', return_value='v1'):
                self.assertTrue(R.run_stage(d, st, stage, {}, redo=True))
            self.assertEqual(st['stages']['stage4i']['status'], 'stale')
            self.assertEqual(st['stages']['stage5']['status'], 'stale')
            self.assertEqual(st['writing_retry_budget']['used'], 2)

    def test_story_change_preserves_artifacts_and_held_budget_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / 'stages').mkdir()
            artifact = d / 'stages/idea.md'
            artifact.write_text('Historical idea, preserved.')
            (d / 'story.md').write_text('Original story')
            src = d / 'revised-story.md'
            src.write_text('Correct signed story')
            st = self.state()
            st['stages']['stage5'] = {'status': 'held', 'error': 'audit_retry_budget_exhausted'}
            (d / 'run.json').write_text(json.dumps(st))
            got = W.lock_story(d, src)
            self.assertEqual(got['stages']['stage4i']['status'], 'stale')
            self.assertEqual(got['stages']['stage5']['status'], 'held')
            self.assertEqual(got['writing_retry_budget']['used'], 2)
            self.assertEqual(artifact.read_text(), 'Historical idea, preserved.')

    def test_corrective_notes_survive_hand_hold_and_clear_only_on_success(self):
        for completed in (False, True):
            with self.subTest(completed=completed), tempfile.TemporaryDirectory() as tmp:
                d = Path(tmp)
                notes = {'stage': 'stage3', 'notes': 'Exact corrective request from the real gate.'}
                st = {'brand': 'test-brand', 'slug': 'test-run', 'production_route': 'ai',
                      'writing_lane': {'lane': 'swipe'}, 'stages': {}, 'viewer_redo': notes,
                      'writing_retry_budget': {'limit': 2, 'used': 1, 'pending': ['stage3'], 'history': []}}
                (d / 'run.json').write_text(json.dumps(st))
                stage = {'key': 'stage3', 'id': '3', 'name': 'Injection'}
                def attempt(folder, current, planned, extras, redo=False):
                    current['stages']['stage3'] = {'status': 'done' if completed else 'error'}
                    R.save(folder, current)
                    return completed
                with patch.object(W, 'apply_call', side_effect=lambda d, st: st), \
                     patch.object(W, 'format_approved', return_value=True), \
                     patch.object(W, 'keep_controls_preset'), patch.object(W, 'run_inputs', return_value={}), \
                     patch.object(W, 'plan', return_value=[stage]), patch.object(R, 'claude'), \
                     patch.object(R, 'run_stage', side_effect=attempt):
                    W.run_writing(d, st, {})
                got = json.loads((d / 'run.json').read_text())
                if completed:
                    self.assertNotIn('viewer_redo', got)
                else:
                    self.assertEqual(got['viewer_redo'], notes)
                    self.assertEqual(got['writing_retry_budget']['pending'], ['stage3'])
                self.assertEqual(got['writing_retry_budget']['used'], 1)

    def test_same_story_does_not_invalidate_completed_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / 'story.md').write_text('Same signed story')
            (d / 'run.json').write_text(json.dumps(self.state()))
            got = W.lock_story(d, d / 'story.md')
            self.assertEqual(got['stages']['stage4i']['status'], 'done')


if __name__ == '__main__':
    unittest.main()
