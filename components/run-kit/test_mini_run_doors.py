"""A hand-written mini door is read from its own argparse (2026-10-19).

The kojic-acid-doctor run was refused on the mini ("the following arguments are required: --label")
because the filer only handed a label to doors with a lab_door.json. Spends nothing, files nothing.

    /usr/bin/python3 test_mini_run_doors.py      (from components/run-kit/)
"""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mini_run as M  # noqa: E402

DOOR = '''import argparse
ap = argparse.ArgumentParser()
ap.add_argument("--kit")
ap.add_argument("--label", required=True)
ap.add_argument("--dry_run", default="no")
'''


class HandWrittenDoor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        (self.repo / "door.py").write_text(DOOR)
        self.row = {"component": "x", "script": "door.py"}

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, args):
        return M.checked_args(self.repo, self.row, None, None, args, "brand")

    def test_a_door_that_requires_label_is_handed_one(self):
        self.assertTrue(self.check({"kit": "k"}))

    def test_its_declared_dry_run_is_allowed(self):
        self.assertTrue(self.check({"kit": "k", M.DRY_RUN: "yes"}))

    def test_an_argument_it_does_not_take_is_refused(self):
        with self.assertRaises(M.Refused):
            self.check({"nope": "1"})

    def test_a_door_without_label_is_not_handed_one(self):
        (self.repo / "door.py").write_text('ap.add_argument("--kit")\n')
        self.assertFalse(self.check({"kit": "k"}))


if __name__ == "__main__":
    unittest.main()
