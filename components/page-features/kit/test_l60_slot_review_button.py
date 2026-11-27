#!/usr/bin/env python3
"""L60 (slot review): the emails page's verdict on a planned send (60) through POST /act. The kit turns it into exactly
`review.py mark <brand> <YYYY-MM> <slot> <status> --by <its own person> [--note=…]`, takes the status only from the
table's own list and refuses a bad item or note before anything runs. Nothing runs: build() returns the argv.

    /usr/bin/python3 components/page-features/kit/test_l60_slot_review_button.py
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import serve  # noqa: E402

REAL = serve.ROOT
ITEM = "brand_a__2026-12__dec-04"


class SlotReview(unittest.TestCase):
    def act(self, person="owner"):
        return serve.Act("emails", REAL, person)

    def body(self, **kw):
        return dict({"family": "emails", "n": 60, "item": ITEM, "part": "-", "field": "approved"}, **kw)

    def test_the_real_table(self):
        self.assertEqual(serve.direct_table("emails", REAL)["60"],
                         {"kind": "quick", "run": "slots", "verb": "mark",
                          "fields": ["approved", "needs-work", "cut", "pending"]})

    def test_one_mark_command_as_the_kits_person(self):
        argv, line = self.act().build(self.body(value="Lead with the price", by="email_lead"))
        self.assertEqual(argv[1:], [os.path.join(REAL, "components/marketing-calendar/machine/review.py"), "mark",
                                    "brand_a", "2026-12", "dec-04", "approved", "--by", "owner",
                                    "--note=Lead with the price"])
        self.assertIsNone(line)
        argv, _ = self.act().build(self.body(field="cut"))
        self.assertEqual(argv[-3:], ["cut", "--by", "owner"], "no note: none passed, the old note stays")

    def test_refused_before_anything_runs(self):
        for kw, code in (({"field": "delete"}, 400), ({"field": None}, 400), ({"item": "brand_a__dec-04"}, 400),
                         ({"item": "brand_a__2026-12__../x"}, 400), ({"item": "brand_a__2026-12__dec-04"}, 400),
                         ({"value": "two\nlines"}, 400), ({"value": "-x"}, 400), ({"value": "x" * 201}, 400)):
            with self.assertRaises(serve.Refused) as e:
                self.act().build(self.body(**kw))
            self.assertEqual(e.exception.code, code, kw)
        with self.assertRaises(serve.Refused) as e:
            serve.Act("emails", REAL, None, "no person").build(self.body())
        self.assertEqual(e.exception.code, 403)

    def test_edit_is_one_review_edit_command(self):
        angle = "She has one tube and a question nobody answered — " * 5
        argv, line = self.act().build(dict(self.body(), n=61, field="angle", value=angle.strip()))
        self.assertEqual(argv[1:], [os.path.join(REAL, "components/marketing-calendar/machine/review.py"), "edit",
                                    "brand_a", "2026-12", "dec-04", "angle", "--value=" + angle.strip(), "--by", "owner"])
        self.assertIsNone(line)
        argv, _ = self.act().build(dict(self.body(), n=61, field="offer", value=""))
        self.assertEqual(argv[-3:], ["--value=", "--by", "owner"], "an empty value clears the rewrite")
        for kw in ({"field": "why"}, {"field": "angle", "value": "x" * 601}, {"field": "angle", "value": "a\nb"},
                   {"field": "angle", "value": "-rm"}):
            with self.assertRaises(serve.Refused) as e:
                self.act().build(dict(self.body(), n=61, **kw))
            self.assertEqual(e.exception.code, 400, kw)

    def test_a_table_entry_naming_another_verb_or_status_is_not_direct(self):
        real = serve.direct_table
        try:
            for entry in ({"kind": "quick", "run": "slots", "verb": "set_edit", "fields": ["approved"]},
                          {"kind": "quick", "run": "slots", "verb": "edit", "fields": ["angle", "why"]},
                          {"kind": "quick", "run": "slots", "verb": "mark", "fields": ["approved", "wipe"]}):
                serve.direct_table = lambda fam, root=REAL, e=entry: {"60": e}
                with self.assertRaises(serve.Refused) as e:
                    self.act().build(self.body(field=entry["fields"][0]))
                self.assertEqual(e.exception.code, 403, entry)
        finally:
            serve.direct_table = real


if __name__ == "__main__":
    unittest.main()
