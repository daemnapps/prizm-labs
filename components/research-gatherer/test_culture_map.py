#!/usr/bin/env python3
"""Tests for research_gatherer/culture_map.py — the bottom-up culture map.
No network, no model, temp folders only (the component's test rule):
evidence ids, the feed -> avatar rule, the line check, the hand-copy-once rule."""
import json
import shutil
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
from research_gatherer import culture_map as CM   # noqa: E402

REAL_WS = HERE.parents[1]


def w(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text if isinstance(text, str) else json.dumps(text))


class Workspace(unittest.TestCase):
    """A tiny workspace: brand b, avatar a1 with subs s1 and s2."""

    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())
        # the language layer engine is read-only code; a copy runs against the temp tree
        src = next(q for q in (REAL_WS / "components" / "language-layer" / "language_layer" / "engine.py",
                               REAL_WS / "tools" / "language-layer" / "language_layer" / "engine.py") if q.is_file())
        w(self.ws / "components/language-layer/language_layer/engine.py", src.read_text())
        av = self.ws / "brands/b/core-avatars"
        w(av / "avatars.json", {"avatars": [{"id": "a1", "label": "Avatar one", "sub_avatars": ["s1", "s2"]},
                                            {"id": "mom", "sub_avatars": []}]})
        w(av / "a1/profile.md", "# King\nHe loves the Marathon.\n")
        w(av / "a1/language/rules.md", "Say king.\n")
        w(av / "a1/language/prospects.json", {"funnel": "prospect", "entries": [
            {"id": "language_b_a1_prospect_0001", "text": "respect your barber", "use": ["trust-language"],
             "signal": {"likes": 852}, "source": {"name": "TikTok comment", "pulled": "2026-10-01"}},
            {"id": "language_b_a1_prospect_0002", "text": "2 different people 💀", "use": ["laugh"],
             "signal": {"likes": 15400}},
            {"id": "language_b_a1_prospect_0003", "text": "where do I buy", "use": ["question"],
             "signal": {"likes": 99999}},
            {"id": "language_b_a1_prospect_0004", "text": "old line", "use": ["taste"], "status": "retired"},
        ]})
        feeds = self.ws / "components/swipe-organic/records/avatar-feeds"
        for fid, url, views in (("b--a1", "https://t.test/@a/video/1", 500), ("b--s1", "https://t.test/@c/video/2", 900),
                                ("b--feed-x", "https://t.test/@d/video/3", 1), ("damon--saves", "https://t.test/@e/video/4", 1)):
            w(feeds / fid / "items.json", {"items": {f"tiktok:{views}": {
                "url": url, "author": url.split("@")[1].split("/")[0], "caption": "cap #nba", "hashtags": ["nba", "fyp"],
                "sift": {"keep": True, "kind": "skit"}}}})
            w(feeds / fid / "observations.jsonl",
              json.dumps({"item": f"tiktok:{views}", "at": "2026-09-01", "views": 1}) + "\n" +
              json.dumps({"item": f"tiktok:{views}", "at": "2026-09-19", "views": views}) + "\n")
            w(feeds / fid / "sweeps.jsonl", json.dumps({"at": "2026-09-19T18:00:00+00:00"}) + "\n")
        dig = self.ws / "components/swipe-organic/records/culture-digs/b/a1/s1"
        w(dig / "affinity.md", "# affinity\noriginal sound 4\n")
        w(dig / "opportunity.md", "# opportunity\n")
        w(dig / "formats.md", "# not evidence for the map\n")
        w(self.ws / "runs/video-teardown/b/r1/stages/1k-culture.json",
          {"schema": 1, "run": "r1", "brand": "b", "avatar": "a1", "sub": None,
           "refs": [{"id": "R1", "name": "Mamba out", "kind": "person", "use": ["nostalgia"], "receipts": ["C1"]},
                    {"id": "R2", "name": "Love Me", "kind": "song", "use": [], "receipts": []}]})
        w(self.ws / "runs/video-teardown/b/r2/stages/1k-culture.json",
          {"schema": 1, "run": "r2", "brand": "b", "avatar": "mom", "refs": [{"id": "R1", "name": "x"}]})

    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)


