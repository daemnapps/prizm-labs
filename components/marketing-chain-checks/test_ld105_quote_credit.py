#!/usr/bin/env python3
"""LD-105 (check the designed email), the shared half: the check step's findings are read against the words a
reader will get, and a quote's credit must match where the language bank says it was said.

    /usr/bin/python3 components/marketing-chain-checks/test_ld105_quote_credit.py

The cases are the real ones from the November audit (runs/email-production/notes/2026-11-04-november-email-audit.md,
fact 4 and 5), with their words and source fields copied into made-up rows; no brand is named.

  1  a finding whose quoted line is gone from the page clears; one still on the page holds; an unreadable check holds
  2  read_check_block reads the same way; with no page text it is today's reading, unchanged
  3  a Reddit post credited to a customer holds, naming the Reddit source
  4  a YouTube comment and a TikTok comment the bank only ASSUMES is a customer's hold as a customer's line
  5  a customer survey line credited to a customer passes; a Reddit line credited to Reddit passes
  6  an Instagram ad comment credited to a follower passes, even with one typo fixed (the near match)
  7  a paid panel line credited to a customer holds; credited to the panel it passes
  8  a quote the bank does not hold, or a credit that names no kind of source (a first name), is not judged here
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import marketing_chain_checks as Q  # noqa: E402

CHECK = """```CHECK
{"facts": [], "chops": [],
 "typos": [{"quote": "teh brush you already own", "fix": "the brush you already own"},
           {"quote": "it dont stop", "fix": "it doesn't stop"}]}
```"""
PAGE = ("Never written for your face. Start with the brush you already own. "
        "Run daily, it dont stop. Send it back and we refund you.")


def row(text, name, typ, speaker, ref=None, attribution=None, kind=None):
    r = {"id": "language_zz_%d" % (abs(hash(text)) % 10000), "text": text, "speaker": speaker,
         "source": {"name": name, "type": typ, "kind": kind or typ}}
    if ref:
        r["source"]["ref"] = ref
    if attribution:
        r["attribution"] = attribution
    return r


REDDIT = "My hair grows in curly so the new hairs grow right back into my skin"
SURVEY = "Using my hands does not cut it enough"
TIKTOK = "Yall forget this takes time and not something you do once and see change"
YOUTUBE = "The US Army issued me a shaving profile. My wife has been wanting me to shave forever, but I keep getting razor bumps"
INSTA = "First time I stayed and watched an ad. Man I been using so many products 8 got tired and stopped shaving I need this"
PANEL = "I noticed a significant difference from the first use"
ROWS = [
    row(REDDIT, "reddit (r/wicked_edge, r/Blackskincare, r/bald, r/shaving)", "community", "prospect",
        ref="https://www.reddit.com/r/wicked_edge/comments/abc"),
    row(SURVEY, "Brand Improvement (Customers) survey — Q: What gut instinct made you buy?", "survey", "customer"),
    row(TIKTOK, "TikTok comment", "comment", "customer", attribution="assumed", kind="post",
        ref="https://www.tiktok.com/@zz/video/1?comment_id=2"),
    # the experience index's shape: a quote, a source type and a url, no speaker
    {"id": "x-6a9a6823f3", "quote": YOUTUBE, "source": {"type": "youtube-comment", "url": "https://www.youtube.com/watch?v=x"}},
    row(INSTA, "Instagram ad comment", "comment", "lead", kind="post"),
    row(PANEL, "paid creator panel (participants are paid, NOT customers)", "panel", "customer"),
]


class FindingsReadThePage(unittest.TestCase):
    def test_a_line_fixed_on_the_page_clears_its_finding(self):
        live, gone = Q.check_split(CHECK, "delivery", PAGE)
        self.assertEqual([i["quote"] for i in live], ["it dont stop"])
        self.assertEqual([i["quote"] for i in gone], ["teh brush you already own"])
        self.assertEqual(Q.check_items(CHECK, "delivery", still_in=PAGE), live)

    def test_case_spacing_and_markup_do_not_keep_a_finding_alive_or_clear_it(self):
        page = "Run   daily, <i>IT</i> dont stop."
        live, gone = Q.check_split(CHECK, "delivery", page)
        self.assertEqual([i["quote"] for i in live], ["it dont stop"])

    def test_an_unreadable_check_still_holds(self):
        live, gone = Q.check_split("no block here", "delivery", PAGE)
        self.assertEqual([i["kind"] for i in live], ["check-unreadable"])
        self.assertEqual(gone, [])

    def test_read_check_block_reads_the_same_way_and_is_unchanged_without_a_page(self):
        self.assertEqual(Q.read_check_block(CHECK, still_in=PAGE), [i["text"] for i in Q.check_split(CHECK, "delivery", PAGE)[0]])
        self.assertEqual(len(Q.read_check_block(CHECK)), 2)
        self.assertEqual(len(Q.check_items(CHECK, "delivery")), 2)


class CreditsMatchTheirSource(unittest.TestCase):
    def check(self, quote, who, verified=False):
        return Q.quote_credit_check([{"quote": quote, "who": who, "verified": verified}], ROWS)

    def test_a_reddit_post_credited_to_a_customer_holds_naming_the_source(self):
        p = self.check(REDDIT + ".", "A ZZ customer", verified=True)
        self.assertEqual(len(p), 1, p)
        self.assertIn("reddit", p[0].lower())
        self.assertIn("r/wicked_edge", p[0])
        self.assertIn("A ZZ customer", p[0])
        self.assertIn("verified buyer", p[0])

    def test_a_youtube_comment_credited_to_a_customer_holds(self):
        p = self.check(YOUTUBE + ".", "A ZZ customer")
        self.assertEqual(len(p), 1, p)
        self.assertIn("youtube", p[0].lower())

    def test_a_comment_the_bank_only_assumes_is_a_customer_is_not_a_customers_line(self):
        p = self.check(TIKTOK, "A ZZ customer", verified=True)
        self.assertEqual(len(p), 1, p)
        self.assertIn("TikTok comment", p[0])

    def test_a_customer_survey_line_credited_to_a_customer_passes(self):
        self.assertEqual(self.check(SURVEY, "A ZZ customer", verified=True), [])

    def test_a_reddit_line_credited_to_reddit_passes(self):
        self.assertEqual(self.check(REDDIT, "A man on Reddit"), [])

    def test_an_ad_comment_credited_to_a_follower_passes_with_a_typo_fixed(self):
        fixed = INSTA.replace(" 8 got", " I got")
        self.assertEqual(self.check(fixed, "A ZZ follower"), [])
        p = self.check(fixed, "A ZZ customer")
        self.assertEqual(len(p), 1, p)
        self.assertIn("Instagram ad comment", p[0])

    def test_a_paid_panel_line_is_not_a_customers(self):
        self.assertEqual(len(self.check(PANEL, "A ZZ customer")), 1)
        self.assertEqual(self.check(PANEL, "A tester in our product panel"), [])

    def test_what_this_check_does_not_judge(self):
        self.assertEqual(self.check("A line no bank holds, word for word or near it.", "A ZZ customer"), [])
        self.assertEqual(self.check(REDDIT, "Andrew"), [])                 # a first name claims no kind of source
        self.assertEqual(self.check(REDDIT, ""), [])

    def test_a_section_that_prints_verified_buyer_claims_a_customer_whatever_the_name(self):
        self.assertEqual(Q.credit_claim("Andrew", verified=True), "customer")
        self.assertEqual(len(self.check(REDDIT, "Andrew", verified=True)), 1)

    def test_a_customer_survey_asking_about_competitors_is_still_a_customers_line(self):
        # found on the real November emails: the survey question names competitors, the speaker is our customer
        r = row("a brush to get into my pores and really clean them",
                "Brand Improvement (Customers) survey — Q: What annoyed you about other grooming products from competitors?",
                "survey", "customer")
        self.assertEqual(Q.source_kind(r), "customer")
        review = row("This soap faded my spots", "Amazon reviews — competitor kojic soap (market voice)", "review", "customer")
        self.assertEqual(Q.source_kind(review), "review")

    def test_the_source_kinds(self):
        kinds = [Q.source_kind(r) for r in ROWS]
        self.assertEqual(kinds, ["reddit", "customer", "tiktok", "youtube", "instagram", "panel"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
