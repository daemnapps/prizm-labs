"""The design line's small guards. A picture's alt text is what the reader gets with images off: the section's words, never the review page's source
label ("Made from a real reference"), which the clean render hides (the team, 2026-10-27: it reached 21 emails).

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
        """brand-a-nov-07--glow-up's layout: a box with two step tiles and no big picture (KeyError: 'hero', 2026-10-23)."""
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
        """The hooks refresh the pictures of every email an update rebuilt (the team, 2026-10-27); a design-only change
        or a run this Mac does not hold is left alone."""
        import tempfile
        import layout_file as LF
        with tempfile.TemporaryDirectory() as repo:
            (Path(repo) / "runs/email-production/brand-b/brand-b-nov-01").mkdir(parents=True)
            names = ["runs/email-production/brand-b/brand-b-nov-01/klaviyo/card.json",
                     "runs/email-production/brand-b/brand-b-nov-01/klaviyo/email.html",
                     "runs/email-production/brand-b/brand-b-nov-01/design/email.json",
                     "runs/email-production/brand-a/not-here/klaviyo/card.json", "brands/brand-b/x.json"]
            self.assertEqual([d.name for d in LF.changed_runs(names, repo)], ["brand-b-nov-01"])


class APictureThatShowsWhatIsNotInTheBox(unittest.TestCase):
    def test_the_problem_names_the_picture_and_why(self):
        """the team, 2026-10-28: a wrong picture is the one check the team keeps, and it says which picture and why."""
        import build
        spec = {"brand": "x", "sections": [{"s": "photo_card", "picture": {"photo": "drive:a.jpg", "alt": "WIDGET in its case on the shelf"}}]}
        lk = {"check": {"prices": {"$1": "x"}, "not_in_box": [{"word": "case", "why": "the charging case is sold separately"}]}}
        out = build.product_check(spec, lk, "WIDGET in its case on the shelf")
        bad = [x["detail"] for x in out if x["result"] == "PROBLEM"]
        self.assertEqual(len(bad), 1, out)
        self.assertIn("photo card picture shows the case", bad[0])
        self.assertIn("sold separately", bad[0])
        words_only = {"brand": "x", "sections": [{"s": "letter", "text": "Keep it in the case."}]}
        out = build.product_check(words_only, lk, "Keep it in the case.")
        self.assertEqual([x["detail"] for x in out if x["result"] == "PROBLEM"], ['mentions "case": the charging case is sold separately'])

if __name__ == "__main__":
    unittest.main()
