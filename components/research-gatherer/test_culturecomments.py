#!/usr/bin/env python3
"""Tests for feedcomments / digcomments / retag --culture (2026-10-06) and the
apply step's two new doors (`add` rows, `add_use` tags). No network, no
model, temp folders only — fixtures shaped like the real files, named like
nothing real.

    python3 -m unittest components/research-gatherer/test_culturecomments.py
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from research_gatherer import bank_apply as BA        # noqa: E402
from research_gatherer import culturecomments as CC   # noqa: E402
from research_gatherer import retag as RT             # noqa: E402

AVATARS = {"avatars": [
    {"id": "core-one", "sub_avatars": ["sub-a", "sub-b"]},
    {"id": "core-two", "sub_avatars": []},
]}
LANG = "brands/b/core-avatars/core-one/language"

COMMENTS_MD = """# Comments — 4 captured of 90 on the post

The room talking to each other, ranked by likes. **This is the payload** —
a caption is a creator broadcasting, this is the avatar unprompted.

- **120** · @someone — first line of a comment
that keeps going on a second line
- **40** · @other —
- **3** · @third — short one
- **0** · @x.y — ends here
"""

POST_MD = """# acct — tiktok

- url: https://www.tiktok.com/@acct/video/123
- posted: 2026-01-01
"""


def sha(t):
    return hashlib.sha1(t.encode()).hexdigest()[:12]


class Tree(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        av = self.root / "brands" / "b" / "core-avatars"
        av.mkdir(parents=True)
        (av / "avatars.json").write_text(json.dumps(AVATARS))
        (self.root / LANG).mkdir(parents=True)
        self.bank = self.root / LANG / "prospects.json"
        self.bank.write_text(json.dumps({"schema": 1, "entries": [
            {"id": "language_b_core-one_prospect_0007", "text": "we all know the rule", "funnel": "prospect",
             "use": "community-voice", "signal": {"likes": 5},
             "source": {"type": "comment", "ref": "https://x.test/p/1", "id": "c1"}},
            {"id": "language_b_core-one_prospect_0008", "text": "a survey answer", "funnel": "prospect",
             "use": ["problem-language"], "source": {"type": "survey", "ref": "sheet"}},
        ]}, indent=1) + "\n")

    def tearDown(self):
        self.t.cleanup()


class FeedMapping(Tree):
    def test_core_avatar(self):
        self.assertEqual(CC.map_feed("b--core-two", self.root), ("b", "core-two", None))

    def test_sub_avatar(self):
        self.assertEqual(CC.map_feed("b--sub-b", self.root), ("b", "core-one", "sub-b"))

    def test_skipped(self):
        self.assertIsNone(CC.map_feed("damon--sub-a", self.root))
        self.assertIsNone(CC.map_feed("b--a-shop-feed", self.root))
        self.assertIsNone(CC.map_feed("no-brand-separator", self.root))

    def test_rank_kept_by_views_then_growth_minus_done(self):
        items = {
            "tiktok:1": {"url": "u1", "sift": {"keep": True}},
            "tiktok:2": {"url": "u2", "sift": {"keep": True}},
            "tiktok:3": {"url": "u3", "sift": {"keep": False}},
            "tiktok:4": {"url": "u4", "sift": {"keep": True}},
            "tiktok:5": {"url": "u5", "sift": {"keep": True}},
        }
        obs = CC.latest_views([
            json.dumps({"item": "tiktok:1", "at": "2026-01-01", "views": 100}),
            json.dumps({"item": "tiktok:1", "at": "2026-01-02", "views": 500}),
            json.dumps({"item": "tiktok:2", "at": "2026-01-01", "views": 500}),
            json.dumps({"item": "tiktok:2", "at": "2026-01-02", "views": 500}),
            json.dumps({"item": "tiktok:3", "at": "2026-01-02", "views": 9999}),
            json.dumps({"item": "tiktok:4", "at": "2026-01-02", "views": 9000}),
            json.dumps({"item": "tiktok:5", "at": "2026-01-02", "views": 1}),
        ])
        got = [p["url"] for p in CC.rank_posts(items, obs, 3, done={"u4"})]
        self.assertEqual(got, ["u1", "u2", "u5"])   # u3 not kept, u4 already pulled, u1 grew


class CommentsParser(unittest.TestCase):
    def test_parse(self):
        cs = CC.parse_comments_md(COMMENTS_MD)
        self.assertEqual(len(cs), 4)
        self.assertEqual(cs[0]["likes"], 120)
        self.assertEqual(cs[0]["text"], "first line of a comment\nthat keeps going on a second line")
        self.assertEqual(cs[1]["text"], "")
        self.assertEqual(cs[3]["author"], "x.y")

    def test_missing_is_empty(self):
        self.assertEqual(CC.parse_comments_md("# Comments\n\n> MISSING — the scrape failed.\n"), [])

    def test_post_url(self):
        self.assertEqual(CC.parse_post_md(POST_MD), "https://www.tiktok.com/@acct/video/123")

    def test_dig_rows(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "tiktok-acct-123"
            d.mkdir()
            (d / "post.md").write_text(POST_MD)
            (d / "comments.md").write_text(COMMENTS_MD)
            rows = CC.dig_rows(d, "b--sub-a", "sub-a", "2026-10-06")
        self.assertEqual(len(rows), 3)                       # the empty one is gone
        r = rows[0]
        self.assertEqual((r["source_kind"], r["property"], r["item"], r["sub"], r["likes"]),
                         ("dig-comment", "tiktok", "b--sub-a", "sub-a", 120))
        self.assertEqual(r["ref"], "https://www.tiktok.com/@acct/video/123")
        self.assertNotIn("someone", json.dumps(rows))         # no handle stored
        # the id is stable: same post, commenter and words -> same id
        self.assertEqual(r["source_id"], CC.dig_comment_id(r["ref"], "someone",
                                                           "first line of a comment\nthat keeps going on a second line"))


class Dedupe(Tree):
    def test_against_bank_and_itself(self):
        have = CC.bank_keys("b", "core-one", self.root)
        self.assertIn(("https://x.test/p/1", "c1"), have)
        rows = [dict(ref="https://x.test/p/1", source_id="c1", text="old"),
                dict(ref="https://x.test/p/1", source_id="c2", text="new"),
                dict(ref="https://x.test/p/1", source_id="c2", text="new again"),
                dict(ref="https://x.test/p/2", source_id="c1", text="other post")]
        got = CC.dedupe(rows, have)
        self.assertEqual([(r["ref"], r["source_id"]) for r in got],
                         [("https://x.test/p/1", "c2"), ("https://x.test/p/2", "c1")])

    def test_no_words(self):
        self.assertFalse(CC.has_words("😂😂 🔥"))
        self.assertFalse(CC.has_words("100 !!"))
        self.assertTrue(CC.has_words("ok 😂"))
        self.assertTrue(CC.has_words("لم مزه"))


def write_prop(root, prop):
    p = root / "runs" / "proposal.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(prop))
    return p


class ApplyAdd(Tree):
    def entry(self, cid, text="new words", ref="https://x.test/p/9"):
        return {"text": text, "funnel": "prospect", "use": ["laugh"], "sub": "sub-a",
                "source": {"type": "comment", "kind": "dig-comment", "ref": ref, "id": cid, "item": "b--sub-a"}}

    def test_adds_numbered_and_dedupes(self):
        prop = {"kind": "language-bank-proposal", "version": 1, "brand": "b", "tool": "t", "add": [
            {"file": f"{LANG}/prospects.json", "entry": self.entry("n1")},
            {"file": f"{LANG}/prospects.json", "entry": self.entry("n1")},            # same twice
            {"file": f"{LANG}/prospects.json", "entry": self.entry("c1", ref="https://x.test/p/1")},  # in bank
            {"file": f"{LANG}/prospects.json", "entry": self.entry("n2")},
        ]}
        rep = BA.apply(write_prop(self.root, prop), self.root)
        self.assertEqual((rep["applied"], rep["skipped"]), (2, 2))
        ids = [e["id"] for e in json.loads(self.bank.read_text())["entries"]]
        self.assertEqual(ids[-2:], ["language_b_core-one_prospect_0009", "language_b_core-one_prospect_0010"])

    def test_refused_without_link(self):
        prop = {"kind": "language-bank-proposal", "version": 1, "brand": "b", "add": [
            {"file": f"{LANG}/prospects.json", "entry": self.entry("n1", ref="not a link")}]}
        before = self.bank.read_text()
        with self.assertRaises(BA.Refused):
            BA.apply(write_prop(self.root, prop), self.root)
        self.assertEqual(self.bank.read_text(), before)


class RetagAddOnly(Tree):
    def test_candidates_only_comment_types(self):
        rows = RT.candidates("b", "core-one", self.root)
        self.assertEqual([e["id"] for _, _, e in rows], ["language_b_core-one_prospect_0007"])

    def test_parse_drops_unknown_tags(self):
        got = RT.parse('noise [{"i": 0, "add": ["laugh", "objection", "laugh"]}, {"i": 7, "add": ["taste"]}]', 2)
        self.assertEqual(got, {0: ["laugh"]})

    def test_model_read_and_apply_only_adds(self):
        rows = RT.candidates("b", "core-one", self.root)
        tags, done = RT.read(rows, "{{ROWS}}", "m", claude=lambda p: '[{"i": 0, "add": ["community-voice", "laugh"]}]')
        prow = RT.build(rows, tags)
        self.assertEqual(prow[0]["add_use"], ["laugh"])        # community-voice is already there
        prop = {"kind": "language-bank-proposal", "version": 1, "brand": "b", "rows": prow}
        BA.apply(write_prop(self.root, prop), self.root)
        e = json.loads(self.bank.read_text())["entries"][0]
        self.assertEqual(e["use"], ["community-voice", "laugh"])
        self.assertEqual(e["text"], "we all know the rule")

    def test_apply_refuses_a_non_culture_tag(self):
        prop = {"kind": "language-bank-proposal", "version": 1, "brand": "b", "rows": [
            {"file": f"{LANG}/prospects.json", "index": 0, "id": "language_b_core-one_prospect_0007",
             "add_use": ["hook"]}]}
        with self.assertRaises(BA.Refused):
            BA.apply(write_prop(self.root, prop), self.root)

    def test_tags_already_there_is_a_skip(self):
        prop = {"kind": "language-bank-proposal", "version": 1, "brand": "b", "rows": [
            {"file": f"{LANG}/prospects.json", "index": 0, "id": "language_b_core-one_prospect_0007",
             "text_sha": sha("we all know the rule"), "add_use": ["community-voice"]}]}
        rep = BA.apply(write_prop(self.root, prop), self.root)
        self.assertEqual((rep["applied"], rep["skipped"]), (0, 1))


if __name__ == "__main__":
    unittest.main()
