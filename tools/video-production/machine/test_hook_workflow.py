import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import hook_workflow as W


class Workflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / 'runs/video-production/brand/ad/hooks/h02'
        (self.run / 'media').mkdir(parents=True)
        (self.run / 'clips').mkdir()
        self.control = self.root / 'control.mp4'; self.control.write_bytes(b'control')
        self.picture = self.run / 'media/S1-F1.png'; self.picture.write_bytes(b'picture')
        self.clip = self.run / 'clips/G01-C1.mp4'; self.clip.write_bytes(b'clip')
        (self.run / 'vo').mkdir(); (self.run / 'vo/S1.mp3').write_bytes(b'voice')
        self.row = {'id': 'V1', 'line': 'Hook', 'scroll': 'Model demo', 'controls': {}}
        W.write(self.run.parent / 'index.json', {})
        W.write(self.run.parent / 'hook-matrix.json', {'openings': [self.row]})
        W.write(self.run / 'opening.json', {'matrix_row': self.row, 'text': 'Hook',
            'source': {'control': 'control.mp4', 'control_sha256': W.digest(self.control)}})
        W.write(self.run / 'picture-recipe.json', {'brief': {'base': 'control.mp4'}})
        W.write(self.run / 'clips/ledger.json', {'G01-C1': {'file': str(self.clip),
            'line_check': {'verdict': 'PASS'}, 'qc': {'lips': {'ok': True}}}})
        self.body = {'ok': True, 'problems': []}
        def loader(root, relative):
            if relative.endswith('hook_matrix.py'):
                return SimpleNamespace(check=lambda *a: [])
            if relative.endswith('preview.py'):
                return SimpleNamespace(preview=lambda *a, **k: {'inputs': [{'path': str(self.control), 'role': 'base'}], 'findings': []})
            if relative.endswith('lineparity.py'):
                return SimpleNamespace(compare=lambda *a: 1.0, threshold_of=lambda: 0.9, say_numbers=lambda s: s)
            if relative.endswith('movement.py'):
                return SimpleNamespace(bank=lambda: [])
            return SimpleNamespace(check=lambda *a: self.body)
        self.patcher = patch.object(W, 'load', side_effect=loader)
        self.patcher.start(); self.addCleanup(self.patcher.stop)
        W.write(self.run / 'plan.json', {'scenes': [{'voice': 'Hook'}]})
        W.write(self.run / 'voice-binding.json', {'line': 'Hook', 'sha256': W.digest(self.run / 'vo/S1.mp3')})
        state = W.inspect(self.run, self.root)
        W.write(self.run / 'clip-binding.json', {'sha256': W.digest(self.clip),
            'frame_sha256': W.digest(self.picture), 'setup_signature': state['setup_signature'],
            'clip_signature': state['clip_signature']})

    def approve_frame(self):
        W.act(self.run, self.root, 'check_frame')
        W.act(self.run, self.root, 'approve_frame')

    def approve_clip(self):
        self.approve_frame()
        W.act(self.run, self.root, 'check_clip')
        W.act(self.run, self.root, 'approve_clip')

    def test_generation_cannot_skip_checks_or_approval(self):
        with self.assertRaises(ValueError): W.require_clip(self.run, self.root)
        W.act(self.run, self.root, 'check_frame')
        with self.assertRaises(ValueError): W.require_clip(self.run, self.root)
        W.act(self.run, self.root, 'approve_frame')
        W.require_clip(self.run, self.root)

    def test_changed_picture_invalidates_frame_and_clip_approval(self):
        self.approve_clip()
        W.require_edit(self.run, self.root)
        self.picture.write_bytes(b'new picture')
        state = W.inspect(self.run, self.root)
        self.assertFalse(state['can_make_clip'])
        self.assertFalse(state['can_edit'])

    def test_changed_recipe_invalidates_old_approvals(self):
        self.approve_clip()
        W.write(self.run / 'picture-recipe.json', {'brief': {'base': 'control.mp4', 'swaps': 'changed'}})
        self.assertFalse(W.inspect(self.run, self.root)['can_edit'])

    def test_extra_arm_stops_clip_approval_and_edit(self):
        self.approve_frame()
        self.body = {'ok': False, 'problems': ['three arms']}
        W.act(self.run, self.root, 'check_clip')
        self.assertFalse(W.inspect(self.run, self.root)['can_approve_clip'])
        with self.assertRaises(ValueError): W.act(self.run, self.root, 'approve_clip')
        with self.assertRaises(ValueError): W.require_edit(self.run, self.root)

    def test_numeral_transcript_matches_spoken_number_hook(self):
        import lineparity
        self.approve_frame()
        state = W.inspect(self.run, self.root)
        state['line'] = 'This cheek is forty-five. That clear one is seventy.'
        ledger = W.read(self.run / 'clips/ledger.json')
        ledger['G01-C1']['line_check']['heard'] = 'This cheek is 45. That clear one is 70.'
        W.write(self.run / 'clips/ledger.json', ledger)
        loader = W.load.side_effect
        with patch.object(W, 'inspect', return_value=state), patch.object(W, 'load',
                side_effect=lambda root, path: lineparity if path.endswith('lineparity.py') else loader(root, path)):
            W.act(self.run, self.root, 'check_clip')
            self.assertTrue(W.read(self.run / 'hook-clip-review.json')['checks_ok'])
            ledger['G01-C1']['line_check']['heard'] = 'Like someone sprinkled pepper on your cheek. Wipe it. Still there.'
            W.write(self.run / 'clips/ledger.json', ledger)
            W.act(self.run, self.root, 'check_clip')
            self.assertFalse(W.read(self.run / 'hook-clip-review.json')['checks_ok'])

    def test_changed_clip_requires_new_review(self):
        self.approve_clip()
        self.clip.write_bytes(b'new take')
        self.assertFalse(W.inspect(self.run, self.root)['can_edit'])

    def test_copy_only_change_keeps_frame_approval_but_invalidates_clip(self):
        self.approve_clip()
        opening = W.read(self.run / 'opening.json')
        opening['text'] = opening['matrix_row']['line'] = 'New spoken hook'
        W.write(self.run / 'opening.json', opening)
        W.write(self.run.parent / 'hook-matrix.json', {'openings': [opening['matrix_row']]})
        state = W.inspect(self.run, self.root)
        self.assertTrue(state['frame_checked'])
        self.assertFalse(state['can_make_clip'])
        self.assertTrue(state['can_make_voice'])
        self.assertFalse(state['can_edit'])

    def test_line_revision_preserves_bytes_and_reopens_only_dependencies(self):
        self.approve_clip()
        picture_before = self.picture.read_bytes()
        voice_before = (self.run / 'vo/S1.mp3').read_bytes()
        result = W.revise(self.run, self.root, 'spoken_line', 'Replacement line')
        self.assertEqual(self.picture.read_bytes(), picture_before)
        self.assertEqual((self.run / 'vo/S1.mp3').read_bytes(), voice_before)
        self.assertTrue(result['workflow']['stages'][2]['complete'])
        self.assertTrue(result['workflow']['can_make_voice'])
        self.assertFalse(result['workflow']['can_check_clip'])
        self.assertEqual(W.read(self.run / 'lines.json')['S1'], 'Replacement line')

    def test_saving_same_value_spends_nothing_and_keeps_approvals(self):
        self.approve_clip()
        result = W.revise(self.run, self.root, 'spoken_line', 'Hook')
        self.assertTrue(result['unchanged'])
        self.assertFalse((self.run / 'hook-changes.json').exists())
        self.assertTrue(W.inspect(self.run, self.root)['can_edit'])

    def test_new_frame_cannot_reapprove_old_clip(self):
        self.approve_clip()
        self.picture.write_bytes(b'changed frame')
        self.approve_frame()
        with self.assertRaises(ValueError): W.act(self.run, self.root, 'check_clip')

    def test_motion_change_reuses_voice_and_frame(self):
        self.approve_clip()
        state = W.revise(self.run, self.root, 'motion', 'Hold hands still')['workflow']
        self.assertTrue(state['can_make_clip'])
        self.assertTrue(state['voice_current'])
        self.assertFalse(state['can_check_clip'])

    def test_reusing_control_archives_frame_and_requires_new_review(self):
        self.approve_clip()
        old_sha = W.digest(self.picture)
        voice = (self.run / 'vo/S1.mp3').read_bytes()
        W.act(self.run, self.root, 'reuse_control_frame')
        direction = W.read(self.run / 'picture-recipe.json')['brief']['shot_direction']
        self.assertIsInstance(direction, dict)
        self.assertIn('gesture', direction)
        self.assertEqual(self.picture.read_bytes(), self.control.read_bytes())
        self.assertEqual((self.run / 'versions' / ('frame-' + old_sha) / 'S1-F1.png').read_bytes(), b'picture')
        self.assertEqual((self.run / 'vo/S1.mp3').read_bytes(), voice)
        self.assertFalse(W.inspect(self.run, self.root)['can_edit'])
        self.assertFalse(W.inspect(self.run, self.root)['can_make_clip'])


if __name__ == '__main__':
    unittest.main()
