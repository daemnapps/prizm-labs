#!/usr/bin/env python3
"""LD-105 (check the designed email), the card's tests: the delivery gate reads the email as designed
(design/email.json), so a line fixed on the page clears its finding, and a quote whose credit does not match its
source in the brand's language bank holds the email, naming the source.

    /usr/bin/python3 components/email-production/test_ld105_check_designed_email.py

Offline. A made-up brand `zz-brand` in a temp workspace, its language bank written there; the catalogue, the
calendar hand-off and the look are stubs (as test_si151_picked_reviewed.py). No model, no Klaviyo, no key.

  1  no design: today's reading, every step-8c finding holds
  2  a line fixed on the page clears its finding (written to `cleared`, never dropped silently); one still on the
     page holds
  3  an UNFILLED note the copy kept but the page filled holds nothing
  4  a Reddit line credited to a customer ("· verified buyer") holds, naming the Reddit source; the same line
     credited to Reddit passes
  5  the design build's product check (the rows editor's page holds on) carries the same credit problem
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix="ld105-check-designed-")).resolve()
WS = TMP / "ws"
os.environ["AI_WORKSPACE"] = str(WS)            # before anything imports paths.py

HERE = Path(__file__).resolve().parent
import run_month as RM                            # noqa: E402,F401  (first: simple_email takes this folder off the path)
import simple_email as S                          # noqa: E402  (puts machine/ on the path)
import brand_facts as BF                          # noqa: E402
sys.path.insert(0, str(HERE / "design"))
import build as B                                 # noqa: E402

BRAND, LABEL = "zz-brand", "zz-brand-nov-01"
URL = "https://example.test/p"
REDDIT = "My hair grows in curly so the new hairs grow right back into my skin"
SURVEY = "Using my hands does not cut it enough"
EMAIL = {
    "headline": "Start with teh brush you already own.",
    "body": ["Run it daily, it dont stop.", "[UNFILLED: the customer line]"],
    "offer": None, "button": {"label": "Get it", "link": URL},
    "subjects": [{"subject": "A clean subject", "preview": "A clean preview"}],
}
CHECK = """```CHECK
{"facts": [], "chops": [],
 "typos": [{"quote": "teh brush you already own", "fix": "the brush you already own"},
           {"quote": "it dont stop", "fix": "it doesn't stop"}]}
```
"""


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data, indent=1, ensure_ascii=False))


def bank():
    """brands/zz-brand/core-avatars/a1/language/: a Reddit line and a customer survey line, as research-gatherer
    writes them."""
    lang = WS / "brands" / BRAND / "core-avatars" / "a1" / "language"
    write(lang / "prospects.json", {"avatar": "a1", "funnel": "prospect", "entries": [
        {"id": "language_zz_a1_prospect_1", "text": REDDIT, "speaker": "prospect",
         "source": {"name": "reddit (r/wicked_edge, r/shaving)", "type": "community", "kind": "community",
                    "ref": "https://www.reddit.com/r/wicked_edge/comments/abc"}}]})
    write(lang / "customers" / "one-time.json", {"avatar": "a1", "funnel": "customer", "entries": [
        {"id": "language_zz_a1_customer_1", "text": SURVEY, "speaker": "customer",
         "source": {"name": "Brand Improvement (Customers) survey", "type": "survey", "kind": "survey"}}]})


def run(design=None):
    rd = WS / "runs/email-production" / BRAND / LABEL
    write(rd / "run.json", {"brand": BRAND, "assignment": {}})
    write(rd / "stage8c--check.md", CHECK)
    write(rd / "stage8--blocks.md", "```EMAIL\n%s\n```\n" % json.dumps(EMAIL))
    f = rd / "design" / "email.json"
    if f.exists():
        f.unlink()
    if design is not None:
        write(f, dict({"kind": "design", "brand": BRAND, "label": LABEL, "subject": "A clean subject",
                       "preview": "A clean preview", "link": URL}, sections=design))
    return rd


FIXED = [{"s": "band"},
         {"s": "headline", "text": "Start with the brush you <i>already</i> own.", "sub": "Run it daily, it dont stop."},
         {"s": "example", "quote": SURVEY, "who": "A ZZ customer", "ask": "Tell us where it broke."},
         {"s": "foot"}]


def stubs():
    return [mock.patch.object(BF, "catalogue", lambda brand, ws=None: {"sellable": [{"url": URL}], "never": []}),
            mock.patch.object(S.CH, "inspect", lambda *a, **k: {"problems": []}),
            mock.patch.object(S, "price_check", lambda email, brand, run_dir: []),
            mock.patch.object(S, "saving_check", lambda email, brand, run_dir: []),
            mock.patch.object(S, "look", lambda brand: (_ for _ in ()).throw(AssertionError("look read")))]


class Base(unittest.TestCase):
    def setUp(self):
        bank()
        self._p = stubs()
        for p in self._p:
            p.start()

    def tearDown(self):
        for p in self._p:
            p.stop()

    def items(self, design=None):
        return S.delivery_items(EMAIL, BRAND, run(design))

    def kinds(self, items, kind):
        return [i for i in items if i["kind"] == kind]


class TheCheckReadsTheDesignedEmail(Base):
    def test_no_design_keeps_todays_reading(self):
        got = self.items()
        self.assertEqual(sorted(i["quote"] for i in self.kinds(got, "typo")),
                         ["it dont stop", "teh brush you already own"])
        self.assertEqual(len(self.kinds(got, "unfilled")), 1)

    def test_a_line_fixed_on_the_page_clears_its_finding(self):
        got = self.items(FIXED)
        self.assertEqual([i["quote"] for i in self.kinds(got, "typo")], ["it dont stop"])

    def test_the_cleared_finding_is_written_down_not_dropped(self):
        kept, cleared = S.delivery_split(EMAIL, BRAND, run(FIXED))
        self.assertEqual([i["quote"] for i in kept if i["kind"] == "typo"], ["it dont stop"])
        gone = [c for c in cleared if c["kind"] == "typo"]
        self.assertEqual(len(gone), 1, cleared)
        self.assertEqual(gone[0]["by"], "the designed email")
        self.assertEqual(gone[0]["id"], S.Q.problem_id("delivery", "typo", "teh brush you already own"))

    def test_fixing_every_line_clears_every_finding(self):
        page = [dict(s) for s in FIXED]
        page[1]["sub"] = "Run it daily, it does not stop."
        self.assertEqual(self.kinds(self.items(page), "typo"), [])

    def test_an_unfilled_note_the_page_filled_holds_nothing(self):
        self.assertEqual(self.kinds(self.items(FIXED), "unfilled"), [])
        page = FIXED + [{"s": "headline", "text": "[UNFILLED: still a hole]"}]
        self.assertEqual(len(self.kinds(self.items(page), "unfilled")), 1)


class QuoteCreditsMatchTheirSource(Base):
    def test_a_reddit_line_credited_to_a_verified_buyer_holds_naming_the_source(self):
        page = FIXED[:2] + [{"s": "example", "quote": REDDIT + ".", "who": "A ZZ customer"}] + FIXED[3:]
        bad = self.kinds(self.items(page), "quote-credit")
        self.assertEqual(len(bad), 1, bad)
        self.assertIn("r/wicked_edge", bad[0]["text"])
        self.assertIn("A ZZ customer", bad[0]["text"])

    def test_the_same_line_credited_to_reddit_passes(self):
        page = FIXED + [{"s": "bigquote", "quote": REDDIT, "who": "A man on Reddit"}]
        self.assertEqual(self.kinds(self.items(page), "quote-credit"), [])

    def test_a_quote_inside_a_notes_list_is_read_too(self):
        page = FIXED + [{"s": "notes", "notes": [{"quote": REDDIT, "who": "A ZZ customer"}]}]
        self.assertEqual(len(self.kinds(self.items(page), "quote-credit")), 1)

    def test_eves_card_carries_the_same_problem(self):
        page = FIXED[:2] + [{"s": "example", "quote": REDDIT, "who": "A ZZ customer"}] + FIXED[3:]
        rd = run(page)
        spec = json.loads((rd / "design" / "email.json").read_text())
        spec["_run"] = str(rd)
        rows = B.product_check(spec, {"check": {"prices": {"$1.00": "a stub price"}}}, "Start with the brush.")
        bad = [r for r in rows if r["result"] != "ok" and "r/wicked_edge" in r["detail"]]
        self.assertEqual(len(bad), 1, rows)
        self.assertNotEqual(bad[0].get("about"), "picture")       # the words' problem, not the designer's picture


if __name__ == "__main__":
    unittest.main(verbosity=2)
