#!/usr/bin/env python3
"""The campaign a piece is for (email_lead, 2026-11-03: fold a campaign's pieces together on the content board, "black friday
y están los 25 de brand_b y luego los 18 de brand_a"). A hand-off's `moment` is the brand's dated moment its BRIEF.md
names most often, at least MOMENT_MIN times (statics.py); an email's is its card's `theme` (view.py). Reads the real
brands/ moment lists, read only; everything else in temp folders.

    /usr/bin/python3 components/creative-queue/test_campaign_moment.py
"""
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import statics as S  # noqa: E402
import view as V  # noqa: E402


class MomentOf(unittest.TestCase):
    KEYS = ["thanksgiving", "black-friday", "cyber-monday", "christmas"]

    def test_the_most_named_moment_wins_in_any_spelling(self):
        text = ("# BRIEF · brand_a · Black Friday mail day\n| **Deadline** | black-friday, the week of Thanksgiving |\n"
                "A black friday haul. BLACK FRIDAY offer.")
        self.assertEqual(S.moment_of(text, self.KEYS), "black-friday")

    def test_below_the_floor_is_no_campaign(self):
        self.assertEqual(S.MOMENT_MIN, 3)
        self.assertIsNone(S.moment_of("Black Friday is coming. Black Friday.", self.KEYS), "named twice is a passing mention")
        self.assertIsNone(S.moment_of("Braille neck car selfie", self.KEYS))
        self.assertIsNone(S.moment_of("", self.KEYS))

    def test_whole_words_only(self):
        self.assertIsNone(S.moment_of("christmassy christmastime christmasses", ["christmas"]))

    def test_a_brands_dated_moments_only(self):
        keys = S.moments_of("brand_b")
        self.assertIn("black-friday", keys)
        self.assertNotIn("results-stories", keys, "a `live` moment is not a campaign")
        self.assertEqual(S.moments_of("no-such-brand"), [])


