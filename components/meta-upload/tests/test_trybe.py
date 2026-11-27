"""The Trybe rule (2026-11-15): an ad built from a creator's Trybe video carries trybe=<trybe_id> on its link
AND its name ends with the trybe_id, or the creator is unpaid and the sale unattributed. Checked on what is
actually posted to a fake Meta, on the name funnel-tracking reads back, and on the creator machine's
hand-off (deliveries.json) reaching 1-check as one tagged card per submission. Nothing reaches Meta or Drive."""
import json, re, sys, tempfile, unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import trybe_tag as TT
import upload as U
import performance as P
import to_check as T
import feed_creator as FC
from fake_meta import FakeMeta
from test_cards import Base, PAGE

TID = "7c690b8b"


class Tag(unittest.TestCase):
    def test_name_ends_with_the_id(self):
        n = TT.meta_name("b_p_brief-0001_batch-2026-11-15-a_quiz", TID)
        self.assertTrue(n.endswith(TID))
        self.assertEqual(n, "b_p_brief-0001_batch-2026-11-15-a_quiz_trybe-" + TID)
        self.assertEqual(TT.meta_name(n, TID), n)                      # never tagged twice
        self.assertEqual(TT.split(n), ("b_p_brief-0001_batch-2026-11-15-a_quiz", TID))
        self.assertEqual(TT.meta_name("x_y", None), "x_y")             # no id: name unchanged

    def test_funnel_tracking_reads_the_id_back(self):
        # components/funnel-tracking/machine/trybe.py: right(ad_name, 8) and [0-9a-f]{8}$
        n = TT.meta_name("b_p_none_batch-2026-11-15-a_quiz", TID)
        self.assertEqual(n[-8:], TID)
        self.assertEqual(re.search(r"([0-9a-f]{8})$", n).group(1), TID)

    def test_link_carries_trybe(self):
        u = TT.link("https://shop.example.com/quiz/?a=1&trybe=old00000", TID)
        q = parse_qs(urlparse(u).query)
        self.assertEqual(q["trybe"], [TID])
        self.assertEqual(q["a"], ["1"])
        self.assertEqual(TT.tagged(TT.meta_name("u_f", TID), u), [])
        self.assertTrue(TT.tagged("u_f", u))                           # name without the id fails
        self.assertTrue(TT.tagged(TT.meta_name("u_f", TID), "https://shop.example.com/"))

    def test_a_bad_id_is_refused(self):
        for bad in ("7C690B8", "zzzzzzzz", "7c690b8b9"):
            with self.assertRaises(ValueError):
                TT.clean(bad)
        self.assertEqual(TT.clean("7C690B8B"), TID)

    def test_performance_still_reads_a_tagged_name(self):
        d = P.ours(TT.meta_name("brand_b_brilliance-body-scrub_brief-0154_batch-2026-10-02-a_quiz", TID))
        self.assertEqual(d["ad_name"], "brand_b_brilliance-body-scrub_brief-0154_batch-2026-10-02-a")
        self.assertEqual(d["funnel"], "quiz")
        self.assertEqual(d["trybe_id"], TID)


class Upload(Base):
    def posted(self, **over):
        m = FakeMeta("brand_b")
        U.upload_card(self.approve(self.card(lane="creator", n=1, **over)), m=m, log=lambda *_: None)
        return [p for e, p in m.posts if e == "ads"]

    def test_a_trybe_card_posts_a_tagged_ad(self):
        ads = self.posted(trybe_id=TID)
        self.assertEqual(len(ads), 1)
        self.assertTrue(ads[0]["name"].endswith("_trybe-" + TID))
        self.assertTrue(ads[0]["creative"]["name"].endswith(TID))
        spec = ads[0]["creative"]["object_story_spec"]
        link = (spec.get("link_data") or {}).get("link") or spec["video_data"]["call_to_action"]["value"]["link"]
        self.assertEqual(parse_qs(urlparse(link).query)["trybe"], [TID])
        self.assertEqual(TT.tagged(ads[0]["name"], link), [])

    def test_a_card_without_trybe_is_unchanged(self):
        ads = self.posted()
        self.assertNotIn("trybe", ads[0]["name"])
        self.assertNotIn("trybe=", json.dumps(ads[0]))

    def test_the_card_plan_tags_every_page(self):
        f = self.card(lane="creator", n=1, trybe_id=TID)
        p = U.card_plan(f, json.loads((f / "card.json").read_text()))
        self.assertTrue(p["ads"])
        for a in p["ads"]:
            self.assertEqual(TT.tagged(a["meta_ad_name"], a["url"]), [])


