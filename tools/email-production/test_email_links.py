#!/usr/bin/env python3
"""Every own link in an email carries the tracking standard's email tags, and the Klaviyo
draft's own UTM tracking says the same thing — proven without Klaviyo.

    python3 test_email_links.py

A made-up brand in a temp workspace; the Klaviyo call is replaced by a recorder.

  1  the finished HTML tags the logo and the button (utm_source/medium/campaign/content,
     utm_term = the segment), adds funnel= on a CPK funnel page, keeps the link's own query
     string and merge tags, and leaves unsubscribe, mailto and partner links alone
  2  tagging twice changes nothing (never doubled)
  3  the delivery gate holds an email whose own links miss the tags, and passes the tagged one
  4  the draft sets Klaviyo's tracking_options to the same values the links carry, and the
     template Klaviyo gets is the tagged HTML
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlsplit

TMP = Path(tempfile.mkdtemp(prefix="email-links-test-"))
WS = TMP / "ws"
os.environ["AI_WORKSPACE"] = str(WS)            # before anything imports paths.py

import simple_email as S                          # noqa: E402

BRAND, LABEL = "testbrand", "testbrand-jan-02--someone"
FUNNEL = "https://go.example.test/f1/quiz/?ref=a&e={{ email|urlencode }}"
EMAIL = {
    "headline": "A headline", "hero": {"prompt": "p", "alt": "a"},
    "body": ["One.", "Two."], "offer": None,
    "button": {"label": "Take the quiz", "link": FUNNEL},
    "subjects": [{"subject": "A subject", "preview": "A preview"}],
}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data, indent=1))


def make_brand():
    b = WS / "brands" / BRAND
    write(b / "email-sms/simple.json", {
        "logo": {"url": "https://cdn.example.net/logo.png", "alt": "T", "width": 100,
                 "link": "https://www.example.test"},
        "from": {"email": "hi@example.test", "label": "Test"},
        "send_time": {"local": "13:00", "recipient_time_zone": True},
        "klaviyo_key": "KLAVIYO_TESTBRAND_KEY",
        "fonts": {"headline": "serif", "body": "sans-serif"},
        "colors": {"page": "#fff", "card": "#fff", "text": "#000", "muted": "#777",
                   "button": "#000", "button_text": "#fff"}})
    write(b / "web/funnels/tracking.json", {"funnels": [
        {"name": "F1", "hosts": ["go.example.test"],
         "pages": [{"path": "/f1/quiz/", "step": "quiz"}, {"path": "/f1/checkout/", "step": "checkout"}]}]})


def links(doc):
    import html, re
    return [html.unescape(h) for h in re.findall(r'href="([^"]+)"', doc)]


def q(url):
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}


class Tags(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        make_brand()
        cls.lk = S.look(BRAND)

    def doc(self, email=EMAIL, term="Core | Lead"):
        return S.finished_html(email, self.lk, {}, "cid:logo", BRAND, LABEL, term)

    def test_logo_and_button_carry_the_standard(self):
        hs = links(self.doc())
        logo = next(h for h in hs if "www.example.test" in h)
        button = next(h for h in hs if "go.example.test" in h)
        self.assertEqual(q(logo)["utm_source"], "klaviyo")
        self.assertEqual(q(logo)["utm_medium"], "email")
        self.assertEqual(q(logo)["utm_campaign"], LABEL)
        self.assertEqual(q(logo)["utm_content"], LABEL + ".logo")
        self.assertEqual(q(button)["utm_content"], LABEL + ".button")
        self.assertEqual(q(button)["utm_term"], "Core | Lead")
        self.assertEqual(q(button)["funnel"], "F1")          # a CPK funnel page
        self.assertNotIn("funnel", q(logo))                   # the store is not a funnel
        self.assertIn("ref=a&e={{ email|urlencode }}&utm_source=klaviyo", button)   # kept as written

    def test_unsubscribe_mailto_and_partner_links_are_left_alone(self):
        doc = self.doc() + ('<a href="mailto:hi@example.test">m</a>'
                            '<a href="https://partner.example.org/x?aff=1">p</a>')
        out = S.EL.tag(doc, BRAND, LABEL, workspace=WS)
        hs = links(out)
        self.assertIn("{% unsubscribe_link %}", hs)
        self.assertIn("mailto:hi@example.test", hs)
        self.assertIn("https://partner.example.org/x?aff=1", hs)
        self.assertEqual(S.link_problems(out, BRAND), [])

    def test_tagging_twice_never_doubles(self):
        once = self.doc()
        twice = S.EL.tag(once, BRAND, LABEL, LABEL, "Core | Lead", WS)
        self.assertEqual(once, twice)
        button = next(h for h in links(once) if "go.example.test" in h)
        self.assertEqual(button.count("utm_source="), 1)

    def test_a_link_that_overrides_the_source_is_corrected_not_doubled(self):
        e = dict(EMAIL, button={"label": "Go", "link": "https://example.test/p?utm_source=facebook"})
        button = next(h for h in links(self.doc(e)) if "example.test/p" in h)
        self.assertEqual(button.count("utm_source="), 1)
        self.assertEqual(q(button)["utm_source"], "klaviyo")

    def test_the_gate_holds_untagged_links_and_passes_tagged_ones(self):
        raw = S.render(EMAIL, self.lk, {}, "cid:logo")
        found = S.link_problems(raw, BRAND)
        self.assertTrue(any("missing utm_source" in p for p in found), found)
        self.assertTrue(any("no funnel=F1" in p for p in found), found)
        self.assertEqual(S.link_problems(self.doc(), BRAND), [])

    def test_the_draft_tells_klaviyo_the_same_tags(self):
        calls = []

        def kl(method, path, key, payload=None, form=None):
            calls.append((method, path, payload))
            if path == "templates":
                return {"data": {"id": "T1"}}
            if path == "campaigns":
                return {"data": {"id": "C1", "relationships": {"campaign-messages": {"data": [{"id": "M1"}]}}}}
            return {}
        doc = self.doc(term="Core | Lead")
        with mock.patch.object(S, "kl", kl):
            S.create_draft("KEY", doc, EMAIL, self.lk, BRAND, LABEL, {"date": "2099-01-02"},
                           ["Core | Lead"], ["SEG1"], 0, None)
        self.assertNotIn("campaign-send-jobs", [c[1] for c in calls])
        camp = next(c[2] for c in calls if c[1] == "campaigns")["data"]["attributes"]
        tr = camp["tracking_options"]
        self.assertTrue(tr["add_tracking_params"])
        kl_tags = {p["name"]: p["value"] for p in tr["custom_tracking_params"]}
        self.assertTrue(all(p["type"] == "static" for p in tr["custom_tracking_params"]))
        tpl = next(c[2] for c in calls if c[1] == "templates")["data"]["attributes"]["html"]
        button = next(h for h in links(tpl) if "go.example.test" in h)
        for k, v in kl_tags.items():                    # Klaviyo and the link never disagree
            self.assertEqual(q(button)[k], v, k)
        self.assertNotIn("utm_content", kl_tags)        # per link, so it stays on the link


class Term(unittest.TestCase):
    """utm_term fits Klaviyo's 100-character limit (a send to all five Core segments was
    112 and Klaviyo refused the draft, 2026-10-15)."""
    EVERYONE = ["Core | Lead", "Core | One-Time Customer", "Core | Returning Customer",
                "Core | Loyal Customer", "Core | VIP Customer"]

    def test_a_short_term_is_unchanged(self):
        self.assertEqual(S.EL.term_for(["Core | Lead", "Core | VIP Customer"]),
                         "Core | Lead + Core | VIP Customer")
        self.assertIsNone(S.EL.term_for([]))

    def test_every_segment_of_one_group_says_the_group_once(self):
        term = S.EL.term_for(self.EVERYONE)
        self.assertLessEqual(len(term), S.EL.TERM_MAX)
        self.assertEqual(term, "Core | Lead + One-Time Customer + Returning Customer"
                               " + Loyal Customer + VIP Customer")

    def test_anything_still_too_long_is_cut_to_the_limit(self):
        term = S.EL.term_for(["Group %d | Segment with a long name" % i for i in range(6)])
        self.assertLessEqual(len(term), S.EL.TERM_MAX)
        self.assertGreater(len(term), S.EL.TERM_MAX - 5)   # cut near the limit, not emptied
        self.assertTrue(term.endswith("…"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
