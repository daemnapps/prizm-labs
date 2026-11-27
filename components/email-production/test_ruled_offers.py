"""The writer and the calendar agree on what an offer is (2026-11-03).

A priced `### key — Name` section in the bank's human-ruled half (a funnel offer, a dated promotion) is an
offer the calendar plans; `offers.parse` reads it through the calendar's own reader, so a send the calendar
assigns it to is not refused at the door. A note section stays a note. Stdlib only, no model, no key."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import offers  # noqa: E402

BANK = """# Offer bank

## tube — The Tube
_lane: a_  ·  _hero: paid_
- Price: **$29.00**
- Link: https://example.test/tube

---

# Ruled by a human — carried forward, not generated

### holiday-sale — The holiday offer
| The 3-pack | **$57** — $19 a tube |

### popup — Standing sign-up pop-up offer
| Opt-in | **Free pouch with the tube** (at $0.00) — worth $19 |

### guarantee — The guarantee
60 days.

### rules — Standing rules
- Never invent an offer.
"""


class RuledOffers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        ws = Path(self.tmp.name)
        (ws / "brands" / "zz" / "products").mkdir(parents=True)
        (ws / "brands" / "zz" / "products" / "offer-bank.md").write_text(BANK)
        self.p = mock.patch.object(offers, "WORKSPACE", ws)
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def test_a_priced_ruled_section_is_an_offer_and_a_note_is_not(self):
        rows = {r["key"]: r for r in offers.parse("zz")}
        self.assertIn("tube", rows)
        self.assertIn("holiday-sale", rows)
        self.assertTrue(rows["holiday-sale"]["ruled"])
        self.assertEqual(rows["holiday-sale"]["states_prices"], ["19", "57"])
        self.assertNotIn("guarantee", rows)
        self.assertNotIn("popup", rows)                 # the sign-up opt-in is a note, not an offer
        self.assertNotIn("rules", rows)

    def test_the_writer_no_longer_refuses_what_the_calendar_assigns(self):
        self.assertIsNone(offers.refuse("zz", "holiday-sale", "a", "2026-11-27"))
        self.assertIn("not in the offer bank", offers.refuse("zz", "guarantee", "a", "2026-11-27"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
