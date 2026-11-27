#!/usr/bin/env python3
"""python3 tests/test_session_teardown.py — stdlib unittest, no network, no model call (a fake model answers)."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "machine"))
sys.path.insert(0, str(ROOT.parent / "run-kit"))
import friction        # noqa: E402
import leak            # noqa: E402
import money           # noqa: E402
import record          # noqa: E402
import run as runner   # noqa: E402
import sections        # noqa: E402
import source          # noqa: E402
import timeline        # noqa: E402
from marketing_chain_checks import Held   # noqa: E402

SAMPLE = ROOT / "samples" / "basic"


STRUCTURE = {"format": "sales page", "sections": [
    {"n": 1, "job": "names the problem and promises a result", "form": "headline + subhead", "words": 30,
     "pictures": [{"does": "shows the result"}], "button": "none"},
    {"n": 2, "job": "explains the problem and that it is common", "form": "paragraphs", "words": 70,
     "pictures": [], "button": "none"},
    {"n": 3, "job": "a customer's result", "form": "quote / testimonial", "words": 25, "pictures": [], "button": "none"},
    {"n": 4, "job": "what is inside", "form": "bulleted list", "words": 80, "pictures": [{"does": "the ingredients"}],
     "button": "opens the ingredient list"},
    {"n": 5, "job": "how to use it", "form": "numbered steps", "words": 60, "pictures": [{"does": "the steps"}],
     "button": "none"},
    {"n": 6, "job": "the choice of amounts and the ask", "form": "offer box", "words": 40,
     "pictures": [{"does": "the product"}], "button": "buy the most chosen amount"},
    {"n": 7, "job": "removes the risk", "form": "paragraphs", "words": 25, "pictures": [], "button": "none"},
    {"n": 8, "job": "answers doubts", "form": "FAQ", "words": 50, "pictures": [], "button": "none"}]}
CALLS = []


def fake_model(prompt, model):
    """Answers like the model would, using only ids that appear in the prompt."""
    import re
    CALLS.append(prompt.splitlines()[0])
    ids = re.findall(r"### (s\d{4}) · LEFT", prompt) or re.findall(r"(s\d{4}) at", prompt)
    if prompt.startswith("# PAGE TEARDOWN"):
        return "```json\n" + json.dumps(STRUCTURE) + "\n```"
    if prompt.startswith("# Teardown"):
        return json.dumps({"findings": [
            {"finding": "tapped See reviews and left without scrolling past the price", "section": "§2 paragraphs",
             "kind": "swing", "fix_kind": "", "fix": "", "left": 12, "converted": 1,
             "moments": [{"recording_id": ids[0], "at_s": 14, "note": "taps reviews, leaves"}]},
            {"finding": "tapped See reviews and nothing happened", "section": "§2 paragraphs", "kind": "fix",
             "type": "bug", "effort": "s", "element": "See reviews",
             "fix": "Point the See reviews link at the reviews on the page", "left": 10,
             "converted": 0, "moments": []},
            {"finding": "rage-tapped the price", "section": "§2 paragraphs", "kind": "swing", "left": 6,
             "converted": 0, "moments": []}],
            "notes": "sample"})
    return "Here it is:\n" + json.dumps({"swings": [
        {"type": "design",
         "hypothesis": "Rage at the price → show the amounts sooner, because 6 of 30 rage-tapped it",
         "change": "Move §6 offer box up under §2 paragraphs; keep the offer and the button unchanged.",
         "variant_offer": "1", "clips": [], "from": [3]},
        {"type": "design",
         "hypothesis": "Move reviews above the price → more reach checkout, because 12 of 30 left after tapping reviews",
         "change": "Put three short reviews directly above the price block; keep the price and button unchanged.",
         "variant_offer": "1",
         "clips": [{"recording_id": ids[0], "at_s": 14, "note": "taps reviews, leaves"},
                   {"recording_id": "not-a-picked-recording", "at_s": 3, "note": "must be dropped"}],
         "from": [1]}]})


class Leak(unittest.TestCase):
    def test_loss_counts_on_the_page_left_from(self):
        views = [{"session": "a", "page_id": "b_p_quiz", "step": "landing", "at": "2026-11-01T00:00:00"},
                 {"session": "a", "page_id": "b_p_offer", "step": "landing", "at": "2026-11-01T00:01:00"},
                 {"session": "b", "page_id": "b_p_quiz", "step": "landing", "at": "2026-11-01T00:00:00"},
                 {"session": "c", "page_id": "b_p_quiz", "step": "landing", "at": "2026-11-01T00:00:00"},
                 {"session": "c", "page_id": "b_p_offer", "step": "landing", "at": "2026-11-01T00:02:00"}]
        outs = [{"session": "c", "event": "checkout_reached", "revenue": 0, "at": "2026-11-01T00:03:00"},
                {"session": "c", "event": "purchase", "revenue": 50, "at": "2026-11-01T00:05:00"}]
        got = {p["page_id"]: p for p in leak.find(views, outs, min_visitors=1)["pages"]}
        self.assertEqual(got["b_p_quiz"]["left_sessions"], ["b"])        # a moved on: not lost on the quiz
        self.assertEqual(got["b_p_offer"]["left_sessions"], ["a"])
        self.assertEqual(got["b_p_offer"]["converted_sessions"], ["c"])
        self.assertEqual(got["b_p_offer"]["at_stake"], 50.0)             # 1 lost × $50 per reacher

    def test_small_pages_are_not_ranked(self):
        views = [{"session": "a", "page_id": "b_p_x", "step": "landing", "at": "2026-11-01T00:00:00"}]
        self.assertFalse(leak.find(views, [], min_visitors=200)["pages"][0]["ranked"])

    def test_checkout_and_later_steps_are_not_leaks(self):
        views = [{"session": "a", "page_id": "b_p_checkout", "step": "checkout", "at": "2026-11-01T00:00:00"}]
        self.assertEqual(leak.find(views, [], 1)["pages"], [])


class Timeline(unittest.TestCase):
    def test_reads_like_a_person_watched_it(self):
        ev = [{"at": "2026-11-01T00:00:00+00:00", "event": "$pageview", "url": "https://x.example/p/landing/"},
              {"at": "2026-11-01T00:00:09+00:00", "event": "$rageclick", "text": "$57"},
              {"at": "2026-11-01T00:00:20+00:00", "event": "$pageleave", "url": "https://x.example/p/landing/", "scroll": 31}]
        tl = timeline.build("s1", ev, {"clicks": 3, "active_s": 15})
        self.assertIn('   9s  RAGE-TAPPED "$57"', tl["lines"])
        self.assertIn("scrolled 31%", tl["lines"][2])
        self.assertEqual(tl["ended"], "left")

    def test_purchase_ends_as_bought(self):
        ev = [{"at": "2026-11-01T00:00:00", "event": "checkout_reached"}, {"at": "2026-11-01T00:01:00", "event": "purchase"}]
        self.assertEqual(timeline.build("s", ev)["ended"], "bought")


class Contract(unittest.TestCase):
    def good(self):
        return {"id": "b_p_x_hyp-1", "kind": "hypothesis", "page_id": "brand_place_page", "type": "design",
                "control": {"version": "v1", "path": "/p/", "offer": "1"}, "variant_offer": "1",
                "hypothesis": "Change X → more reach checkout, because Y", "change": "Move the reviews above the price",
                "primary_metric": "checkout_reached", "confirm_metric": "purchase",
                "rank": 1, "value_usd_month": 1200.0, "basis": "gap 40% × 600 lost × $20 per reacher",
                "stop": runner.definitions()["stop"],
                "evidence": {"leak": {"step": "landing", "visitors": 10, "reached_next": 2, "revenue_per_visitor": 1,
                                      "window": "", "source": "all", "device": "all"},
                             "recordings": {"left": 30, "converted": 10},
                             "patterns": [{"pattern": "p", "left": 12, "converted": 1}], "clips": [], "clarity": None},
                "by": {}, "status": "draft"}

    def test_good_record_passes(self):
        self.assertEqual(record.check(self.good()), [])

    def test_design_test_cannot_change_the_offer(self):
        r = self.good(); r["variant_offer"] = "2"
        self.assertIn("a design test keeps the control's offer", record.check(r))

    def test_offer_test_must_change_the_offer(self):
        r = self.good(); r["type"] = "offer"
        self.assertIn("an offer test changes the offer", record.check(r))

    def test_counts_cannot_exceed_recordings_read(self):
        r = self.good(); r["evidence"]["patterns"][0]["left"] = 31
        self.assertTrue(any("exceed" in b for b in record.check(r)))

    def test_never_written_approved(self):
        r = self.good(); r["status"] = "approved"
        self.assertTrue(any("draft" in b for b in record.check(r)))

    def test_a_swing_carries_rank_value_and_basis(self):
        for k, v in (("rank", 4), ("value_usd_month", -1), ("basis", "")):
            r = self.good(); r[k] = v
            self.assertTrue(record.check(r), k)

    def test_no_evidence_no_hypothesis(self):
        r = self.good(); r["evidence"]["patterns"] = []
        self.assertTrue(any("evidence" in b for b in record.check(r)))


class Run(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_sample_run_writes_a_valid_hypothesis(self):
        out = runner.run("sample", source.Sample(SAMPLE), label="t1", ask=fake_model, model="test-model", out=self.tmp / "t1")
        rec = json.loads((out / "hypothesis.json").read_text())
        self.assertEqual(record.check(rec), [])
        self.assertEqual(rec["page_id"], "sample_body-cpk_landing")              # the offer page leaks most
        self.assertEqual(rec["evidence"]["recordings"], {"left": 30, "converted": 10})
        self.assertEqual([c["recording_id"] for c in rec["evidence"]["clips"]].count("not-a-picked-recording"), 0)
        self.assertEqual(rec["by"]["model"], "test-model")
        for f in ("leak.json", "picked.json", "structure--sent.md", "structure.json", "teardown--sent.md",
                  "hypothesis--sent.md", "teardown.json", "run.json", "page.html", "check.json",
                  "deliverable/hypothesis.json", "moments/moments.json", "moments/MOMENT-MAP.md", "fixes.json",
                  "deliverable/fixes.json", "swings/swing-1/hypothesis.json", "swings/swing-2/hypothesis.json"):
            self.assertTrue((out / f).is_file(), f)
        self.assertEqual(len(list((out / "timelines").iterdir())), 40)
        self.assertEqual(json.loads((out / "check.json").read_text())["delivery"]["result"], "pass")
        self.assertEqual((out / "deliverable" / "hypothesis.json").read_text(), (out / "hypothesis.json").read_text())

    def test_dry_run_calls_no_model(self):
        def boom(p, m):
            raise AssertionError("model called in a dry run")
        out = runner.run("sample", source.Sample(SAMPLE), label="t2", dry_run=True, ask=boom, model="m", out=self.tmp / "t2")
        self.assertFalse((out / "hypothesis.json").exists())
        self.assertIn("dry run", json.loads((out / "run.json").read_text())["state"])
        for f in ("structure--sent.md", "teardown--sent.md", "hypothesis--sent.md"):   # every prompt still filled
            self.assertTrue((out / f).is_file(), f)
        self.assertEqual({k: v["status"] for k, v in json.loads((out / "run.json").read_text())["stages"].items()
                          if k in ("structure", "teardown", "hypothesis")},
                         {"structure": "dry", "teardown": "dry", "hypothesis": "dry"})

    def test_prompts_carry_no_unfilled_field(self):
        out = runner.run("sample", source.Sample(SAMPLE), label="t3", ask=fake_model, model="m", out=self.tmp / "t3")
        for f in ("structure--sent.md", "teardown--sent.md", "hypothesis--sent.md"):
            self.assertNotRegex((out / f).read_text(), r"\{[a-z_]+\}")

    def test_a_page_with_a_running_test_is_skipped(self):
        folder = self.tmp / "s"; shutil.copytree(SAMPLE, folder)
        pages = json.loads((folder / "pages.json").read_text())
        pages["pages"]["sample_body-cpk_landing"]["tests"] = [{"state": "live"}]
        (folder / "pages.json").write_text(json.dumps(pages))
        out = runner.run("sample", source.Sample(folder), label="t4", dry_run=True, ask=fake_model, model="m", out=self.tmp / "t4")
        self.assertEqual(json.loads((out / "run.json").read_text())["page_id"], "sample_body-cpk_quiz")


class Sections(unittest.TestCase):
    """The page under test read into sections (page-teardown's structure) so depth reads as a section."""

    def test_bands_run_top_to_bottom_and_cover_the_page(self):
        pm = sections.page_map(STRUCTURE)
        self.assertEqual([s["label"] for s in pm][5], "§6 offer box")
        self.assertEqual(pm[0]["start"], 0.0)
        self.assertEqual(pm[-1]["end"], 100.0)
        self.assertTrue(all(a["end"] == b["start"] for a, b in zip(pm, pm[1:])))
        self.assertEqual(sections.at(pm, 100)["label"], "§8 FAQ")
        self.assertEqual(sections.at(pm, 0)["label"], "§1 headline + subhead")

    def test_timeline_names_the_section_reached(self):
        pm = sections.page_map(STRUCTURE)
        ev = [{"at": "2026-11-01T00:00:00", "event": "$pageview", "url": "https://x.example/p/landing/"},
              {"at": "2026-11-01T00:00:20", "event": "$pageleave", "url": "https://x.example/p/landing/", "scroll": 31}]
        tl = timeline.build("s1", ev, {}, page_path="/p/landing/", page_map=pm)
        self.assertEqual(tl["furthest"], sections.at(pm, 31)["label"])
        self.assertIn("furthest %s" % tl["furthest"], tl["lines"][1])
        self.assertEqual(tl["shots"][0]["moments"][1]["t"], 20)                   # the frame map's {t, does} rows
        other = timeline.build("s1", ev, {}, page_path="/p/other/", page_map=pm)  # another page: no section named
        self.assertIsNone(other["furthest"])

    def test_the_page_systems_reader_names_the_build_run(self):
        ws = Path(tempfile.mkdtemp())
        try:
            d = ws / "runs" / "page-chain" / "b" / "p_v2"
            d.mkdir(parents=True)
            (d / "run.json").write_text(json.dumps({"topic": "smooth arms", "job": "variant"}))
            (d / "page.json").write_text(json.dumps({"sections": [
                {"n": 1, "job": "makes the offer", "blocks": [{"type": "offer", "text": "Three tubes"}]}]}))
            ctx = {"run": "runs/page-chain/b/p_v2", "control": {"version": "v2", "brief": "PB-4"},
                   "brief": {"hypothesis": {"text": "Lead with proof"}}}
            st, plan, got = sections.from_context(ctx, ws)
            self.assertEqual(st["sections"][0]["form"], "offer")
            self.assertEqual((plan["brief"], plan["hypothesis"], plan["topic"]), ("PB-4", "Lead with proof", "smooth arms"))
            self.assertEqual(sections.from_context(None, ws), (None, None, None))
            self.assertEqual(sections.from_context({"run": "runs/page-chain/b/none"}, ws), (None, None, None))
        finally:
            shutil.rmtree(ws, ignore_errors=True)

    def test_no_structure_falls_back_to_scroll(self):
        self.assertIsNone(sections.page_map(None))
        self.assertIn("scroll %", sections.as_text(None))


class SharedChain(unittest.TestCase):
    """Runs on run-kit's Chain, page-teardown's structure prompt and marketing-chain-checks' gates."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        del CALLS[:]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_page_is_read_with_page_teardowns_own_prompt(self):
        out = runner.run("sample", source.Sample(SAMPLE), label="c1", ask=fake_model, model="m", out=self.tmp / "c1")
        st = json.loads((out / "run.json").read_text())
        self.assertEqual(st["tool"], "session-teardown")
        self.assertTrue(st["stages"]["structure"]["prompt_name"].startswith("structure-v"))
        self.assertEqual((out / "structure--sent.md").read_text().splitlines()[0],
                         runner.prompts.latest(runner.shared.PAGE_TEARDOWN_PROMPTS, "structure").read_text().splitlines()[0])
        self.assertIn("§6 offer box", (out / "teardown--sent.md").read_text())      # the page map reached the teardown
        self.assertIn("§6 offer box", (out / "hypothesis--sent.md").read_text())
        self.assertEqual(sum(st["reach"]["left"].values()), 30)                     # every left recording placed

    def test_a_page_chain_teardown_on_file_is_used_without_a_model_call(self):
        runs = self.tmp / "page-chain"
        d = runs / "sample" / "landing_v1"
        d.mkdir(parents=True)
        (d / "run.json").write_text(json.dumps({"source_url": "https://funnel.example.com/body-cpk/landing/",
                                                "updated": "2026-11-14T00:00:00"}))
        (d / "structure.json").write_text(json.dumps(STRUCTURE))
        swipe = runs / "sample" / "swipe_v1"                                          # a swipe's teardown: never used
        swipe.mkdir()
        (swipe / "run.json").write_text(json.dumps({"source_url": "https://elsewhere.example/page/", "updated": "2099"}))
        (swipe / "structure.json").write_text(json.dumps({"sections": [{"n": 1, "form": "WRONG", "words": 5}]}))
        out = runner.run("sample", source.Sample(SAMPLE), label="c2", ask=fake_model, model="m", out=self.tmp / "c2",
                         runs_root=runs)
        st = json.loads((out / "run.json").read_text())
        self.assertEqual(st["stages"]["structure"]["status"], "reused")
        self.assertFalse(any(c.startswith("# PAGE TEARDOWN") for c in CALLS))
        self.assertFalse((out / "structure--sent.md").exists())
        self.assertNotIn("WRONG", (out / "teardown--sent.md").read_text())

    def test_rerun_from_keeps_earlier_steps(self):
        runner.run("sample", source.Sample(SAMPLE), label="c3", ask=fake_model, model="m", out=self.tmp / "c3")
        del CALLS[:]
        out = runner.run("sample", source.Sample(SAMPLE), label="c3", ask=fake_model, model="m", out=self.tmp / "c3",
                         rerun_from="hypothesis")
        st = json.loads((out / "run.json").read_text())
        self.assertEqual(st["stages"]["structure"]["status"], "reused")
        self.assertEqual(st["stages"]["teardown"]["status"], "reused")
        self.assertEqual(len(CALLS), 1)
        self.assertEqual(record.check(json.loads((out / "hypothesis.json").read_text())), [])

    def test_delivery_gate_holds_a_record_that_breaks_the_contract(self):
        def offer_unchanged(prompt, model):
            text = fake_model(prompt, model)
            return text.replace('"type": "design"', '"type": "offer"') if prompt.startswith("# Hypothesis") else text
        with self.assertRaises(Held):
            runner.run("sample", source.Sample(SAMPLE), label="c4", ask=offer_unchanged, model="m", out=self.tmp / "c4")
        out = self.tmp / "c4"
        self.assertEqual(json.loads((out / "check.json").read_text())["delivery"]["result"], "HELD")
        self.assertIn("refused", json.loads((out / "run.json").read_text())["state"])
        self.assertTrue((out / "hypothesis.json").is_file())                     # written, so it can be read
        self.assertFalse((out / "deliverable" / "hypothesis.json").exists())      # never handed on

    def test_inputs_gate_holds_too_few_recordings(self):
        folder = self.tmp / "s"; shutil.copytree(SAMPLE, folder)
        (folder / "recordings.json").write_text("{}")
        with self.assertRaises(Held):
            runner.run("sample", source.Sample(folder), label="c5", ask=fake_model, model="m", out=self.tmp / "c5")
        self.assertEqual(json.loads((self.tmp / "c5" / "check.json").read_text())["inputs"]["result"], "HELD")
        self.assertEqual(CALLS, [])

    def test_models_come_from_the_registry(self):
        reg = {m["id"] for m in json.loads((ROOT.parent / "models" / "models.json").read_text())["models"]}
        for tier, model in runner.tiers().items():
            self.assertIn(model, reg, tier)
        self.assertEqual(runner.tiers()["designs"], runner.claude_flags.model())


class MoneyFixesSwings(unittest.TestCase):
    """owner, 2026-11-14: every finding priced; small fixes to the team, at most three big swings to the owner."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        del CALLS[:]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_price_is_the_gap_times_lost_visitors_times_value(self):
        got = money.price(15, 1, 30, 10, lost=600, value_per_reacher=20, days=15)
        self.assertEqual(got["gap"], 0.4)                    # 50% of leavers − 10% of buyers
        self.assertEqual(got["visitors_month"], 480)          # 0.4 × 600 lost × 30/15 days
        self.assertEqual(got["at_stake_month"], 9600.0)
        self.assertIn("$9,600 a month", got["basis"])
        self.assertIn("upper bound", got["basis"])
        self.assertEqual(money.price(1, 9, 30, 10, 600, 20, 15)["at_stake_month"], 0.0)   # buyers do it more: nothing
        self.assertEqual(money.price(99, 0, 30, 10, 600, 20, 30)["gap"], 1.0)              # counts clamp to recordings

    def test_friction_counts_dead_and_rage_taps_per_element(self):
        ev = {"a": [{"event": "$dead_click", "text": "See reviews"}, {"event": "$rageclick", "text": "$57"}],
              "b": [{"event": "$dead_click", "text": "See reviews"}],
              "c": [{"event": "$autocapture", "text": "Buy"}] * 3}
        rows = friction.count(ev, {"left": ["a", "b"], "converted": ["c"]})
        self.assertIn({"kind": "dead", "element": "See reviews", "left": 2, "converted": 0}, rows)
        self.assertFalse(any(r["element"] == "$57" for r in rows))                  # one recording: below the floor
        self.assertFalse(any(r["element"] == "Buy" for r in rows))                  # only buyers did it

    def test_fixes_and_swings_are_split_priced_and_ranked(self):
        out = runner.run("sample", source.Sample(SAMPLE), label="m1", ask=fake_model, model="m", out=self.tmp / "m1")
        fx = json.loads((out / "fixes.json").read_text())
        self.assertEqual(record.check_fixes(fx), [])
        self.assertRegex(fx["id"], r"^sample_body-cpk_landing_fix-\d{8}-1$")
        self.assertEqual(fx["control"], {"version": "v1"})
        f1 = fx["fixes"][0]
        self.assertEqual((f1["id"], f1["what"], f1["type"], f1["effort"]),
                         ("f1", "Point the See reviews link at the reviews on the page", "bug", "s"))
        self.assertEqual(f1["where"]["section"], "§2 paragraphs")
        self.assertTrue(f1["where"]["section_job"])                               # the job, from the page's structure
        self.assertEqual(f1["where"]["selector"], "See reviews")
        self.assertEqual((f1["why"]["left"], f1["why"]["converted"]), (10, 0))
        self.assertGreater(f1["value_usd_month"], 0)
        self.assertIn("upper bound", f1["basis"])
        self.assertEqual(fx["evidence"]["recordings"], {"left": 30, "converted": 10})
        self.assertTrue(json.loads((out / "run.json").read_text())["fix_state"].startswith("ready"))
        s1 = json.loads((out / "swings" / "swing-1" / "hypothesis.json").read_text())
        s2 = json.loads((out / "swings" / "swing-2" / "hypothesis.json").read_text())
        self.assertIn("reviews", s1["hypothesis"])             # 12 of 30 is worth more than 6 of 30: ranked first
        self.assertEqual((s1["id"], s2["id"]), ("m1-s1", "m1-s2"))
        self.assertEqual((s1["rank"], s2["rank"]), (1, 2))
        self.assertGreater(s1["value_usd_month"], s2["value_usd_month"])
        self.assertTrue(s1["basis"].startswith("finding 1:"))
        self.assertEqual(json.loads((out / "hypothesis.json").read_text()), s1)   # swing 1 until the owner picks
        st = json.loads((out / "run.json").read_text())
        self.assertGreaterEqual(st["swings"][0]["at_stake_month"], st["swings"][1]["at_stake_month"])
        self.assertIn("See reviews", (out / "teardown--sent.md").read_text())     # friction counted reached the prompt
        page = (out / "page.html").read_text()
        self.assertIn("Big swing 1", page)
        self.assertIn("Team fix list", page)

    def test_the_owners_pick_becomes_the_hypothesis(self):
        out = runner.run("sample", source.Sample(SAMPLE), label="m2", ask=fake_model, model="m", out=self.tmp / "m2")
        runner.pick_swing(out, 2)
        rec = json.loads((out / "hypothesis.json").read_text())
        self.assertEqual(rec["id"], "m2-s2")
        self.assertEqual(json.loads((out / "deliverable" / "hypothesis.json").read_text()), rec)
        self.assertEqual(json.loads((out / "run.json").read_text())["picked"], 2)
        self.assertIn("picked", (out / "page.html").read_text())
        with self.assertRaises(runner.RunError):
            runner.pick_swing(out, 3)

    def test_fixes_queue_while_a_test_runs(self):
        folder = self.tmp / "s"; shutil.copytree(SAMPLE, folder)
        pages = json.loads((folder / "pages.json").read_text())
        pages["pages"]["sample_body-cpk_landing"]["tests"] = [{"state": "live"}]
        (folder / "pages.json").write_text(json.dumps(pages))
        out = runner.run("sample", source.Sample(folder), label="m3", page_id="sample_body-cpk_landing",
                         ask=fake_model, model="m", out=self.tmp / "m3")
        self.assertTrue(json.loads((out / "run.json").read_text())["fix_state"].startswith("queued"))

    def test_a_fix_list_that_breaks_the_shape_is_refused(self):
        ev = record.evidence({"step": "landing", "visitors": 10, "reached_next": 2, "revenue_per_visitor": 1},
                             {"left": ["a"], "converted": []}, [{"pattern": "p", "left": 1, "converted": 0}], [])
        fix = {"what": "make it something else", "pattern": "something odd here", "left": 1, "converted": 0,
               "basis": "gap 100% × 8 lost × $1", "type": "vibes", "effort": "xl"}
        bad = record.check_fixes(record.build_fixes("b_p_x_fix-20261114-1", {"page_id": "b_p_x", "control": {"version": "v1"}},
                                                    ev, [fix], {}))
        self.assertTrue(any("type must be" in b for b in bad))
        self.assertTrue(any("effort must be" in b for b in bad))
        ok = dict(fix, type="design", effort="s")
        self.assertEqual(record.check_fixes(record.build_fixes("b_p_x_fix-20261114-1", {"page_id": "b_p_x",
                                                                "control": {"version": "v1"}}, ev, [ok], {})), [])
        self.assertTrue(any("id must be" in b for b in record.check_fixes(
            record.build_fixes("m1", {"page_id": "b_p_x", "control": {"version": "v1"}}, ev, [ok], {}))))

    def test_a_second_fix_list_the_same_day_gets_the_next_number(self):
        a = runner.run("sample", source.Sample(SAMPLE), label="n1", ask=fake_model, model="m", out=self.tmp / "b" / "n1")
        b = runner.run("sample", source.Sample(SAMPLE), label="n2", ask=fake_model, model="m", out=self.tmp / "b" / "n2")
        ids = [json.loads((d / "fixes.json").read_text())["id"] for d in (a, b)]
        self.assertEqual([i[-2:] for i in ids], ["-1", "-2"])

    def test_the_pages_build_record_is_read_first(self):
        runs = self.tmp / "page-chain"
        d = runs / "sample" / "body-cpk_landing_v1"
        d.mkdir(parents=True)
        (d / "run.json").write_text(json.dumps({"page": "sample_body-cpk_landing", "version": "v1", "brief": "PB-9",
                                                "job": "new-page", "topic": "smooth arms", "updated": "2026-11-14"}))
        (d / "page.json").write_text(json.dumps({"format": "sales page", "sections": [
            {"n": 1, "job": "names the problem", "blocks": [{"type": "headline", "text": "Smooth skin by Sunday"}]},
            {"n": 2, "job": "makes the offer", "blocks": [{"type": "offer", "text": "Three tubes, best value"},
                                                          {"type": "button", "text": "Get mine"}]}]}))
        out = runner.run("sample", source.Sample(SAMPLE), label="m4", ask=fake_model, model="m", out=self.tmp / "m4",
                         runs_root=runs)
        st = json.loads((out / "run.json").read_text())
        self.assertEqual(st["stages"]["structure"]["status"], "reused")
        self.assertEqual(st["plan"]["brief"], "PB-9")
        sent = (out / "teardown--sent.md").read_text()
        self.assertIn("page brief: PB-9", sent)
        self.assertIn('§2 offer · ', sent)
        self.assertIn('heading: "Smooth skin by Sunday"', sent)
        self.assertFalse(any(c.startswith("# PAGE TEARDOWN") for c in CALLS))


class NoBrandNames(unittest.TestCase):
    def test_code_and_prompts_name_no_brand(self):
        brands = [p.name for p in (ROOT.parents[1] / "brands").iterdir() if p.is_dir()]
        for f in list((ROOT / "machine").glob("*.py")) + list((ROOT / "prompts").glob("*.md")):
            text = f.read_text().lower()
            for b in brands:
                self.assertNotIn(b.lower(), text, "%s names %s" % (f.name, b))


class LiveSourceShape(unittest.TestCase):
    def test_posthog_reads_keys_by_name_and_sends_only_reads(self):
        sent = []

        class Resp:
            def __init__(self, body): self.body = body
            def read(self): return json.dumps(self.body).encode()
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def opener(req):
            sent.append((req.get_method(), req.full_url, req.get_header("Authorization")))
            if "/query/" in req.full_url:
                return Resp({"results": [["s1", "b_p_x", "landing", "2026-11-01T00:00:00"]]})
            return Resp({"results": [{"id": "s1", "recording_duration": 30, "active_seconds": 12, "click_count": 2,
                                      "start_url": "u", "start_time": "t"}]})
        ph = source.PostHog(host="https://h.example", project="9", token="t", opener=opener)
        self.assertEqual(ph.page_views("b", 14)[0]["page_id"], "b_p_x")
        self.assertEqual(ph.recordings(["s1"])["s1"]["active_s"], 12)
        self.assertTrue(all(m in ("GET", "POST") for m, _, _ in sent))
        self.assertTrue(all("/query/" in u or "/session_recordings/" in u for _, u, _ in sent))
        self.assertEqual(ph.replay_link("s1", 14), "https://h.example/project/9/replay/s1?t=14")


if __name__ == "__main__":
    unittest.main(verbosity=1)
