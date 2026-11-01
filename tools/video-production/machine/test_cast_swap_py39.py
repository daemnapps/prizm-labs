#!/usr/bin/env python3
"""python3 machine/test_cast_swap_py39.py — from any cwd. Stdlib unittest only.

cast_swap imports under whichever interpreter runs this file — the Mac's own
/usr/bin/python3 is 3.9.6, where a `Path | None` hint raised TypeError at
import and broke every whole-character swap (SI-200 (cast_swap on 3.9))."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MACHINE = Path(__file__).resolve().parent

PROBE = (
    "import sys; sys.path.insert(0, sys.argv[1]); import cast_swap; "
    "from pathlib import Path; "
    "assert callable(cast_swap.look_for); "
    "print(cast_swap.look_for(Path(sys.argv[2])))"
)


class ImportsUnderThisInterpreter(unittest.TestCase):
    def test_cast_swap_imports_and_look_for_exists(self):
        with tempfile.TemporaryDirectory() as empty:
            r = subprocess.run([sys.executable, "-c", PROBE, str(MACHINE), empty],
                               capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0,
                         f"cast_swap does not import under Python {sys.version.split()[0]}:\n{r.stderr}")
        self.assertEqual(r.stdout.strip(), "None", "look_for on a folder with no looks returns None")


if __name__ == "__main__":
    unittest.main()
