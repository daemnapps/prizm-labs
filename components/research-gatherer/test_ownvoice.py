#!/usr/bin/env python3
"""Tests for annotate.py / ownvoice.py / comments.py — no network, no model,
no warehouse, temp folders only (the component's test rule). Both model
calls are stand-ins: a script that prints canned JSON for the intake read,
and a fake labeller module for the language layer's labeller."""
import json
import stat
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from research_gatherer import engine, annotate as A, comments as C, ownvoice as OV   # noqa: E402


class Clean(unittest.TestCase):
    def test_cuts_quoted_mail(self):
        self.assertEqual(A.clean("It works.\nOn Mon, Sep 1, 2026 at 9:00 AM Brand <x@y.com> wrote:\n> old"), "It works.")

    def test_redacts_contact_details(self):
        c = A.clean("Send to 12 Main St Anytown, NJ 00000 or call 555-555-0100, me@mail.com, order #123456")
        for bad in ("00000", "555-555-0100", "me@mail.com", "123456"):
            self.assertNotIn(bad, c)

    def test_signature_after_signoff_cut(self):
        t = "I was not impressed.\nThank you,\nBarb\n7008 Foxglove Drive\nNew Albany, OH 43054"
        self.assertEqual(A.clean(t), "I was not impressed.\nThank you,")

    def test_address_line_dropped(self):
        self.assertEqual(A.clean("I HAVE DEVELOPED A RASH\nTwo Park Avenue | New York, NY 10016"), "I HAVE DEVELOPED A RASH")

    def test_long_sentence_with_street_word_kept(self):
        t = "I have been using your 2 products just shy of 1 month. The problem is that the scrub is way to rough for my old skin."
        self.assertEqual(A.clean(t), t)

    def test_emoji_and_typos_kept(self):
        self.assertEqual(A.clean("2 diff people 😂 lol"), "2 diff people 😂 lol")

    def test_trailing_title_lines_dropped(self):
        self.assertEqual(A.cut_signature("No difference at all.\n\n[name], Ph.D.\nCEO, Example.com", ""), "No difference at all.")
        self.assertEqual(A.cut_signature("I HAVE DEVELOPED A RASH [name]\nPartner", ""), "I HAVE DEVELOPED A RASH [name]")

    def test_cut_and_names(self):
        self.assertEqual(A.cut_signature("No results.\n\nJane, Ph.D.\nCEO", "Jane, Ph.D."), "No results.")
        self.assertEqual(A.remove_names("Thanks Maria, it works", ["Maria"]), "Thanks [name], it works")


class SourceIds(unittest.TestCase):
    """Proposal 5 — the source named by the Naming Standard."""
    def test_facebook_ad_post(self):
        items = [{"text": "Recipe", "commentId": "9", "commentUrl": "https://fb/c/9",
                  "facebookUrl": "https://www.facebook.com/100000000000001/posts/100000000000002"}]
        r = OV.fb_rows(items, {}, "2026-09-28", ads={"100000000000001_100000000000002": "120211"},
                       page_names={"100000000000001": "Brand_X"})[0]
        self.assertEqual((r["source_id"], r["property"], r["ad"]),
                         ("post_facebook_brand-x_100000000000002", "brand-x", "live_meta_120211"))

    def test_instagram_post(self):
        r = OV.ig_rows([{"text": "hi", "id": "1", "postUrl": "https://www.instagram.com/p/AbCdEfGhIjK/"}],
                       "2026-09-28", account="brandx")[0]
        self.assertEqual(r["source_id"], "post_instagram_brandx_AbCdEfGhIjK")

    def test_tiktok_post(self):
        r = C.tiktok_rows([{"text": "2 diff people 😂", "cid": "77",
                            "videoWebUrl": "https://www.tiktok.com/@creator_one0/video/7000000000000000001"}], "2026-09-28")[0]
        self.assertEqual((r["source_id"], r["ref"]), ("post_tiktok_creator-one0_7000000000000000001",
                         "https://www.tiktok.com/@creator_one0/video/7000000000000000001?comment_id=77"))


