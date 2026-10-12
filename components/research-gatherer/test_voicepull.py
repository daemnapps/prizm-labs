#!/usr/bin/env python3
"""Tests for the free internal-source modes — surveys.py, reviews.py,
interviews.py, voicepull.py — and daily.py's fence and commit filter.
No network, no model, no Keychain, temp folders only (the component's test
rule). The intake read is a stand-in script that keeps every row; the
labeller is a stand-in module."""
import json
import os
import socket
import stat
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from research_gatherer import engine, voicepull as V, surveys as S, reviews as R, interviews as I   # noqa: E402
import daily as D   # noqa: E402

LABEL = {"awareness": "most-aware", "sophistication": "none", "lane_words": "customer", "why": "w"}
LAB = types.SimpleNamespace(label=lambda rows, brand, model: {r["id"]: dict(LABEL) for r in rows},
                            origin_of=lambda r: "external", voice_of=lambda r: "audience")
KEEP_ALL = """#!/usr/bin/env python3
import sys, re, json
rows = [int(m) for m in re.findall(r"^(\\d+)\\. \\[", sys.stdin.read(), re.M)]
print(json.dumps([{"i": i, "keep": True, "exit": "none", "use": ["result"], "topics": ["t"],
                   "ad_use": "proof", "names": [], "cut": ""} for i in rows]))
"""

CSV = """Timestamp,Email Address,What do you like most about the device?,Leave any other comments.
4/9/2023 11:06:24,old@x.com,Old answer that is already in,none
9/20/2026 10:00:00,a@x.com,It cleared my razor bumps in a week,N/A
9/25/2026 10:25:58,b@x.com,Feels like a barber did it,Keep it up
"""


def ws_with_bank(tmp, brand="b", avatar="a", pulls=None):
    engine.configure(workspace=tmp)
    ldir = tmp / "brands" / brand / "core-avatars" / avatar / "language"
    for f in ("customers/unsegmented.json", "leads.json", "prospects.json",
              "churned/subscriber.json", "churned/non-subscriber.json"):
        (ldir / f).parent.mkdir(parents=True, exist_ok=True)
        (ldir / f).write_text(json.dumps({"schema": 1, "entries": []}, indent=1))
    ops = tmp / "brands" / brand / "operations"
    ops.mkdir(parents=True, exist_ok=True)
    (ops / "brand.json").write_text(json.dumps({"brand": brand, "label": "B"}))
    (ops / "language-pulls.json").write_text(json.dumps(dict({"language_avatar": avatar}, **(pulls or {}))))
    fake = tmp / "claude"
    fake.write_text(KEEP_ALL)
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    return ldir, str(fake)


def entries(ldir):
    out = []
    for f in ldir.rglob("*.json"):
        out += [dict(e, _f=str(f.relative_to(ldir))) for e in json.loads(f.read_text()).get("entries", [])]
    return out


