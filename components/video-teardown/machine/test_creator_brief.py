#!/usr/bin/env python3
"""creator_brief.py — the one creator brief file: tags written, page parsed, contract checked.

    python3 components/video-teardown/machine/test_creator_brief.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import creator_brief as CB  # noqa: E402

PAGE = """# The Glow-Up Stack

**One video.** This is one of 1 briefs in your folder — each brief is one video. It's for inspiration: keep the direction, the hooks and the angle, and make it yours.

**Format:** Glow-up selfie stack
**Inspired by:** Dated before clips that snap into one confident after shot.
**Primary product:** Example Brush
**Suggested length:** 15–30 seconds
**Sound:** You lip-sync it and never talk.
**Swipe file:** https://example.com/v/1

**Core Idea**
Your old clips show the skin at its worst. Then one long hold where it is clear. What you washed with could not reach it; the brush does.

**Suggested Hook Directions**
- "My skin was so bad"
- "Day one vs now:"

**Key Story Beats**
1. You open on your worst clip.
2. Two more clips, better each time.
3. The drop: the clear-skin hold.
4. At the sink, the brush in use.
5. You close on the brush in the shower.

**Must-Have Shots**
- The clear-skin hold
- Your real dated before clips
- The brush in use, shown clearly
- The brush in the shower

**Product Points to Include**
Choose the points that best reflect your real experience:
- What you washed with could not reach it. This does.
- Wet it, wash on the bristles, rinse.

**How to Say It**
- Straight, no jokes.

## The script, straight through

Read it as-is if you'd rather, or say it your way — the lines are in order, one per beat. Keep the product points above; everything else is yours.

My skin was so bad