class Lane(unittest.TestCase):
    """The ruling — first match wins."""
    def test_order_on_file_is_customer(self):
        self.assertEqual(A.decide_lane({"relationship": "ordered"}, {}, {"lane_words": "prospect"}),
                         ("customer", "relationship", None))

    def test_order_on_file_with_exit_is_churned(self):
        self.assertEqual(A.decide_lane({"relationship": "ordered"}, {"exit": "cancel-subscription"}, {})[0], "churned-subscriber")
        self.assertEqual(A.decide_lane({"relationship": "ordered"}, {"exit": "refund-or-return"}, {})[0], "churned-non-subscriber")

    def test_words_decide_otherwise(self):
        self.assertEqual(A.decide_lane({}, {}, {"lane_words": "customer"}), ("customer", "language", "assumed"))
        self.assertEqual(A.decide_lane({}, {}, {"lane_words": "lead"}), ("lead", "language", None))
        self.assertEqual(A.decide_lane({}, {}, {"lane_words": "prospect"}), ("prospect", "language", None))


ROW = dict(kind="comment", text="Recipe please, Jane 😂", said="2026-08-10", pulled="2026-09-28",
           ref="https://www.facebook.com/reel/1/?comment_id=9", post="p_1", source_name="Facebook comment",
           source_type="comment", likes=3, replies=1, relationship="commenter, relationship unknown")
INTAKE = {"keep": True, "exit": "none", "use": ["question"], "topics": ["recipe"], "sub": "not-a-real-sub",
          "ad_use": "question", "names": ["Jane"], "cut": ""}
LABEL = {"awareness": "most-aware", "sophistication": "none", "lane_words": "lead", "why": "Recipe please",
         "origin": "external", "voice": "audience", "model": "sonnet"}


class Entry(unittest.TestCase):
    def test_carries_every_field(self):
        lane, e = A.build_entry(dict(ROW), dict(INTAKE), dict(LABEL), "a", "run1", subs=("real-sub",), today="2026-09-28")
        self.assertEqual(lane, "lead")
        self.assertEqual(e["text"], "Recipe please, [name] 😂")
        self.assertEqual(e["source"], {"name": "Facebook comment", "type": "comment", "date": "2026-09-28",
                                       "ref": ROW["ref"], "question": None, "pulled": "2026-09-28",
                                       "post": "p_1", "said": "2026-08-10"})
        self.assertEqual(e["signal"], {"likes": 3, "replies": 1})
        self.assertEqual(e["awareness"], {"level": "most-aware", "why": "Recipe please", "by": "model",
                                          "model": "sonnet", "date": "2026-09-28"})
        self.assertEqual(e["sophistication"], {"signal": "none", "by": "model", "date": "2026-09-28"})
        self.assertEqual((e["lane_by"], e["lane_words"], e["origin"], e["voice"]), ("language", "lead", "external", "audience"))
        self.assertIsNone(e["sub"])                      # an unknown slug is never written
        self.assertNotIn("author", json.dumps(e))        # no handle stored


def _bank(tmp, files):
    ldir = tmp / "brands" / "b" / "core-avatars" / "a" / "language"
    (ldir / "customers").mkdir(parents=True)
    (ldir / "churned").mkdir()
    for f, ids in files.items():
        (ldir / f).write_text(json.dumps({"schema": 1, "entries": [
            {"id": i, "text": "x", "source": {"ref": f"seen-{i}"}} for i in ids]}, indent=2 if "non" in f else 1))
    return ldir


