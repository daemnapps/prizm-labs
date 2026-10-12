#!/usr/bin/env python3
"""The rollout's promises, proven without spending anything.

    python3 test_rollout.py

No network, no model, no Klaviyo, no pictures. Every test runs against a
made-up brand in a temp folder (AI_WORKSPACE points the tool at it), and a
stub `claude` on the PATH that leaves a mark if anything ever calls it.

  1  the dry run makes zero model calls and writes nothing under runs/
  2  a missing --brand is an error, never a default brand
  3  the price gate holds an email through the shared marketing-chain-checks library
  4  an email type nobody defined is blocked, with the real ones named
  5  furniture words come from the brand's own file, not from the code
"""
import json
import pathlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRAND = "testbrand"
TMP = Path(tempfile.mkdtemp(prefix="email-production-test-"))
WS = TMP / "ws"
os.environ["AI_WORKSPACE"] = str(WS)            # before anything imports paths.py

EMAIL_BLOCK = {
    "headline": "A headline",
    "hero": {"prompt": "a picture", "alt": "a picture"},
    "body": ["First paragraph.", "The set is $PRICE today."],
    "offer": {"line": "The set — $PRICE"},
    "button": {"label": "Get it", "link": "https://example.test/p"},
    "subjects": [{"subject": "A subject", "preview": "A preview line"}],
}


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def make_workspace():
    b = WS / "brands" / BRAND
    write(b / "email-sms" / "sends" / "old-email.md",
          "# An old subject\n- sent: 2026-01-01\n- preview: a preview\n\n---\n\nHello there.\n"
          "[IMAGE alt=Tiles]\n[IMAGE alt=Bedroom]\nThe Better Way\nInspired by testing. Made anywhere.\n- Pat\nReal copy line here.\n")
    write(b / "email-sms" / "email-types.json", json.dumps({"types": [
        {"key": "house-special", "well": "brand", "name": "House special", "what": "this brand's own kind"}],
        "treatments": []}))
    write(b / "email-sms" / "simple.json", json.dumps({
        "logo": {"url": "https://example.test/logo.png", "alt": "Testbrand", "width": 100, "link": "#"},
        "signoff": ["Warm regards,", "Pat Example"], "tagline": "Inspired by testing. Made anywhere.",
        "furniture": ["tiles", "bedroom", "the better way"],
        "fonts": {"headline": "serif", "body": "sans-serif"},
        "colors": {"page": "#fff", "card": "#fff", "text": "#000", "muted": "#777",
                   "button": "#000", "button_text": "#fff"}}))
    write(b / "products" / "offer-bank.md",
          "# Offers\n\n## the-set — The Set\n\n- status: live\n- price: $40.00\n\n## other — Other\n\n- price: $99.99\n")
    write(b / "products" / "store.json", json.dumps({"site": "https://example.test", "products": [
        {"handle": "the-big-set", "title": "The Big Set"}]}))
    write(b / "products" / "little-tin.md", "# Little Tin\n")
    # what may be linked, and what is a draft — the brand's own call (2026-09-21)
    write(b / "products" / "heroes.json", json.dumps({
        "heroes": ["the-big-set"],
        "sellable": [{"handle": "the-big-set", "title": "The Big Set",
                      "url": "https://example.test/p"}],
        "never": {"handles": ["ghost-tin"], "why": "a draft, never launched"}}))


def make_run(label, price, offer="the-set", brand_in_run=True):
    rd = WS / "runs" / "email-production" / BRAND / label
    block = json.loads(json.dumps(EMAIL_BLOCK).replace("PRICE", price))
    write(rd / "stage8--blocks.md", "```EMAIL\n" + json.dumps(block, indent=1) + "\n```\n")
    write(rd / "stage8c--check.md", '```CHECK\n{"facts": [], "chops": [], "typos": []}\n```\n')
    state = {"label": label, "assignment": {"offer": offer}, "stages": {}}
    if brand_in_run:
        state["brand"] = BRAND
    write(rd / "run.json", json.dumps(state))
    return rd


