"""Pickup boundaries, provider accounting, retries, revisions and privacy."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
import pickup as p
import usage


class PickupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.key = 'acme_item_brief-0001'
        self.delivery = self.root / ('runs/handoffs/video-editor/acme/' + self.key + '/delivery-state.json')
        p.write(self.delivery, {'revision_id': self.key + '-R00'})
        self.transcript = self.root / 'transcript.jsonl'
        self.transcript.touch()
        self.sid = 'session-1'

    def append(self, *rows):
        with self.transcript.open('a') as f:
            for row in rows:
                f.write(json.dumps(row) + '\n')

    def claude(self, rid, n=10, model='model-a'):
        return {'type': 'assistant', 'version': '2.1.285', 'requestId': rid, 'timestamp': '2026-11-19T00:00:00Z',
                'message': {'id': rid, 'model': model, 'content': 'PRIVATE CONTENT', 'usage': {
                    'input_tokens': n, 'output_tokens': n, 'cache_read_input_tokens': n,
                    'cache_creation_input_tokens': n, 'speed': 'standard',
                    'cache_creation': {'ephemeral_5m_input_tokens': n, 'ephemeral_1h_input_tokens': 0}}}}

    def hook(self, event='Stop', provider='anthropic', **extra):
        return p.handle(self.root, provider, {'session_id': self.sid, 'transcript_path': str(self.transcript),
                        'hook_event_name': event, **extra})

    def pickup(self, provider='anthropic', **kw):
        return self.hook('UserPromptSubmit', provider, prompt='Pick up brief ' + self.key, **kw)

    def summary(self):
        return usage.summarize(self.key, self.root)

    def test_before_pickup_excluded_repeated_blocks_and_hook_retries_deduped(self):
        self.append(self.claude('old'))
        self.pickup()
        self.append(self.claude('new'), self.claude('new'))
        self.hook(); self.hook()
        self.assertEqual(self.summary()['tokens'], 40)
        self.assertEqual(self.summary()['requests'], 1)
        self.assertEqual(self.summary()['session_ids'], [self.sid])
        receipts = ''.join(f.read_text() for f in (self.root / 'runs/brief-usage/requests').glob('*'))
        self.assertNotIn('PRIVATE', receipts)
        self.assertNotIn(str(self.transcript), receipts)

    def test_streamed_response_replaces_counts_monotonically(self):
        self.pickup()
        self.append(self.claude('a')); self.hook()
        self.append(self.claude('a', 20)); self.hook()
        self.assertEqual(self.summary()['tokens'], 80)
        self.assertEqual(self.summary()['requests'], 1)

    def test_stage_switch_closes_previous_and_revision_stays_on_work(self):
        self.pickup(); self.append(self.claude('a')); self.hook()
        p.write(self.delivery, {'revision_id': self.key + '-R01'})
        self.hook('UserPromptSubmit', prompt='Pick up brief ' + self.key + ' --stage revision')
        self.append(self.claude('b', model='model-b')); self.hook()
        report = self.summary()
        self.assertEqual(report['tokens'], 80)
        self.assertEqual({x['revision_id'] for x in report['breakdown']}, {self.key + '-R00', self.key + '-R01'})
        self.assertEqual(len(report['breakdown']), 2)
        self.assertIn('released', [s['state'] for s in report['tracking']])

    def test_explicit_release_stops_attribution(self):
        self.pickup(); self.append(self.claude('a'))
        self.hook('UserPromptSubmit', prompt='/brief-release')
        self.append(self.claude('unrelated')); self.hook()
        self.assertEqual(self.summary()['tokens'], 40)

    def test_unknown_fields_stay_null(self):
        self.pickup(); self.append(self.claude('a')); self.hook()
        g = self.summary()['breakdown'][0]
        self.assertIsNone(g['person']); self.assertIsNone(g['account_ref']); self.assertIsNone(g['effort'])

    def test_cannot_infer_pickup_from_mentions_or_ambiguous_brief(self):
        self.hook('UserPromptSubmit', prompt='Would we pick up brief ' + self.key + '?')
        self.assertEqual(self.summary()['state'], 'not-connected')
        other = self.root / 'runs/handoffs/video-editor/acme/acme_other_brief-0001/delivery-state.json'
        p.write(other, {'revision_id': 'acme_other_brief-0001-R00'})
        with self.assertRaises(ValueError):
            self.hook('UserPromptSubmit', prompt='Pick up brief 0001')

    def test_resume_preserves_boundary_and_new_session_keeps_prior_history(self):
        self.pickup(); self.append(self.claude('first')); self.hook()
        self.hook('SessionStart'); self.pickup()
        self.sid = 'session-2'
        self.hook('UserPromptSubmit', prompt='Pick up brief ' + self.key + ' --continued-from session-1')
        self.append(self.claude('second')); self.hook()
        self.assertEqual(self.summary()['tokens'], 80)
        self.assertEqual(self.summary()['session_ids'], ['session-1', 'session-2'])
        self.assertEqual(next(x for x in self.summary()['attempts'] if x['session_id'] == 'session-2')['continued_from_session_id'], 'session-1')

    def codex_start(self):
        self.append({'type': 'session_meta', 'payload': {'cli_version': '0.166.0'}},
                    {'type': 'turn_context', 'payload': {'model': 'model-a', 'effort': 'high'}})

    def codex_tokens(self, input=100, cache=80, output=30):
        return {'type': 'event_msg', 'timestamp': '2026-11-19T00:00:00Z', 'payload': {'type': 'token_count', 'info': {
            'total_token_usage': {'input_tokens': input, 'cached_input_tokens': cache, 'output_tokens': output, 'reasoning_output_tokens': 20, 'total_tokens': input + output}}}}

    def test_codex_baseline_cache_reasoning_and_duplicate_totals(self):
        self.codex_start(); self.append(self.codex_tokens()); self.pickup('openai')
        self.append(self.codex_tokens(150, 110, 40), self.codex_tokens(150, 110, 40))
        self.hook(provider='openai'); self.hook(provider='openai')
        r = self.summary()
        self.assertEqual(r['tokens'], 60)
        self.assertEqual(r['token_classes'], {'input': 20, 'output': 10, 'cache_read': 30, 'cache_write': 0})
        self.assertEqual(r['breakdown'][0]['effort'], 'high')

    def test_codex_model_effort_changes_kept(self):
        self.codex_start(); self.pickup('openai'); self.append(self.codex_tokens())
        self.append({'type': 'turn_context', 'payload': {'model': 'model-b', 'effort': 'low'}}, self.codex_tokens(150, 110, 40))
        self.hook(provider='openai')
        self.assertEqual({(x['model'], x['effort']) for x in self.summary()['breakdown']}, {('model-a', 'high'), ('model-b', 'low')})

    def test_invalid_or_changed_transcript_is_visible_error(self):
        self.pickup()
        broken = self.claude('a'); del broken['message']['usage']['output_tokens']
        self.append(broken)
        with self.assertRaises(ValueError): self.hook()
        self.assertEqual(self.summary()['state'], 'collection-error')
        self.assertIsNone(self.summary()['tokens'])
        self.assertEqual(self.summary()['collection_errors'], 1)

    def test_new_claude_transcript_created_after_prompt_but_resume_requires_file(self):
        self.transcript.unlink()
        self.hook('SessionStart', source='startup')
        self.pickup()
        self.append(self.claude('a')); self.hook()
        self.assertEqual(self.summary()['tokens'], 40)
        self.sid = 'resumed-session'
        self.transcript.unlink()
        self.hook('SessionStart', source='resume')
        with self.assertRaises(ValueError): self.pickup()

    def test_codex_counter_reset_refuses(self):
        self.codex_start(); self.pickup('openai')
        self.append(self.codex_tokens(), self.codex_tokens(10, 0, 1))
        with self.assertRaises(ValueError): self.hook(provider='openai')
        self.assertEqual(self.summary()['state'], 'collection-error')


if __name__ == '__main__':
    unittest.main()
