"""A stage whose outputs are unchanged is revalidated against today's inputs; changed outputs are refused."""
import json
import tempfile
import unittest
from pathlib import Path

import cache_contract as C


class Revalidate(unittest.TestCase):
    def setUp(self):
        self.run = Path(tempfile.mkdtemp())
        (self.run / 'vo').mkdir()
        (self.run / 'vo' / 'timing.json').write_text('{}')
        (self.run / 'plan.json').write_text(json.dumps({'scenes': [{'id': 'S1', 'voice': 'hi'}]}))
        C.seal(self.run, 'voice', None, {'providers.json': 'a'})

    def test_config_drift_is_revalidated_and_the_reason_kept(self):
        self.assertEqual(C.state(self.run, 'voice', None, {'providers.json': 'b'}), 'stale_inputs')
        r = C.revalidate(self.run, 'voice', 'a clip rate changed', None, {'providers.json': 'b'})
        self.assertEqual(r['revalidated']['reason'], 'a clip rate changed')
        self.assertEqual(C.state(self.run, 'voice', None, {'providers.json': 'b'}), 'current')

    def test_changed_outputs_are_refused(self):
        (self.run / 'vo' / 'timing.json').write_text('{"x": 1}')
        with self.assertRaises(ValueError):
            C.revalidate(self.run, 'voice', 'x', None, {'providers.json': 'b'})


class WrittenIsSealed(unittest.TestCase):
    """brief-0380: a step rewrote storyboard.json after the seal and the next run stopped on changed_outputs."""
    def test_a_rewritten_storyboard_is_current_once_its_writer_seals_it(self):
        run = Path(tempfile.mkdtemp())
        (run / 'plan.json').write_text(json.dumps({'scenes': [{'id': 'S1'}]}))
        (run / 'storyboard.json').write_text('{"sections": []}')
        self.assertTrue(C.written(run, 'storyboard'))
        (run / 'storyboard.json').write_text('{"sections": [1]}')
        self.assertEqual(C.state(run, 'storyboard', None, C.machine_config()), 'changed_outputs')
        C.written(run, 'storyboard')
        self.assertEqual(C.state(run, 'storyboard', None, C.machine_config()), 'current')


if __name__ == '__main__':
    unittest.main()