class Filing(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        engine.configure(workspace=self.tmp)
        self.ldir = _bank(self.tmp, {
            "customers/unsegmented.json": ["language_b_a_customer_0001"], "prospects.json": ["language_b_a_prospect_0001"],
            "churned/subscriber.json": ["language_b_a_churned_0014"], "churned/non-subscriber.json": ["language_b_a_churned_0013"],
            "leads.json": []})

    def test_bank_refs_sees_existing(self):
        self.assertIn("seen-language_b_a_prospect_0001", A.bank_refs(self.ldir))

    def test_shared_lane_word_never_duplicates_and_format_kept(self):
        base = {"text": "x", "source": {"ref": "r"}}
        f = A.file_lanes(self.ldir, {"churned-non-subscriber": [dict(base)], "churned-subscriber": [dict(base)]})
        self.assertEqual(sorted(x["id"] for x in f), ["language_b_a_churned_0015", "language_b_a_churned_0016"])
        self.assertIn('\n  "schema"', (self.ldir / "churned/non-subscriber.json").read_text())

    def test_empty_leads_file_gets_the_standard_name(self):
        f = A.file_lanes(self.ldir, {"lead": [{"text": "link?", "source": {"ref": "r2"}}]})
        self.assertEqual(f[0]["id"], "language_b_a_lead_0001")

    def test_escaped_file_stays_escaped(self):
        p = self.ldir / "prospects.json"
        p.write_text(json.dumps({"schema": 1, "entries": [{"id": "language_b_a_prospect_0001", "text": "café"}]}, indent=1))
        A.file_lanes(self.ldir, {"prospect": [{"text": "ok", "source": {"ref": "r3"}}]})
        self.assertIn("caf\\u00e9", p.read_text())

    def test_report_names_thin_levels(self):
        rep = A.report([{"funnel": "lead", "awareness": {"level": "most-aware"}, "ad_use": "question"}], [], [])
        self.assertIn("problem-aware", rep["thin_levels"])
        self.assertEqual(rep["lanes"], {"lead": 1})

    def test_comments_to_sub_stay_in_the_sub_folder(self):
        sub_dir = self.tmp / "brands" / "b" / "core-avatars" / "a" / "sub-avatars"
        sub_dir.mkdir(parents=True)
        (sub_dir / "sub-01-thin.md").write_text("# thin")
        filed = C.file_to_sub("b", "a", "thin", [("lead", {"text": "link?", "source": {"ref": "r"}})], "2026-09-28")
        self.assertTrue(filed[0]["_file"].startswith("brands/b/core-avatars/a/sub-avatars/sub-01-thin/language/"))
        self.assertEqual(filed[0]["id"], "language_b_a_lead_0001")


class Pipeline(unittest.TestCase):
    """intake read -> labeller -> entries, with both model calls stood in."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        engine.configure(workspace=self.tmp)
        _bank(self.tmp, {"prospects.json": []})
        self.fake = self.tmp / "claude"
        verdicts = [dict(INTAKE, i=0), {"i": 1, "keep": False, "drop_why": "logistics"}]
        self.fake.write_text("#!/bin/sh\ncat > /dev/null\necho '" + json.dumps(verdicts) + "'\n")
        self.fake.chmod(self.fake.stat().st_mode | stat.S_IEXEC)
        self.lab = types.SimpleNamespace(
            label=lambda rows, brand, model: {r["id"]: dict(LABEL) for r in rows},
            origin_of=lambda r: "external", voice_of=lambda r: "audience")

    def test_read_and_sort(self):
        rows = [dict(ROW), dict(ROW, ref="r-2", text="Please change my address")]
        cfg = {"model": "m", "batch": 30}
        entries, dropped, held = A.read_and_sort(rows, "b", "a", "B", "t", cfg, "run1", labeller=self.lab, claude=str(self.fake))
        self.assertEqual((len(entries), len(dropped), len(held)), (1, 1, 0))
        self.assertEqual(entries[0][0], "lead")

    def test_no_label_means_held_not_guessed(self):
        none = types.SimpleNamespace(label=lambda rows, brand, model: {}, origin_of=lambda r: "", voice_of=lambda r: "")
        entries, dropped, held = A.read_and_sort([dict(ROW)], "b", "a", "B", "t", {"model": "m", "batch": 30},
                                                 "run1", labeller=none, claude=str(self.fake))
        self.assertEqual((len(entries), len(held)), (0, 1))

    def test_deep_rows_get_labels_and_standard_ids(self):
        out = A.enrich_deep([{"id": "sub-2026-09-18-0001", "text": "link?", "source": {"date": "2026-09-01"}}],
                            "b", "a", "sub", "B", "m", today="2026-09-28", labeller=self.lab)
        self.assertEqual(out[0]["id"], "language_b_a_lead_0001")
        self.assertEqual((out[0]["source"]["date"], out[0]["source"]["said"]), ("2026-09-28", "2026-09-01"))
        self.assertEqual(out[0]["awareness"]["level"], "most-aware")


if __name__ == "__main__":
    unittest.main(verbosity=1)
