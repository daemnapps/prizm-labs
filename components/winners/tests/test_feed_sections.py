"""The feed's further sections: the top ad per angle, the desk's calls, the send-back reasons and the score per
prompt version. Offline, every file in a scratch root.

    /usr/bin/python3 components/winners/tests/test_feed_sections.py
"""
import json, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import bank  # noqa: E402
import feed  # noqa: E402
import feed_sections as FS  # noqa: E402
from test_bank import audit, row, w  # noqa: E402

HOOKS = """## V1

- **Source:** "comes right back" is from "It fades a little, then comes right back." (a review)
- **Source:** "eight years" is from "eight years in the same place" [0556]

## V2

- **Source:** "comes right back" is from "It fades a little, then comes right back." (a review)
"""


class Base(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        rows = [row(1, "Script 30", ["111"], 1000, 50, 1500), row(2, "Touch Face", ["221"], 800, 20, 900),
                row(3, "Plain", ["331"], 600, 10, 500), row(4, "Second of its angle", ["441"], 900, 5, 300),
                row(5, "No sale", ["551"], 50, 0, 0)]
        self.a1 = audit(self.root, "2025", "2025-01-01", "2026-11-02", rows)
        bank.main(["--brand", "acme", "--root", str(self.root), "--audit", str(self.a1)])
        self.home = self.root / "runs/winners/acme"
        w(self.home, "tags.json", {"Script 30": {"on_screen": "Skin close-up", "message": "Hidden cause"},
                                   "Touch Face": {"on_screen": "Creator using the product", "message": "A trick"},
                                   "Second of its angle": {"on_screen": "Actor skit", "message": "hidden cause"},
                                   "No sale": {"on_screen": "Sale graphic", "message": "A sale"}})

    def tearDown(self):
        self._t.cleanup()

    def bank(self):
        return bank.load_bank(self.home / "bank.json", "acme")

    def save(self, b):
        bank.write(self.root, b)

    def text(self):
        return FS.text(self.root, "acme")


class TopAdPerAngle(Base):
    def test_one_row_per_angle_the_top_by_purchases_with_its_type(self):
        rows = FS.angle_rows(self.root, "acme", self.bank())
        self.assertEqual([(e["angle"], e["id"]) for e in rows],
                         [("Hidden cause", "acme-111"), ("A trick", "acme-221"), (None, "acme-331")])
        self.assertEqual((rows[0]["type"], rows[0]["format"], rows[0]["angle_from"]), ("Skin close-up", "Video", "tag"))
        self.assertNotIn("acme-441", [e["id"] for e in rows])          # second of its angle, any spelling of the tag
        self.assertNotIn("acme-551", [e["id"] for e in rows])          # no purchase: not the top of anything

    def test_the_briefs_own_angle_and_concept_win_over_the_tag(self):
        b = self.bank()
        r = next(x for x in b["rows"] if x["id"] == "acme-221")
        r["brief_key"], r["run"] = "acme_widget_brief-0002", "runs/video-writing/acme/a-run"
        self.save(b)
        w(self.root, "components/image-teardown/briefs.json", {"briefs": {"acme_widget_brief-0002": {
            "key": "acme_widget_brief-0002", "angle": "never-the-tool", "concept": "one face, two ages"}}})
        w(self.root, "runs/video-writing/acme/a-run/stages/4b-hooks.md", HOOKS)
        e = next(x for x in FS.angle_rows(self.root, "acme", self.bank()) if x["id"] == "acme-221")
        self.assertEqual((e["angle"], e["angle_from"], e["concept"]), ("never-the-tool", "brief", "one face, two ages"))
        self.assertEqual(len(e["words"]), 2)                           # the same line twice is listed once
        self.assertIn("It fades a little, then comes right back.", e["words"][0])
        md = self.text()
        self.assertIn("- Angle: never-the-tool (from the brief's record)", md)
        self.assertIn("- Concept: one face, two ages", md)
        self.assertIn("- Customer words traced by its writing run:", md)

    def test_a_winner_leads_its_angle_over_a_bigger_candidate(self):
        b = self.bank()
        b["bar"]["max_cpa"] = 50                                       # 111 (CPA 20) clears; 441 (CPA 180) does not
        self.save(b)
        rows = FS.angle_rows(self.root, "acme", self.bank())
        self.assertEqual((rows[0]["id"], rows[0]["state"]), ("acme-111", "winner"))
        self.assertIn("- State: winner", self.text())

    def test_a_creator_videos_read_gives_its_angle_and_type(self):
        b = self.bank()
        b["rows"].append({"id": "acme-trybe-1", "state": "candidate", "name": "creator one", "ad_ids": ["901"],
                          "trybe_id": "abcd1234", "tags": {"format": "Day in the life", "angle": "the routine"},
                          "snapshots": [{"kind": "creator", "since": "2026-10-01", "until": "2026-11-01",
                                         "pulled_at": "2026-11-02", "purchases": 3, "spend": 90, "cpa": 30, "roas": 2}]})
        self.save(b)
        e = next(x for x in FS.angle_rows(self.root, "acme", self.bank()) if x["id"] == "acme-trybe-1")
        self.assertEqual((e["angle"], e["angle_from"], e["type"]), ("the routine", "creator", "Day in the life"))

    def test_the_brands_own_header_wins_and_declares_fills_the_concept(self):
        b = self.bank()
        r = next(x for x in b["rows"] if x["id"] == "acme-221")
        r["brief_key"] = "acme_widget_brief-0003"
        self.save(b)
        w(self.root, "components/image-teardown/briefs.json", {"briefs": {"acme_widget_brief-0003": {
            "key": "acme_widget_brief-0003", "angle": "register-angle", "declares": {"concept": "declared concept"}}}})
        w(self.root, "brands/acme/briefs/briefs.json", {"briefs": [{"brief": "brief-0003", "product": "widget",
                                                                    "angle": "header-angle", "concept": None}]})
        e = next(x for x in FS.angle_rows(self.root, "acme", self.bank()) if x["id"] == "acme-221")
        self.assertEqual((e["angle"], e["angle_from"], e["concept"]), ("header-angle", "brief", "declared concept"))

    def test_customer_words_come_from_the_language_block_too(self):
        b = self.bank()
        r = next(x for x in b["rows"] if x["id"] == "acme-221")
        r["run"] = "runs/video-writing/acme/b-run"
        self.save(b)
        w(self.root, "runs/video-writing/acme/b-run/stages/4b-hooks.md",
          "x\nLANGUAGE USED:\n- x-1 | flakes falling like snow\n- lang_0458 | scaly shins\n\nAfter the block\n- y | not this\n")
        e = next(x for x in FS.angle_rows(self.root, "acme", self.bank()) if x["id"] == "acme-221")
        self.assertEqual(e["words"], ["flakes falling like snow", "scaly shins"])

    def test_words_not_traced_says_why(self):
        self.assertIn("- Customer words: not traced (no writing run behind this ad)", self.text())


class DeskCalls(Base):
    def line(self, at, flag, suggested, call, why):
        return {"at": at, "asof": at[:10], "flag": flag, "kind": "ad", "name": f"ad {flag}", "suggested": suggested,
                "call": call, "why": why, "agreed": suggested == call, "numbers": {"spend": 120.0, "cpa": 60.0}}

    def test_no_call_says_so(self):
        self.assertIn("No call is on record yet (`runs/media-buying/acme/decisions.jsonl`).", self.text())

    def test_every_disagreement_is_listed_with_its_numbers_and_reason(self):
        rows = [self.line("2026-11-01T10:00:00", "F1", "off", "off", "over the line"),
                self.line("2026-11-02T10:00:00", "F2", "off", "keep", "the page is new")]
        w(self.root, "runs/media-buying/acme/decisions.jsonl", "".join(json.dumps(r) + "\n" for r in rows))
        md = self.text()
        self.assertIn("2 calls on record: 1 took the desk's suggestion, 1 did not.", md)
        self.assertIn("- Desk suggested off: 2 calls, 1 agreed, changed to: keep ×1", md)
        self.assertIn("- 2026-11-02 · F2 · ad F2 · desk suggested off, the call was keep · spend $120 · CPA $60 · "
                      "reason on record: the page is new", md)
        self.assertNotIn("ad F1 · desk suggested", md)                 # an agreed call is counted, not listed


class SentBack(Base):
    def test_no_summary_says_so(self):
        self.assertIn("No send-back summary on file (`runs/meta-upload/acme/SENT-BACK.json`).", self.text())

    def test_reasons_are_counted_with_the_step_each_points_at(self):
        w(self.root, "runs/meta-upload/acme/SENT-BACK.json", {"brand": "acme", "total": 2, "since": "2026-11-01",
          "until": "2026-11-03", "reasons": [{"id": "hook", "label": "Hook weak", "count": 2, "last": "2026-11-03",
          "steps": [{"step": 2, "name": "Teardown", "tool": "video-teardown"}], "units": ["ad-b", "ad-a"]}], "steps": []})
        md = self.text()
        self.assertIn("2 send-backs, 2026-11-01 to 2026-11-03.", md)
        self.assertIn("- Hook weak: 2 · points at 2 Teardown (video-teardown) · last 2026-11-03 · ads: ad-b, ad-a", md)

    def test_none_sent_back_says_so(self):
        w(self.root, "runs/meta-upload/acme/SENT-BACK.json", {"brand": "acme", "total": 0, "reasons": [], "steps": []})
        self.assertIn("No ad has been sent back", self.text())


class Score(Base):
    def test_no_score_says_so(self):
        self.assertIn("No score on file yet.", self.text())

    def test_the_newest_score_is_shown_by_hook_and_brief_prompt_version(self):
        old = {"counts": {"ads": 9, "matched": 1}, "data_through": "2026-10-01",
               "by_hook_prompt": [{"version": "old v1", "ads": 1, "spend": 1, "purchases": 0, "cpa": None, "roas": 0}]}
        new = {"counts": {"ads": 10, "matched": 3}, "data_through": "2026-11-03",
               "by_hook_prompt": [{"version": "hook v2", "ads": 2, "spend": 300.0, "purchases": 6, "cpa": 50.0, "roas": 1.5}],
               "by_brief_prompt": [{"version": "brief v7", "ads": 3, "spend": 400.0, "purchases": 6, "cpa": 66.67, "roas": 1.2}]}
        w(self.home, "score/2026-10-20/score.json", old)
        w(self.home, "score/2026-11-04/score.json", new)
        md = self.text()
        self.assertIn("Source: `runs/winners/acme/score/2026-11-04/score.json` (ad data through 2026-11-03). 3 of 10 ads", md)
        self.assertIn("| hook v2 | 2 | $300 | 6 | $50 | 1.50 |", md)
        self.assertIn("| brief v7 | 3 | $400 | 6 | $67 | 1.20 |", md)
        self.assertNotIn("old v1", md)


class InTheFeed(Base):
    def test_the_sections_go_to_their_own_file_and_feed_md_is_unchanged(self):
        self.assertEqual(feed.main(["--brand", "acme", "--root", str(self.root)]), 0)
        md = (self.home / "feed.md").read_text()
        self.assertNotIn("What the results taught", md)          # the live hook prompt reads feed.md whole
        taught = (self.home / "taught.md").read_text()
        order = [taught.index(h) for h in ("# What the results taught", "## Top ad per angle", "## Desk calls",
                                           "## Sent back from the approval page", "## Score per prompt version")]
        self.assertEqual(order, sorted(order))
        feed.main(["--brand", "acme", "--root", str(self.root)])
        self.assertEqual((self.home / "taught.md").read_text(), taught)

    def test_a_source_that_cannot_be_read_costs_one_line_never_the_feed(self):
        w(self.home, "score/2026-11-04/score.json", {"counts": "not a map"})
        md = self.text()
        self.assertIn("## Score per prompt version\n\nNot read (", md)
        self.assertIn("## Top ad per angle", md)
        self.assertEqual(feed.main(["--brand", "acme", "--root", str(self.root)]), 0)

    def test_another_windows_print_stays_the_feeds_own_page(self):
        self.assertNotIn("What the results taught", feed.peek(self.root, "acme", "2025-01-01_2026-11-02"))


if __name__ == "__main__":
    unittest.main()
