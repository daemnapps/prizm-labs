#!/usr/bin/env python3
"""meta_copy — the narrow pull, against a stand-in Meta. No network."""
import io, json, shutil, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import meta_copy as MC  # noqa: E402


def ad(i, spend, buys):
    return {"ad_id": str(i), "ad_name": f"ad {i}", "spend": str(spend),
            "actions": [{"action_type": "omni_purchase", "value": str(buys)}],
            "action_values": [{"action_type": "omni_purchase", "value": str(buys * 60)}]}


class Fake:
    """Answers like Meta; the usage meter climbs by `step` per call."""

    def __init__(self, step=1):
        self.n, self.step, self.urls = 0, step, []

    def __call__(self, req):
        self.n += 1
        url = req.full_url
        self.urls.append(url)
        if "insights" in url and "filtering" not in url:
            body = {"data": [ad(i, 10000 - i, 50) for i in range(30)][:25]}
        elif "insights" in url:
            body = {"data": [ad(100 + i, 600 + i, 40 - i) for i in range(30)]}
        else:
            body = {"creative": {"body": "the words", "title": "the headline"}}
        r = mock.MagicMock()
        r.__enter__.return_value = r
        r.read.return_value = json.dumps(body).encode()
        r.headers = {"x-business-use-case-usage": json.dumps({"1": [{"total_cputime": self.n * self.step}]})}
        return r


class Pull(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(self.td, ignore_errors=True))
        p = mock.patch.object(MC, "out_dir", lambda brand, day=None: self.td)
        p.start(); self.addCleanup(p.stop)
        s = mock.patch.object(MC.time, "sleep", lambda *_: None)
        s.start(); self.addCleanup(s.stop)

    def door(self, fake):
        return MC.Door("brand-b", say=lambda *_: None, opener=fake, tok="t", account="1")

    def test_exactly_the_ask(self):
        fake = Fake()
        out = MC.pull("brand-b", door=self.door(fake), say=lambda *_: None)
        self.assertLessEqual(len(out), 50)
        self.assertEqual(sum("insights" in u for u in fake.urls), 2)          # 1 top-spend + 1 cpa page
        self.assertEqual(fake.n, 2 + len(out))                                 # one call per picked ad
        self.assertTrue(all("limit=25" in u for u in fake.urls if "insights" in u and "filtering" not in u))
        whys = {w for a in out for w in a["why"]}
        self.assertEqual(whys, {"spend", "cpa"})
        self.assertEqual(out[0]["primary"], ["the words"])

    def test_stops_at_75_and_resumes_without_asking_again(self):
        fake = Fake(step=20)                                                   # 20, 40, 60, 80 → stop
        self.assertIsNone(MC.pull("brand-b", door=self.door(fake), say=lambda *_: None))
        self.assertEqual(fake.n, 4)
        self.assertTrue((self.td / "insights.json").is_file())
        again = Fake()
        out = MC.pull("brand-b", door=self.door(again), say=lambda *_: None)
        self.assertFalse(any("insights" in u for u in again.urls))             # never re-pulled
        self.assertEqual(again.n, len(out) - 2)                                # only the words not yet read


BODY = ("Fade the appearance of dark spots and uneven skin tone and nourish discolored skin for a smooth, "
        "radiant glow. Women over fifty are telling us the spots on their hands faded in weeks of twice-weekly use.")


class Index(unittest.TestCase):
    def test_duplicates_collapse_to_one_row_each(self):
        a = lambda i, body, media, spend, why: {"ad_id": i, "ad_name": f"ad {i}", "spend": spend, "purchases": 10,
                                                "value": spend * 2, "cpa": spend / 10, "why": why,
                                                "primary": [body], "headlines": ["Same head"], "media": [media]}
        ads = [a("1", "It was never your razor.", "video:9", 1000, ["spend"]),
               a("2", "it was never your razor", "video:9", 500, ["cpa"]),     # same words, same video, re-cased
               a("3", "Something else.", "image:h", 200, ["cpa"])]
        ix = MC.index(ads)
        prim = [g for g in ix["copy"] if g["slot"] == "primary"]
        self.assertEqual(len(prim), 2)
        near = MC.index([a("4", BODY + " ✨\nGet Yours Now 👉 try.x.com", "video:1", 300, ["spend"]),
                         a("5", BODY + "✨\n👉 try.x.com", "video:2", 100, ["cpa"])])
        one = [g for g in near["copy"] if g["slot"] == "primary"]
        self.assertEqual((len(one), one[0]["spend"], len(one[0]["versions"])), (1, 400, 2))
        top = prim[0]
        self.assertEqual((top["duplicates"], top["spend"], top["why"]), (1, 1500, ["cpa", "spend"]))
        self.assertEqual([x["ad_id"] for x in top["ads"]], ["1", "2"])
        self.assertEqual(len([g for g in ix["copy"] if g["slot"] == "headlines"]), 1)
        self.assertEqual([g["media"] for g in ix["creative"]], ["video:9", "image:h"])
        self.assertEqual(ix["creative"][0]["duplicates"], 1)
        self.assertEqual(top["creatives"], ["video:9"])                       # copy names its creative
        self.assertEqual(len(ix["creative"][0]["primary"]), 1)                # creative names its copy, once


if __name__ == "__main__":
    unittest.main()
