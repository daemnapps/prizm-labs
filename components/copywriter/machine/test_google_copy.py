"""google_copy — the Google text-ad chain, with no model and no network.

    python3 machine/test_google_copy.py
"""
import json, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import google_copy as GC  # noqa: E402

FORMATS = [
    {"id": "h1", "kind": "headline", "format": "[PRODUCT] for [PROBLEM]", "slot": "search", "days": 900, "state": "ok", "from": "x.com"},
    {"id": "h2", "kind": "headline", "format": "[BRAND] Official Site", "slot": "brand", "days": 800, "state": "ok", "from": "x.com"},
    {"id": "d1", "kind": "description", "format": "Get your [BODY PART] clean in [HOW FAST] with [PRODUCT].", "slot": "how-it-works", "days": 700, "state": "ok", "from": "y.com"},
    {"id": "h9", "kind": "headline", "format": "", "slot": "", "days": 1, "state": "missing", "from": "z.com"},
]
KW = dict(formats=FORMATS, keywords=["razor bumps", "ingrown hair"], competitors=["rivalco"], prices=["$49.99"],
          promo=False, caps={"FLEX"}, final_url="https://shop.example.com/a/", allowed_hosts=["shop.example.com"])


def ad(heads, descs, p1="bumps", p2="flex"):
    return {"headlines": [{"text": t, "format": f} for t, f in heads],
            "descriptions": [{"text": t, "format": f} for t, f in descs], "path1": p1, "path2": p2}


GOOD_H = [("FLEX for razor bumps", "h1"), ("Razor bumps gone smoother", "h1"), ("Ingrown hair help here", "h1")] + \
         [(f"Line number {i}", "h2") for i in range(12)]
GOOD_D = [(f"Get your neck clean in one minute with FLEX, day {i}.", "d1") for i in range(4)]


class Check(unittest.TestCase):
    def test_clean_ad_passes(self):
        self.assertEqual(GC.check(ad(GOOD_H, GOOD_D), **KW), [])

    def test_length_bang_emoji_caps_competitor_price_claim(self):
        h = GOOD_H[:]
        h[3] = ("A headline far longer than thirty chars", "h2")
        h[4] = ("Buy now!", "h2")
        h[5] = ("Smooth skin \U0001F525", "h2")
        h[6] = ("BEST brush", "h2")
        h[7] = ("Better than RivalCo", "h2")
        h[8] = ("Only $49.99", "h2")
        h[9] = ("Cures razor bumps", "h2")
        p = " | ".join(GC.check(ad(h, GOOD_D), **KW))
        for s in ("limit is 30", "exclamation", "emoji", "\"BEST\" in capitals", "another brand (rivalco)",
                  "not a promotion", "\"cures\" is a claim"):
            self.assertIn(s, p)

    def test_price_on_promo_must_be_on_page(self):
        k = dict(KW, promo=True)
        h = GOOD_H[:]
        h[3] = ("Now $49.99", "h2")
        self.assertEqual(GC.check(ad(h, GOOD_D), **k), [])
        h[3] = ("Now $39.99", "h2")
        self.assertIn("not a price on the landing page", " ".join(GC.check(ad(h, GOOD_D), **k)))

    def test_format_must_be_handed_and_usable(self):
        h = GOOD_H[:]
        h[3] = ("Made up line", "h7")
        h[4] = ("Broken format line", "h9")
        h[5] = ("Description format used", "d1")
        p = GC.check(ad(h, GOOD_D), **KW)
        self.assertEqual(sum("not one of the headline formats" in x for x in p), 3)

    def test_needs_search_words_counts_and_paths(self):
        h = [(f"Line number {i}", "h2") for i in range(10)]
        p = " | ".join(GC.check(ad(h, GOOD_D[:2], p1="far too long a path"), **KW))
        self.assertIn("only 0 headlines carry the words of a search", p)
        self.assertIn("10 headlines, 15 are asked", p)
        self.assertIn("2 descriptions, 4 are asked", p)
        self.assertIn("path1", p)

    def test_no_search_echo_when_group_has_none(self):
        h = [(f"Line number {i}", "h2") for i in range(15)]
        self.assertEqual(GC.check(ad(h, GOOD_D), **dict(KW, keywords=[])), [])

    def test_landing_host_rule(self):
        p = GC.check(ad(GOOD_H, GOOD_D), **dict(KW, final_url="https://other.example.com/x"))
        self.assertTrue(any("is not on shop.example.com" in x for x in p))

    def test_keep_clean_drops_only_named_lines(self):
        h = GOOD_H[:]
        h[4] = ("Buy now!", "h2")
        a = ad(h, GOOD_D)
        clean, dropped = GC.keep_clean(a, GC.check(a, **KW))
        self.assertEqual(len(clean["headlines"]), 14)
        self.assertEqual(dropped, [("headlines", 4)])