def run(script, *args, path_prefix=None):
    env = dict(os.environ)
    if path_prefix:
        env["PATH"] = f"{path_prefix}{os.pathsep}{env['PATH']}"
    return subprocess.run([sys.executable, script, *args], cwd=HERE, env=env,
                          capture_output=True, text=True)


def tree(root):
    return sorted(str(p.relative_to(root)) for p in Path(root).rglob("*")) if Path(root).exists() else []


class DryRun(unittest.TestCase):
    def test_zero_calls_and_nothing_written(self):
        stub_dir = TMP / "bin"
        mark = TMP / "claude-was-called"
        write(stub_dir / "claude", f"#!/bin/sh\necho called >> '{mark}'\necho stub\n")
        (stub_dir / "claude").chmod(0o755)
        before_ws = tree(WS / "runs")
        before_here = tree(HERE / "results") if (HERE / "results").exists() else []
        r = run("email.py", str(WS / "brands" / BRAND / "email-sms" / "sends" / "old-email.md"),
                "--brand", BRAND, "--brand-root", str(WS), "--label", "_dry-test",
                "--offer", "the-set", "--type", "house-special", "--dry-run", path_prefix=stub_dir)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn("variables resolved", r.stdout)
        self.assertIn("decided at triage", r.stdout)
        self.assertFalse(mark.exists(), "the dry run called a model")
        self.assertEqual(tree(WS / "runs"), before_ws, "the dry run wrote under runs/")
        self.assertFalse((WS / "runs" / "email-production" / BRAND / "_dry-test").exists())
        if (HERE / "results").exists():
            self.assertEqual(tree(HERE / "results"), before_here)
        # the path column is filled in for what resolved
        row = next(ln for ln in r.stdout.splitlines() if ln.strip().startswith("OK") and "offer" in ln)
        self.assertIn("offer-bank.md", row)

    def test_the_stub_would_have_been_seen(self):
        """The proof above is only a proof if a real call WOULD leave the mark."""
        stub_dir = TMP / "bin2"
        mark = TMP / "claude-was-called-2"
        write(stub_dir / "claude", f"#!/bin/sh\necho called >> '{mark}'\necho stub\n")
        (stub_dir / "claude").chmod(0o755)
        env = dict(os.environ, PATH=f"{stub_dir}{os.pathsep}{os.environ['PATH']}")
        subprocess.run(["claude", "-p"], env=env, capture_output=True, text=True, input="x")
        self.assertTrue(mark.exists())

    def test_doctor_no_longer_deletes(self):
        self.assertNotIn('"rm"', (HERE / "doctor.py").read_text())


class NoDefaultBrand(unittest.TestCase):
    def test_missing_brand_is_an_error(self):
        # the pull/ and sweep/ scripts that defaulted to one brand (SI-164 (email scripts need brand))
        for script in ("pull/build_email_folders.py", "pull/classify.py", "pull/derive.py",
                       "pull/index_sends.py", "pull/learnings.py", "pull/ledger.py",
                       "pull/performance.py", "pull/products.py", "sweep/layouts.py",
                       "sweep/rebuild.py", "sweep/qc.py", "sweep/qa_index.py"):
            with self.subTest(script=script):
                r = run(script)
                self.assertNotEqual(r.returncode, 0, script)
                self.assertIn("--brand", r.stderr, script)
        for script in ("store.py", "offers.py", "live_read.py", "check_month.py", "figma_board.py",
                       "build_learnings.py", "pick_frame.py", "shopify.py"):
            r = run(script)
            self.assertNotEqual(r.returncode, 0, script)
            self.assertIn("--brand", r.stderr, script)

    def test_a_run_without_a_brand_names_the_file(self):
        sys.path.insert(0, str(HERE / "machine"))
        import brand_facts as BF
        rd = make_run("no-brand-run", "40.00", brand_in_run=False)
        with self.assertRaises(SystemExit) as cm:
            BF.run_brand(rd)
        self.assertIn(str(rd / "run.json"), str(cm.exception))
        self.assertEqual(BF.run_brand(rd, "given"), "given")

    def test_runs_are_filtered_by_their_own_run_json(self):
        sys.path.insert(0, str(HERE / "machine"))
        import brand_facts as BF
        res = TMP / "results"
        for name, brand in (("sep-01", BRAND), (f"otherbrand-sep-01", "otherbrand"), ("sep-02", "otherbrand")):
            write(res / name / "design.json", "{}")
            write(res / name / "run.json", json.dumps({"brand": brand}))
        self.assertEqual([p.name for p in BF.runs_of(BRAND, res, "sep")], ["sep-01"])
        self.assertEqual([p.name for p in BF.runs_of("otherbrand", res, "sep")], ["otherbrand-sep-01", "sep-02"])


