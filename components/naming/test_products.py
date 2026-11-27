#!/usr/bin/env python3
"""One product record, the same way for every brand (components/naming/products.py).

    /usr/bin/python3 components/naming/test_products.py

Stdlib unittest, Python 3.9. Reads the workspace's own brand folders and kits; no network, no model, no key.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import names  # noqa: E402
import products as P  # noqa: E402


class Products(unittest.TestCase):
    def test_every_brand_and_product_gets_the_same_shape(self):
        seen = 0
        for b in P.brands():
            for pid in names.product_ids(b):
                r = P.record(b, pid)
                self.assertIsNotNone(r, (b, pid))
                self.assertEqual((r["brand"], r["id"]), (b, pid))
                self.assertTrue(set(r["missing"]) <= set(P.PARTS))
                for part in P.PARTS:                                  # held, or named as missing; never both
                    self.assertNotEqual(bool(r.get(part)), part in r["missing"], (b, pid, part))
                for path in [r.get("bank"), r.get("kit")] + list(r.get("refs") or []):
                    if path:
                        self.assertFalse(path.startswith("/"), path)  # repo-relative (builder card rule 4)
                        self.assertTrue((P._root() / path).exists(), path)
                for d in r.get("drive") or []:
                    self.assertTrue(d["drive_id"] and d["label"].startswith("Shared Assets/"), d)
                seen += 1
        if not seen:
            self.skipTest("no brand products in this checkout")

    def test_any_name_of_a_product_gives_the_same_record(self):
        for b in P.brands():
            for pid in names.product_ids(b):
                for alias in names.product_aliases(b, pid):
                    self.assertEqual(P.record(b, alias)["id"], pid, (b, alias))

    def test_an_unknown_name_is_no_product(self):
        for b in P.brands():
            self.assertIsNone(P.record(b, "no-such-product-anywhere"))

    def test_check_lists_every_brand(self):
        rows = P.check()
        self.assertEqual(sorted({b for b, _, _ in rows}), P.brands())


if __name__ == "__main__":
    unittest.main()
