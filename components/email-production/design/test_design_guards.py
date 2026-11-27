"""The design line's small guards. A picture's alt text is what the reader gets with images off: the section's words, never the review page's source
label ("Made from a real reference"), which the clean render hides (email_lead, 2026-10-27: it reached 21 emails).

    /usr/bin/python3 test_design_guards.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import engine  # noqa: E402


class AltText(unittest.TestCase):
    def test_the_source_label_never_reaches_the_alt(self):
        for src, label in engine.SOURCE.items():
            sec = ('<section><figure class="m-pic r"><img src="x.jpg" alt="A woman in a sunlit shower">'
                   '<span class="pk pk-%s">%s</span></figure><p>Twice a week.</p></section>' % (src, label))
            alt = build.alt_of(sec)
            self.assertNotIn(label, alt)
            self.assertEqual(alt, "A woman in a sunlit shower Twice a week.")

    def test_the_words_and_picture_alts_stay(self):
        sec = '<h2>The routine</h2><img src="a.jpg" alt="The scrub tube"><p>Step 1 &middot; the clearing</p>'
        self.assertEqual(build.alt_of(sec), "The routine The scrub tube Step 1 · the clearing")


class BoxWithoutHero(unittest.TestCase):
    def test_a_box_of_tiles_alone_builds(self):
        """brand_a-nov-07--glow-up's layout: a box with two step tiles and no big picture (KeyError: 'hero', 2026-10-23)."""
        pic = {"photo": "x.jpg", "alt": "A bottle", "source": "photo"}
        orig = engine.picture
        engine.picture = lambda lk, p, th: '<img src="%s" alt="%s">' % (p["photo"], p["alt"])
        try:
            h = engine.s_box({}, {"s": "box", "title": "Two steps, one price.",
                                   "tiles": [{"picture": pic, "name": "STEP 01", "line": "Deep clean"},
                                             {"picture": pic, "name": "STEP 02", "line": "Stay moisturized"}]}, None)
        finally:
            engine.picture = orig
        self.assertIn("Two steps, one price.", h)
        self.assertEqual(h.count('class="m-bx"'), 2)


class MomentOfASend(unittest.TestCase):
    def test_only_a_moment_key_asks_for_research(self):
        """The calendar's prose occasions are not moments (23 November emails held for research files, 2026-10-27)."""
        import line
        for occ, want in (("nba-regular-season", "nba-regular-season"), ("black-friday: the weekend", "black-friday"),
                          ("dancing-with-the-stars-finale", "dancing-with-the-stars-finale"),
                          ("recorded problem: one product is a step", None), ("HELD OPEN — live", None),
                          ("a recorded problem — the six-week clock", None), ("none", None), ("", None)):
            self.assertEqual(line.moment_of({"occasion": occ}), want, occ)


class EmailsAnUpdateRebuilt(unittest.TestCase):
    def test_only_klaviyo_files_of_held_runs_count(self):
        """The hooks refresh the pictures of every email an update rebuilt (email_lead, 2026-10-27); a design-only change
        or a run this Mac does not hold is left alone."""
        import tempfile
        import layout_file as LF
        with tempfile.TemporaryDirectory() as repo:
            (Path(repo) / "runs/email-production/brand_b/brand_b-nov-01").mkdir(parents=True)
            names = ["runs/email-production/brand_b/brand_b-nov-01/klaviyo/card.json",
                     "runs/email-production/brand_b/brand_b-nov-01/klaviyo/email.html",
                     "runs/email-production/brand_b/brand_b-nov-01/design/email.json",
                     "runs/email-production/brand_a/not-here/klaviyo/card.json", "brands/brand_b/x.json"]
            self.assertEqual([d.name for d in LF.changed_runs(names, repo)], ["brand_b-nov-01"])


