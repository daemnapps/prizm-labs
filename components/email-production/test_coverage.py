"""coverage.py: a send ahead with nothing written is listed (email_lead, 2026-11-10), matched by the slot a run records.

    /usr/bin/python3 test_coverage.py
"""
import unittest

import coverage as C

SLOTS = [
    {"id": "nov-09", "date": "2026-11-10", "channel": "email"},
    {"id": "nov-11", "date": "2026-11-12", "channel": "email"},
    {"id": "nov-51", "date": "2026-11-10", "channel": "sms", "follows": "nov-09"},
    {"id": "nov-52", "date": "2026-11-17", "channel": "sms", "follows": "nov-11"},
    {"id": "nov-60", "date": "2026-12-20", "channel": "email"},
    {"id": "nov-01", "date": "2026-11-01", "channel": "email"},
]


class Coverage(unittest.TestCase):
    def test_lists_only_sends_ahead_with_nothing_written(self):
        written = {"nov-09"}                      # nov-09 written (its folder may carry another name)
        got = C.gaps(SLOTS, "2026-11-10", 14, lambda s: s in written,
                     lambda slot: None if slot["id"] == "nov-51" else "no text written for this send")
        self.assertEqual([(g["id"], g["why"]) for g in got], [
            ("nov-11", "no email written for this send"),
            ("nov-52", "no text written for this send"),
            ("nov-52", "the email it goes with (nov-11) has no written version")])

    def test_a_text_with_no_email_named_is_listed(self):
        got = C.gaps([{"id": "x", "date": "2026-11-11", "channel": "sms"}], "2026-11-10", 14,
                     lambda s: True, lambda slot: None)
        self.assertEqual([g["why"] for g in got], ["it names no email to go with"])

    def test_nothing_missing_says_so(self):
        self.assertEqual(C.gaps(SLOTS[:1], "2026-11-10", 14, lambda s: True, lambda slot: None), [])
        self.assertIn("has something written", C.lines("brand_b", [], "2026-11-10", 14)[0])


TEXTS = [
    {"label": "b-nov-48-sms", "slot": "nov-48", "date": "2026-11-27", "state": "ready for review", "card_state": "scheduled"},
    {"label": "b-nov-49-sms", "slot": "nov-49", "date": "2026-11-28", "state": "ready for review", "card_state": None},
    {"label": "b-nov-50-sms", "slot": "nov-50", "date": "2026-11-30", "state": "held: rewrite", "card_state": "waiting"},
    {"label": "b-nov-45-sms", "slot": "nov-45", "date": "2026-11-26", "state": "superseded 2026-11-04: renumbered",
     "card_state": None},
    {"label": "b-nov-54-sms", "slot": "nov-54", "date": "2026-11-29", "state": "ready for review", "card_state": None},
    {"label": "b-nov-55-sms", "slot": "nov-55", "date": "2026-11-25", "state": "ready for review",
     "card_state": "approved — place in Postscript"},
    {"label": "b-nov-51-sms", "slot": "nov-51", "date": "2026-11-10", "state": "ready for review", "card_state": None},
]


class TextsNotScheduled(unittest.TestCase):
    """A written text with no go is listed (email_lead, 2026-11-24: Nov 27-30 texts caught by hand three days out)."""

    def test_lists_written_texts_with_no_schedule_in_date_order(self):
        got = C.unscheduled(TEXTS, "2026-11-24", 14, cut={"nov-54"})
        self.assertEqual([(t["date"], t["label"], t["why"]) for t in got["open"]], [
            ("2026-11-28", "b-nov-49-sms", "no card made"),
            ("2026-11-30", "b-nov-50-sms", "card is waiting; draft held: rewrite")])

    def test_scheduled_superseded_cut_and_out_of_window_are_skipped(self):
        labels = [t["label"] for t in C.unscheduled(TEXTS, "2026-11-24", 14, cut={"nov-54"})["open"]]
        for skipped in ("b-nov-48-sms", "b-nov-45-sms", "b-nov-54-sms", "b-nov-51-sms"):
            self.assertNotIn(skipped, labels)
        self.assertIn("b-nov-54-sms", [t["label"] for t in C.unscheduled(TEXTS, "2026-11-24", 14)["open"]])

    def test_placed_by_hand_is_apart_and_said_unconfirmed(self):
        got = C.unscheduled(TEXTS, "2026-11-24", 14)
        self.assertEqual(got["unconfirmed"], [{"label": "b-nov-55-sms", "date": "2026-11-25"}])
        out = C.text_lines("b", got, "2026-11-24", 14)
        self.assertEqual(out[0].split(" (")[0], "Texts written, not scheduled")
        self.assertIn("  placed by a person, not confirmed:", out)

    def test_nothing_unscheduled_says_none(self):
        got = C.unscheduled(TEXTS[:1], "2026-11-24", 14)
        self.assertEqual(got, {"open": [], "unconfirmed": []})
        self.assertEqual(C.text_lines("b", got, "2026-11-24", 14)[1], "  none")


if __name__ == "__main__":
    unittest.main()
