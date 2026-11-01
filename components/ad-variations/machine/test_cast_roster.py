"""SI-94 (late-night run-breakers): cast() reads the roster through brandpath,
where the folder plan keeps it (ai-elements/characters/casting/roster.json).
Read-only on brands/."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import brandctx  # noqa: E402


def _root():
    for d in HERE.parents:
        if (d / "components" / "brandpath" / "brandpath.py").is_file():
            return d
    raise RuntimeError("no workspace root above " + str(HERE))


class CastRoster(unittest.TestCase):
    def test_roster_is_read_through_brandpath(self):
        root = _root()
        for brand in ("brand-b", "brand-a"):
            with self.subTest(brand=brand):
                c = brandctx.BrandContext(root, brand)
                self.assertNotEqual(c.cast(), brandctx.MISSING)
                self.assertEqual(len(c.read_files), 1)
                self.assertIn("ai-elements/characters/casting/roster.json", c.read_files[0])


if __name__ == "__main__":
    unittest.main()
