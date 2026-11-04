#!/usr/bin/env python3
"""The copy library reads from the workspace, never from lab/.

    /usr/bin/python3 tools/copywriter/library/test_library_reads.py

Loads build_library.py by path and calls its readers one by one. Never calls
main(), which writes index.json — and the last test checks nothing under the
library folder or brands/ was written while it ran. Stdlib only.
"""
import contextlib, importlib.util, io, sys, time, unittest
from pathlib import Path

sys.dont_write_bytecode = True
START = time.time()
HERE = Path(__file__).resolve().parent
SRC = HERE / "build_library.py"

_spec = importlib.util.spec_from_file_location("_copy_library_under_test", SRC)
mod = importlib.util.module_from_spec(_spec)
with contextlib.redirect_stdout(io.StringIO()):
    _spec.loader.exec_module(mod)


def quiet(fn):
    with contextlib.redirect_stdout(io.StringIO()):
        fn()


class LibraryReads(unittest.TestCase):

    def setUp(self):
        mod.rows[:] = []
        mod.notes[:] = []

    def test_no_lab_constant(self):
        self.assertFalse(hasattr(mod, "LAB"))
        for p in (mod.SWIPE_PAID, mod.SWIPE_ORGANIC):
            self.assertNotIn("lab", p.relative_to(mod.WS).parts, p)
        self.assertNotIn('"lab"', SRC.read_text(encoding="utf-8"))

    def test_captions_read_the_component(self):
        cat = mod.WS / "components" / "swipe-organic" / "records" / "owner-saves" / "catalog.json"
        if not cat.is_file():
            self.skipTest(f"{cat.relative_to(mod.WS)} absent")
        quiet(mod.captions)
        saves = [r for r in mod.rows if r.get("audience", {}).get("source") == "owner-saves"]
        self.assertGreaterEqual(len(saves), 1, mod.notes)
        for r in saves:
            self.assertFalse(r["path"].startswith("lab/"), r["path"])

    def test_our_pages_read_brands(self):
        quiet(mod.our_pages)
        pages = [r for r in mod.rows if r["channel"] == "owned-pages"]
        self.assertGreaterEqual(len(pages), 1, mod.notes)
        brands = {r["brand"] for r in pages}
        self.assertEqual(len(brands), 1, brands)
        brand = brands.pop()
        sys.path.append(str(mod.WS / "components" / "brandpath"))
        import brandpath as BP
        base = BP.brand_path(brand, "intake", root=mod.WS / "brands")
        expect = sum(1 for sub in ("landing-pages", "quiz") if (base / sub).is_dir()
                     for f in (base / sub).iterdir() if not f.name.startswith("."))
        self.assertEqual(len(pages), expect)
        for r in pages:
            self.assertTrue(r["path"].startswith("brands/"), r["path"])

    def test_zz_nothing_written(self):
        # Named to sort last, so it sees every reader above.
        newer = []
        for root in (mod.WS / "brands", HERE):
            for f in root.rglob("*"):
                if "__pycache__" in f.parts:
                    continue
                if f.is_file() and f.stat().st_mtime > START:
                    newer.append(str(f.relative_to(mod.WS)))
        self.assertEqual(newer, [])


if __name__ == "__main__":
    unittest.main()
