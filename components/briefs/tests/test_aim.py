#!/usr/bin/env python3
"""aim_of: who a brief is for, first answer on file wins; another avatar's or another product's answer is never lent.

    /usr/bin/python3 components/briefs/tests/test_aim.py

A fixture repo in a temp folder with a stand-in brand and product table; no real brand file is read.
"""
import json, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

COMPONENT = Path(__file__).resolve().parent.parent
sys.path.append(str(COMPONENT))
import aim as AM  # noqa: E402
import briefs_index as BI  # noqa: E402

N = BI.names()
CATALOG = {"flex": "flex-face-brush", "flex-face-brush": "flex-face-brush", "cream": "cream"}


def put(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data))


def reg(num, run=None, avatar="man", product="flex-face-brush"):
    k = "acme_%s_brief-%04d" % (product, num)
    return k, {"id": k, "brief": "brief-%04d" % num, "brand": "acme", "product": product, "avatar": avatar, "run": run, "key": k}


class Aim(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.patches = [mock.patch.object(N, "product_id", lambda b, p, root=None: CATALOG.get(str(p or "").lower())),
                        mock.patch.object(N, "product_aliases", lambda b, c, root=None: ["flex"] if c == "flex-face-brush" else []),
                        mock.patch.object(N, "WS", self.repo)]
        for p in self.patches:
            p.start()
        rows = dict([reg(1, "runs/video-writing/acme/one"), reg(2, "two"), reg(3, "runs/ad-variations/acme/sp-ad-a"), reg(4, "runs/video-writing/acme/four"),
                     reg(5, "runs/video-production/acme/five"), reg(6, "runs/video-writing/acme/six"), reg(7, None, None),
                     reg(8, "runs/video-writing/acme/eight"), reg(8, None, "woman", "cream")])
        put(self.repo / "components/image-teardown/briefs.json", {"briefs": rows})
        put(self.repo / "brands/acme/briefs/briefs.json", {"briefs": [
            {"brief": "brief-0001", "product": "flex-face-brush", "count": "brand+product", "avatar": "man", "sub_avatar": "sub-02-night",
             "angle": "its-not-you", "moves": {"who": "night", "awareness": "most-aware", "face": "male/25-34/black"}}]})
        w = self.repo / "runs/video-writing/acme"
        put(w / "one/run.json", {"brand": "acme", "aim": {"avatar": "man", "sub": "day", "demographic": "male/45-54/white", "desire": "smooth (freedom-from-pain)",
                                                          "awareness": "unaware", "stage": "3", "doubt": "for-me", "claim": "x"}})
        put(w / "two/run.json", {"declared_audience": {"avatar": "man", "sub": "sub-03-ingrown", "awareness": "unaware"},
                                 "audience": {"_avatar": "man", "_sub_avatar": "other"},
                                 "market_state": {"lead_desire": "clear skin", "awareness": "Problem aware (2)", "sophistication": "stage-3"}})
        v = self.repo / "runs/ad-variations/acme"
        put(v / "sp-ad-a/run.json", {"brand": "acme", "product": "flex", "sprint": "sp", "ad": "a"})
        put(v / "sp/sprint.json", {"avatar": "man", "ads": [{"id": "a", "sub": "bald", "awareness": "problem-aware", "desire": "a smooth head"}, {"id": "b", "sub": "not-this"}]})
        put(w / "four/run.json", {"audience": {"_avatar": "woman", "_sub_avatar": "her-sub"}, "market_state": {"lead_desire": "hers", "awareness": "unaware"}})
        put(self.repo / "runs/video-production/acme/five/run.json", {"writing_run": "runs/video-writing/acme/five-w", "copied_from": "runs/video-writing/acme/two"})
        put(w / "five-w/run.json", {"market_state": {"lead_desire": "its own", "awareness": "solution-aware or product-aware"}})
        put(w / "six/run.json", {"product": "cream", "market_state": {"lead_desire": "the cream's"}})
        put(w / "eight/run.json", {"aim": {"avatar": "man", "sub": "eight-sub"}})

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def of(self, n, product="flex-face-brush"):
        return AM.aim_of("acme", "acme_%s_brief-%04d" % (product, n), repo=self.repo)

    def test_the_brief_header_wins_then_the_runs_aim_fills(self):
        a = self.of(1)
        self.assertEqual((a["sub"], a["demographic"], a["awareness"], a["claim"]), ("night", "male/25-34/black", "most-aware", "its-not-you"))
        self.assertEqual((a["desire"], a["doubt"], a["stage"]), ("smooth (freedom-from-pain)", "for-me", "3"))
        self.assertEqual(a["from"]["sub"], "brief record")
        self.assertEqual(a["from"]["doubt"], "runs/video-writing/acme/one/run.json aim")

    def test_older_fields_and_both_key_spellings(self):
        a = self.of(2)
        self.assertEqual((a["sub"], a["awareness"], a["desire"], a["stage"], a["doubt"]), ("ingrown", "unaware", "clear skin", "stage-3", None))
        self.assertEqual(AM.aim_of("acme", "acme_flex_brief-0002", repo=self.repo), a)
        self.assertEqual(AM.aim_of("acme", "brief-0002", repo=self.repo), a)

    def test_sprint_ad_fields(self):
        a = self.of(3)
        self.assertEqual((a["sub"], a["awareness"], a["desire"]), ("bald", "problem-aware", "a smooth head"))

    def test_another_avatars_answer_is_never_lent(self):
        a = self.of(4)
        self.assertEqual((a["avatar"], a["sub"], a["desire"], a["awareness"]), ("man", None, None, None))
        self.assertEqual(a["conflicts"], [{"source": "runs/video-writing/acme/four/run.json", "avatar": "woman"}])

    def test_made_from_link_yes_copied_from_another_ad_no_and_two_levels_is_no_answer(self):
        a = self.of(5)
        self.assertEqual((a["desire"], a["sub"], a["awareness"]), ("its own", None, None))

    def test_another_products_run_is_not_read(self):
        self.assertIsNone(self.of(6)["desire"])

    def test_nothing_on_file_is_none(self):
        for key in ("acme_flex-face-brush_brief-0007", "acme_flex_brief-0999", "garbage"):
            a = AM.aim_of("acme", key, repo=self.repo)
            self.assertEqual([a[k] for k in AM.FIELDS], [None] * len(AM.FIELDS))

    def test_a_number_two_products_share_is_not_guessed(self):
        self.assertIsNone(AM.aim_of("acme", "brief-0008", repo=self.repo)["avatar"])
        self.assertEqual(self.of(8)["sub"], "eight-sub")
        self.assertEqual(self.of(8, "cream")["avatar"], "woman")

    def test_reads_only(self):
        before = {p: p.read_bytes() for p in self.repo.rglob("*") if p.is_file()}
        for n in range(1, 9):
            self.of(n)
        self.assertEqual(before, {p: p.read_bytes() for p in self.repo.rglob("*") if p.is_file()})


if __name__ == "__main__":
    unittest.main()
