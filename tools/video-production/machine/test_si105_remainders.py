#!/usr/bin/env python3
"""SI-105 (midnight remainders): the footage step says the index lives on
another Mac, and the library check switches the element library through
`use()` — the old two writes only for an elements that predates it. No
network; the element library is a stub module written to a temp folder.

    /usr/bin/python3 machine/test_si105_remainders.py
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import shutil
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"test_si105_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


footage = load("footage")
library_check = load("library_check")

# an elements that has the SI-100 (elements use seam): use() records its
# argument and points LIBRARY one level down, so the old direct write
# (LIBRARY = library_dir) would show; _cache is cleared in place, never replaced
WITH_USE = '''
from pathlib import Path
LIBRARY = Path("/no/such/library")
_cache = {"stale": 1}
_ORIGINAL_CACHE = _cache
USED = []

def use(library):
    global LIBRARY
    USED.append(library)
    LIBRARY = Path(library) / "via_use"
    _cache.clear()
    return LIBRARY
'''

# an elements from before use()
WITHOUT_USE = '''
from pathlib import Path
LIBRARY = Path("/no/such/library")
_cache = {"stale": 1}
_ORIGINAL_CACHE = _cache
'''


class FootageReport(unittest.TestCase):
    def test_no_index_says_this_machine_not_shared_assets(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            footage.report({"indexed": False, "cut": [], "generate": [], "presenter": [], "other": []})
        text = out.getvalue()
        self.assertIn("no footage index on this machine", text)
        self.assertIn("the asset index lives on the Mac that built it", text)
        self.assertNotIn("on Shared Assets", text)


class LibrarySwitch(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="si105-"))
        self.lib = self.tmp / "library"
        (self.lib / "via_use").mkdir(parents=True)
        self._module_file = library_check._module_file

    def tearDown(self):
        library_check._module_file = self._module_file
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _stub(self, source: str) -> None:
        f = self.tmp / "stub" / "elements.py"
        f.parent.mkdir(exist_ok=True)
        f.write_text(source)
        library_check._module_file = lambda: f

    def test_with_use_switches_through_use(self):
        self._stub(WITH_USE)
        mod = library_check.load(self.lib)
        self.assertEqual(mod.USED, [self.lib])
        self.assertEqual(mod.LIBRARY, self.lib / "via_use")    # not overwritten by a direct write
        self.assertIs(mod._cache, mod._ORIGINAL_CACHE)          # not replaced by a direct write
        self.assertEqual(mod._cache, {})

    def test_without_use_sets_library_and_cache_the_old_way(self):
        self._stub(WITHOUT_USE)
        mod = library_check.load(self.lib)
        self.assertFalse(hasattr(mod, "use"))
        self.assertEqual(mod.LIBRARY, self.lib)
        self.assertIsNot(mod._cache, mod._ORIGINAL_CACHE)
        self.assertEqual(mod._cache, {})

    def test_no_library_dir_leaves_the_module_alone(self):
        self._stub(WITH_USE)
        with self.assertRaises(library_check.NoLibrary):        # the stub's default does not exist
            library_check.load(None)


if __name__ == "__main__":
    unittest.main()
