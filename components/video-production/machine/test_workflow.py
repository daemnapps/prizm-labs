#!/usr/bin/env python3
"""Offline workflow orchestration tests; fake commands write only into a temporary workspace."""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workflow as W
import workflow_runner as R


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.oldroot = W.WS
        W.WS = self.root
        self.path = self.root / 'state.json'
        self.values = {'brand': 'test', 'label': 'example'}
        self.state = {'format': 'test', 'values': dict(self.values)}
        self.steps = []
        self.mock = patch.object(W, 'workflow', lambda _, **kwargs: {'what': 'Test workflow', 'steps': self.steps})
        self.mock.start()

    def tearDown(self):
        self.mock.stop()
        W.WS = self.oldroot
        self.tmp.cleanup()

    def write(self, ref, content='example'):
        path = self.root / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def cmd(self, id='build', output='output.txt', paid=False, code=None):
        script = id + '.py'
        self.write(script, code or "from pathlib import Path\nPath(%r).write_text('done')\n" % output)
        return {'id': id, 'name': id, 'component': 'fixture', 'does': 'Build fixture',
                'executor': 'command', 'run': 'python3 ' + script, 'done_when': output, 'paid': paid}

    def advance(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return R.advance('test', self.path, self.state, **kwargs)

    def cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return R.main(list(args))

    def test_later_artifact_cannot_skip_missing_prerequisite(self):
        rows = [{'id': 'idea', 'done': None}, {'id': 'brief', 'done': True}]
        self.assertEqual(W.next_station(rows)['id'], 'idea')

    def test_run_executes_in_order_and_resumes_without_repeating(self):
        self.steps = [self.cmd('one', 'one.txt'), self.cmd('two', 'two.txt')]
        self.assertEqual(self.advance(), 0)
        before = (self.root / 'one.log').read_bytes()
        with patch.object(R.subprocess, 'run', side_effect=AssertionError('repeated command')):
            self.assertEqual(self.advance(), 0)
        self.assertEqual((self.root / 'one.log').read_bytes(), before)
        self.assertEqual(set(self.state['receipts']), {'one', 'two'})

    def test_no_paid_call_without_named_authorization(self):
        self.steps = [self.cmd(paid=True)]
        self.assertEqual(self.advance(), 2)
        self.assertFalse((self.root / 'output.txt').exists())
        self.assertEqual(self.advance(allowed=['build']), 0)

    def test_swipe_setup_is_paid_and_scratch_is_not(self):
        s = self.cmd()
        s['paid_routes'] = ['swipe']
        self.steps = [s]
        self.state['values']['route'] = 'swipe'
        self.assertEqual(self.advance(), 2)
        self.assertFalse((self.root / 'output.txt').exists())
        self.state['values']['route'] = 'scratch'
        self.assertEqual(self.advance(), 0)

    def test_failed_component_stops_and_does_not_retry_automatically(self):
        self.steps = [self.cmd(code='import sys\nsys.exit(3)\n'), self.cmd('later', 'later.txt')]
        self.assertEqual(self.advance(), 2)
        self.assertEqual(self.state['attempts']['build']['exit_code'], 3)
        with patch.object(R.subprocess, 'run', side_effect=AssertionError('unexpected retry')):
            self.assertEqual(self.advance(), 2)
        self.assertFalse((self.root / 'later.txt').exists())
        self.write('build.py', "from pathlib import Path\nPath('output.txt').write_text('fixed')\n")
        self.assertEqual(self.advance(retry='build'), 0)

    def test_interrupted_attempt_requires_inspection_before_retry(self):
        self.steps = [self.cmd()]
        self.state['attempts'] = {'build': {'state': 'running'}}
        self.assertEqual(self.advance(), 2)
        self.assertFalse((self.root / 'output.txt').exists())

    def test_zero_exit_without_output_is_not_success(self):
        self.steps = [self.cmd(code='pass\n')]
        self.assertEqual(self.advance(), 2)
        self.assertNotIn('build', self.state.get('receipts', {}))

    def test_existing_output_is_never_regenerated_blindly(self):
        self.steps = [self.cmd()]
        self.write('output.txt', 'existing')
        with patch.object(R.subprocess, 'run', side_effect=AssertionError('regenerated')):
            self.assertEqual(self.advance(), 2)
        self.assertIn('adopt', self.state['next']['reason'])

    def test_held_writing_with_brief_file_is_incomplete(self):
        self.write('brief.md')
        self.write('run.json', json.dumps({'stages': {'stage5': {'status': 'done'}, 'stage4b': {'status': 'error'}}}))
        step = {'done_when': 'brief.md', 'run_check': {'file': 'run.json', 'stages': ['stage5'], 'reject_incomplete': True}}
        self.assertFalse(W.is_done(step, {}))

    def test_stale_filed_brief_is_not_done(self):
        self.write('working.md', 'new')
        self.write('filed.md', 'old')
        self.assertFalse(W.is_done({'done_when': 'filed.md', 'same_as': 'working.md'}, {}))

    def test_downstream_run_record_updates_do_not_invalidate_setup(self):
        step = self.cmd()
        step['done_when'] = 'run.json'
        step['run_check'] = {'file': 'run.json', 'stages': ['stage0'], 'root_fields': ['brand']}
        self.write('run.json', json.dumps({'brand': 'test', 'stages': {'stage0': {'status': 'done'}}}))
        proof = R.snapshot(['run.json'], step, {})
        self.write('run.json', json.dumps({'brand': 'test', 'stages': {'stage0': {'status': 'done'}, 'stage3': {'status': 'done'}}}))
        self.assertTrue(R.unchanged(proof, step, {}))
        self.write('run.json', json.dumps({'brand': 'different', 'stages': {'stage0': {'status': 'done'}}}))
        self.assertFalse(R.unchanged(proof, step, {}))

    def test_agent_task_requires_all_evidence_and_cannot_skip_ahead(self):
        self.steps = [{'id': 'idea', 'name': 'Idea', 'component': 'research', 'does': 'Find idea',
                       'executor': 'agent', 'evidence': ['concept.md', 'sources.md']}]
        args = ['complete', 'test', '--brand', 'test', '--label', 'example', '--station', 'idea']
        self.write('concept.md')
        self.assertEqual(self.cli(*args), 2)
        self.write('sources.md')
        self.assertEqual(self.cli(*args), 0)
        self.assertEqual(self.cli('run', 'test', '--brand', 'test', '--label', 'example'), 0)
        self.write('sources.md', 'changed evidence')
        self.assertEqual(self.cli('run', 'test', '--brand', 'test', '--label', 'example'), 2)

    def test_dry_run_has_no_writes_and_does_not_execute(self):
        self.steps = [self.cmd()]
        before = sorted(p.name for p in self.root.iterdir())
        with patch.object(R.subprocess, 'run', side_effect=AssertionError('dry-run executed')):
            self.assertEqual(self.cli('run', 'test', '--brand', 'test', '--label', 'example', '--dry-run'), 2)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), before)

    def test_shell_metacharacters_remain_one_argument(self):
        argv = R.command({'run': 'python3 maker.py --story {story}'}, {'story': 'a b; $(touch bad).md'})
        self.assertEqual(argv[-1], 'a b; $(touch bad).md')
        self.assertEqual(argv[0], sys.executable)

    def test_missing_command_input_is_not_executed(self):
        with self.assertRaisesRegex(ValueError, 'missing inputs'):
            R.command({'run': 'python3 maker.py {story}'}, {})

    def test_from_state_keeps_saved_brand_label_and_brief_key(self):
        self.write('handoff.json', json.dumps({'values': dict(self.values, brief_key='brief-123')}))
        self.steps = [{'id': 'manual', 'name': 'Manual', 'component': 'agent', 'does': 'Review', 'run': ''}]
        with patch.object(W, 'status', return_value=[] ) as status, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(W.main(['status', 'test', '--from-state', str(self.root/'handoff.json')]), 0)
        self.assertEqual(status.call_args[0][1]['brief_key'], 'brief-123')
        self.assertEqual(status.call_args[0][1]['label'], 'example')

    def test_review_cannot_be_completed_by_agent_receipt(self):
        self.steps = [{'id': 'review', 'name': 'Review', 'component': 'review', 'does': 'Approve',
                       'executor': 'review', 'gate': 'owner', 'review_asset': 'brief.md'}]
        self.write('brief.md')
        self.assertEqual(self.cli('complete', 'test', '--brand', 'test', '--label', 'example',
                                  '--station', 'review', '--evidence', 'brief.md'), 2)

    def test_no_paths_outside_workspace(self):
        with self.assertRaises(ValueError):
            R.local('../outside.txt')

    def test_changed_input_invalidates_downstream_receipts(self):
        self.steps = [self.cmd('one', 'one.txt'), self.cmd('two', 'two.txt')]
        self.steps[0]['run'] += ' {source}'
        self.state['values']['source'] = 'source-a'
        self.assertEqual(self.advance(), 0)
        self.state['values']['source'] = 'source-b'
        step, _, _ = R.next_step('test', self.state)
        self.assertEqual(step['id'], 'one')

    def test_runner_resumes_all_saved_parameters_without_repeating_flags(self):
        self.steps = [{'id': 'idea', 'name': 'Idea', 'component': 'research', 'does': 'Find idea',
                       'executor': 'agent', 'inputs': ['story'], 'evidence': ['{story}']}]
        self.write('concept.md')
        self.assertEqual(self.cli('complete', 'test', '--brand', 'test', '--label', 'example',
                                  '--set', 'story=concept.md', '--station', 'idea'), 0)
        self.assertEqual(self.cli('run', 'test', '--brand', 'test', '--label', 'example'), 0)

    def test_changed_input_file_invalidates_same_path_receipt(self):
        self.steps = [self.cmd()]
        self.steps[0]['input_files'] = ['source.md']
        self.write('source.md', 'first')
        self.assertEqual(self.advance(), 0)
        self.write('source.md', 'changed at the same path')
        self.assertEqual(R.next_step('test', self.state)[0]['id'], 'build')

    def test_agent_cannot_adopt_failed_writing_contract(self):
        self.steps = [{'id': 'brief', 'name': 'Brief', 'component': 'writing', 'does': 'Finish writing',
                       'executor': 'agent', 'evidence': ['brief.md'],
                       'brief_check': {'run': 'run.json', 'brief': 'brief.md'}}]
        self.write('brief.md', 'draft exists')
        self.write('run.json', '{"stages":{"stage5":{"status":"held"}}}')
        self.assertEqual(self.cli('complete', 'test', '--brand', 'test', '--label', 'example',
                                  '--station', 'brief'), 2)

    def test_agent_run_check_is_semantic_not_file_presence(self):
        self.steps = [{'id': 'prepare', 'name': 'Prepare', 'component': 'writing', 'does': 'Prepare',
                       'executor': 'agent', 'done_when': 'run.json', 'evidence': ['run.json'],
                       'run_check': {'file': 'run.json', 'stages': ['stage1']}}]
        self.write('run.json', '{"stages":{"stage1":{"status":"held"}}}')
        self.assertEqual(self.cli('complete', 'test', '--brand', 'test', '--label', 'example',
                                  '--station', 'prepare'), 2)


