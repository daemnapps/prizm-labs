"""The Galaxy filter picks the day's ads in three lanes, truly different, proven and deep, and says why it cuts (made-up brand, no files)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import creative_filter as F  # noqa: E402


STEMS = [("barber chair", "bumps along my neckline", "wedding photos"), ("night shift", "razor burn under my jaw", "job interview"),
         ("gym locker", "ingrown hairs across my cheeks", "first date"), ("school pickup", "dark marks on my chin", "family reunion"),
         ("long commute", "clogged pores around my nose", "graduation day"), ("barbecue weekend", "oily shine by noon", "boardroom meeting"),
         ("church choir", "scarring from old acne", "anniversary dinner"), ("night classes", "itchy red patches", "reunion trip")]


def person(pid, rows=1600, lines=None, avatar="av"):
    i = int(pid[1:]) % len(STEMS) if pid[1:].isdigit() else 0
    a, b, c = STEMS[i]
    lines = lines or [("experience", "ends in bumps %s" % a, "I got %s again after the %s and nothing helped" % (b, a)),
                      ("feeling", "embarrassed at %s" % c, "I feel embarrassed because of %s before %s" % (b, c)),
                      ("desire", "clear skin by %s" % c, "I want my face clear for %s without %s" % (c, b)),
                      ("doubt", "does it work", "")]
    return {"id": pid, "avatar": avatar, "rows_read": rows, "awareness_lead": "problem-aware", "problem": ["bumps", "neck"],
            "points": [{"kind": k, "point": p, "said": [s] if s else [], "rows": 4, "urgent": False} for k, p, s in lines]}


def winner(wid, buys, kind="Creator talking to camera", media="video", idea=None):
    ideas = {"w-talk": "razor bumps never your razor", "w-skit": "years of acne finally cleared", "w-demo": "creams just sit on top",
             "w-anim": "parasites hiding in pores", "w-static": "free brush this weekend", "w-none": "nothing sold"}
    return {"id": wid, "name": wid, "idea": idea or ideas.get(wid, "story of " + wid), "on_screen": kind, "media": media, "purchases": buys, "spend": buys * 50, "cpa": 50}


SIGNALS = [("skit ad - Icon LP", "Actor skit", 50, 30, 3.0), ("talk ad", "Creator talking to camera", 20, 20, 1.0)]
IMAGE_FORMATS = ["caption-box", "two-panel", "notes-app", "red-circle", "price-strike", "split-data"]


def ctx(**kw):
    c = {"brand": "acme", "total": 0, "signals": [], "outside": [], "image_formats": IMAGE_FORMATS,
         "winners": [winner("w-talk", 900), winner("w-skit", 700, "Actor skit"), winner("w-demo", 500, "Creator using the product"),
                     winner("w-anim", 400, "Animation"), winner("w-none", 0), winner("w-static", 200, "Sale graphic", "image")],
         "people": [person("p%d" % i) for i in range(8)]}
    c.update(kw)
    return c


class Standard(unittest.TestCase):
    def test_two_names_for_one_ad_are_one_format(self):
        self.assertEqual(F.storyline_of("testimonial-montage"), "montage")
        self.assertEqual(F.storyline_of("narrator-montage"), "montage")
        self.assertEqual(F.storyline_of("song-ad"), F.storyline_of("music-video-narrative"))

    def test_no_name_belongs_to_two_formats(self):
        seen = {}
        for f, v in F.STD["formats"].items():
            for a in v["aliases"]:
                self.assertNotIn(a, seen, "%s is in %s and %s" % (a, f, seen.get(a)))
                seen[a] = f

    def test_a_picture_kind_is_not_a_video_format(self):
        self.assertEqual(F.storyline_of("Sale graphic"), "")
        self.assertEqual(F.story_of("caption-box"), ("caption-box", "image"))
        self.assertEqual(F.story_of("micro-drama"), ("scene", "video"))


class Lanes(unittest.TestCase):
    def test_no_sales_and_no_real_line_are_cut_before_scoring(self):
        out = F.select(ctx(), 4, "video-internal")
        self.assertEqual(out["gates"]["no proof (no sales)"], 6 * 8 * 4 // 4 * 4 // 4 if False else 1 * 8 * 4)
        self.assertEqual(out["gates"]["no real line to open on"], 1 * 8 * 4)       # the line-less doubt x 4 video ads x 8 people
        self.assertNotIn("w-none", {r["winner"]["id"] for r in out["batch"]})
        self.assertTrue(all(r["point"]["said"] for r in out["batch"]))

    def test_creators_lane_only_takes_formats_a_person_can_film(self):
        rows = F.select(ctx(), 8, "creators")["batch"]
        self.assertTrue(rows)
        self.assertNotIn("w-anim", {r["winner"]["id"] for r in rows})             # an animation is not filmed by a creator
        self.assertTrue(all(F.STD["formats"][r["cell"]["storyline"]]["creators"] for r in rows))
        self.assertTrue(all(r["maker"] == "creator-brief" for r in rows))

    def test_internal_lane_can_make_what_a_creator_cannot(self):
        rows = F.select(ctx(), 8, "video-internal")["batch"]
        self.assertIn("explainer", {r["cell"]["storyline"] for r in rows})
        self.assertTrue(all(r["maker"] == "video-writing" and r["media"] == "video" for r in rows))

    def test_images_lane_makes_pictures_in_different_picture_formats(self):
        rows = F.select(ctx(), 5, "images")["batch"]
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(r["media"] == "image" and r["maker"] == "statics-sprint" for r in rows))
        fm = [r["cell"]["storyline"] for r in rows]
        self.assertTrue(set(fm) <= set(IMAGE_FORMATS))
        self.assertEqual(len(set(fm)), len(fm))                                     # each picture its own format
        self.assertEqual(max(__import__("collections").Counter(r["winner"]["id"] for r in rows).values()), 1)

    def test_rows_in_a_lane_are_apart_from_each_other(self):
        rows = F.select(ctx(), 6, "video-internal")["batch"]
        self.assertGreaterEqual(len(rows), 4)
        for i, a in enumerate(rows):
            for b in rows[i + 1:]:
                n, s, known, kseen = F.apart(a["cell"], b["cell"], F.CFG["opening_same_at"])
                self.assertGreaterEqual(n, F.RULE["pair"]["min"], (a["id"], b["id"]))
                self.assertGreaterEqual(s, F.seen_needed(F.RULE["seen"]["min"], kseen))

    def test_a_near_copy_of_a_live_ad_is_dropped(self):
        first = F.select(ctx(), 1, "video-internal")["batch"][0]
        live = dict(first["cell"], where="live", name="live-ad", opening=None)
        out = F.select(ctx(outside=[live]), 1, "video-internal")
        self.assertGreaterEqual(out["cuts"].get("too close to an ad Meta already has (live)", 0), 1)
        self.assertNotEqual(out["batch"][0]["cell"]["person"] + out["batch"][0]["cell"]["message"], first["cell"]["person"] + first["cell"]["message"])

    def test_the_lanes_of_one_day_are_kept_apart_from_each_other(self):
        out = F.daily(ctx(), {"video-internal": 4, "creators": 4, "images": 3})
        self.assertEqual([r["lane"] for r in out["batch"]], sorted((r["lane"] for r in out["batch"]), key=["video-internal", "creators", "images"].index))
        self.assertEqual([r["rank"] for r in out["batch"]], list(range(1, len(out["batch"]) + 1)))
        rows = out["batch"]
        for i, a in enumerate(rows):
            for b in rows[i + 1:]:
                n, s, known, kseen = F.apart(a["cell"], b["cell"], F.CFG["opening_same_at"])
                self.assertGreaterEqual(n, F.RULE["pair"]["min"], (a["id"], b["id"]))

    def test_more_sales_rank_first(self):
        self.assertEqual(F.select(ctx(), 2, "video-internal")["batch"][0]["winner"]["id"], "w-talk")

    def test_one_proven_ad_cannot_fill_a_lane(self):
        rows = F.select(ctx(), 6, "video-internal")["batch"]
        per = {}
        for r in rows:
            per[r["winner"]["id"]] = per.get(r["winner"]["id"], 0) + 1
        self.assertLessEqual(max(per.values()), F.CFG["lanes"]["video-internal"]["per_winner"])

    def test_thin_profile_weighs_less_and_is_marked(self):
        out = F.select(ctx(people=[person("p-full"), person("p-thin", rows=100)]), 6, "video-internal")
        thin = [r for r in out["batch"] if r["person"]["id"] == "p-thin"]
        full = [r["score"] for r in out["batch"] if r["person"]["id"] == "p-full"]
        self.assertTrue(all(r["person"]["depth"] == "thin" for r in thin))
        if thin:
            self.assertLess(max(r["score"] for r in thin), max(full))

    def test_a_row_names_its_profile_and_the_point_inside_it(self):
        r = F.select(ctx(), 2, "video-internal")["batch"][0]
        self.assertTrue(r["profile"]["label"])
        self.assertEqual(r["element"], "%s/%s" % (r["profile"]["id"], r["point"]["id"]))
        self.assertTrue(r["point"]["id"].startswith(r["point"]["kind"] + "-"))
        self.assertIn(r["profile"]["label"], r["reason"])

    def test_every_row_says_why(self):
        for r in F.daily(ctx(), {"video-internal": 3, "creators": 3, "images": 3})["batch"]:
            self.assertIn("Proven:", r["reason"])
            self.assertIn("Opens on their line", r["reason"])

    def test_watch_time_lifts_the_format_that_holds(self):
        t = F.watch_table(SIGNALS)
        self.assertGreater(t["scene"]["score"], t["presenter"]["score"])
        out = F.select(ctx(signals=SIGNALS, winners=[winner("w-skit", 300, "Actor skit"), winner("w-talk", 300)]), 1, "video-internal")
        self.assertEqual(out["batch"][0]["winner"]["id"], "w-skit")

    def test_setting_comes_from_the_point_words(self):
        self.assertEqual(F.setting_of("bumps every time I leave the barber"), "barbershop")
        self.assertEqual(F.setting_of("nothing about a place"), "")

    def test_unknown_columns_never_make_two_ads_the_same(self):
        a = {"person": "p1", "awareness": "problem-aware", "message": "years of acne", "storyline": "scene", "opening": "x y z", "setting": "car", "media": "video"}
        b = {"person": "p2", "awareness": "problem-aware", "message": "razor not problem", "media": "video"}
        self.assertIsNone(F._nearest(a, [b], 0.45, 3, 2))
        self.assertIsNotNone(F._nearest(a, [dict(a)], 0.45, 3, 2))

    def test_ad_names_join_without_the_page_suffix(self):
        self.assertEqual(F.ad_base("Cason Winchester #2 - Parasite LP #2"), "Cason Winchester #2")


class Start(unittest.TestCase):
    def test_a_pick_is_ordered_the_standard_way_and_nothing_is_spent(self):
        out = F.daily(ctx(), {"video-internal": 2, "creators": 1, "images": 1})
        calls = []

        class P:
            returncode, stdout, stderr = 0, "ask written", ""

        def fake(cmd, **kw):
            calls.append(cmd)
            return P()
        with tempfile.TemporaryDirectory() as d:
            done = F.start(out, {1, 4}, runner=fake, dest=d)
            self.assertEqual([x["rank"] for x in done], [1, 4])
            self.assertTrue((Path(d) / (out["made"] + "-starts.json")).exists())
        self.assertEqual(len(calls), 2)
        self.assertIn("ask.py", calls[0][1])
        self.assertIn("--profile", calls[0])
        self.assertIn(out["batch"][0]["point"]["said"][0], calls[0])
        self.assertEqual(done[0]["door"], F.STD["lanes"]["video-internal"]["door"])
        self.assertEqual(done[1]["lane"], "images")


if __name__ == "__main__":
    unittest.main()
