"""SI-110 (variations one locator): format_swap, proven_to_format and measure
find the workspace through run-kit's paths.repo(), never by counting parents;
brandctx reads brand folders through brandpath, so a clone anywhere reads its
own brands/. Offline; every tree is a temp folder. Read-only on brands/."""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "run-kit"))
from run_kit import paths  # noqa: E402

sys.path.insert(0, str(HERE))
import brandctx  # noqa: E402
import format_swap  # noqa: E402
import measure  # noqa: E402
with contextlib.redirect_stderr(io.StringIO()):
    import proven_to_format  # noqa: E402

BRAND, AVATAR = "zz-brand", "a1"


class OneLocator(unittest.TestCase):
    def test_repo_lines_use_run_kit(self):
        want = paths.repo(HERE)
        for mod in (format_swap, proven_to_format, measure):
            with self.subTest(module=mod.__name__):
                self.assertEqual(mod.REPO, want)

    def test_no_parent_counting(self):
        for f in ("format_swap.py", "proven_to_format.py", "measure.py"):
            with self.subTest(file=f):
                self.assertNotIn("parents[2]", (HERE / f).read_text())

    def test_default_layout_home_unchanged(self):
        root = paths.repo(HERE)
        c = brandctx.BrandContext(root, BRAND)
        self.assertEqual(c.home, root / "brands" / BRAND)


class TempClone(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve() / "clone"
        real = paths.repo(HERE)
        for p in (real, Path.home() / "Projects" / "workspace"):
            self.assertNotIn(p, [self.root, *self.root.parents])
        bp = self.root / "components" / "brandpath"
        bp.mkdir(parents=True)
        shutil.copy(real / "components" / "brandpath" / "brandpath.py", bp / "brandpath.py")
        b = self.root / "brands" / BRAND
        (b / "products").mkdir(parents=True)
        (b / "products" / "heroes.json").write_text(json.dumps({"heroes": ["hero-one"], "hero_rule": "lead with it"}))
        lang = b / "core-avatars" / AVATAR / "language"
        lang.mkdir(parents=True)
        (lang / "bank.json").write_text(json.dumps({"entries": [
            {"id": "L1", "text": "a verbatim customer line long enough to keep", "status": "active",
             "use": ["hook"]}]}))     # queried through the language layer, which picks rows by what they are

    def tearDown(self):
        self.tmp.cleanup()

    def test_products_and_language_read_the_clone(self):
        c = brandctx.BrandContext(self.root, BRAND, AVATAR)
        self.assertEqual(c.home, self.root / "brands" / BRAND)

        prod = c.products()
        self.assertNotEqual(prod, brandctx.MISSING)
        self.assertIn("hero-one", prod)
        self.assertIn(f"brands/{BRAND}/products/heroes.json", c.read_files)

        lang = c.language()
        self.assertNotEqual(lang, brandctx.MISSING)
        self.assertIn("a verbatim customer line", lang)
        self.assertIn(f"brands/{BRAND}/core-avatars/{AVATAR}/language/bank.json", c.read_files)


if __name__ == "__main__":
    unittest.main()