class DecidedAndQuoteTests(unittest.TestCase):
    """Quotes only (owner, 2026-11-27): a review station is decided by the decision layer and the run continues; the
    owner's go on the exact quote is the one person stop, and it opens the paid stations after it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.oldroot = W.WS
        self.decide = R.decision_module()          # the real layer, its queue and settings in the temp folder
        self.decide.QUEUE = self.root / 'calls.jsonl'
        self.decide.SETTINGS = self.root / 'settings.json'
        self.decide.precedents = lambda: {}
        self.settings({'writing': 'auto'})
        W.WS = self.root
        self.path = self.root / 'runs/video-production/test/workflow-example/workflow-state.json'
        self.state = {'format': 'test', 'values': {'brand': 'test', 'label': 'example'}}
        self.steps = []
        self.patches = [patch.object(W, 'workflow', lambda _, **kwargs: {'what': 'Test', 'steps': self.steps}),
                        patch.object(R, 'decision_module', return_value=self.decide)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        W.WS = self.oldroot
        self.tmp.cleanup()

    def settings(self, automation):
        (self.root / 'settings.json').write_text(json.dumps({'automation': automation}))

    def write(self, ref, content='example'):
        path = self.root / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def calls(self):
        q = self.root / 'calls.jsonl'
        return [json.loads(x) for x in q.read_text().splitlines()] if q.is_file() else []

    def cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return R.main(list(args) + ['--brand', 'test', '--label', 'example'])

    def saved(self):
        return json.loads(self.path.read_text())

    def draft_and_decided(self):
        script = self.root / 'build.py'
        script.write_text("from pathlib import Path\nPath('built.txt').write_text('done')\n")
        self.steps = [{'id': 'draft', 'name': 'Draft', 'component': 'fixture', 'does': 'Write', 'executor': 'agent',
                       'evidence': ['draft.md']},
                      {'id': 'draft-review', 'name': 'Draft review', 'component': 'decision layer', 'does': 'Decide',
                       'executor': 'decided', 'overrule': 'owner', 'review_asset': 'draft.md', 'input_files': ['draft.md']},
                      {'id': 'build', 'name': 'Build', 'component': 'fixture', 'does': 'Build', 'executor': 'command',
                       'run': 'python3 build.py', 'done_when': 'built.txt'}]
        self.write('draft.md', 'first version')
        self.assertEqual(self.cli('complete', 'test', '--station', 'draft'), 0)

    def test_decided_station_files_one_call_and_the_run_continues(self):
        self.draft_and_decided()
        self.assertEqual(self.cli('run', 'test'), 0)
        calls = self.calls()
        self.assertEqual(len(calls), 1)
        self.assertEqual((calls[0]['run'], calls[0]['gate'], calls[0]['mode']), ('workflow-example', 'draft-review', 'auto'))
        self.assertTrue(calls[0]['item']['n'].startswith('draft-review@'))
        self.assertEqual(self.saved()['receipts']['draft-review']['decision_call'], calls[0]['id'])
        self.assertTrue((self.root / 'built.txt').is_file())
        self.assertEqual(self.cli('run', 'test'), 0)
        self.assertEqual(len(self.calls()), 1)    # resuming never files the same version again

    def test_decided_station_cannot_be_completed_by_hand(self):
        self.draft_and_decided()
        self.assertEqual(self.cli('complete', 'test', '--station', 'draft-review', '--evidence', 'draft.md'), 2)
        self.assertEqual(self.calls(), [])

    def test_overrule_reopens_the_station_and_is_never_decided_again(self):
        self.draft_and_decided()
        self.assertEqual(self.cli('run', 'test'), 0)
        call = self.calls()[0]['id']
        self.decide.set_verdict(call, 'overrule', 'too soft')
        self.assertEqual(self.cli('run', 'test'), 2)
        state = self.saved()
        self.assertEqual(state['next']['station'], 'draft-review')
        self.assertIn('overruled', state['next']['reason'])
        self.assertIn('too soft', state['next']['reason'])
        self.assertEqual(state['waiting_on'], 'assistant')
        self.assertEqual(len(self.calls()), 1)
        self.write('draft.md', 'reworked version')
        self.assertEqual(self.cli('run', 'test'), 2)
        self.assertEqual(self.saved()['next']['station'], 'draft')
        self.assertEqual(self.cli('complete', 'test', '--station', 'draft'), 0)
        self.assertEqual(self.cli('run', 'test'), 2)            # the new version is decided; the old build is not reused blindly
        self.assertEqual(len(self.calls()), 2)
        self.assertEqual(self.saved()['next']['station'], 'build')

    def test_shadow_mode_waits_for_the_agree(self):
        self.settings({'writing': 'shadow'})
        self.draft_and_decided()
        self.assertEqual(self.cli('run', 'test'), 2)
        self.assertIn('shadow', self.saved()['next']['reason'])
        self.assertFalse((self.root / 'built.txt').exists())
        self.decide.set_verdict(self.calls()[0]['id'], 'agree')
        self.assertEqual(self.cli('run', 'test'), 0)

    def test_decided_manifest_binds_current_bytes(self):
        self.write('clip.mp4', 'first media bytes')
        self.write('review.json', json.dumps({'files': {'clip.mp4': R.digest(b'first media bytes')}}))
        step = {'id': 'media-review', 'review_asset': 'review.json', 'review_files': ['clip.mp4']}
        self.assertIn('clip.mp4', R.decided_version(step, {})[1])
        self.write('clip.mp4', 'replacement media bytes')
        with self.assertRaisesRegex(ValueError, 'current output bytes'):
            R.decided_version(step, {})

    def quote_then_paid(self, total=10):
        self.write('make.py', "from pathlib import Path\nPath('made.txt').write_text('done')\n")
        self.write('quote.json', json.dumps({'total_usd': total, 'lines': [], 'stop_point': 'the cut'}))
        self.steps = [{'id': 'price', 'name': 'Quote', 'component': 'fixture', 'does': 'Price', 'executor': 'agent',
                       'quote': True, 'stops_for': 'owner: the quote', 'evidence': ['quote.json', 'go.json'],
                       'go': {'quote': 'quote.json', 'record': 'go.json'}},
                      {'id': 'make', 'name': 'Make', 'component': 'fixture', 'does': 'Make', 'executor': 'command',
                       'run': 'python3 make.py', 'done_when': 'made.txt', 'paid': True}]

    def test_quote_is_the_one_stop_and_needs_his_go_on_that_quote(self):
        self.quote_then_paid()
        self.assertEqual(self.cli('run', 'test'), 2)
        self.assertEqual(self.saved()['waiting_on'], 'owner: the quote')
        self.assertIn('THE ONE STOP', (self.path.parent / 'NEXT.md').read_text())
        self.write('go.json', json.dumps({'approved_by': 'owner', 'said': 'go', 'cap_usd': 20}))   # not bound to the quote
        self.assertEqual(self.cli('complete', 'test', '--station', 'price'), 2)
        self.assertEqual(self.cli('go', 'test', '--approved-by', 'owner', '--said', 'go', '--cap', '5'), 2)   # under it
        self.assertEqual(self.cli('go', 'test', '--approved-by', 'owner', '--cap', '20'), 2)                 # no words
        self.assertFalse((self.root / 'made.txt').exists())
        self.assertEqual(self.cli('go', 'test', '--approved-by', 'owner', '--said', 'go', '--cap', '20'), 0)
        self.assertEqual(self.cli('complete', 'test', '--station', 'price'), 0)
        self.assertEqual(self.cli('run', 'test'), 0)            # the go opens the paid station; no --allow-paid
        self.assertTrue((self.root / 'made.txt').is_file())

    def test_changed_quote_needs_a_new_go(self):
        self.quote_then_paid()
        self.assertEqual(self.cli('go', 'test', '--approved-by', 'owner', '--said', 'go', '--cap', '20'), 0)
        self.assertEqual(self.cli('complete', 'test', '--station', 'price'), 0)
        self.write('quote.json', json.dumps({'total_usd': 15, 'lines': [], 'stop_point': 'the cut'}))
        self.assertEqual(self.cli('run', 'test'), 2)
        self.assertEqual(self.saved()['next']['station'], 'price')
        self.assertFalse((self.root / 'made.txt').exists())

    def test_go_is_only_recorded_at_a_quote(self):
        self.draft_and_decided()
        self.assertEqual(self.cli('go', 'test', '--approved-by', 'owner', '--said', 'go', '--cap', '20'), 2)
        self.assertFalse((self.root / 'go.json').exists())


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.oldroot = W.WS
        # Load the real public review component before using the isolated repo.
        self.review = R.review_module()
        W.WS = self.root
        self.file = self.root / 'brief.md'
        self.file.write_text('reviewed version')
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        subprocess.run(['git', 'add', 'brief.md'], cwd=self.root, check=True)
        subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                        'commit', '-qm', 'fixture'], cwd=self.root, check=True)
        self.commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.root).decode().strip()
        self.step = {'id': 'brief-review', 'gate': 'owner', 'review_asset': 'brief.md'}
        self.values = {'brief_review': 'RQ-test'}
        self.records = [
            {'item': 'RQ-test', 'created': '1', 'verdict': {'event': 'request',
              'asset': {'warehouse': 'repo', 'ref': 'brief.md', 'at': self.commit}}},
            {'item': 'RQ-test', 'created': '2', 'reviewer': 'owner',
             'verdict': {'event': 'verdict', 'verdict': 'approve'}},
            {'item': 'RQ-test', 'created': '3', 'verdict': {'event': 'close', 'decision': 'accepted'}}]

    def tearDown(self):
        W.WS = self.oldroot
        self.tmp.cleanup()

    def proof(self):
        with patch.object(R, 'review_module', return_value=self.review), patch.object(self.review, 'read_records', return_value=self.records):
            return R.review_proof(self.step, self.values)

    def test_accepted_exact_version_passes(self):
        self.assertEqual(self.proof()['review_item'], 'RQ-test')

    def test_changed_brief_does_not_reuse_old_approval(self):
        self.file.write_text('new unreviewed text')
        with self.assertRaisesRegex(ValueError, 'differs'):
            self.proof()

    def test_review_edit_does_not_inherit_earlier_approval(self):
        self.records[0]['created'] = '4'
        with self.assertRaisesRegex(ValueError, 'changed after'):
            self.proof()

    def test_rejected_review_cannot_pass(self):
        self.records[-1]['verdict']['decision'] = 'rejected'
        with self.assertRaisesRegex(ValueError, 'not accepted'):
            self.proof()

    def test_unversioned_review_is_not_auto_applied(self):
        self.records[0]['verdict']['asset'].pop('at')
        with self.assertRaisesRegex(ValueError, 'pinned'):
            self.proof()

    def test_another_person_cannot_satisfy_named_review(self):
        self.records[1]['reviewer'] = 'someone-else'
        with self.assertRaisesRegex(ValueError, 'not accepted'):
            self.proof()


if __name__ == '__main__':
    unittest.main()