Same me. Check the dates.
"""

PIECE = '```json\n{"piece": {"avatar": "av-one", "sub": "none", "awareness": "problem-aware", "angle": "reach", "format": "glow-up-stack", "lead": "unassigned", "setting": "bathroom", "style_id": "phone-ugc", "lane": "organic"}}\n```\n'


def make_run(root):
    d = Path(root) / "run-a"
    (d / "stages").mkdir(parents=True)
    (d / "stages" / "7b-page.md").write_text(PAGE)
    (d / "stages" / "5-brief.md").write_text("# spec\n\n" + PIECE)
    st = {"slug": "brand-x-swipe-a", "brand": "brandx", "product": "brush",
          "origin_url": "https://example.com/post/1",
          "queue_item": {"swipe_id": "tt-1", "source_url": "https://example.com/post/1"},
          "stages": {"stage5": {"out": "stages/5-brief.md"},
                     "stage7b": {"out": "stages/7b-page.md", "prompt_name": "stage7b-concept-v10-owner.md",
                                 "finished": "2026-11-15T10:00:00Z"}}}
    (d / "run.json").write_text(json.dumps(st))
    return d


class TestCreatorBrief(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = make_run(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_file_writes_one_file_with_every_tag(self):
        out = CB.file(self.run)
        self.assertEqual(out, self.run / "brief--video--creator.md")
        text = out.read_text()
        self.assertTrue(text.startswith("---\ncontract: 1\n"))
        b = CB.read(out)
        for k in CB.TAGS:
            self.assertIn(k, b)
        self.assertEqual(b["brief_id"], "brand-x-swipe-a")
        self.assertEqual(b["brand"], "brandx")
        self.assertEqual(b["product"], "brush")
        self.assertEqual(b["product_name"], "Example Brush")
        self.assertEqual(b["format"], "glow-up-stack")
        self.assertEqual(b["angle"], "reach")
        self.assertEqual(b["avatar"], "av-one")
        self.assertEqual(b["sub"], "")              # "none" is no value
        self.assertEqual(b["lane"], "organic")
        self.assertEqual(b["swipe_link"], "https://example.com/v/1")
        self.assertEqual(b["source_post"], "https://example.com/post/1")
        self.assertEqual(b["swipe_id"], "tt-1")
        self.assertEqual(b["run"], "runs/video-writing/brandx/brand-x-swipe-a")
        self.assertEqual(b["prompt"], "stage7b-concept-v10-owner.md")
        self.assertEqual(b["written"], "2026-11-15")
        self.assertEqual(b["status"], "draft")

    def test_page_parts_parse(self):
        b = CB.read(CB.file(self.run))
        self.assertEqual(b["title"], "The Glow-Up Stack")
        self.assertEqual(b["hooks"], ["My skin was so bad", "Day one vs now:"])
        self.assertEqual(len(b["beats"]), 5)
        self.assertEqual(len(b["shots"]), 4)
        self.assertEqual(len(b["product_points"]), 2)   # the "Choose…" line is not a point
        self.assertIn("could not reach it", b["core_idea"])
        self.assertTrue(b["script"].startswith("My skin was so bad"))
        self.assertTrue(b["page"].startswith("# The Glow-Up Stack"))

    def test_the_page_words_are_untouched(self):
        out = CB.file(self.run)
        self.assertTrue(out.read_text().endswith(PAGE))

    def test_check_clean_and_findings(self):
        out = CB.file(self.run)
        self.assertEqual(CB.check(out, position_text="NEVER: \"left field\" · a results claim"), [])
        bad = CB.check(out, position_text='NEVER: "same me" (0 rows) · "PFB"')
        self.assertTrue(any("same me" in x for x in bad))

    def test_never_list_drops_counts_and_rules(self):
        self.assertEqual(CB.never_list('NEVER: "a b" · "c" (all 0 rows) · a results claim inside x'),
                         ["a b", "c"])

    def test_no_page_no_file(self):
        (self.run / "stages" / "7b-page.md").unlink()
        self.assertIsNone(CB.file(self.run))

    def test_check_flags_a_short_brief(self):
        out = CB.file(self.run)
        out.write_text(out.read_text().replace("- \"Day one vs now:\"\n", ""))
        self.assertTrue(any(x.startswith("hooks") for x in CB.check(out, position_text="")))


class TestNoDocOnCreatorRoute(unittest.TestCase):
    """Step 10: the creator route makes no Google Doc; the filed brief is the brief (2026-11-15)."""

    def setUp(self):
        import os
        self.os = os
        self.old = os.environ.pop("VT_CREATOR_DOC", None)
        import importlib.util
        spec = importlib.util.spec_from_file_location("vt_run_doc", Path(__file__).resolve().parent / "run.py")
        self.R = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.R)

    def tearDown(self):
        self.os.environ.pop("VT_CREATOR_DOC", None)
        if self.old is not None:
            self.os.environ["VT_CREATOR_DOC"] = self.old

    def test_creator_route_makes_no_doc(self):
        self.assertFalse(self.R.doc_on_run({"production_route": "creator"}))

    def test_flag_restores_the_doc(self):
        self.os.environ["VT_CREATOR_DOC"] = "1"
        self.assertTrue(self.R.doc_on_run({"production_route": "creator"}))

    def test_other_routes_unchanged(self):
        for route in ("ai", "founder", "", None):
            self.assertTrue(self.R.doc_on_run({"production_route": route}))


class TestLeadCommentStrip(unittest.TestCase):
    """A brief with two stamp comments kept 3 KB of 19 KB at stage 7 (2026-11-15)."""

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("vt_run_strip", Path(__file__).resolve().parent / "run.py")
        self.R = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.R)

    def test_two_stamps_keep_the_whole_brief(self):
        two = "<!-- swipe-match: PASSED -->\n<!-- brief-read: APPROVED -->\n**Swipe file:** x\n\n# T\n\nbody\n\n<!-- manifest -->\n\n## MANIFEST\n"
        self.assertEqual(self.R.strip_lead_comment(two), two)

    def test_one_leading_comment_still_comes_off(self):
        self.assertEqual(self.R.strip_lead_comment("<!-- chatter -->\n\n# T\n"), "# T\n")
        self.assertEqual(self.R.strip_lead_comment("<!-- two\nlines -->\n\n# T\n"), "# T\n")
        self.assertEqual(self.R.strip_lead_comment("# T\n\n<!-- later -->\n\nx"), "# T\n\n<!-- later -->\n\nx")


class TestCardFormats(unittest.TestCase):
    def test_cards_heading_is_the_script(self):
        page = PAGE.replace("## The script, straight through", "## The cards, straight through").replace(
            "Read it as-is if you'd rather, or say it your way — the lines are in order, one per beat. Keep the product points above; everything else is yours.",
            "Nothing is spoken in this format — these are the words on screen, in order.")
        parts = CB.parse_page(page)
        self.assertTrue(parts["script"].startswith("My skin was so bad"))
        self.assertEqual(len(parts["how_to_say"]), 1)       # the cards never leak into a section above


class TestLiftedLineQuotes(unittest.TestCase):
    def test_inner_quotes_survive(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("vt_run_q", Path(__file__).resolve().parent / "run.py")
        R = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(R)
        self.assertEqual(R._unquote('"A" then "B"'), '"A" then "B"')
        self.assertEqual(R._unquote('"Face brush effect:"'), "Face brush effect:")
        self.assertEqual(R._unquote("plain"), "plain")



class TestAuditFixesProse(unittest.TestCase):
    """Audit v13 writes the verdict as prose, not a table; the re-run must still read it."""

    def test_prose_verdict_names_its_pass(self):
        t = ("## VERDICT\n\n**RE-RUN 4e, the close pass.** Two things must change:\n\n"
             "1. **Swap the card.**\n2. **Cut the hedge.**\n\n## CHECK TABLE\n\n| 3 | Register | PASS | ok |\n")
        f = CB.audit_fixes(t)
        self.assertEqual([x["at"] for x in f], ["4e"])
        self.assertIn("Swap the card", f[0]["fix"])
        self.assertNotIn("Register", f[0]["fix"])

    def test_bold_check_table_is_not_a_fix(self):
        t = ("**VERDICT — RE-RUN**\n\n**Re-run 4c.** Fix the beat.\n\n---\n\n**CHECK TABLE**\n\n"
             "| 3 | Register | PASS | ok |\n")
        self.assertEqual([x["at"] for x in CB.audit_fixes(t)], ["4c"])

    def test_ship_has_no_fixes(self):
        self.assertEqual(CB.audit_fixes("## VERDICT\n\n**SHIP**\n"), [])

if __name__ == "__main__":
    unittest.main()