class PriceGate(unittest.TestCase):
    def test_a_wrong_price_is_held_by_the_shared_library(self):
        rd = make_run("held-run", "99.99")
        r = run("simple_email.py", str(rd), "--brand", BRAND, "--no-images")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("HELD — not sent to Klaviyo", r.stderr)
        self.assertIn("$99.99 is not a price the offer bank sells for `the-set` today", r.stderr)
        check = json.loads((rd / "deliverable" / "check.json").read_text())
        self.assertEqual(list(check), ["delivery"])
        self.assertEqual(check["delivery"]["result"], "HELD")
        self.assertNotIn("prices", check)

    def test_a_right_price_passes_and_the_layout_is_recorded(self):
        rd = make_run("clean-run", "40.00")
        write(rd / "deliverable" / "check.json", json.dumps({"prices": "FAIL", "problems": ["old shape"]}))
        r = run("simple_email.py", str(rd), "--brand", BRAND, "--no-images")
        self.assertEqual(r.returncode, 0, r.stderr)
        check = json.loads((rd / "deliverable" / "check.json").read_text())
        self.assertEqual(check, {"delivery": {"result": "pass", "problems": [], "items": [], "cleared": []}})
        state = json.loads((rd / "run.json").read_text())
        self.assertEqual(state["elements"]["template/email"]["id"], "simple")

    def test_unfilled_and_unchecked_hold_too(self):
        rd = make_run("unfilled-run", "40.00")
        t = (rd / "stage8--blocks.md").read_text().replace("First paragraph.", "[UNFILLED: a part]")
        (rd / "stage8--blocks.md").write_text(t)
        (rd / "stage8c--check.md").unlink()
        r = run("simple_email.py", str(rd), "--brand", BRAND, "--no-images")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("UNFILLED", r.stderr)
        self.assertIn("never checked", r.stderr)

    def test_the_gate_is_the_shared_one(self):
        src = (HERE / "simple_email.py").read_text()
        self.assertIn("import marketing_chain_checks as Q", src)
        self.assertIn('Q.hold("delivery"', src)
        self.assertNotIn("MONEY = re.compile", src)


