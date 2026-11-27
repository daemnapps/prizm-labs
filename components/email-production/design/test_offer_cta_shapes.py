"""An offer section's button comes as words, as {"label", "link"} or not at all, and the build never dies on it
(brand_a dec-13 and dec-15, 2026-11-16: a layout wrote the button as a dict, and design/build.py stopped with
"'dict' object has no attribute 'replace'"). No network, no key.

    python3 components/email-production/design/test_offer_cta_shapes.py
"""
import sys
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine as EN  # noqa: E402


class OfferButton(unittest.TestCase):
    def test_words_give_the_button(self):
        out = EN.s_offer({}, {"price": "$109.99", "cta": "GET THE KING SET"}, {})
        self.assertEqual(len(out), 2)
        self.assertIn("GET THE KING SET", out[1])

    def test_a_label_and_link_give_the_same_button(self):
        out = EN.s_offer({}, {"price": "$109.99", "cta": {"label": "GET THE KING SET", "link": "https://x"}}, {})
        self.assertEqual(len(out), 2)
        self.assertIn("GET THE KING SET", out[1])

    def test_no_button_is_the_price_alone(self):
        out = EN.s_offer({}, {"price": "$109.99", "was": "$139.95"}, {})
        self.assertEqual(len(out), 1)
        self.assertIn("$109.99", out[0])
        self.assertIn("$139.95", out[0])


class EverySection(unittest.TestCase):
    def test_a_product_card_with_a_label_and_link_renders(self):
        # brand_a dec-15: the product card's button came as {"label", "link"} too, and s_product escaped a dict
        s = {"s": "product", "name": "The King Set", "line": "Five in the box.", "price": "$129.99", "picture": {"photo": "x"},
             "cta": {"label": "GET THE KING SET", "link": "https://x"}}
        with unittest.mock.patch.object(EN, "picture", lambda *a, **k: ""), \
                unittest.mock.patch.object(EN, "house", lambda spec, lk: spec), \
                unittest.mock.patch.object(EN, "buying_defaults", lambda spec: spec["sections"]):
            out = EN.sections({"sections": [s]}, {})
        self.assertIn("GET THE KING SET", "".join(h for _, h in out) if out and isinstance(out[0], tuple) else str(out))


if __name__ == "__main__":
    unittest.main(verbosity=2)
