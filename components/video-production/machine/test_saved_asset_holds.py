import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import make_set
import elements_check


class SavedAssetHolds(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_existing_plate_provider_failure_cannot_resume_as_clean(self):
        p = self.root / 'wide.png';p.write_bytes(b'preserved')
        with patch.object(make_set, '_person_in', side_effect=RuntimeError('HTTP402')):
            with self.assertRaises(RuntimeError):make_set._reuse_plate(p)
        self.assertEqual(p.read_bytes(), b'preserved')

    def test_existing_person_plate_is_preserved_and_held(self):
        p = self.root / 'wide.png';p.write_bytes(b'preserved')
        with patch.object(make_set, '_person_in', return_value='YES reflected face'):
            with self.assertRaises(RuntimeError):make_set._reuse_plate(p)
        self.assertTrue(p.exists())

    def test_clean_saved_plate_reuses_without_generation(self):
        p = self.root / 'wide.png';p.write_bytes(b'preserved')
        with patch.object(make_set, '_person_in', return_value='') as check:
            self.assertTrue(make_set._reuse_plate(p));check.assert_called_once_with(p)

    def test_absent_plate_is_not_checked(self):
        with patch.object(make_set, '_person_in') as check:
            self.assertFalse(make_set._reuse_plate(self.root / 'absent.png'));check.assert_not_called()

    def test_bank_hold_blocks_otherwise_complete_folder(self):
        with patch.object(elements_check, '_product_on_drive', return_value=None):
            self.assertEqual(elements_check._check_folder(self.root, []), [])
            (self.root/'quality-hold.json').write_text(json.dumps({'reason':'people check: HTTP402'}))
            self.assertEqual(elements_check._check_folder(self.root, []), ['quality hold: people check: HTTP402'])

    def test_unreadable_hold_fails_closed(self):
        (self.root/'quality-hold.json').write_text('{')
        with patch.object(elements_check, '_product_on_drive', return_value=None):
            self.assertIn('quality hold record unreadable', elements_check._check_folder(self.root, [])[0])


if __name__ == '__main__':unittest.main()