class EmailTypes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(HERE / "machine"))
        import email_elements
        cls.EE = email_elements

    def test_library_and_brand_types_pass_unknown_is_refused(self):
        lib = self.EE.E.rows("format", "email")[0]["id"]
        self.assertIsNone(self.EE.type_problem(BRAND, lib))
        self.assertIsNone(self.EE.type_problem(BRAND, "house-special"))      # the brand's own
        why = self.EE.type_problem(BRAND, "made-up-type")
        self.assertIn("made-up-type", why)
        self.assertIn(lib, why)                                              # the real ids are named
        self.assertIn("house-special", why)

    def test_copy_plan_blocks_it(self):
        sys.path.insert(0, str(HERE))
        import copy_plan
        slot = {"id": "sep-01", "type": "made-up-type", "source": "old-email.md", "occasion": "x"}
        flags = copy_plan.flag(["python3", "email.py", "--offer", "none"], slot, "someone", "an angle", BRAND)
        self.assertTrue(any(k == "blocked" and "made-up-type" in m for k, m in flags), flags)
        slot["type"] = "house-special"
        flags = copy_plan.flag(["python3", "email.py", "--offer", "none"], slot, "someone", "an angle", BRAND)
        self.assertFalse(any(k == "blocked" for k, _ in flags), flags)

    def test_the_chain_refuses_it_before_any_step(self):
        r = run("email.py", str(WS / "brands" / BRAND / "email-sms" / "sends" / "old-email.md"),
                "--brand", BRAND, "--brand-root", str(WS), "--label", "_type-test",
                "--type", "made-up-type", "--dry-run")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("elements gate", r.stderr)

    def test_the_type_travels_from_the_calendar(self):
        sys.path.insert(0, str(HERE))
        import brief
        argv = brief.chain_argv({"id": "sep-01", "type": "house-special", "source": "old-email.md"}, BRAND)
        self.assertEqual(argv[argv.index("--type") + 1], "house-special")

    def test_the_layout_is_a_real_template(self):
        self.assertEqual(self.EE.layout("simple")["id"], "simple")
        with self.assertRaises(self.EE.Unknown):
            self.EE.layout("not-a-layout")


class Furniture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(HERE / "machine"))
        import brand_facts
        cls.BF = brand_facts

    def test_words_come_from_the_brand_file(self):
        v = self.BF.vocab(BRAND)
        for alt in ("Tiles", "bedroom", "The Better Way", "Testbrand", "testbrand on instagram", "Shop"):
            self.assertTrue(self.BF.is_furniture_alt(alt, v), alt)
        self.assertFalse(self.BF.is_furniture_alt("A man at a sink", v))
        self.assertTrue(self.BF.is_furniture_line("Inspired by testing. Made anywhere.", v))
        self.assertTrue(self.BF.is_furniture_line("- Pat", v))
        self.assertFalse(self.BF.is_furniture_line("Real copy line here.", v))
        # change the brand's file and the answer changes — the code holds no list
        f = WS / "brands" / BRAND / "email-sms" / "simple.json"
        d = json.loads(f.read_text())
        keep = d["furniture"]
        d["furniture"] = []
        f.write_text(json.dumps(d))
        try:
            self.assertFalse(self.BF.is_furniture_alt("Tiles", self.BF.vocab(BRAND)))
        finally:
            d["furniture"] = keep
            f.write_text(json.dumps(d))

    def test_the_source_reader_drops_it(self):
        sys.path.insert(0, str(HERE))
        import figma_brief as FB
        got = FB.source_email(BRAND, {"source": "old-email.md"})
        alts = [b["alt"] for b in got["blocks"]]
        self.assertIn("Real copy line here.", alts)
        for gone in ("Tiles", "Bedroom", "Inspired by testing. Made anywhere.", "- Pat"):
            self.assertNotIn(gone, alts)

    def test_product_names_come_from_the_brand(self):
        pat = self.BF.product_only(BRAND)
        self.assertTrue(pat.match("The Big Set on a shelf"))
        self.assertTrue(pat.match("image of little tin"))
        self.assertFalse(pat.match("a man at a sink"))

    def test_no_brand_words_left_in_the_code(self):
        """Strings and names only — comments and docstrings may tell the history."""
        import io
        import tokenize
        brands = [p.name for p in (HERE.parents[1] / "brands").iterdir()
                  if p.is_dir() and not p.name.startswith(("_", "."))]
        pat = re.compile(r"(?<![A-Za-z])(" + "|".join(map(re.escape, brands)) + r")(?![a-z])", re.I)
        for name in ("design_email.py", "figma_brief.py", "figma_draft.py", "pick_frame.py",
                     "gen_placeholders.py", "shopify.py", "loop.py", "store.py", "offers.py",
                     "live_read.py", "check_month.py", "figma_board.py", "build_learnings.py",
                     "build_system.py", "email.py", "simple_email.py", "run_month.py"):
            prev = None
            for tok in tokenize.generate_tokens(io.StringIO((HERE / name).read_text()).readline):
                if tok.type in (tokenize.NL, tokenize.COMMENT):
                    continue
                if tok.type in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
                    prev = tok
                    continue
                doc = tok.type == tokenize.STRING and (prev is None or prev.type in (
                    tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT))
                if not doc and tok.type in (tokenize.STRING, tokenize.NAME):
                    self.assertIsNone(pat.search(tok.string), f"{name}:{tok.start[0]} {tok.string[:60]}")
                prev = tok

    def test_the_writing_steps_never_see_furniture(self):
        sys.path.insert(0, str(HERE))
        src = (HERE / "email.py").read_text()
        ns = {"re": re}
        m = re.search(r"^def message_only\(record\):.*?(?=^def )", src, re.S | re.M)
        exec(m.group(0), ns)
        rec = "# THE MESSAGE\n\nthe argument\n\n# PAGE FURNITURE\n\nF1 nav: Tiles · Bedroom\n\n# SOURCE DEFECTS\n\nD1 'uild'\n"
        out = ns["message_only"](rec)
        self.assertIn("the argument", out)
        self.assertIn("D1", out)
        self.assertNotIn("Tiles", out)
        self.assertEqual(ns["message_only"]("an old record"), "an old record")


