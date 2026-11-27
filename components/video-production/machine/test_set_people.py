"""A paid-provider failure must not bank an unchecked setting plate."""
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sp = importlib.util.spec_from_file_location('test_make_set', Path(__file__).with_name('make_set.py'))
M = importlib.util.module_from_spec(sp)
sp.loader.exec_module(M)

class SetPeople(unittest.TestCase):
    def run_check(self, answer=None, error=None):
        judge = SimpleNamespace(ask=Mock(return_value=(answer, {}), side_effect=error))
        spec = SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module: None))
        with patch.object(M._ilu, 'spec_from_file_location', return_value=spec), patch.object(M._ilu, 'module_from_spec', return_value=judge):
            return M._person_in(Path('/tmp/plate.jpg'))

    def test_clean_plate(self):
        self.assertEqual(self.run_check('NO — empty room'), '')

    def test_person_is_reported(self):
        self.assertIn('YES', self.run_check('YES reflection in mirror'))

    def test_failed_provider_is_not_clean(self):
        with self.assertRaises(RuntimeError):
            self.run_check(error=RuntimeError('HTTP402'))

    def test_ambiguous_answer_is_not_clean(self):
        with self.assertRaises(RuntimeError):
            self.run_check('Possibly someone near the window')

if __name__ == '__main__':
    unittest.main()