class Surveys(unittest.TestCase):
    SV = {"survey": "customers", "name": "Brand Improvement (Customers)", "sheet": "SHEET", "relationship": "ordered"}

    def test_rows_skip_email_and_trivial_and_old(self):
        rows, newest = S.rows_from_csv(CSV, self.SV, "b", "B", "2026-09-29", since="2026-08-25")
        self.assertEqual([r["text"] for r in rows], ["It cleared my razor bumps in a week", "Feels like a barber did it",
                                                     "Keep it up"])
        self.assertNotIn("@x.com", json.dumps(rows))
        self.assertEqual(newest.strftime("%Y-%m-%d"), "2026-09-25")
        r = rows[0]
        self.assertEqual((r["source_id"], r["relationship"], r["said"]), ("survey_b_customers", "ordered", "2026-09-20"))
        self.assertTrue(r["question"].startswith("q-01_what-do-you-like-most"))
        self.assertEqual(r["item"], S.rows_from_csv(CSV, self.SV, "b", "B", "x", since="2026-08-25")[0][0]["item"])

    def test_question_reuses_the_banks_number(self):
        q = S.question_ids(["What do you like most about the device?"], {"what-do-you-like-most-about-the-device": "q-07_what-do-you-like-most-about-the-device"})
        self.assertEqual(q[0], "q-07_what-do-you-like-most-about-the-device")
        self.assertEqual(S.question_ids(["Brand new?"], {"x": "q-03_x"})[0], "q-04_brand-new")

    def test_cursor_is_a_timestamp(self):
        rows, _ = S.rows_from_csv(CSV, self.SV, "b", "B", "t", since="2026-09-20T10:00:00")
        self.assertEqual(len(rows), 2)

    def test_run_files_then_nothing_new_and_dry_run_files_nothing(self):
        tmp = Path(tempfile.mkdtemp())
        ldir, fake = ws_with_bank(tmp, pulls={"surveys": [dict(self.SV, lane="churned", since="2026-08-25")]})
        self.assertEqual(S.main(["--brand", "b", "--dry-run"], fetch=lambda s: (CSV, None), labeller=LAB, claude=fake), 0)
        self.assertEqual(entries(ldir), [])
        self.assertFalse((tmp / "runs/research/b/surveys-state.json").exists())
        S.main(["--brand", "b"], fetch=lambda s: (CSV, None), labeller=LAB, claude=fake)
        got = entries(ldir)
        self.assertEqual(len(got), 3)
        self.assertTrue(all(e["_f"] == "churned/non-subscriber.json" for e in got))   # the refund lane
        self.assertTrue(all(e["origin"] == "internal" and e["source"]["item"] for e in got))
        self.assertTrue(got[0]["id"].startswith("language_b_a_churned_"))
        st = json.loads((tmp / "runs/research/b/surveys-state.json").read_text())
        self.assertEqual(st["customers"]["last_response"], "2026-09-25T10:25:58")
        S.main(["--brand", "b"], fetch=lambda s: (CSV, None), labeller=LAB, claude=fake)
        self.assertEqual(len(entries(ldir)), 3)                                        # nothing twice
        self.assertTrue(list((tmp / "runs/research/b").glob("surveys-*/page.html")))

    def test_unreadable_sheet_is_named_not_guessed(self):
        tmp = Path(tempfile.mkdtemp())
        ldir, fake = ws_with_bank(tmp, pulls={"surveys": [self.SV]})
        S.main(["--brand", "b"], fetch=lambda s: (None, "cannot open"), labeller=LAB, claude=fake)
        self.assertEqual(entries(ldir), [])


JUNIP = [{"id": 11, "rating": 5, "title": "Wow", "body": "My bumps are gone", "created_at": "2026-09-01T10:00:00Z",
          "verified_buyer": True, "target_title": "the device - Black"},
         {"id": 12, "rating": 2, "title": "Meh", "body": "", "created_at": "2026-09-02T10:00:00Z",
          "verified_buyer": False, "target_title": "WAR"},
         {"id": 10, "rating": 5, "title": "", "body": "Old one", "created_at": "2026-06-01T10:00:00Z", "verified_buyer": True}]


class Reviews(unittest.TestCase):
    def test_junip_rows(self):
        rows, newest = R.rows_from_reviews("junip", JUNIP, "b", "B", "2026-09-29", since="2026-07-01")
        self.assertEqual([r["text"] for r in rows], ["My bumps are gone", "Meh"])
        self.assertEqual((rows[0]["relationship"], rows[0]["rating"], rows[0]["item"], rows[0]["source_id"]),
                         ("ordered", 5, "11", "review_junip_b"))
        self.assertNotEqual(rows[1]["relationship"], "ordered")
        self.assertEqual(newest, "2026-09-02T10:00:00Z")

    def test_judgeme_rows(self):
        rows, _ = R.rows_from_reviews("judgeme", [{"id": 5, "rating": 4, "body": "Soft skin", "verified": "buyer",
                                                    "created_at": "2026-09-01T00:00:00Z", "product_title": "Scrub"}],
                                      "b", "B", "t")
        self.assertEqual((rows[0]["relationship"], rows[0]["source_id"]), ("ordered", "review_judgeme_b"))

    def test_junip_pages(self):
        pages = [{"product_reviews": JUNIP[:1], "meta": {"page": {"after": "x"}}}, {"product_reviews": JUNIP[1:], "meta": {}}]
        calls = []
        got = R.pull_junip({}, "k", get=lambda u, h=None: calls.append((u, h)) or pages[len(calls) - 1])
        self.assertEqual(len(got), 3)
        self.assertIn("page%5Bafter%5D=x", calls[1][0])
        self.assertEqual(calls[0][1], {"Junip-Store-Key": "k"})

    def test_run_rating_in_signal_and_cursor(self):
        tmp = Path(tempfile.mkdtemp())
        ldir, fake = ws_with_bank(tmp, pulls={"reviews": {"platform": "junip", "key": "TEST_JUNIP_KEY", "since": "2026-07-01"}})
        os.environ["TEST_JUNIP_KEY"] = "k"
        try:
            R.main(["--brand", "b"], get=lambda u, h=None: {"product_reviews": JUNIP, "meta": {}}, labeller=LAB, claude=fake)
        finally:
            del os.environ["TEST_JUNIP_KEY"]
        got = {e["source"]["item"]: e for e in entries(ldir)}
        self.assertEqual(got["11"]["signal"]["rating"], 5)
        self.assertEqual((got["11"]["_f"], got["11"]["lane_by"]), ("customers/unsegmented.json", "relationship"))
        self.assertEqual(got["12"].get("attribution"), "assumed")                       # words, not an order
        self.assertEqual(json.loads((tmp / "runs/research/b/reviews-state.json").read_text())["last_review"],
                         "2026-09-02T10:00:00Z")

    def test_missing_key_pulls_nothing(self):
        tmp = Path(tempfile.mkdtemp())
        ldir, fake = ws_with_bank(tmp, pulls={"reviews": {"platform": "judgeme", "key": "NOT_A_REAL_KEY_NAME_X"}})
        real = V.key
        V.key = lambda n: None
        try:
            self.assertEqual(R.main(["--brand", "b"], get=lambda *a, **k: self.fail("no call without a key")), 0)
        finally:
            V.key = real
        self.assertEqual(entries(ldir), [])