class FeedMapping(Workspace):
    def test_rule(self):
        ros = {"b": CM.roster("b", self.ws)}
        self.assertEqual(CM.map_feed("b--a1", ros), ("b", "a1", None))
        self.assertEqual(CM.map_feed("b--s1", ros), ("b", "a1", "s1"))
        self.assertEqual(CM.map_feed("b--s2", ros), ("b", "a1", "s2"))
        self.assertIsNone(CM.map_feed("b--feed-x", ros))
        self.assertIsNone(CM.map_feed("damon--saves", ros))
        self.assertIsNone(CM.map_feed("other--a1", ros))

    def test_feeds_for_avatar(self):
        got = [(f, s) for f, s, _ in CM.feeds_for("b", "a1", self.ws)]
        self.assertEqual(got, [("b--a1", None), ("b--s1", "s1")])


class EvidenceIds(Workspace):
    def test_pack_ids(self):
        pack = CM.build_pack("b", "a1", self.ws)
        ids = CM.pack_ids(pack)
        self.assertIn("language_b_a1_prospect_0001", ids)
        self.assertIn("language_b_a1_prospect_0002", ids)
        self.assertNotIn("language_b_a1_prospect_0003", ids)     # not a culture tag
        self.assertNotIn("language_b_a1_prospect_0004", ids)     # retired
        self.assertIn("post:https://t.test/@a/video/1", ids)
        self.assertIn("post:https://t.test/@c/video/2", ids)
        self.assertNotIn("post:https://t.test/@d/video/3", ids)    # unmapped feed
        self.assertIn("feed:b--a1@a", ids)
        self.assertNotIn("feed:b--a1#nba", ids)                  # a hashtag needs 2+ posts
        self.assertIn("dig:b/a1/s1/affinity.md", ids)
        self.assertIn("dig:b/a1/s1/opportunity.md", ids)
        self.assertNotIn("dig:b/a1/s1/formats.md", ids)
        self.assertIn("run:r1#R1", ids)
        self.assertIn("run:r1#R2", ids)
        self.assertNotIn("run:r2#R1", ids)                         # another avatar's read

    def test_loudest_first_and_latest_views(self):
        pack = CM.build_pack("b", "a1", self.ws)
        rows = [i for i in pack["items"] if i["kind"] == "bank-row"]
        self.assertEqual(rows[0]["id"], "language_b_a1_prospect_0002")
        post = next(i for i in pack["items"] if i["id"] == "post:https://t.test/@a/video/1")
        self.assertEqual(post["views"], 500)
        self.assertEqual(pack["sources"]["feeds"][0]["last_sweep"], "2026-09-19")

    def test_ids_stable(self):
        a = CM.pack_ids(CM.build_pack("b", "a1", self.ws))
        b = CM.pack_ids(CM.build_pack("b", "a1", self.ws))
        self.assertEqual(a, b)

    def test_no_reads_says_so(self):
        shutil.rmtree(self.ws / "runs")
        pack = CM.build_pack("b", "a1", self.ws)
        self.assertTrue(any("1k-culture" in n for n in pack["notes"]))


class Verify(unittest.TestCase):
    KNOWN = {"language_b_a1_prospect_0001", "post:https://t.test/@a/video/1", "run:r1#R1"}

    def test_drops_uncited_and_unknown(self):
        body = "\n".join([
            "## Who they trust",
            "- His barber: \"respect your barber\" (852 likes) [language_b_a1_prospect_0001]",
            "- Kevin Hart is his favourite",
            "- Druski sketches [post:https://t.test/@zz/video/9]",
            "- Mixed: one good one bad [language_b_a1_prospect_0001, made_up_0009]",
            "- Kobe [run:r1#R1] [post:https://t.test/@a/video/1]",
            "### a subheading passes",
            "## Culture uses",
            "| Reference / format | What it does | Receipt |",
            "|---|---|---|",
            "| Barber verdict | trust | [language_b_a1_prospect_0001] |",
            "| Fake row | laugh | |",
            "## To test",
            "- The Marathon anchor (profile). Needs a feed post or comment naming it.",
        ])
        text, rep = CM.verify(body, self.KNOWN)
        self.assertIn("respect your barber", text)
        self.assertIn("Kobe", text)
        self.assertIn("| Barber verdict", text)
        self.assertIn("| Reference / format", text)
        self.assertIn("The Marathon anchor", text)               # To test is never checked
        self.assertNotIn("Kevin Hart", text)
        self.assertNotIn("Druski", text)
        self.assertNotIn("Mixed", text)
        self.assertNotIn("Fake row", text)
        self.assertEqual(rep["uncited"], 2)
        self.assertEqual(rep["unknown"], 2)
        self.assertEqual(rep["kept"], 3)        # checked lines only

    def test_footer_counts(self):
        _, rep = CM.verify("## Off-limits\n- nothing cited\n", set())
        self.assertIn("1 dropped", CM.footer(rep))
        self.assertIn("1 cited nothing", CM.footer(rep))

    def test_empty_sections_marked(self):
        out = CM.fill_empty_sections("## Who they trust\n## Off-limits\n- x [a]\n")
        self.assertIn("## What they laugh at", out)
        self.assertIn("## To test", out)
        self.assertEqual(out.count("_Nothing in the evidence backs this section yet._"), len(CM.SECTIONS) - 2)
        self.assertIn("_Nothing waiting to be tested._", out)


