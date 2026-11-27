"""An edit asks for the picture's own shape (the team, 2026-10-22): a 3:2 picture asked for 16:9, the model reframed the
scene and the judge held every try. No network.

    /usr/bin/python3 test_edit_aspect.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import picture_record as PR  # noqa: E402


class EditAspect(unittest.TestCase):
    def test_each_shape_keeps_its_own_aspect(self):
        self.assertEqual(PR.nearest_aspect(1536, 1024), "3:2")
        self.assertEqual(PR.nearest_aspect(1024, 1024), "1:1")
        self.assertEqual(PR.nearest_aspect(1080, 1350), "4:5")
        self.assertEqual(PR.nearest_aspect(1920, 1080), "16:9")

    def test_a_picture_with_no_record_reads_as_none(self):
        self.assertIsNone(PR.read(Path("."), None))


if __name__ == "__main__":
    unittest.main()