TRANSCRIPT = """---
kind: interview
date: 2026-09-30
---
WEBVTT

1
00:00:01.000 --> 00:00:04.000
<v Sam Lee>Thanks for joining, tell me about your skin.</v>

2
00:00:05.000 --> 00:00:09.000
<v Robin>I have brown spots all over my legs and nothing works.</v>

3
00:00:10.000 --> 00:00:12.000
<v Robin>I tried everything under the sun.</v>
<v Robin>Yes.</v>
"""


class Interviews(unittest.TestCase):
    def test_turns_joined_and_labels(self):
        t = I.turns("**Sam:** Hi there\nRobin: I have spots\non my legs\n[00:12]\nSam: ok")
        self.assertEqual(t, [("Sam", "Hi there"), ("Robin", "I have spots on my legs"), ("Sam", "ok")])

    def test_customer_turns_only(self):
        rows, meta, why = I.rows_from_transcript("x/2026-09-30-robin.md", TRANSCRIPT, "b", "t", company=["Sam"])
        self.assertIsNone(why)
        self.assertEqual(len(rows), 1)                    # Robin's turns merge; "Yes." joins them
        self.assertIn("brown spots", rows[0]["text"])
        self.assertNotIn("Robin", json.dumps(rows))
        self.assertEqual((rows[0]["source_id"], rows[0]["relationship"]), ("interview_b_2026-09-30", "ordered"))

    def test_named_customers_only(self):
        rows, _, _ = I.rows_from_transcript(
            "f.md", "---\ncustomers: [Ann]\n---\nAnn: I love it so much honestly\nBo: This is a long answer too", "b", "t")
        self.assertEqual([r["text"] for r in rows], ["I love it so much honestly"])

    def test_no_side_named_is_held(self):
        rows, _, why = I.rows_from_transcript("f.md", "Ann: I love it so much honestly", "b", "t")
        self.assertEqual(rows, [])
        self.assertTrue(why)

    def test_panel_kind(self):
        rows, _, _ = I.rows_from_transcript("2025-03-26-panel.md", "---\nkind: panel\ncompany: [Host]\n---\nTara: that glass skin look is what I want",
                                            "b", "t")
        self.assertEqual((rows[0]["source_id"], rows[0]["source_type"]), ("panel_b_2025-03-26", "focus-group"))
        self.assertNotEqual(rows[0]["relationship"], "ordered")

    def test_run_reads_a_file_once(self):
        tmp = Path(tempfile.mkdtemp())
        ldir, fake = ws_with_bank(tmp, pulls={"interviews": {"inbox": "core-avatars/a/language/evidence/inbox",
                                                             "company_speakers": ["Sam"]}})
        inbox = ldir / "evidence" / "inbox"
        inbox.mkdir(parents=True)
        (inbox / "README.md").write_text("Sam: this is not a transcript at all")
        (inbox / "2026-09-30-robin.md").write_text(TRANSCRIPT)
        I.main(["--brand", "b", "--dry-run"], labeller=LAB, claude=fake)
        self.assertFalse((tmp / "runs/research/b/interviews-state.json").exists())
        I.main(["--brand", "b"], labeller=LAB, claude=fake)
        self.assertEqual(len(entries(ldir)), 1)
        st = json.loads((tmp / "runs/research/b/interviews-state.json").read_text())
        self.assertEqual(list(st["ingested"]), ["brands/b/core-avatars/a/language/evidence/inbox/2026-09-30-robin.md"])
        I.main(["--brand", "b"], labeller=LAB, claude=fake)
        self.assertEqual(len(entries(ldir)), 1)


