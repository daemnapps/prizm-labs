"""SI-128 (brandpath missing note): a brand folder with no FOLDERS.json or no
products/DRIVE-INDEX.json says so once per process, and the answers do not change.

No key, no network: a throwaway brands/ folder.
    /usr/bin/python3 components/brandpath/tests/test_missing_note.py
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import brandpath as BP  # noqa: E402
import drive_index as DI  # noqa: E402

BRAND = "zz-note-brand"


class MissingNote(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "brands"
        self.b = self.root / BRAND
        (self.b / "products").mkdir(parents=True)
        (self.b / "existing-content" / "ads").mkdir(parents=True)
        # a fresh "already said" memory per test, so test order does not matter
        for p in (unittest.mock.patch.object(BP, "_NOTED", set()),
                  unittest.mock.patch.object(DI, "_SAID", set()),
                  unittest.mock.patch.object(DI, "_CACHE", {})):
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def test_neither_file_notes_once_and_answers_unchanged(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            for _ in range(3):
                self.assertEqual(BP.folders(BRAND, root=self.root), BP.DEFAULTS)
                self.assertEqual(BP.brand_path(BRAND, "intake", "ads", root=self.root),
                                 self.b / "existing-content" / "ads")
                self.assertEqual(DI.rows(BRAND, self.root), [])
                self.assertIsNone(DI.row(BRAND, "some-id", self.root))
                DI._CACHE.clear()   # a cache miss must not repeat the note either
        out = err.getvalue()
        self.assertEqual(out.count("FOLDERS.json"), 1, out)
        self.assertEqual(out.count("DRIVE-INDEX.json"), 1, out)
        self.assertEqual(len(out.strip().splitlines()), 2, out)
        self.assertIn(BRAND, out)

    def test_once_per_brand(self):
        other = self.root / "zz-note-other"
        other.mkdir()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            BP.folders(BRAND, root=self.root)
            BP.folders("zz-note-other", root=self.root)
            BP.folders(BRAND, root=self.root)
        self.assertEqual(err.getvalue().count("FOLDERS.json"), 2, err.getvalue())

    def test_no_note_when_files_present(self):
        (self.b / BP.FOLDERS_FILE).write_text(json.dumps({"intake": ["existing-content"]}))
        (self.b / "products" / "DRIVE-INDEX.json").write_text(json.dumps({"files": []}))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            BP.folders(BRAND, root=self.root)
            DI.rows(BRAND, self.root)
        self.assertEqual(err.getvalue(), "")

    def test_no_note_when_brand_folder_absent(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(BP.folders("zz-no-such-brand", root=self.root), BP.DEFAULTS)
            self.assertEqual(DI.rows("zz-no-such-brand", self.root), [])
        self.assertEqual(err.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