class Chain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        GC.RUNS = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_swipe_lines_longest_first_no_truncated_no_dupes(self):
        ads = [{"headlines": ["Short ad", "Cut off line..."], "days_running": 5},
               {"headlines": ["Long ad", "short ad"], "descriptions": ["Clean in 30 seconds."], "days_running": 900}]
        got = [(k, t) for _, k, t, _ in GC.swipe_lines(ads)]
        self.assertEqual(got[0], ("headline", "Long ad"))
        self.assertNotIn(("headline", "Cut off line..."), got)
        self.assertEqual(sum(t.lower() == "short ad" for _, t in got), 1)

    def test_strip_then_write_with_fake_model_and_page(self):
        sw = Path(self.tmp.name) / "sw.json"
        sw.write_text(json.dumps([{"network": "search", "domain": "x.com", "days_running": 900,
                                   "headlines": ["Lux for acne"], "descriptions": ["Get your skin clean in 30 seconds with Lux."]}]))
        strip_answer = '```json\n[{"n":1,"kind":"headline","format":"[PRODUCT] for [PROBLEM]","slot":"search"},' \
                       '{"n":2,"kind":"description","format":"Get your [BODY PART] clean in [HOW FAST] with [PRODUCT].","slot":"how-it-works"}]\n```'
        GC.strip("tb", str(sw), say=lambda *_: None, ask_fn=lambda t: strip_answer)
        fm = json.loads((GC.RUNS / "copywriter/tb/google-formats/formats.json").read_text())["formats"]
        self.assertEqual([f["state"] for f in fm], ["ok", "ok"])
        prod = Path(self.tmp.name) / "p.md"
        prod.write_text("# FLEX™ Brush\n\nCleans.")
        groups = Path(self.tmp.name) / "g.json"
        groups.write_text(json.dumps({"campaign": "c", "competitors": ["rivalco"], "groups": [
            {"name": "Razor Bumps", "final_url": "https://shop.example.com/a/", "keywords": [{"text": "razor bumps", "searches": 100}],
             "words": [{"text": "my neck bumps", "row": "r1"}]}]}))
        d2 = [(t, "d2") for t, _ in GOOD_D]              # line numbers run on across kinds: the description is d2
        first = ad([("FLEX for razor bumps!", "h1")] + [(f"FLEX for razor bumps {i}", "h1") for i in range(14)], d2)
        good = ad([(f"FLEX for razor bumps {i}", "h1") for i in range(15)], d2)
        answers = iter(["```json\n" + json.dumps(first) + "\n```", "```json\n" + json.dumps(good) + "\n```"])
        seen = []
        out = GC.write("tb", str(groups), str(prod), "lab", allowed_hosts=["shop.example.com"], say=lambda *_: None,
                       ask_fn=lambda t: (seen.append(t), next(answers))[1],
                       fetch=lambda u: "<h1>Get your neck back</h1><p>90-day guarantee. Rated 4.8 by 1,000 verified reviews.</p>")
        rec = out["groups"][0]
        self.assertEqual(rec["state"], "ok")
        self.assertIn("exclamation", seen[1])                  # the second try is told what broke
        self.assertIn("Get your neck back", seen[0])            # the page's own promise is in the prompt
        self.assertIn("my neck bumps", seen[0])                 # the customer's words are in the prompt
        self.assertTrue((GC.RUNS / "copywriter/tb/lab/razor-bumps/ad.md").is_file())


if __name__ == "__main__":
    unittest.main()