class Extras(unittest.TestCase):
    def test_forced_churn_and_origin(self):
        lane, e = V.lay_extras("customer", {"funnel": "customer", "speaker": "customer", "source": {}, "lane_by": "relationship"},
                               {"force_lane": "churned", "item": "r1", "rating": 3})
        self.assertEqual((lane, e["funnel"], e["origin"], e["source"]["item"], e["signal"]["rating"]),
                         ("churned-non-subscriber", "churned", "internal", "r1", 3))

    def test_cancelled_subscription_stays_subscriber(self):
        lane, _ = V.lay_extras("churned-subscriber", {"funnel": "churned", "speaker": "churned", "source": {}}, {"force_lane": "churned"})
        self.assertEqual(lane, "churned-subscriber")

    def test_language_pulls_laid_over_brand_json(self):
        tmp = Path(tempfile.mkdtemp())
        ws_with_bank(tmp, pulls={"reviews": {"platform": "junip"}})
        bj = V.brand_json("b")
        self.assertEqual((bj["label"], bj["reviews"]["platform"], V.avatar_for("b", bj)), ("B", "junip", "a"))


class Daily(unittest.TestCase):
    def test_fence_blocks_apify_hosts(self):
        real = socket.getaddrinfo
        fake_engine = types.SimpleNamespace(apify_layer=lambda: "live")
        try:
            D.fence_apify(fake_engine)
            with self.assertRaises(D.ApifyBlocked):
                socket.getaddrinfo("api.apify.com", 443)
            with self.assertRaises(D.ApifyBlocked):
                fake_engine.apify_layer()
            self.assertIn("api.apify.com", D.REACHED)
        finally:
            socket.getaddrinfo = real
            D.REACHED.clear()

    def test_only_the_runs_files_are_committed(self):
        ok = ["brands/b/core-avatars/a/language/leads.json", "brands/b/core-avatars/language-sources.json",
              "runs/research/b/surveys-2026-09-29-0530/page.html", "runs/language-layer/_system/BANK.md"]
        no = ["brands/b/operations/brand.json", "components/x.py", "brands/b/core-avatars/a/avatar.md"]
        for p in ok:
            self.assertTrue(any(rx.match(p) for rx in D.COMMIT_PATHS), p)
        for p in no:
            self.assertFalse(any(rx.match(p) for rx in D.COMMIT_PATHS), p)

    def test_produced_keeps_the_first_path_whole(self):
        import subprocess
        tmp = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q", str(tmp)], check=True)
        f = tmp / "brands/b/core-avatars/a/language/leads.json"
        f.parent.mkdir(parents=True)
        f.write_text("{}")
        subprocess.run(["git", "-C", str(tmp), "add", "."], check=True)
        subprocess.run(["git", "-C", str(tmp), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"], check=True)
        f.write_text('{"a": 1}')                                   # " M path" — a leading space
        (tmp / "components").mkdir()
        (tmp / "components/x.py").write_text("")
        ok, other = D.produced(tmp)
        self.assertEqual((ok, other), (["brands/b/core-avatars/a/language/leads.json"], ["components/x.py"]))

    def test_summary_md(self):
        md = D.summary_md({"run": "r", "brands": {"b": [dict(mode="reviews", pulled=3, new=2, filed=2, dropped=0, held=0,
                                                              missing=["MISSING — key"])]}})
        self.assertIn("| reviews | 3 | 2 | 2 | 0 | 0 | MISSING — key |", md)


if __name__ == "__main__":
    unittest.main(verbosity=1)