class HandCopy(Workspace):
    def test_copied_once_never_overwritten(self):
        home = CM.avatar_home("b", "a1", self.ws)
        (home / "culture-map.md").write_text("# hand built v1\n")
        hand = CM.preserve_hand("b", "a1", self.ws)
        self.assertEqual(hand.read_text(), "# hand built v1\n")
        (home / "culture-map.md").write_text(CM.MARK + "\n# generated\n")
        CM.preserve_hand("b", "a1", self.ws)
        self.assertEqual((home / CM.HAND_NAME).read_text(), "# hand built v1\n")
        (home / "culture-map.md").write_text("# hand edited again\n")
        CM.preserve_hand("b", "a1", self.ws)
        self.assertEqual((home / CM.HAND_NAME).read_text(), "# hand built v1\n")

    def test_generated_map_is_not_kept_as_hand(self):
        home = CM.avatar_home("b", "a1", self.ws)
        (home / "culture-map.md").write_text(CM.MARK + "\n# generated\n")
        self.assertIsNone(CM.preserve_hand("b", "a1", self.ws))
        self.assertFalse((home / CM.HAND_NAME).exists())

    def test_candidates_carry_hand_profile_rules(self):
        home = CM.avatar_home("b", "a1", self.ws)
        (home / "culture-map.md").write_text("# hand built v1\nKevin Hart\n")
        CM.preserve_hand("b", "a1", self.ws)
        (home / "culture-map.md").write_text(CM.MARK + "\n# generated\n")
        c = CM.candidate_text("b", "a1", self.ws)
        self.assertIn("Kevin Hart", c)
        self.assertIn("Marathon", c)
        self.assertIn("Say king.", c)
        self.assertNotIn("# generated", c)


class EndToEnd(Workspace):
    def test_run_with_fake_model(self):
        fake = self.ws / "fake-claude"
        fake.write_text("#!/bin/sh\ncat >/dev/null\nprintf '## Who they trust\\n- barber [language_b_a1_prospect_0001]\\n"
                        "- invented\\n## To test\\n- Marathon (profile)\\n'\n")
        fake.chmod(0o755)
        home = CM.avatar_home("b", "a1", self.ws)
        (home / "culture-map.md").write_text("# hand built\n")
        got = CM.run("b", "a1", ws=self.ws, claude=str(fake))
        self.assertEqual((got["kept"], got["dropped"]), (1, 1))
        out = (home / "culture-map.md").read_text()
        self.assertTrue(out.startswith(CM.MARK))
        self.assertIn("feeds last swept", out.replace("My Feeds: 2 feeds, last swept", "feeds last swept"))
        self.assertIn("1 lines kept, 1 dropped", out)
        self.assertEqual((home / CM.HAND_NAME).read_text(), "# hand built\n")
        self.assertTrue((Path(got["record"]) / "prompt-as-sent.md").is_file())

    def test_dry_run_writes_nothing(self):
        fake = self.ws / "fake-claude"
        fake.write_text("#!/bin/sh\ncat >/dev/null\necho '## Who they trust'\n")
        fake.chmod(0o755)
        home = CM.avatar_home("b", "a1", self.ws)
        (home / "culture-map.md").write_text("# hand built\n")
        CM.run("b", "a1", dry_run=True, ws=self.ws, claude=str(fake))
        self.assertEqual((home / "culture-map.md").read_text(), "# hand built\n")
        self.assertFalse((home / CM.HAND_NAME).exists())
        self.assertFalse((self.ws / "runs/research").exists())


if __name__ == "__main__":
    unittest.main()
