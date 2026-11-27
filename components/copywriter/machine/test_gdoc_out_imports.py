#!/usr/bin/env python3
"""gdoc_out.py gets past its imports — SI-85 (gdoc_out import).

    /usr/bin/python3 machine/test_gdoc_out_imports.py

gdoc_out.py strips its own folder off sys.path (copy.py there shadows the
stdlib `copy`), so its siblings must be loaded by file. `import paths` by
name died with ModuleNotFoundError before the argparse ever ran. No model,
no network, no Drive, no key: only --help and the refusal without --folder.
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GDOC_OUT = HERE / "gdoc_out.py"
STRIP = "sys.path = [q for q in sys.path if Path(q or \".\").resolve() != HERE]"


def run(*args):
    p = subprocess.run([sys.executable, str(GDOC_OUT), *args], cwd=str(ROOT),
                       capture_output=True, text=True, timeout=20)
    return p.returncode, p.stdout, p.stderr


class GdocOutImports(unittest.TestCase):

    def test_help_runs(self):
        c, o, e = run("--help")
        self.assertEqual(c, 0, e.strip()[-500:])
        self.assertIn("--folder", o)
        self.assertNotIn("[--folder", o, "--folder must be required, not optional")

    def test_no_folder_is_refused(self):
        c, o, e = run("some-slug")
        self.assertNotEqual(c, 0)
        self.assertIn("folder", e)
        self.assertNotIn("ModuleNotFoundError", e)

    def test_paths_is_loaded_by_file(self):
        src = GDOC_OUT.read_text(encoding="utf-8")
        for line in src.splitlines():
            self.assertIsNone(re.match(r"^\s*import paths\b", line), line)
            self.assertIsNone(re.match(r"^\s*from paths import", line), line)
        self.assertIn('spec_from_file_location("paths"', src)

    def test_the_strip_stays(self):
        self.assertIn(STRIP, GDOC_OUT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
