"""Run-local owner instructions reach both the exact writer request and the hook check."""
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
import owner_controls as O
import hook_matrix as H
import run as R
import writing_result as state


class OwnerControlsWiring(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        for f in ('stages', 'hand', 'prompts'):
            (self.d / f).mkdir()
        quote = 'Keep this piece straight; no planted gags.'
        (self.d / 'RULINGS.md').write_text(quote)
        (self.d / 'owner-controls.json').write_text(json.dumps({
            'schema': 1, 'authority': 'owner-instruction', 'decision_date': '2026-11-18',
            'constraints': {'humor': {'level': 0, 'source': 'RULINGS.md', 'quote': quote}}}))
        (self.d / 'run.json').write_text('{}')

    def test_exact_hand_companion_includes_explicit_owner_instruction(self):
        out = self.d / 'stages/3-injection.md'
        answer = self.d / 'hand/3-injection.md'
        answer.write_text('The answer to the configured request.')
        companion = answer.with_suffix('.prompt.md')
        companion.write_text(O.block(self.d) + 'BODY')
        with patch.object(W, 'slim', return_value=('BODY', [])), \
             patch.object(W, 'prior_language_block', return_value=''), \
             patch.object(W, '_HAND', [str(self.d / 'hand')]), \
             patch.object(W, '_CURRENT', {'key': 'stage3'}):
            self.assertEqual(W.claude_v2('BODY', out), 'session-hand')
            self.assertEqual(out.read_bytes(), answer.read_bytes())
            companion.write_text('BODY')
            with self.assertRaises(W.HandPromptMismatch):
                W.claude_v2('BODY', out)

    def test_acceptance_hash_binds_constraints_and_each_allowed_source(self):
        initial = state.context_hash(self.d, {})
        controls = self.d / 'owner-controls.json'
        original = controls.read_text()
        changed = json.loads(original)
        changed['constraints']['humor']['level'] = 1
        controls.write_text(json.dumps(changed))
        self.assertNotEqual(initial, state.context_hash(self.d, {}))
        controls.write_text(original)
        for source in ('RULINGS.md', 'story.md', 'owner-script.md'):
            with self.subTest(source=source):
                p = self.d / source
                previous = p.read_text() if p.exists() else None
                before = state.context_hash(self.d, {})
                p.write_text((previous or '') + 'Changed exact source instruction.')
                self.assertNotEqual(before, state.context_hash(self.d, {}))
                if previous is None:
                    p.unlink()
                else:
                    p.write_text(previous)
        controls.unlink()
        self.assertNotEqual(initial, state.context_hash(self.d, {}))

    def test_no_owner_controls_preserves_legacy_unreferenced_source_hash(self):
        (self.d / 'owner-controls.json').unlink()
        before = state.context_hash(self.d, {})
        (self.d / 'story.md').write_text('Unreferenced legacy source.')
        (self.d / 'owner-script.md').write_text('Unreferenced legacy source.')
        self.assertEqual(before, state.context_hash(self.d, {}))

    def test_split_passes_validated_constraints_to_normal_hook_check(self):
        p = {'key': 'stage4v2a', 'splits': [('READING', 'stage4r', '4a', 'Reading'),
                                          ('HOOKS', 'stage4b', '4b', 'Hooks')]}
        out = self.d / 'stages/4ab-reading-hooks.md'
        out.write_text('=== PART 1: READING ===\nReading.\n=== PART 2: HOOKS ===\nHooks.\n')
        st = {'brand': 'test-brand', 'stages': {'stage4v2a': {'out': str(out.relative_to(self.d))}}}
        with patch.object(H, 'from_text', return_value=({}, [])) as checked, \
             patch.object(W, 'controls_preset', return_value=('maxed', 'fixture')), \
             patch.object(R, 'structure_gate'):
            W.split(self.d, st, p)
        self.assertEqual(checked.call_args.kwargs['constraints'], O.load(self.d))
        self.assertEqual(checked.call_args.kwargs['preset'], 'maxed')


if __name__ == '__main__':
    unittest.main()
