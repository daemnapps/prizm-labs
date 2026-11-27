#!/usr/bin/env python3
"""The flow and page prompts (flows/prompts/): shape, bindings, draft-only, no live pick-up, and every bank row an
example cites is real, with its quote inside that row's text. No model, no network, no key."""
import glob
import json
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROMPTS = sorted((HERE / "prompts").glob("*.md"))
LIVE = HERE.parent / "prompts"
WORKSPACE = HERE.parents[2]
SECTIONS = ["## Inputs", "## The task", "## Real examples", "## Output", "## Banned"]
ROW = re.compile(r"\[(language_([a-z0-9-]+?)_([a-z0-9-]+)_(?:customer|lead|prospect|churned)_\d+)\]")
QUOTE = re.compile(r"\"([^\"]{6,})\"")


def norm(s):
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("“", '"').replace("”", '"')).strip()


_BANKS = {}


def bank(brand, avatar):
    key = (brand, avatar)
    if key not in _BANKS:
        rows = {}
        for f in glob.glob(str(WORKSPACE / "brands" / brand / "core-avatars" / avatar / "language" / "**" / "*.json"),
                           recursive=True):
            try:
                d = json.loads(Path(f).read_text())
            except (OSError, ValueError):
                continue
            for r in (d.get("entries") or []) if isinstance(d, dict) else []:
                if isinstance(r, dict) and r.get("id"):
                    rows[r["id"]] = r.get("text") or ""
        _BANKS[key] = rows
    return _BANKS[key]


class FlowPrompts(unittest.TestCase):
    def test_there_are_nine(self):
        self.assertEqual(len(PROMPTS), 9, [p.name for p in PROMPTS])

    def test_sections_in_order_after_a_role_line(self):
        for p in PROMPTS:
            text = p.read_text()
            self.assertRegex(text, r"\nRole: ", p.name)
            at = [text.find(s) for s in SECTIONS]
            self.assertNotIn(-1, at, f"{p.name} is missing a section")
            self.assertEqual(at, sorted(at), f"{p.name} has its sections out of order")
            self.assertLess(text.find("Role: "), at[0], p.name)

    def test_binds_the_words_rule_the_offer_rule_and_bank_rows(self):
        for p in PROMPTS:
            text = p.read_text()
            self.assertIn("{words_rule}", text, p.name)
            self.assertIn("{offer_rule}", text, p.name)
            self.assertTrue(any(s in text for s in ("{customer_language}", "{proof_language}", "{objection_language}")),
                            p.name)
            self.assertIn("SOURCES", text, p.name)

    def test_draft_only(self):
        for p in PROMPTS:
            text = p.read_text()
            self.assertIn("status: draft", text, p.name)
            banned = text[text.find("## Banned"):]
            self.assertRegex(banned, r"(Scheduling, sending or building|Publishing or changing|Changing the live)",
                             p.name)

    def test_the_live_lane_cannot_pick_them_up(self):
        live_stems = {re.split(r"-v\d+-", f.name)[0] for f in LIVE.glob("*.md")}
        for p in PROMPTS:
            stem = re.split(r"-v\d+-", p.name)[0]
            self.assertNotIn(stem, live_stems, p.name)
            self.assertFalse(any(stem.startswith(s + "-") or s.startswith(stem + "-") for s in live_stems), p.name)
        self.assertFalse((LIVE / "flows").exists())

    def test_the_readme_lists_every_prompt(self):
        readme = (HERE / "README.md").read_text()
        for p in PROMPTS:
            self.assertIn(f"prompts/{p.name}", readme)

    def test_every_cited_row_is_real_and_every_quote_is_its_text(self):
        if not (WORKSPACE / "brands").is_dir():
            self.skipTest("no brands/ in this checkout")
        cited = 0
        for p in PROMPTS:
            for line in p.read_text().splitlines():
                for m in ROW.finditer(line):
                    rid, brand, avatar = m.group(1), m.group(2), m.group(3)
                    rows = bank(brand, avatar)
                    self.assertIn(rid, rows, f"{p.name}: {rid} is not in the bank")
                    cited += 1
                    for q in QUOTE.findall(line[:m.start()]):
                        self.assertIn(norm(q), norm(rows[rid]), f"{p.name}: quote is not {rid}'s text")
        self.assertGreater(cited, 0)


class Runner(unittest.TestCase):
    """flows/run_flow.py fills a prompt from files and the bank; it calls no model and records nothing."""

    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.insert(0, str(HERE))
        import run_flow
        cls.R = run_flow

    def test_every_prompt_has_a_flow_and_funnels(self):
        stems = {re.split(r"-v\d+-", p.name)[0] for p in PROMPTS}
        self.assertEqual(stems, set(self.R.FLOW_FUNNELS))
        for reader, proof in self.R.FLOW_FUNNELS.values():
            self.assertIn(reader, ("lead", "customer"))
            self.assertEqual(proof, "customer")

    def test_offer_section_takes_only_the_named_offers_and_the_proof(self):
        bank = ("# Offer bank\n\n## flex — A brush\nprice\n\n## crush — Other\nno\n\n## Guarantees\n\n"
                "### popup — Pop-up offer\ntowel\n\n### other — x\nno\n\n## Proof\n- 160,000 orders\n")
        got = self.R.offer_section(bank, ["flex", "popup"])
        self.assertIn("A brush", got)
        self.assertIn("towel", got)
        self.assertIn("160,000 orders", got)
        self.assertNotIn("Other", got)
        self.assertNotIn("### other", got)
        self.assertEqual(self.R.offer_section(bank, []), bank)

    def test_fill_leaves_no_placeholder_and_writes_nothing(self):
        if not (WORKSPACE / "brands" / "brand_a").is_dir():
            self.skipTest("no brands/ in this checkout")
        before = sorted(str(p) for p in (WORKSPACE / "runs" / "language-layer").rglob("*")) \
            if (WORKSPACE / "runs" / "language-layer").is_dir() else []
        for flow in ("welcome", "post-purchase"):
            text, _p, where, left = self.R.fill(flow, "brand_a", "fed-up-king", offer=["flex", "popup"],
                                                sets={"length": "6"})
            self.assertNotIn("cannot import", text, flow)              # the offer rules really were read
            self.assertIn("`{customer_language}`", text, flow)          # the inputs table stays a table
            self.assertIn("## Proof", text, flow)                       # the filed proof travels with the offer
            core = {"customer_language", "proof_language", "objection_language", "offer_rule", "words_rule",
                    "language_bank", "product_file", "sender_identity", "brand", "length"}
            self.assertEqual(core & set(left), set(), flow)       # the files and the bank fill these
            self.assertTrue(all(("[UNFILLED] %s" % n) in text for n in left), flow)
            self.assertIn("funnel %s" % self.R.FLOW_FUNNELS[flow][0], where["customer_language"])
        after = sorted(str(p) for p in (WORKSPACE / "runs" / "language-layer").rglob("*")) \
            if (WORKSPACE / "runs" / "language-layer").is_dir() else []
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