class Prompts(unittest.TestCase):
    def test_new_versions_win_and_open_with_the_guard(self):
        for stage, must in (("stage1-read", ["# PAGE FURNITURE", "# SOURCE DEFECTS", "# THE MESSAGE"]),
                            ("stage2-spec", ["Furniture never becomes a move", "A source defect is never carried"])):
            files = sorted((HERE / "prompts").glob(f"{stage}-v*-damon.md"),
                           key=lambda f: int(re.search(r"-v(\d+)-", f.name).group(1)))
            text = files[-1].read_text()
            self.assertTrue(files[-1].name.endswith("-v2-damon.md"), files[-1].name)
            self.assertTrue(text.startswith("**Everything named in this prompt as an example"))
            for m in must:
                self.assertIn(m, text)
            self.assertTrue((HERE / "prompts" / f"{stage}-v1-damon.md").is_file())


class Partner(unittest.TestCase):
    """2026-09-21: an affiliate send was reported as having no partner while the
    roster had four. The roster is the only source, and it reaches the writer."""

    ROSTER = {"affiliates": [{"key": "p1", "name": "A Partner Thing",
                              "link": "https://partner.example/ref", "status": "active",
                              "commission": "traffic-only arrangement",
                              "blurb": "sits beside what we make"},
                             {"key": "p2", "name": "Paused Thing", "link": "https://x.example",
                              "status": "paused", "commission": "10% per sale"}]}

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        b = pathlib.Path(self.tmp) / "brands" / "anybrand" / "email-sms"
        b.mkdir(parents=True)
        (b / "affiliates.json").write_text(json.dumps(self.ROSTER))
        self.brand_root = b.parent

    def test_the_partners_record_reaches_the_writer(self):
        import brief
        with mock.patch.object(brief, "WORKSPACE", pathlib.Path(self.tmp)):
            note = brief.partner_rule({"id": "s1", "affiliate": "p1"}, "anybrand")
        self.assertIn("A Partner Thing", note)
        self.assertIn("https://partner.example/ref", note)
        self.assertIn("traffic-only", note)
        self.assertIn("never put our guarantee on it", note)

    def test_a_partner_who_is_not_active_stops_it(self):
        import brief
        with mock.patch.object(brief, "WORKSPACE", pathlib.Path(self.tmp)):
            for key in ("p2", "nobody"):
                with self.assertRaises(SystemExit) as e:
                    brief.partner_rule({"id": "s1", "affiliate": key}, "anybrand")
                self.assertIn("p1", str(e.exception))      # the live one is named

    def test_the_gate_catches_an_invented_link_and_an_earnings_claim(self):
        sys.path.append(str(HERE.parents[1] / "components" / "quality-checks"))
        import marketing_chain_checks as Q
        partner = Q.partner_on_file(self.brand_root, "p1")
        self.assertIsNone(Q.partner_on_file(self.brand_root, "p2"))   # paused is not live
        bad = Q.partner_check("Grab it at https://bit.ly/deal — we get paid when you do.",
                              partner, own_domains=["ours.example"])
        self.assertTrue(any("bit.ly" in p for p in bad))
        self.assertTrue(any("real link" in p for p in bad))
        self.assertTrue(any("earnings claim" in p for p in bad))
        self.assertEqual(Q.partner_check(
            "Grab it at https://partner.example/ref or see https://ours.example/x",
            partner, own_domains=["ours.example"]), [])