class ListCarriesIt(unittest.TestCase):
    def test_quick_reads_the_campaign_from_the_brief_on_disk(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            key = "brand_a_flex-face-brush_brief-0301"
            (out / "brand_a" / key).mkdir(parents=True)
            (out / "brand_a" / key / "BRIEF.md").write_text("Black Friday " * 11)
            (out / "brand_a" / "brand_a_flex-face-brush_brief-0232").mkdir(parents=True)
            (out / "brand_a" / "brand_a_flex-face-brush_brief-0232" / "BRIEF.md").write_text("Braille neck car selfie")
            rows = [{"brand": "brand_a", "key": key}, {"brand": "brand_a", "key": "brand_a_flex-face-brush_brief-0232"},
                    {"brand": "brand_a", "key": "brand_a_flex-face-brush_brief-0999"}]   # no brief on disk
            (out / S.LAST).write_text(json.dumps({"read_at": "x", "rows": rows, "incomplete": [], "error": None, "_at": 1e12}))
            got = S.quick(out, clock=lambda: 1e12, spawn=lambda o, r: None)["rows"]
        self.assertEqual([r["moment"] for r in got], ["black-friday", None, None])


class EmailTheme(unittest.TestCase):
    def test_an_email_carries_its_cards_theme(self):
        with tempfile.TemporaryDirectory() as d:
            for label, card in (("brand_b-nov-34", {"date": "2026-11-27", "theme": "black-friday"}),
                                ("brand_b-nov-08", {"date": "2026-11-09"}),
                                ("brand_b-nov-09", {"date": "2026-11-10", "theme": "  "})):
                k = Path(d) / "brand_b" / label / "klaviyo"
                k.mkdir(parents=True)
                (k / "card.json").write_text(json.dumps(card))
            got = {r["email_run"]: r["moment"] for r in V.email_rows(d, date(2026, 11, 3))}
        self.assertEqual(got, {"brand_b-nov-34": "black-friday", "brand_b-nov-08": None, "brand_b-nov-09": None})


class CalendarHandedOver(unittest.TestCase):
    """view.py hands the board owner's promo calendar as it wrote it into the shadow root (email_lead, 2026-11-04)."""

    def test_the_calendars_pieces_read_only_and_trimmed(self):
        obs = {"promo-calendar": {"as_of": "2026-11-04T05:30:31Z", "source": "promo-calendar", "entries": {
            "b_piece": {"brand": "brand_a", "type": "video-ad", "role": "organic", "lane": "promo", "moment": "christmas",
                        "due": "2026-11-24", "title": "Christmas · Organic 1", "observed_stage": "idea",
                        "priority": "normal", "offer": "brands/brand_a/products/offer-bank.md", "rank": 3},
            "a_piece": {"brand": "brand_b", "type": "email", "role": "sms", "due": "2026-11-13"},
            "zz-test": {"brand": "brand_b", "type": "image-ad"}}}}
        got = V.calendar(obs)
        self.assertEqual(got["as_of"], "2026-11-04T05:30:31Z")
        self.assertEqual([e["id"] for e in got["entries"]], ["a_piece", "b_piece"], "sorted by id, test pieces left out")
        self.assertEqual(set(got["entries"][1]), set(V.CAL_FIELDS) | {"id"}, "only the fields the board reads")
        self.assertEqual(got["entries"][1]["moment"], "christmas")
        self.assertIsNone(V.calendar({}), "no calendar written: null, never an empty column made up")

    def test_build_carries_it_from_the_shadow_root(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "observations").mkdir()
            (Path(d) / "observations" / "promo-calendar.json").write_text(json.dumps(
                {"as_of": "2026-11-04T05:30:31Z", "entries": {"x": {"brand": "brand_a", "type": "landing-page"}}}))
            got = V.build({"built": "2026-10-30T17:49:00Z", "entries": []}, d, "2026-11-04T12:00:00Z")
        self.assertEqual(got["calendar"]["entries"][0]["id"], "x")
        self.assertEqual(got["rows"], [], "the calendar's pieces are never rows")


class SentBackNote(unittest.TestCase):
    """view.py hands the board owner's own words when he sent a piece back (email_lead, 2026-11-05)."""

    def test_the_latest_disapproval_per_brief(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "learnings.jsonl"
            f.write_text("\n".join([
                json.dumps({"at": "2026-10-04T10:00:00", "by": "owner", "brief_key": "k1", "note": "old",
                            "reasons": [{"id": "other", "label": "Something else"}]}),
                json.dumps({"at": "2026-10-25T12:35:40", "by": "owner", "brief_key": "k1", "note": "not unique",
                            "reasons": [{"id": "other", "label": "Something else"}]}),
                "not json",
                json.dumps({"at": "2026-10-01T00:00:00", "by": "owner", "brief_key": "k2", "note": "bad"})]))
            got = V.learnings(f)
        self.assertEqual(got["k1"], {"by": "owner", "at": "2026-10-25T12:35:40", "note": "not unique", "reasons": ["Something else"]})
        self.assertEqual(got["k2"]["reasons"], [])
        self.assertEqual(V.learnings(Path("/no/such/file.jsonl")), {}, "no Drive: nothing, never an error")

    def test_only_a_sent_back_row_carries_it(self):
        idx = {"built": "2026-10-30T17:49:00Z", "entries": [
            {"id": "brand_a_flex_brief-0251", "type": "image-ad", "brand": "brand_a", "stage": "making", "flag": "sent-back"},
            {"id": "brand_a_flex_brief-0252", "type": "image-ad", "brand": "brand_a", "stage": "making"}]}
        note = {"by": "owner", "at": "2026-10-25T12:35:40", "note": "not unique", "reasons": []}
        with tempfile.TemporaryDirectory() as d:
            got = V.build(idx, d, "2026-11-05T12:00:00Z", None,
                          {"brand_a_flex_brief-0251": note, "brand_a_flex_brief-0252": note})
        by = {r["id"]: r for r in got["rows"]}
        self.assertEqual(by["brand_a_flex_brief-0251"]["sent_back"], note)
        self.assertNotIn("sent_back", by["brand_a_flex_brief-0252"], "not sent back: no note, even if one is on file")


class EmailsToWrite(unittest.TestCase):
    """view.py hands the Calendar view the calendar's emails not written yet (email_lead, 2026-11-05)."""

    def test_only_unwritten_email_slots_from_today(self):
        with tempfile.TemporaryDirectory() as d:
            cal, em = Path(d) / "cal", Path(d) / "em"
            m = cal / "brand_b" / "2026-11"; m.mkdir(parents=True)
            m.joinpath("slots.json").write_text(json.dumps([
                {"id": "nov-01", "date": "2026-11-01", "type": "routine"},                 # before today
                {"id": "nov-08", "date": "2026-11-09", "type": "stack"},                   # written under its own name
                {"id": "nov-09", "date": "2026-11-10", "type": "stack"},                   # written as nov-08a, recorded
                {"id": "nov-10", "date": "2026-11-11", "type": "proof", "segment": "Core | Lead"},
                {"id": "nov-11", "date": "2026-11-12", "type": "promo", "channel": "sms"},  # a text: not designed
                {"id": "nov-12", "date": "2026-11-13", "type": "promo"}]))                  # written, then taken off
            m.joinpath("review.json").write_text(json.dumps({"slots": {"nov-10": {"status": "approved"}}}))
            def run(name, slot=None, off=False):
                r = em / "brand_b" / name; (r / "deliverable").mkdir(parents=True)
                (r / "deliverable" / "email.json").write_text("{}")
                if slot:
                    (r / "run.json").write_text(json.dumps({"calendar_handoff": {"slot_id": slot}}))
                if off:
                    (r / "off-page.json").write_text("{}")
            run("brand_b-nov-08"); run("brand_b-nov-08a", slot="nov-09"); run("brand_b-nov-12", off=True)
            got = V.towrite(cal, em, date(2026, 11, 5))
        self.assertEqual([r["slot"] for r in got], ["nov-10", "nov-12"])
        self.assertEqual(got[0], {"brand": "brand_b", "slot": "nov-10", "month": "2026-11", "send": "2026-11-11",
                                  "type": "proof", "segment": "Core | Lead", "approved": True})
        self.assertFalse(got[1]["approved"], "the month has a review and this slot is not approved in it")


if __name__ == "__main__":
    unittest.main()
