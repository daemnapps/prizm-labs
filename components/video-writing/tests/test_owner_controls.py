"""Explicit run instructions constrain one dial without lowering shared floors."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'machine'))
import hook_matrix as H
import owner_controls as O


class OwnerControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.quote = 'No planted gags anywhere; keep this piece straight.'
        (self.root / 'RULINGS.md').write_text(self.quote)
        self.data = dict(schema=1, authority='owner-instruction', decision_date='2026-11-18',
                        constraints={'humor': dict(level=0, source='RULINGS.md', quote=self.quote)})

    def write(self):
        (self.root / 'owner-controls.json').write_text(json.dumps(self.data))
        return O.load(self.root)

    def matrix(self):
        _, targets = H.controls().target('maxed', None, 'video')
        return dict(format_contract={'speaker': 'one presenter'}, openings=[
            dict(id='V%d' % n, line='A line', scroll='A visible action', thumb='The first frame',
                 watch_payoff='The demonstration', body_join='Returns to the explanation',
                 format_evidence={'speaker': 'The same presenter remains visible'},
                 controls={k: dict(level=v, evidence='Visible execution in the test fixture') for k,v in targets.items()})
            for n in range(6)])

    def test_default_does_not_change_and_generated_output_cannot_override(self):
        self.assertEqual(O.load(self.root), {})
        self.assertEqual(O.block(self.root), '')
        matrix = self.matrix()
        for row in matrix['openings']: row['controls']['humor']['level'] = 0
        matrix['owner_controls'] = self.data
        self.assertTrue(any('humor is below' in e for e in H.check(matrix)))

    def test_exact_owner_level_applies_only_named_dial(self):
        constraints = self.write()
        matrix = self.matrix()
        for row in matrix['openings']: row['controls']['humor']['level'] = 0
        self.assertEqual(H.check(matrix, constraints=constraints), [])
        matrix['openings'][1]['controls']['absurdity']['level'] = 0
        self.assertTrue(any('absurdity is below' in e for e in H.check(matrix, constraints=constraints)))
        matrix['openings'][0]['controls']['humor']['level'] = 2
        self.assertTrue(any('V0: humor must equal' in e for e in H.check(matrix, constraints=constraints)))

    def test_unknown_dial_invalid_scale_and_boolean_refused(self):
        for key, value in [('imagined', 0), ('humor', 999), ('humor', True)]:
            self.data['constraints'] = {key: dict(level=value, source='RULINGS.md', quote=self.quote)}
            with self.assertRaises(O.InvalidOwnerControls): self.write()

    def test_requires_authority_date_and_exact_quote(self):
        for key, value in [('authority', 'generated-output'), ('decision_date', 'whenever')]:
            original = self.data[key]; self.data[key] = value
            with self.assertRaises(O.InvalidOwnerControls): self.write()
            self.data[key] = original
        self.data['constraints']['humor']['quote'] = 'An instruction absent from the source'
        with self.assertRaises(O.InvalidOwnerControls): self.write()

    def test_no_path_escape_or_generated_stage_source(self):
        for source in ('../RULINGS.md', '/tmp/RULINGS.md', 'stages/5-brief.md', 'hand/answer.md'):
            self.data['constraints']['humor']['source'] = source
            with self.assertRaises(O.InvalidOwnerControls): self.write()

    def test_external_symlink_refused(self):
        outside = self.root.parent / (self.root.name + '-outside.md')
        outside.write_text(self.quote)
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        (self.root / 'RULINGS.md').unlink()
        (self.root / 'RULINGS.md').symlink_to(outside)
        with self.assertRaises(O.InvalidOwnerControls): self.write()

    def test_missing_source_and_malformed_file_refused(self):
        (self.root / 'RULINGS.md').unlink()
        with self.assertRaises(O.InvalidOwnerControls): self.write()
        (self.root / 'owner-controls.json').write_text('{')
        with self.assertRaises(O.InvalidOwnerControls): O.load(self.root)

    def test_prompt_carries_exact_source_and_no_shared_default_edit(self):
        before = H.controls().target('maxed', None, 'video')
        self.write()
        text = O.block(self.root)
        self.assertIn('humor = 0', text)
        self.assertIn(self.quote, text)
        self.assertIn('RULINGS.md', text)
        self.assertEqual(H.controls().target('maxed', None, 'video'), before)

    def test_from_text_prose_and_shape_checks_remain(self):
        matrix = self.matrix()
        for row in matrix['openings']: row['controls']['humor']['level'] = 0
        text = '\n'.join('%s %s: %s' % (prefix, row['id'], row[field])
                         for row in matrix['openings']
                         for prefix,field in [('LINE','line'),('SCROLL','scroll'),('THUMB','thumb')])
        text += '\n```hook-matrix\n' + json.dumps(matrix) + '\n```'
        self.assertEqual(H.from_text(text, constraints=self.write())[1], [])
        text = text.replace('LINE V0: A line', 'LINE V0: Changed line')
        self.assertTrue(any('V0: line differs' in e for e in H.from_text(text, constraints=O.load(self.root))[1]))


if __name__ == '__main__':
    unittest.main()