class APictureThatShowsWhatIsNotInTheBox(unittest.TestCase):
    def test_the_problem_names_the_picture_and_why(self):
        """email_lead, 2026-10-28: a wrong picture is the one check editor keeps, and it says which picture and why."""
        import build
        spec = {"brand": "x", "sections": [{"s": "photo_card", "picture": {"photo": "drive:a.jpg", "alt": "FLEX in its case on the shelf"}}]}
        lk = {"check": {"prices": {"$1": "x"}, "not_in_box": [{"word": "case", "why": "the charging case is sold separately"}]}}
        out = build.product_check(spec, lk, "FLEX in its case on the shelf")
        bad = [x["detail"] for x in out if x["result"] == "PROBLEM"]
        self.assertEqual(len(bad), 1, out)
        self.assertIn("photo card picture shows the case", bad[0])
        self.assertIn("sold separately", bad[0])
        words_only = {"brand": "x", "sections": [{"s": "letter", "text": "Keep it in the case."}]}
        out = build.product_check(words_only, lk, "Keep it in the case.")
        self.assertEqual([x["detail"] for x in out if x["result"] == "PROBLEM"], ['mentions "case": the charging case is sold separately'])

    def test_the_brand_s_own_offer_line_may_name_it_and_nothing_else_may(self):
        """2026-11-07: owner's holiday offer gives the case away free; only its word-for-word line is cleared."""
        import build
        lk = {"check": {"prices": {"$1": "x"}, "not_in_box": [{"word": "case", "why": "sold separately",
                                                               "except": ["Free FLEX™ Charging Case"]}]}}
        ok = {"brand": "x", "sections": [{"s": "letter", "text": "The King Set + Free FLEX™ Charging Case."}]}
        out = build.product_check(ok, lk, "The King Set + free flex™ charging case.")
        self.assertEqual([x for x in out if x["result"] == "PROBLEM"], [])
        both = "The King Set + Free FLEX™ Charging Case. Keep FLEX in its case."
        out = build.product_check({"brand": "x", "sections": [{"s": "letter", "text": both}]}, lk, both)
        self.assertEqual([x["detail"] for x in out if x["result"] == "PROBLEM"], ['mentions "case": sold separately'])
        pic = {"brand": "x", "sections": [{"s": "photo_card", "picture": {"photo": "drive:a.jpg", "alt": "FLEX in its case"}}]}
        out = build.product_check(pic, lk, "")
        self.assertEqual(len([x for x in out if x["result"] == "PROBLEM"]), 1)

    def test_a_picture_of_the_free_gift_passes_only_in_its_window_and_only_when_the_email_states_it(self):
        """email_lead, 2026-11-19: nov-43, dec-01, dec-03, dec-19 show the case the King Set gives free (owner, 2026-11-07,
        Nov 20 - Dec 25) and were held as "sold separately". Inside the window, with the gift line in the email, the
        picture passes; outside it, or with no gift line, it is still held."""
        import build
        lk = {"check": {"prices": {"$1": "x"}, "not_in_box": [{"word": "case", "why": "sold separately",
              "except": ["Free FLEX™ Charging Case"],
              "except_pictures": {"from": "2026-11-20", "until": "2026-12-25", "why": "owner, 2026-11-07"}}]}}
        def held(date, words):
            spec = {"brand": "x", "date": date, "sections": [
                {"s": "box", "hero": {"picture": {"photo": "drive:a.jpg", "alt": "A FLEX in its charging case on gold"}}},
                {"s": "letter", "text": words}]}
            return [x["detail"] for x in build.product_check(spec, lk, words) if x["result"] == "PROBLEM"]
        gift = "The King Set + Free FLEX™ Charging Case, $1"
        self.assertEqual(held("2026-11-30", gift), [])
        self.assertEqual(held("2026-12-25", gift), [])
        self.assertEqual(len(held("2026-12-26", gift)), 1)           # the gift is over: back to sold separately
        self.assertEqual(len(held("2026-11-19", gift)), 1)
        self.assertEqual(len(held("2026-11-30", "FLEX, $1")), 1)      # no gift in this email: the case is not in the box
        self.assertEqual(held("2026-11-30", gift + " Plus the free Charging Case."), [])   # its words about the gift too
        self.assertEqual(len(held("2026-12-26", "Keep FLEX in its case. " + gift)), 1)   # outside the window, words still hold
        lk["check"]["not_in_box"][0].pop("except_pictures")
        self.assertEqual(len(held("2026-11-30", gift)), 1)            # a brand with no window keeps the old rule


class EveryProductFolderGetsPhotosOffered(unittest.TestCase):
    def test_the_cap_takes_from_every_folder_in_turn(self):
        """email_lead, 2026-11-07: the travel pouch's photos sat past the alphabet's cut and were never offered."""
        import line
        refs = ["drive:brands/x/products/a-scrub/packshot/%d.jpg" % i for i in range(300)] + \
               ["drive:brands/x/products/travel-pouch/packshot/%d.jpg" % i for i in range(3)]
        got = line.fair_share(refs, 10)
        self.assertEqual(len(got), 10)
        self.assertEqual(sum("travel-pouch" in r for r in got), 3)
        self.assertEqual(got[0], refs[0])
        self.assertEqual(line.fair_share(refs[:4], 10), refs[:4])

class ABuyingSectionWithoutItsButton(unittest.TestCase):
    def test_the_live_rows_and_the_pictures_get_the_same_defaults(self):
        """brand_b-nov-29 (2026-11-08): the pictures drew a product card with no button label, the live Klaviyo row
        crashed on KeyError 'cta'. Both now read engine.buying_defaults."""
        spec = {"sections": [{"s": "product", "name": "Body Scrub", "line": "x"}, {"s": "cta", "label": "Shop the bundle"},
                             {"s": "letter", "text": "hi"}]}
        got = engine.buying_defaults(spec)
        self.assertEqual(got[0]["cta"], "Shop the bundle")
        self.assertEqual(got[0]["price"], "")
        self.assertNotIn("cta", got[2])
        self.assertNotIn("cta", spec["sections"][0])
        self.assertIn("buying_defaults(spec)", Path(build.__file__).read_text())


class TheBanksOwnWasPrice(unittest.TestCase):
    def test_the_was_price_on_the_price_line_is_read(self):
        """brand_b-nov-22 (2026-11-08): "$79, was $136.00 bought separately" held as a price not in the list, though the
        offer bank's own Price line gives $136.00."""
        import tempfile, gaps
        with tempfile.TemporaryDirectory() as repo:
            f = Path(repo) / "brands/x/products/offer-bank.md"
            f.parent.mkdir(parents=True)
            f.write_text("## spa — Spa Bundle\n\n- Price: **$79.00**, was $136.00 (bought separately)\n\n"
                         "## duo — Duo\n\n- Price: **$58.00**\n")
            old = gaps.REPO
            gaps.REPO = Path(repo)
            try:
                got = gaps.offer_bank("x")
            finally:
                gaps.REPO = old
        self.assertEqual(got["spa bundle"]["was"], "$136.00")
        self.assertEqual(got["spa bundle"]["price"], "$79.00")
        self.assertNotIn("was", got["duo"])


if __name__ == "__main__":
    unittest.main()
