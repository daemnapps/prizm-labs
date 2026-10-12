#!/usr/bin/env python3
"""SI-113 (four small fixes), swipe-paid#10: the swipe board finds its brands
on disk — every brand folder with signed angles — instead of naming them.

    /usr/bin/python3 components/swipe-paid/test_signed_angle_brands.py

Stdlib only, offline. The brands tree is a tempfile folder; the real brands/
is only listed, to know which names must not appear in the source.
"""
import ast, json, os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import serve as S   # noqa: E402

N = S.N
REAL_BRANDS = sorted(p.name for p in (N.WS / "brands").iterdir()
                     if p.is_dir() and not p.name.startswith("_"))


def angles(folder, active):
    f = folder / "strategy" / "angles.json"
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps({"angles": [
        {"id": a, "status": "active"} for a in active]
        + [{"id": "zz-unsigned", "status": "draft"}]}))


class SignedAngleBrands(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        self.brands = self.ws / "brands"
        angles(self.brands / "zz-a", ["zz-angle"])
        (self.brands / "zz-b" / "strategy").mkdir(parents=True)
        angles(self.brands / "_TEMPLATE", ["zz-template-angle"])
        (self.brands / "README.md").write_text("not a brand\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_brands_with_signed_angles(self):
        with mock.patch.object(N, "WS", self.ws):
            got = S.signed_angle_brands(self.brands)
        self.assertEqual(got, {"zz-a": ["zz-angle"]})

    def test_default_root_is_the_workspace_brands_tree(self):
        with mock.patch.object(N, "WS", self.ws):
            self.assertEqual(S.signed_angle_brands(), {"zz-a": ["zz-angle"]})

    def test_a_new_brand_appears_without_a_code_change(self):
        angles(self.brands / "zz-c", ["zz-other", "zz-first"])
        with mock.patch.object(N, "WS", self.ws):
            got = S.signed_angle_brands(self.brands)
        self.assertEqual(got, {"zz-a": ["zz-angle"],
                               "zz-c": ["zz-first", "zz-other"]})

    def test_no_brands_tree_is_empty_not_a_crash(self):
        self.assertEqual(S.signed_angle_brands(self.ws / "nowhere"), {})


class NoBrandLiteral(unittest.TestCase):
    def setUp(self):
        self.tree = ast.parse(Path(S.__file__).read_text())

    def test_signed_angles_site_calls_the_finder(self):
        sites = [v for d in ast.walk(self.tree) if isinstance(d, ast.Dict)
                 for k, v in zip(d.keys, d.values)
                 if isinstance(k, ast.Constant) and k.value == "signed_angles"]
        self.assertEqual(len(sites), 1)
        call = sites[0]
        self.assertIsInstance(call, ast.Call)
        self.assertEqual(getattr(call.func, "id", None), "signed_angle_brands")

    def test_no_brand_name_as_a_string_in_serve(self):
        self.assertTrue(REAL_BRANDS)
        named = sorted({n.value for n in ast.walk(self.tree)
                        if isinstance(n, ast.Constant)
                        and isinstance(n.value, str)
                        and n.value.lower() in REAL_BRANDS})
        self.assertEqual(named, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
