"""The final check holds a subject another email of the brand already uses for an overlapping audience within
14 days (email_lead, 2026-11-10: brand_a-nov-15 and brand_a-nov-58 both went out as 'The barbershop debate nobody wins',
same audience, two days apart, because the design step writes its own subject after the copy stage's ledger
check). No network: cards are written to a temporary brand folder.

    python3 design/test_repeated_subject.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check as C  # noqa: E402

SUBJECT = "The barbershop debate nobody wins"


def card(root, label, date, subject, segments=("Core | One-Time Customer",), status="draft"):
    d = Path(root) / label
    (d / "klaviyo").mkdir(parents=True)
    c = {"label": label, "date": date, "status": status, "segments": list(segments),
         "subjects": [{"subject": subject, "preview": "p"}]}
    (d / "klaviyo" / "card.json").write_text(json.dumps(c))
    return d, c


class RepeatedSubject(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_same_subject_same_audience_two_days_apart_is_held(self):
        card(self.root, "brand-nov-15", "2026-11-15", SUBJECT)
        d, c = card(self.root, "brand-nov-58", "2026-11-17", SUBJECT)
        self.assertEqual(C.repeated_subject(d, c), ["brand-nov-15"])

    def test_case_and_punctuation_do_not_hide_a_repeat(self):
        card(self.root, "brand-nov-15", "2026-11-15", "the barbershop debate, nobody wins!")
        d, c = card(self.root, "brand-nov-58", "2026-11-17", SUBJECT)
        self.assertEqual(C.repeated_subject(d, c), ["brand-nov-15"])

    def test_a_different_subject_passes(self):
        card(self.root, "brand-nov-15", "2026-11-15", SUBJECT)
        d, c = card(self.root, "brand-nov-58", "2026-11-17", "Against the grain is the closest shave. It isn't the cleanest.")
        self.assertEqual(C.repeated_subject(d, c), [])

    def test_another_audience_passes(self):
        card(self.root, "brand-nov-15", "2026-11-15", SUBJECT, segments=("Core | Lead",))
        d, c = card(self.root, "brand-nov-58", "2026-11-17", SUBJECT)
        self.assertEqual(C.repeated_subject(d, c), [])

    def test_outside_the_window_passes(self):
        card(self.root, "brand-oct-20", "2026-10-20", SUBJECT)
        d, c = card(self.root, "brand-nov-58", "2026-11-17", SUBJECT)
        self.assertEqual(C.repeated_subject(d, c), [])

    def test_a_deprecated_email_does_not_count(self):
        card(self.root, "brand-nov-15", "2026-11-15", SUBJECT, status="deprecated")
        d, c = card(self.root, "brand-nov-58", "2026-11-17", SUBJECT)
        self.assertEqual(C.repeated_subject(d, c), [])

    def test_an_email_never_repeats_itself(self):
        d, c = card(self.root, "brand-nov-58", "2026-11-17", SUBJECT)
        self.assertEqual(C.repeated_subject(d, c), [])


if __name__ == "__main__":
    unittest.main()