class Deliveries(Base):
    """The creator machine's deliveries.json -> 1-check/creator, one tagged card per submission."""

    def setUp(self):
        super().setUp()
        self.repo = Path(self.tmp.name) / "repo"
        self.video = Path(self.tmp.name) / "clip.mp4"
        self.video.write_bytes(b"\x00" * 64)
        self.fetched = []

    def fetch(self, ref):
        self.fetched.append(ref["label"])
        return self.video

    def write(self, recs, label="2026-11-15", subs=None):
        d = self.repo / "runs" / "creator-machine" / "brand_b" / label
        d.mkdir(parents=True, exist_ok=True)
        (d / "deliveries.json").write_text(json.dumps(recs))
        if subs is not None:
            (d / "submissions.json").write_text(json.dumps(subs))
        return d / "deliveries.json"

    def rec(self, tid, who="Creator One", day="2026-11-15", **over):
        r = {"trybe_id": tid, "submission_id": "submission_x" + tid, "creator": who, "state": "approved",
             "media_type": "video", "products": ["Turmeric Body Scrub"], "product": "brilliance-body-scrub",
             "created_at": day + "T05:00:00Z",
             "media": {"drive_id": "id" + tid, "label": f"Shared Assets/runs/creator-machine/brand_b/x/videos/{tid}.mp4",
                       "bytes": 64}}
        r.update(over)
        return r

    def feed(self, files, **kw):
        return FC.feed_trybe("brand_b", files, links=[PAGE["link_id"]], root=self.root, fetch=self.fetch,
                             repo=self.repo, **kw)

    def test_every_video_becomes_a_tagged_card_once(self):
        f = self.write([self.rec(TID), self.rec("b17a93d5", who="Creator Two"),
                        self.rec("f3614270", media="Shared Assets/runs/creator-machine/brand_b/x/videos/f.mp4")])
        res = self.feed([f])
        cards = [p["card"] for p, _, _ in res if p]
        self.assertEqual(len(cards), 3, [w for _, w, _ in res])
        self.assertEqual({c["trybe_id"] for c in cards}, {TID, "b17a93d5", "f3614270"})
        self.assertTrue(all(c["lane"] == "creator" for c in cards))
        # same product, brief and day: three separate ads, never one card
        self.assertEqual(len({c["ad_name"] for c in cards}), 3)
        on_disk = json.loads((self.root / "brand_b" / "1-check" / "creator" / cards[0]["ad_name"] / "card.json").read_text())
        self.assertEqual(on_disk["trybe_id"], cards[0]["trybe_id"])
        self.assertEqual(on_disk["made_by"]["creator"], cards[0]["made_by"]["creator"])
        self.assertEqual(len(self.fetched), 3)
        # run again: nothing is filed twice, whatever state the card is in
        self.assertEqual([p for p, _, _ in self.feed([f]) if p], [])

    def test_already_an_ad_or_no_file_is_listed_not_filed(self):
        f = self.write([self.rec(TID), self.rec("b17a93d5", media=None), self.rec("f3614270")],
                       subs=[{"trybe_id": TID, "ads": {"count": 1}}])
        res = self.feed([f])
        self.assertEqual([p["card"]["trybe_id"] for p, _, _ in res if p], ["f3614270"])
        why = " ".join(w for _, w, _ in res if w)
        self.assertIn("already an ad", why)
        self.assertIn("no saved video", why)

    def test_unknown_product_and_bad_id_are_refused(self):
        f = self.write([self.rec(TID, product=None, products=["Some Unknown Thing"]), self.rec("NOTANID")])
        res = self.feed([f])
        self.assertEqual([p for p, _, _ in res if p], [])
        why = " ".join(w for _, w, _ in res if w)
        self.assertIn("not one of our product ids", why)
        self.assertIn("not a trybe_id", why)

    def live_card(self, product, primary, at, headlines=("Live headline",)):
        f = self.root / "brand_b" / "3-live" / "video" / f"brand_b_{product}_brief-0001_batch-{at[:10]}-a"
        f.mkdir(parents=True)
        (f / "card.json").write_text(json.dumps({"ad_name": f.name, "product": product, "copy_checked": True,
                                                 "words": {"primary": [primary], "headlines": list(headlines),
                                                           "descriptions": []},
                                                 "meta": [{"at": at}]}))

    def test_a_briefless_video_reuses_the_newest_live_cards_words(self):
        self.live_card("brilliance-body-scrub", "Older body.", "2026-10-01T10:00:00")
        self.live_card("brilliance-body-scrub", "Newest body.", "2026-11-01T10:00:00")
        self.live_card("brilliance-face-scrub", "Other product.", "2026-11-10T10:00:00")
        res = self.feed([self.write([self.rec(TID)])])
        card = [p["card"] for p, _, _ in res if p][0]
        self.assertEqual(card["words"]["primary"], ["Newest body."])
        self.assertTrue(card["copy_checked"])
        self.assertEqual(card["brief_id"], "trybe-" + TID)
        self.assertIn("live card", res[0][2])

    def test_a_trybe_product_name_maps_through_the_alias_table(self):
        rec = self.rec(TID, product=None, products=["Turmeric Body Scrub"])
        self.assertIsNone(FC.trybe_product("brand_b", rec, aliases={}))
        self.assertEqual(FC.trybe_product("brand_b", rec, aliases={"Turmeric Body Scrub": "brilliance-body-scrub"}),
                         "brilliance-body-scrub")
        # an alias to a product we do not have is still refused, never guessed
        self.assertIsNone(FC.trybe_product("brand_b", rec, aliases={"Turmeric Body Scrub": "no-such-product"}))

    def test_the_card_writer_refuses_a_bad_id(self):
        with self.assertRaises(T.Refused):
            T.plan("brand_b", "creator", "flexible", [self.video], ad_name="brand_b_brilliance-body-scrub_none_batch-2026-11-15-a",
                   links=[PAGE["link_id"]], root=self.root, trybe_id="nope")


if __name__ == "__main__":
    unittest.main()
