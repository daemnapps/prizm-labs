"""What the writer is handed (2026-11-04): the guarantee word for word, the only deadline the plan gives, the send's type,
no code where the bank says none. And the picture chain knows a product by its plain name. No model, no key."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import brief  # noqa: E402
import offers  # noqa: E402

BANK = """# Bank

## the-set — The Set
- Price: **$129.99**

---

# Ruled by a human

### sale — The sale
| Pack | **$57** |
No code necessary.

## Guarantees

### device — device surfaces
> 90 days. If your skin doesn't transform, full refund.

Plus a warranty.

### guarantee — The guarantee, exact wording

> **60-Day Money Back:** "Use it twice a week. If the
> spots do not fade, you get every penny back."

Do not paraphrase.
"""


class Rules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        ws = Path(self.tmp.name)
        (ws / "brands" / "zz" / "products").mkdir(parents=True)
        (ws / "brands" / "zz" / "products" / "offer-bank.md").write_text(BANK)
        (ws / "brands" / "zz" / "email-sms").mkdir()
        (ws / "brands" / "zz" / "email-sms" / "email-types.json").write_text(json.dumps(
            {"types": [{"key": "sale-window", "what": "A discount, open for a stated period."}]}))
        self.p = [mock.patch.object(offers, "WORKSPACE", ws), mock.patch.object(brief, "WORKSPACE", ws)]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()
        self.tmp.cleanup()

    def test_the_guarantee_goes_word_for_word_and_nothing_stands_in(self):
        r = offers.writer_rules("zz", "sale", (), "sale-window", "2026-11-30")
        self.assertIn("90 days. If your skin doesn't transform, full refund.", r)
        self.assertIn('Use it twice a week. If the spots do not fade, you get every penny back."', r)   # a wrapped quote joined
        self.assertIn('no "zero risk"', r)
        self.assertNotIn("Plus a warranty", r)

    def test_the_only_deadline_is_the_plans(self):
        r = offers.writer_rules("zz", "sale", (), "sale-window", "2026-11-30", "2026-12-10")
        self.assertIn("The only deadline this send may state is 2026-11-30", r)
        self.assertIn("Order by 2026-12-10", r)
        self.assertIn("No clock time", r)
        self.assertIn("This send states no deadline", offers.writer_rules("zz", "none", (), "routine"))
        self.assertIn("This send states no deadline", offers.writer_rules("zz", "sale", (), "sale-window", None))

    def test_the_send_stays_its_type(self):
        r = offers.writer_rules("zz", "sale", (), "sale-window", "2026-11-30")
        self.assertIn("This send is a `sale-window`** (A discount, open for a stated period), and it stays one", r)
        self.assertIn("A subscription is named only when the offer above is one", r)

    def test_no_code_where_the_bank_says_none(self):
        self.assertIn("There is no code", offers.writer_rules("zz", "sale", (), "sale-window", "2026-11-30"))

    def test_the_writer_is_handed_the_plans_deadline(self):
        slot = {"id": "nov-01", "offer": "sale", "source": "s.md", "deadline": "2026-11-30", "order_by": "2026-12-10",
                "date":"2026-11-20", "hour":13, "local":True,
                "segment": "S", "type": "sale-window"}
        argv = brief.chain_argv(slot, "zz")
        self.assertEqual(argv[argv.index("--deadline") + 1], "2026-11-30")
        self.assertEqual(argv[argv.index("--order-by") + 1], "2026-12-10")
        self.assertNotIn("--deadline", brief.chain_argv(dict(slot, deadline=None, order_by=None), "zz"))


class BundleWithNoFile(unittest.TestCase):
    def test_a_bundles_bank_section_and_what_it_holds_stand_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            pr = ws / "brands" / "zz" / "products"
            (pr / "body-scrub").mkdir(parents=True)
            (pr / "body-scrub" / "product.md").write_text("# The Body Scrub\nSalt and turmeric.\n")
            (pr / "other.md").write_text("# Other\nNot in it.\n")
            (pr / "offer-bank.md").write_text("# Bank\n\n## the-set — The Set\n- Price: **$79.00**\n"
                                              "- Holds: Body Scrub · a pouch\n\n## other — Other\n- Price: **$9.00**\n")
            with mock.patch.object(offers, "WORKSPACE", ws):
                got = offers.bundle_as_product("zz", "the-set")
                self.assertIsNone(offers.bundle_as_product("zz", "no-such"))
        self.assertIn("$79.00", got)
        self.assertIn("Salt and turmeric", got)
        self.assertNotIn("Not in it", got)


class Pictures(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("picture_chain", HERE / "design" / "picture_chain.py")
        self.P = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.P)

    def test_a_kit_is_found_by_its_plain_name(self):
        with mock.patch.object(self.P, "kits", return_value={"brilliance-body-scrub": ["brilliance-body-scrub"]}):
            self.assertEqual(self.P.products_in("zz", {}, "the Brilliance Body Scrub on a table"), ["brilliance-body-scrub"])
            self.assertEqual(self.P.products_in("zz", {}, "a brilliant scrub of the floor"), [])

    def test_a_products_name_is_not_it_being_used(self):
        self.assertTrue(self.P.at_rest("the Brilliance Body Scrub standing on a table", ["brilliance-body-scrub"]))
        self.assertFalse(self.P.at_rest("she is scrubbing with the Brilliance Body Scrub", ["brilliance-body-scrub"]))
        self.assertFalse(self.P.at_rest("a kitchen table", []))


if __name__ == "__main__":
    unittest.main(verbosity=2)
