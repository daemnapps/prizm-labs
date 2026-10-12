#!/usr/bin/env python3
"""SI-113 (four small fixes), meta-upload#7: the approve page's brand label
comes from the brand's own account file, never a map in the code.

    /usr/bin/python3 components/meta-upload/tests/test_brand_label.py

Stdlib only, offline. The Brand is a stand-in; the real brands/ is only
listed, to know which names must not appear in the source.
"""
import ast, re, sys, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
sys.path.insert(0, str(COMPONENT))
import approve as A   # noqa: E402

REPO = COMPONENT.parent.parent
REAL_BRANDS = sorted(p.name for p in (REPO / "brands").iterdir()
                     if p.is_dir() and not p.name.startswith("_"))


def fake_brand(d):
    class FakeBrand:
        def __init__(self, name):
            self.name = name
            self.d = d

        def pretty(self, slug):
            return "Pretty " + slug
    return FakeBrand


def no_brand(name):
    raise SystemExit("no Meta account file for '%s'" % name)


class BrandLabel(unittest.TestCase):
    def test_the_account_files_label_wins(self):
        with mock.patch.object(A, "Brand", fake_brand({"label": "ZZ-A LABEL"})):
            self.assertEqual(A.brand_label("zz-a"), "ZZ-A LABEL")

    def test_no_label_falls_back_to_the_brands_spelling(self):
        with mock.patch.object(A, "Brand", fake_brand({})):
            self.assertEqual(A.brand_label("zz-a"), "Pretty zz-a")

    def test_an_empty_label_falls_back_too(self):
        with mock.patch.object(A, "Brand", fake_brand({"label": ""})):
            self.assertEqual(A.brand_label("zz-a"), "Pretty zz-a")

    def test_no_account_file_is_the_name(self):
        with mock.patch.object(A, "Brand", no_brand):
            self.assertEqual(A.brand_label("zz-a"), "zz-a")


class NoBrandInSource(unittest.TestCase):
    def test_approve_names_no_brand_as_a_string(self):
        self.assertTrue(REAL_BRANDS)
        tree = ast.parse((COMPONENT / "approve.py").read_text())
        named = sorted({n.value for n in ast.walk(tree)
                        if isinstance(n, ast.Constant)
                        and isinstance(n.value, str)
                        and n.value.lower() in REAL_BRANDS})
        self.assertEqual(named, [])

    def test_docstrings_and_comments_name_no_brand(self):
        word = re.compile(r"\b(%s)\b" % "|".join(map(re.escape, REAL_BRANDS)),
                          re.I)
        for f in (REPO / "components/gdrive-creator/gdrive_creator/engine.py",
                  COMPONENT / "meta.py", COMPONENT / "brand.py"):
            hits = [(i, line.strip()) for i, line
                    in enumerate(f.read_text().splitlines(), 1)
                    if word.search(line)]
            self.assertEqual(hits, [], str(f.relative_to(REPO)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