class Inbox(unittest.TestCase):
    """The subject and the preview are the first thing a reader sees, and were
    the one part nothing checked (2026-09-21)."""

    def send(self, label, chosen):
        rd = make_run(label, "40.00")
        raw = (rd / "stage8--blocks.md").read_text()
        block = json.loads(raw.split("```EMAIL\n", 1)[1].rsplit("```", 1)[0])
        block["subjects"] = [chosen]
        write(rd / "stage8--blocks.md", "```EMAIL\n" + json.dumps(block, indent=1) + "\n```\n")
        return run("simple_email.py", str(rd), "--brand", BRAND, "--no-images")

    def test_an_empty_or_broken_inbox_line_holds_it(self):
        for i, (chosen, wanted) in enumerate((
                ({"subject": "A subject", "preview": ""}, "empty"),
                ({"subject": "", "preview": "A preview"}, "empty"),
                ({"subject": "A subject", "preview": "uild your set"}, "mid-word"),
                ({"subject": "A subject", "preview": "[UNFILLED: preview]"}, "UNFILLED"))):
            r = self.send(f"inbox{i}", chosen)
            self.assertNotEqual(r.returncode, 0, chosen)
            self.assertIn(wanted, r.stderr, chosen)

    def test_a_good_inbox_line_passes(self):
        r = self.send("inboxok", {"subject": "Just walked the warehouse",
                                  "preview": "the quiet part is done"})
        self.assertEqual(r.returncode, 0, r.stderr)


class Catalogue(unittest.TestCase):
    """the owner, 2026-09-21: a draft is not a product, and every email ends somewhere
    a reader can buy."""

    def edit(self, label, **change):
        """A run whose finished blocks carry `change`."""
        rd = make_run(label, "40.00")
        raw = (rd / "stage8--blocks.md").read_text()
        block = json.loads(raw.split("```EMAIL\n", 1)[1].rsplit("```", 1)[0])
        block.update(change)
        write(rd / "stage8--blocks.md", "```EMAIL\n" + json.dumps(block, indent=1) + "\n```\n")
        return run("simple_email.py", str(rd), "--brand", BRAND, "--no-images")

    def test_a_draft_product_holds_it(self):
        r = self.edit("draftprod", body=["Ask us about the Ghost Tin."])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ghost-tin", r.stderr)

    def test_a_dead_end_holds_it(self):
        for i, link in enumerate(("[UNFILLED: destination]",
                                  "https://example.test/collections/all")):
            r = self.edit(f"deadend{i}", button={"label": "Have a look", "link": link})
            self.assertNotEqual(r.returncode, 0, link)
            self.assertIn("destination", r.stderr, link)

    def test_the_real_product_page_passes(self):
        r = self.edit("goodend", button={"label": "The Big Set",
                                         "link": "https://example.test/p"})
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    make_workspace()
    try:
        unittest.main(verbosity=2)
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
