#!/usr/bin/env python3
"""LD-106 (readiness check): a free check runs before any email writing is spent. A send that is not ready is not
written, and the check names what is missing; a missing moment look or moment research is reported, never a stop
(decision log 2026-11-04, decision 3: that email is built in the brand's base look with a note for editor).

No network, no model, no key: the store read goes through a seam the tests fill.

    /usr/bin/python3 components/email-production/test_ld106_readiness.py
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix="ld106-")).resolve()
os.environ["AI_WORKSPACE"] = str(TMP)            # before anything imports paths.py

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import readiness as R                              # noqa: E402
import run_month as M                              # noqa: E402

BRAND = "zz"
BANK = """# Offer bank

## the-set — The Set
_lane: a_
- Price: **$59.00**
- Link: https://shop.example/products/the-set-handle

## no-price — A thing with no price
- Link: https://shop.example/products/no-price
"""


def brand_files(shopify=True, themes=("halloween",)):
    b = TMP / "brands" / BRAND
    (b / "products").mkdir(parents=True, exist_ok=True)
    (b / "email-sms").mkdir(parents=True, exist_ok=True)
    (b / "products" / "offer-bank.md").write_text(BANK)
    (b / "email-sms" / "machine.json").write_text(json.dumps(
        {"store_feed": "https://shop.example/products.json" if shopify else None, "site": "https://shop.example"}))
    (b / "email-sms" / "design-system.json").write_text(json.dumps({"themes": {t: {} for t in themes}}))


def slot(**kw):
    s = {"id": "nov-01", "date": "2026-11-20", "hour": 13, "local": True, "type": "sale-window",
         "segments": ["Core | Lead"], "product": "none", "offer": "none", "occasion": "a recorded problem"}
    s.update(kw)
    return s


class Store:
    """The seam: answers the store would give, and every URL asked."""

    def __init__(self, answers):
        self.answers, self.asked = answers, []

    def __call__(self, url):
        self.asked.append(url)
        for key, answer in self.answers.items():
            if "/products/%s.js" % key in url:
                return answer
        return 404, ""


def live(available=True):
    return 200, json.dumps({"available": available, "variants": [{"available": available}]})


def fresh_stock(store):
    cache = TMP / "runs" / "email-production" / BRAND / "readiness" / "stock-cache.json"
    if cache.exists():
        cache.unlink()
    return R.Stock(BRAND, fetch=store, pace=0, wait=lambda s: None)


class StockAsAUSShopper(unittest.TestCase):
    def setUp(self):
        brand_files()

    def test_a_sold_out_product_is_not_ready_and_named(self):
        store = Store({"the-set-handle": live(False)})
        r = R.check(slot(product="the-set"), BRAND, "a", "nov-01", stock=fresh_stock(store))
        self.assertFalse(r["ready"])
        self.assertTrue(any("sold out" in m and "the-set" in m for m in r["missing"]), r["missing"])

    def test_the_store_is_asked_as_a_us_shopper_through_the_bank_link(self):
        store = Store({"the-set-handle": live(True)})
        r = R.check(slot(product="the-set"), BRAND, "a", "nov-01", stock=fresh_stock(store))
        self.assertTrue(r["ready"], r)
        self.assertEqual(store.asked, ["https://shop.example/products/the-set-handle.js?country=US"])

    def test_the_answer_is_cached_so_the_store_is_asked_once(self):
        store = Store({"the-set-handle": live(True)})
        stock = fresh_stock(store)
        R.check(slot(product="the-set"), BRAND, "a", "nov-01", stock=stock)
        R.check(slot(id="nov-02", product="the-set"), BRAND, "a", "nov-02", stock=stock)
        R.check(slot(id="nov-03", product="the-set"), BRAND, "a", "nov-03", stock=R.Stock(BRAND, fetch=store, pace=0))
        self.assertEqual(len(store.asked), 1, store.asked)
        cache = TMP / "runs" / "email-production" / BRAND / "readiness" / "stock-cache.json"
        self.assertTrue(cache.is_file())

    def test_a_rate_limited_store_is_a_note_not_a_stop_and_not_cached(self):
        store = Store({"the-set-handle": (429, "", "7")})
        waits = []
        stock = R.Stock(BRAND, fetch=store, pace=0, wait=waits.append)
        fresh_stock(None)
        r = R.check(slot(product="the-set"), BRAND, "a", "nov-01", stock=stock)
        self.assertTrue(r["ready"], r)
        self.assertTrue(any("429" in n for n in r["notes"]), r["notes"])
        self.assertEqual(len(store.asked), 1 + R.RETRIES)          # asked again after the store's named wait
        self.assertEqual(waits, [7] * R.RETRIES)
        R.check(slot(id="nov-02", product="the-set"), BRAND, "a", "nov-02", stock=stock)
        self.assertEqual(len(store.asked), 1 + R.RETRIES)          # never asked twice in one batch
        R.check(slot(product="the-set"), BRAND, "a", "nov-01", stock=R.Stock(BRAND, fetch=store, pace=0, wait=waits.append))
        self.assertEqual(len(store.asked), 2 * (1 + R.RETRIES))    # not cached: the next batch asks again

    def test_a_429_that_clears_on_the_retry_is_read(self):
        answers = [(429, "", ""), live(False)]
        asked = []

        def store(url):
            asked.append(url)
            return answers.pop(0)
        r = R.check(slot(product="the-set"), BRAND, "a", "nov-01",
                    stock=R.Stock(BRAND, fetch=store, pace=0, wait=lambda s: None) if fresh_stock(None) else None)
        self.assertEqual(len(asked), 2)
        self.assertFalse(r["ready"])
        self.assertTrue(any("sold out" in m for m in r["missing"]), r["missing"])

    def test_a_product_the_store_does_not_have_is_not_ready(self):
        r = R.check(slot(product="gone-thing"), BRAND, "a", "nov-01", stock=fresh_stock(Store({})))
        self.assertFalse(r["ready"])
        self.assertTrue(any("gone-thing" in m for m in r["missing"]), r["missing"])

    def test_a_brand_with_no_shopify_store_is_not_read_and_says_so(self):
        brand_files(shopify=False)
        store = Store({})
        r = R.check(slot(product="the-set"), BRAND, "a", "nov-01", stock=fresh_stock(store))
        self.assertTrue(r["ready"], r)
        self.assertEqual(store.asked, [])
        self.assertTrue(any("stock not read" in n for n in r["notes"]), r["notes"])


class OfferBankPrice(unittest.TestCase):
    def setUp(self):
        brand_files()

    def test_an_offer_not_in_the_bank_is_not_ready(self):
        r = R.check(slot(offer="made-up-offer"), BRAND, "a", "nov-01", stock=fresh_stock(Store({})))
        self.assertFalse(r["ready"])
        self.assertTrue(any("made-up-offer" in m and "offer bank" in m for m in r["missing"]), r["missing"])

    def test_an_offer_with_no_price_in_the_bank_is_not_ready(self):
        r = R.check(slot(offer="no-price"), BRAND, None, "nov-01", stock=fresh_stock(Store({"no-price": live()})))
        self.assertFalse(r["ready"])
        self.assertTrue(any("no price" in m and "no-price" in m for m in r["missing"]), r["missing"])

    def test_a_priced_offer_in_stock_is_ready(self):
        r = R.check(slot(offer="the-set"), BRAND, "a", "nov-01", stock=fresh_stock(Store({"the-set-handle": live()})))
        self.assertTrue(r["ready"], r)


class MomentFilesAreNotesForEve(unittest.TestCase):
    def setUp(self):
        brand_files(themes=("halloween",))

    def test_a_missing_moment_look_is_reported_not_stopped(self):
        r = R.check(slot(occasion="black-friday"), BRAND, "a", "nov-01", stock=fresh_stock(Store({})))
        self.assertTrue(r["ready"], r)
        self.assertTrue(any("for editor" in n and "look" in n and "black-friday" in n for n in r["notes"]), r["notes"])

    def test_missing_moment_research_is_reported_not_stopped(self):
        r = R.check(slot(occasion="halloween"), BRAND, "a", "nov-01", stock=fresh_stock(Store({})))
        self.assertTrue(r["ready"], r)
        self.assertTrue(any("for editor" in n and "research" in n and "halloween" in n for n in r["notes"]), r["notes"])
        self.assertFalse(any("look" in n for n in r["notes"]), r["notes"])   # halloween HAS a look

    def test_moment_research_on_file_clears_the_note(self):
        d = TMP / "runs" / "moment-research" / BRAND / "a"
        d.mkdir(parents=True, exist_ok=True)
        (d / "halloween.research.md").write_text("research")
        r = R.check(slot(occasion="halloween"), BRAND, "a", "nov-01", stock=fresh_stock(Store({})))
        self.assertEqual(r["notes"], [])

    def test_a_prose_occasion_is_no_moment(self):
        r = R.check(slot(occasion="a recorded problem — dry skin"), BRAND, "a", "nov-01", stock=fresh_stock(Store({})))
        self.assertEqual(r["notes"], [])


class CalendarIdentity(unittest.TestCase):
    def setUp(self):
        brand_files()

    def test_a_send_with_no_hour_is_not_ready(self):
        s = slot()
        del s["hour"]
        r = R.check(s, BRAND, "a", "nov-01", stock=fresh_stock(Store({})))
        self.assertFalse(r["ready"])
        self.assertTrue(any("calendar" in m and "hour" in m for m in r["missing"]), r["missing"])

    def test_a_written_email_whose_calendar_send_changed_says_so(self):
        run = TMP / "runs" / "email-production" / BRAND / "nov-01"
        run.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, str(run))        # its own temp folder: the other tests' nov-01 is unwritten
        (run / "run.json").write_text(json.dumps({"assignment": {"send_date": "2026-11-19", "type": "sale-window"}}))
        r = R.check(slot(), BRAND, "a", "nov-01", stock=fresh_stock(Store({})))
        self.assertTrue(r["ready"], r)                      # rewriting it is the fix, not a stop
        self.assertTrue(any("date changed" in n for n in r["notes"]), r["notes"])


class TheLine(unittest.TestCase):
    def test_a_line_says_ready_or_not_ready_because(self):
        self.assertEqual(R.line({"label": "nov-01", "ready": True, "missing": [], "notes": []}), "ready      nov-01")
        self.assertEqual(R.line({"label": "nov-02", "ready": False, "missing": ["a", "b"], "notes": []}),
                         "NOT READY  nov-02  because a; b")
        self.assertIn("for editor: x", R.line({"label": "nov-03", "ready": True, "missing": [], "notes": ["for editor: x"]}))

    def test_no_brand_name_in_the_code(self):
        text = (HERE / "readiness.py").read_text().lower()
        for name in ("brand_a", "brand_b"):
            self.assertNotIn(name, text)


SLOTS = [slot(id="nov-01", product="the-set"), slot(id="nov-02", product="none"),
         slot(id="nov-03", offer="made-up-offer")]


def run_month(*extra):
    brand_files()
    d = TMP / "month"
    d.mkdir(exist_ok=True)
    (d / "slots.json").write_text(json.dumps(SLOTS))
    (d / "run.json").write_text(json.dumps({"brand": BRAND}))
    got = {"labels": None}

    def produce(jobs, *a, **k):
        got["labels"] = [lab for lab, _ in jobs]
        return 0
    out = io.StringIO()
    store = Store({"the-set-handle": live(False)})
    with mock.patch.object(M, "produce", produce), mock.patch.object(M.brief, "chain_argv", return_value=["x"]), \
            mock.patch.object(M.brief, "label_prefix", return_value=""), \
            mock.patch.object(M.EE, "type_problem", return_value=None), \
            mock.patch.object(R, "FETCH", store), mock.patch.object(R, "PACE", 0), \
            mock.patch("reviewed_plan.reviewed", lambda _d, s: [dict(x, _review={"note": None, "edits": []}) for x in s]), \
            mock.patch.object(sys, "argv", ["run_month.py", str(d), *extra]), redirect_stdout(out):
        try:
            M.main()
        except SystemExit:
            pass
    return got["labels"], out.getvalue()


class BeforeAnySpend(unittest.TestCase):
    def test_the_batch_lists_ready_or_not_per_send_and_writes_only_the_ready(self):
        fresh_stock(None)
        labels, out = run_month()
        self.assertEqual(labels, ["nov-02"])
        self.assertIn("ready      nov-02", out)
        self.assertRegex(out, r"NOT READY  nov-01  because .*sold out")
        self.assertRegex(out, r"NOT READY  nov-03  because .*made-up-offer")

    def test_the_readiness_switch_spends_nothing(self):
        fresh_stock(None)
        labels, out = run_month("--readiness")
        self.assertIsNone(labels)                       # produce never ran: nothing written, nothing spent
        self.assertIn("ready      nov-02", out)
        self.assertIn("NOT READY  nov-01", out)


if __name__ == "__main__":
    unittest.main(verbosity=1)
