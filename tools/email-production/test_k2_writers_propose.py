#!/usr/bin/env python3
"""K2 (brands write wall): every email-production writer PROPOSES — brands/
is read, never written.

    python3 test_k2_writers_propose.py

No network, no model, no `claude`. Every writer runs end to end against a
made-up brand in a temp workspace (AI_WORKSPACE, set before anything imports
paths.py), with only its network call stubbed. Then: brands/ is byte-for-byte
what it was; each output sits in runs/email-production/<brand>/facts-<day>/
at its brand-relative path; PROPOSAL.md names every target and the one
removal; its copy commands, run from a copy of the workspace, land the files;
and none of the 17 writers' source writes into brands/. SI-21 (email facts
proposals), 2026-10-07.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRAND = "testbrand"
TMP = Path(tempfile.mkdtemp(prefix="email-production-k2-writers-"))
WS = TMP / "ws"
BANK = TMP / "format-bank"
os.environ["AI_WORKSPACE"] = str(WS)            # before anything imports paths.py
os.environ["FORMAT_BANK_DIR"] = str(BANK)       # qa_index reads it at import

WRITERS = [
    "pull/classify.py", "pull/index_sends.py", "pull/learnings.py", "pull/performance.py",
    "pull/ledger.py", "pull/sends_from_bank.py", "pull/products.py", "pull/matrix.py",
    "pull/index_catalogue.py", "offers.py", "store.py", "offer_bank_build.py", "loop.py",
    "sweep/layouts.py", "sweep/qa_index.py", "sweep/census.py", "sweep/board_pass.py",
]
BRAND_WRITE = re.compile(r'(BRAND_ROOT|BRANDS|WORKSPACE\s*/\s*"brands"|ws\s*/\s*"brands")'
                         r'.*\.(write_text|write_bytes|mkdir|unlink)\(')
MARK = "# Ruled by a human — carried forward, not generated"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def make_workspace():
    b = WS / "brands" / BRAND
    write(b / "products" / "offer-bank.md",
          "# Offers\n\n## the-set — The Set\n\n- Price: **$40.00**\n\n---\n\n"
          + MARK + "\n\nA line a person ruled.\n")
    write(b / "products" / "gone.md", "# A product the store no longer sells\n")
    write(b / "email-sms" / "email-types.json", json.dumps({"types": [
        {"key": "story", "well": "help", "role": "earns", "needs": ["offer_file"], "then": ["sale"]},
        {"key": "sale", "well": "ask", "role": "asks", "needs": ["offer_file"], "then": ["thanks"]},
        {"key": "thanks", "well": "brand", "role": "recovers", "needs": [], "then": []}],
        "treatments": []}, indent=1) + "\n")
    write(b / "email-sms" / "catalogue.json", json.dumps({"products": [
        {"handle": "tin", "title": "The Tin", "product_type": "Balm",
         "body_html": "<p>A balm in a tin</p><p>Made with Shea and Jojoba.</p><p>Soft hands</p>",
         "variants": [{"title": "Default", "price": "12.00"}], "options": []}]}))
    (b / "email-sms" / "design-formats").mkdir(parents=True)
    write(BANK / "qc.json", json.dumps([{"board": "jan", "i": 1, "n_missing": 0, "placed": 1,
                                         "assets": 1, "ctas_missing": [], "order_ok": True}]))
    (BANK / "jan").mkdir(parents=True)


def snapshot(root):
    return {str(p.relative_to(root)): (hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "dir")
            for p in sorted(root.rglob("*"))}


def load(rel, name):
    spec = importlib.util.spec_from_file_location(name, HERE / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run_main(main, *argv, **kw):
    sys.argv = list(argv)
    with contextlib.redirect_stdout(io.StringIO()):
        return main(**kw)


class Writers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        make_workspace()
        cls.before = snapshot(WS / "brands")
        sys.path.insert(0, str(HERE))
        sys.modules["daemn_keys"] = types.ModuleType("daemn_keys")
        import facts_proposal
        import offers
        import store
        import loop
        import offer_bank_build
        cls.proposal = WS / "runs" / "email-production" / BRAND / facts_proposal.default_label()

        run_main(offers.main, "offers.py", "--brand", BRAND, "--write")

        store.pull = lambda brand: {"brand": brand, "read": "2026-10-07T00:00:00", "source": None,
                                    "site": "https://example.test", "products": []}
        run_main(store.main, "store.py", "--brand", BRAND, "--write")

        loop.pull = lambda brand, pages=10, size=50: [
            {"status": "ACTIVE", "billingPolicy": {"interval": "MONTH", "intervalCount": 1},
             "completedOrdersCount": 2, "totalLineItemDiscountedPrice": "20.00"}]
        run_main(loop.main, "loop.py", "--brand", BRAND, "--write")

        offer_bank_build.from_shopify = lambda brand: [
            {"key": "the-set", "name": "The Set", "price": "$40.00", "was": None, "subs": [],
             "sizes": [], "handle": "the-set", "url": "https://example.test/p"}]
        run_main(offer_bank_build.main, "offer_bank_build.py", "--brand", BRAND, "--write")

        run_main(load("pull/index_catalogue.py", "ep_index_catalogue").main,
                 "index_catalogue.py", "--brand", BRAND)
        run_main(load("pull/products.py", "ep_products").main, "products.py", "--brand", BRAND)
        run_main(load("sweep/qa_index.py", "ep_qa_index").main, "qa_index.py", brand=BRAND)

        out = WS / "brands" / BRAND / "email-sms" / "design-formats"
        cls.refused = {}
        for rel, name, extra in (("sweep/census.py", "ep_census", []),
                                 ("sweep/board_pass.py", "ep_board_pass", ["--board", "jan"])):
            mod = load(rel, name)
            try:
                run_main(mod.main, rel, "--bank", str(BANK), "--out", str(out), *extra)
                cls.refused[rel] = None
            except SystemExit as e:
                cls.refused[rel] = str(e)

    def test_brands_is_untouched(self):
        self.assertEqual(snapshot(WS / "brands"), self.before)

    def test_every_output_is_proposed_at_its_brand_path(self):
        for rel in ("products/offers.json", "products/store.json", "products/loop.json",
                    "products/offer-bank.md", "email-sms/email-types.json",
                    "products/tin.md", "products/README.md",
                    "email-sms/design-formats/rebuild-qa.md", "run.json", "PROPOSAL.md"):
            self.assertTrue((self.proposal / rel).is_file(), rel)
        # the ruled tail is still read from brands/ and carried into the proposal
        self.assertIn("A line a person ruled.", (self.proposal / "products" / "offer-bank.md").read_text())
        # the catalogue cache was read, not refreshed: nothing proposed for it
        self.assertFalse((self.proposal / "email-sms" / "catalogue.json").exists())

    def test_run_json_records_what_the_run_saw(self):
        rec = json.loads((self.proposal / "run.json").read_text())
        self.assertEqual((rec["machine"], rec["brand"], rec["label"]),
                         ("email-production", BRAND, self.proposal.name))
        types_f = WS / "brands" / BRAND / "email-sms" / "email-types.json"
        self.assertEqual(rec["files"]["email-sms/email-types.json"],
                         hashlib.sha256(types_f.read_bytes()).hexdigest())
        self.assertIsNone(rec["files"]["products/offers.json"])
        self.assertIn("products/gone.md", rec["remove"])
        self.assertNotIn("products/tin.md", rec["remove"])

    def test_the_proposal_names_every_target_and_the_removal(self):
        note = (self.proposal / "PROPOSAL.md").read_text()
        rec = json.loads((self.proposal / "run.json").read_text())
        for rel in rec["files"]:
            self.assertIn("brands/%s/%s" % (BRAND, rel), note)
        self.assertIn("| File in this run | Target | State |", note)
        self.assertRegex(note, r"git rm -q brands/%s/products/gone\.md" % BRAND)
        self.assertIn("git add brands/%s && git commit" % BRAND, note)

    def test_the_copy_commands_land_the_files(self):
        copy = TMP / "fold"
        shutil.copytree(WS, copy, symlinks=True)
        note = (self.proposal / "PROPOSAL.md").read_text()
        block = note.split("```sh\n", 1)[1].split("```", 1)[0]
        cps = "\n".join(l for l in block.splitlines() if "git rm" not in l)
        r = subprocess.run(["sh", "-c", cps], cwd=copy, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("STALE", r.stdout)
        run = copy / self.proposal.relative_to(WS)
        for rel in json.loads((run / "run.json").read_text())["files"]:
            self.assertEqual((copy / "brands" / BRAND / rel).read_bytes(), (run / rel).read_bytes(), rel)

    def test_an_out_into_brands_is_refused(self):
        for rel, msg in self.refused.items():
            self.assertIsNotNone(msg, rel)
            self.assertIn("REFUSED (K2 brands write wall)", msg, rel)
        out = WS / "brands" / BRAND / "email-sms" / "design-formats"
        self.assertFalse((out / "census.json").exists())
        self.assertFalse((out / "sweep").exists())

    def test_no_writer_writes_into_brands(self):
        self.assertEqual(len(WRITERS), 17)
        for rel in WRITERS:
            src = (HERE / rel).read_text()
            for n, line in enumerate(src.splitlines(), 1):
                self.assertIsNone(BRAND_WRITE.search(line), "%s:%d %s" % (rel, n, line.strip()))
            self.assertTrue("facts_proposal." in src or "refuse_brand_write(" in src, rel)

    def test_the_dead_helpers_are_gone(self):
        for rel in ("pull/learnings.py", "pull/products.py", "pull/build_email_folders.py"):
            self.assertNotIn("def chan(", (HERE / rel).read_text(), rel)


if __name__ == "__main__":
    unittest.main(verbosity=2)
