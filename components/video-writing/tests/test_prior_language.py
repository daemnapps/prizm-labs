"""Raw language evidence survives fresh retrieval between writing passes."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MACHINE = Path(__file__).resolve().parents[1] / 'machine'
sys.path.insert(0, str(MACHINE))
import writing_v2 as W


class PriorLanguage(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.run = Path(self.temp.name)
        self.prompts = self.run / 'prompts'
        self.prompts.mkdir()
        self.quote = ('- [language_test_lead_0301] "Urban rx for dark marks"\n'
                      '  _lead · failed-solution · survey · 2025-03_')

    def tearDown(self):
        self.temp.cleanup()

    def test_multiline_quotes_and_metadata_are_retained_exactly(self):
        row = ('- [x-source-id] "First line with an embedded "quote".\n'
               'Second line.\n\nThird line."\n'
               '  _commenter · peer-advice · ATTRIBUTION ASSUMED_')
        (self.prompts / '3-injection.md').write_text('Header\n' + row + '\nTrailing summary')
        carried = W.prior_language_block(self.run, '4f-audit.md')
        self.assertIn(row, carried)
        self.assertIn('Source prompt `prompts/3-injection.md`', carried)
        self.assertNotIn('Trailing summary', carried)

    def test_same_row_is_deduplicated_across_prior_and_current_prompts(self):
        for name in ('3-injection.md', '4ab-reading-hooks.md'):
            (self.prompts / name).write_text(self.quote)
        carried = W.prior_language_block(self.run, '4f-audit.md')
        self.assertEqual(carried.count(self.quote), 1)
        self.assertEqual(W.prior_language_block(self.run, '4f-audit.md', self.quote), '')

    def test_conflicting_row_variants_retain_each_source(self):
        changed = self.quote.replace('Urban rx', 'Another product')
        (self.prompts / '3-injection.md').write_text(self.quote)
        (self.prompts / '4ab-reading-hooks.md').write_text(changed)
        carried = W.prior_language_block(self.run, '4f-audit.md')
        self.assertIn(self.quote, carried)
        self.assertIn(changed, carried)
        self.assertIn('prompts/3-injection.md', carried)
        self.assertIn('prompts/4ab-reading-hooks.md', carried)

    def test_missing_prompt_directory_produces_no_block(self):
        self.assertEqual(W.prior_language_block(self.run / 'missing', '4f-audit.md'), '')

    def test_current_prompt_is_excluded_and_saved_carry_does_not_grow(self):
        (self.prompts / '3-injection.md').write_text(self.quote)
        prior = W.prior_language_block(self.run, '4ab-reading-hooks.md')
        (self.prompts / '4ab-reading-hooks.md').write_text(prior + '\nCurrent unrelated prose')
        for _ in range(3):
            current = W.prior_language_block(self.run, '4ab-reading-hooks.md')
            self.assertEqual(current, prior)
            (self.prompts / '4ab-reading-hooks.md').write_text(current)
        next_pass = W.prior_language_block(self.run, '4f-audit.md')
        self.assertEqual(next_pass.count(self.quote), 1)
        self.assertNotIn('Current unrelated prose', next_pass)

    def test_claude_entry_saves_prior_evidence_after_slimming_without_external_call(self):
        (self.prompts / '3-injection.md').write_text(self.quote)
        (self.run / 'run.json').write_text(json.dumps({'stages': {}}))
        (self.run / 'stages').mkdir()
        out = self.run / 'stages' / '4f-audit.md'
        hand = self.run / 'hand'
        hand.mkdir()
        answer = 'existing local answer — exact\r\n'.encode('utf-8')
        (hand / out.name).write_bytes(answer)
        fresh = 'New fresh retrieval\n'
        final = ('Ask\nStory\nOwner\n'
                 + W.prior_language_block(self.run, out.name, fresh) + fresh)
        (hand / '4f-audit.prompt.md').write_bytes(final.encode('utf-8'))
        with mock.patch.object(W, 'slim', return_value=('New fresh retrieval\n', [])), \
                mock.patch.object(W, '_HAND', [str(hand)]), \
                mock.patch.object(W, 'owner_block', return_value='Owner\n'), \
                mock.patch.object(W, 'story_block', return_value='Story\n'), \
                mock.patch.object(W, 'ask_block', return_value='Ask\n'), \
                mock.patch('run._claude_run', side_effect=AssertionError('External call forbidden')):
            self.assertEqual(W.claude_v2('input before trimming', out), 'session-hand')
        self.assertEqual(out.read_bytes(), answer)
        self.assertEqual((self.prompts / out.name).read_bytes(), final.encode('utf-8'))
        sent = (self.prompts / out.name).read_text()
        self.assertIn(self.quote, sent)
        self.assertIn('Source prompt `prompts/3-injection.md`', sent)
        self.assertIn('New fresh retrieval', sent)

    def test_unbound_session_answer_preserves_stage_and_prompt_evidence(self):
        (self.run / 'run.json').write_text(json.dumps({'stages': {}}))
        (self.run / 'stages').mkdir()
        hand = self.run / 'hand'
        hand.mkdir()
        out = self.run / 'stages' / '4f-audit.md'
        sent = self.prompts / out.name
        companion = hand / '4f-audit.prompt.md'
        answer = hand / out.name
        answer.write_bytes(b'older hand answer\r\n')
        out.write_bytes(b'prior stage\r\n')
        sent.write_bytes(b'prior sent prompt\r\n')
        long_input = 'x' * 200000
        changed_input = long_input + ' changed source tail — exact\r\n'
        new_bytes = changed_input.encode('utf-8')
        digest = hashlib.sha256(new_bytes).hexdigest()[:12]
        current = hand / f'4f-audit.request-{digest}.prompt.md'
        receipt_stat = None
        with mock.patch.object(W, '_HAND', [str(hand)]), \
                mock.patch.object(W, 'slim', side_effect=lambda text, *args: (text, [])), \
                mock.patch('run._claude_run', side_effect=AssertionError('External call forbidden')):
            for previous, error in ((None, 'missing companion'), (long_input, 'differs')):
                with self.subTest(error=error):
                    if previous is not None:
                        companion.write_bytes(previous.encode('utf-8'))
                    before = {p: p.read_bytes() for p in self.run.rglob('*') if p.is_file()}
                    with self.assertRaisesRegex(W.HandPromptMismatch, 'session hand held: .*' + error) as held:
                        W.claude_v2(changed_input, out)
                    self.assertIn(str(current.relative_to(self.run)), str(held.exception))
                    after = {p: p.read_bytes() for p in self.run.rglob('*') if p.is_file()}
                    self.assertEqual(after, {**before, current: new_bytes})
                    if receipt_stat is None:
                        receipt_stat = current.stat()
                    else:
                        self.assertEqual(current.stat().st_ino, receipt_stat.st_ino)
                        self.assertEqual(current.stat().st_mtime_ns, receipt_stat.st_mtime_ns)
                    self.assertEqual(answer.read_bytes(), b'older hand answer\r\n')
                    self.assertEqual(out.read_bytes(), b'prior stage\r\n')
                    self.assertEqual(sent.read_bytes(), b'prior sent prompt\r\n')
                    if previous is None:
                        self.assertFalse(companion.exists())
                    else:
                        self.assertEqual(companion.read_bytes(), previous.encode('utf-8'))

            current.write_bytes(b'unrelated pre-existing file at the receipt path')
            with self.assertRaisesRegex(W.HandPromptMismatch, 'request file collision') as held:
                W.claude_v2(changed_input, out)
            self.assertIn(str(current.relative_to(self.run)), str(held.exception))
            self.assertEqual(current.read_bytes(), b'unrelated pre-existing file at the receipt path')
            self.assertEqual(answer.read_bytes(), b'older hand answer\r\n')
            self.assertEqual(out.read_bytes(), b'prior stage\r\n')
            self.assertEqual(sent.read_bytes(), b'prior sent prompt\r\n')
            self.assertEqual(companion.read_bytes(), long_input.encode('utf-8'))

    def test_stage_entry_preserves_last_sent_prompt_when_hand_does_not_match(self):
        import run as R
        template = self.run / 'template.md'
        template.write_text('new input')
        hand = self.run / 'hand'
        hand.mkdir()
        (self.run / 'stages').mkdir()
        out = self.run / 'stages' / '4f-audit.md'
        out.write_bytes(b'prior stage')
        sent = self.prompts / out.name
        sent.write_bytes(b'previously sent request')
        answer = hand / out.name
        answer.write_bytes(b'stale hand answer')
        companion = hand / '4f-audit.prompt.md'
        companion.write_bytes(b'previously sent request')
        st = {'brand': 'fixture', 'stages': {}}
        stage = {'key': 'stage4e', 'id': '4f', 'name': 'Audit', 'version': 1,
                 'engine': 'claude', 'prompt': str(template), 'vars': {}}
        with mock.patch.object(R, 'TMP', self.run / 'tmp'), \
                mock.patch.object(R.C, 'chain_version', return_value='v1'), \
                mock.patch.object(R, 'claude', W.claude_v2), \
                mock.patch.object(R, '_claude_run') as provider, \
                mock.patch.object(W, '_HAND', [str(hand)]):
            self.assertFalse(R.run_stage(self.run, st, stage, {}))
        self.assertIn('session hand held', st['stages']['stage4e']['error'])
        [current] = hand.glob('4f-audit.request-*.prompt.md')
        self.assertIn(str(current.relative_to(self.run)), st['stages']['stage4e']['error'])
        self.assertIn(b'new input', current.read_bytes())
        self.assertEqual(sent.read_bytes(), b'previously sent request')
        self.assertEqual(out.read_bytes(), b'prior stage')
        self.assertEqual(answer.read_bytes(), b'stale hand answer')
        self.assertEqual(companion.read_bytes(), b'previously sent request')
        provider.assert_not_called()

    def test_unbound_patch_answer_cannot_request_a_paid_rebuild(self):
        stages = self.run / 'stages'
        stages.mkdir()
        source = stages / 'build.md'
        source.write_text('previous script')
        st = {'stages': {'stage4v2b': {'out': 'stages/build.md'}}}
        (self.run / 'run.json').write_text(json.dumps(st))
        hand = self.run / 'hand'
        hand.mkdir()
        (hand / '4cde-patch-1.md').write_text('stale patch')
        p = {'key': 'stage4v2b', 'file_id': '4cde'}
        with mock.patch.object(W, '_HAND', [str(hand)]), \
                mock.patch.object(W, '_CURRENT', {}), \
                mock.patch('run._claude_run') as provider:
            with self.assertRaisesRegex(W.HandPromptMismatch, 'missing companion'):
                W.patch_build(self.run, st, p, 'repair one line', {})
        self.assertEqual(source.read_text(), 'previous script')
        self.assertFalse((stages / '4cde-patch-1.md').exists())
        provider.assert_not_called()


if __name__ == '__main__':
    unittest.main()
