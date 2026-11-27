#!/usr/bin/env python3
"""Every Klaviyo draft carries its event's tag (email_lead, 2026-11-26: emails that belong to an event get a tag, "solo la
etiqueta"): create_draft() tags the campaign "<Occasion> <year>" from the calendar slot, reuses the tag when it exists,
makes it the first time, skips a send with no occasion or a written-out one, and never fails the draft over a tag.
No network: Klaviyo is a stand-in.

    /usr/bin/python3 components/email-production/test_event_tag.py
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import simple_email as S  # noqa: E402

LK = {"from": {"email": "hello@zz.test", "label": "ZZ Beauty"}}


def draft(slot, tags=(), refuse=None):
    """Run create_draft against a stand-in Klaviyo holding `tags` [(id, name)]. -> (record, calls)."""
    calls = []

    def kl(method, path, key, payload=None, form=None):
        calls.append((method, path, payload))
        if refuse and path.startswith(refuse):
            sys.exit("Klaviyo refused %s: 400" % path)
        if path == "campaigns":
            return {"data": {"id": "c1", "relationships": {"campaign-messages": {"data": [{"id": "m1"}]}}}}
        if method == "GET" and path.startswith("tags/"):
            return {"data": [{"id": i, "attributes": {"name": n}} for i, n in tags], "links": {"next": None}}
        if method == "POST" and path == "tags/":
            return {"data": {"id": "new-tag"}}
        return {"data": {"id": "t1"}}
    with mock.patch.object(S, "kl", kl):
        rec = S.create_draft("key", "<html></html>", {"subjects": [{"subject": "S", "preview": "P"}]}, LK, "zz",
                             "zz-dec-01", slot, ["Core"], ["seg1"], 0, None)
    return rec, calls


def linked(calls):
    return [(p, pl) for m, p, pl in calls if m == "POST" and p.endswith("/relationships/campaigns/")]


class TestEventTag(unittest.TestCase):
    def test_the_name(self):
        self.assertEqual(S.event_tag({"occasion": "christmas", "date": "2026-12-08"}), "Christmas 2026")
        self.assertEqual(S.event_tag({"occasion": "gifting-season", "date": "2026-12-03"}), "Gifting Season 2026")
        self.assertEqual(S.event_tag({"occasion": "black-friday", "date": "2026-11-27"}), "Black Friday 2026",
                         "the same name Black Friday was tagged with by hand")

    def test_no_tag_without_a_key(self):
        self.assertIsNone(S.event_tag({"date": "2026-12-08"}))
        self.assertIsNone(S.event_tag({"occasion": "a recorded problem — FLEX is used once a day", "date": "2026-12-08"}))
        self.assertIsNone(S.event_tag({"occasion": "christmas"}), "no send date, no year")

    def test_an_existing_tag_is_reused(self):
        rec, calls = draft({"occasion": "christmas", "date": "2026-12-08"}, tags=[("tg9", "Christmas 2026")])
        self.assertEqual(rec["tag"], "Christmas 2026")
        self.assertFalse([1 for m, p, _ in calls if m == "POST" and p == "tags/"], "no second tag of the same name")
        self.assertEqual(linked(calls), [("tags/tg9/relationships/campaigns/", {"data": [{"type": "campaign", "id": "c1"}]})])

    def test_a_new_tag_is_made_once(self):
        rec, calls = draft({"occasion": "christmas", "date": "2026-12-08"})
        made = [pl for m, p, pl in calls if m == "POST" and p == "tags/"]
        self.assertEqual(made, [{"data": {"type": "tag", "attributes": {"name": "Christmas 2026"}}}])
        self.assertEqual(linked(calls)[0][0], "tags/new-tag/relationships/campaigns/")

    def test_no_occasion_no_tag_call(self):
        rec, calls = draft({"date": "2026-12-08"})
        self.assertIsNone(rec["tag"])
        self.assertFalse([1 for _, p, _ in calls if p.startswith("tags/")])

    def test_a_refused_tag_never_fails_the_draft(self):
        rec, _ = draft({"occasion": "christmas", "date": "2026-12-08"}, refuse="tags/")
        self.assertEqual(rec["campaign_id"], "c1")
        self.assertIsNone(rec["tag"])
        self.assertIn("Christmas 2026", rec["tag_error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
