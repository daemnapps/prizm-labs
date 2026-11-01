#!/usr/bin/env python3
"""python3 test_he3_brand_facts.py — HE-3 (shared brand facts): one read of
what a brand's files and a person's rulings say is true, used by the email
writer's own check (stage 8c, via `catalogue_facts`) and by qc-checks'
`load_dictionary`. Stdlib unittest; no network, no model, no git. Every file
lands in a temp workspace, passed explicitly as the root."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="he3-brand-facts-")).resolve()
(TMP / "brands").mkdir()
(TMP / "components").mkdir()                   # brandpath's repo() wants both
os.environ["AI_WORKSPACE"] = str(TMP)          # before anything reads the workspace

HERE = Path(__file__).resolve().parent
REPO = next(d for d in HERE.parents if (d / "components" / "brand-finder").is_dir())
sys.path.insert(0, str(REPO / "components" / "qc-checks"))
import text_check as tc                                     # noqa: E402  (first: it loads stdlib `email`)
sys.path.insert(0, str(HERE))
import marketing_chain_checks as Q                          # noqa: E402
from marketing_chain_checks import rulings as R             # noqa: E402
from marketing_chain_checks.facts import brand_facts        # noqa: E402
sys.path.append(str(REPO / "tools" / "email-production" / "machine"))
import brand_facts as BF                                    # noqa: E402

BRAND = "fixturebrand"
SELLABLE = [{"handle": "alpha", "title": "Alpha Tool", "url": "https://example.test/alpha"},
            {"handle": "beta", "title": "Beta Kit", "url": "https://example.test/beta"}]
FILES = {
    "products/heroes.json": json.dumps({"heroes": ["alpha"], "sellable": SELLABLE,
                                        "never": {"handles": ["ghost"], "why": "a draft"}}),
    "products/alpha.md": "# Alpha\nThe flat-file product.\n",
    "products/beta/product.md": "\n# Beta\nThe folder product.\n\n",
    "products/ghost.md": "# Ghost\nA draft nobody may read.\n",
    "brand-identity/position.md": "The ruled mechanism.\n",
    "brand-identity/story.md": "Who tells it.\n",
    "operations/operations.md": "Ships in two days.\n",
    "products/offer-bank.md": "## core — Core offer\nThe one offer.\n",
}
EXPECTED = ("----- Alpha Tool (`alpha`) -----\n# Alpha\nThe flat-file product.\n\n"
            "----- Beta Kit (`beta`) -----\n# Beta\nThe folder product.\n\n"
            "----- The brand's ruled position and mechanism -----\nThe ruled mechanism.\n\n"
            "----- The brand's story, and who tells it -----\nWho tells it.\n\n"
            "----- How this brand ships and stocks -----\nShips in two days.\n\n"
            "----- What may be sold, and the guarantee -----\n## core — Core offer\nThe one offer.")
N = [0]


def workspace(brand=BRAND, files=FILES):
    root = Path(tempfile.mkdtemp(dir=TMP, prefix="ws-"))
    for rel, text in files.items():
        f = root / "brands" / brand / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    (root / "components").mkdir(exist_ok=True)
    return root


def plant(root, pid, ruling, fact="", kind="fact", brand=BRAND):
    """A ruling record as rule.py files it (HE-1 (fact rulings))."""
    N[0] += 1
    d = root / R.RECORDS_REL
    d.mkdir(parents=True, exist_ok=True)
    at = "2026-10-02T10:%02d:00Z" % N[0]
    rec = {"schema": 1, "kind": "fact-rulings", "reviewer": "steph", "item": pid,
           "verdict": {"brand": brand, "problem_id": pid, "email": "e1", "kind": kind,
                       "quote": "q", "files_say": None, "ruling": ruling, "fact": fact,
                       "reason": "", "by": "steph", "at": at},
           "notes": "", "created": at, "via": "test"}
    (d / ("%04d--steph--%s.json" % (N[0], pid))).write_text(json.dumps(rec))


class ProductFacts(unittest.TestCase):
    def test_a_both_shapes_and_brand_files_in_todays_layout(self):
        root = workspace()
        got = brand_facts(BRAND, root=root)
        self.assertEqual(got["product_facts"], EXPECTED)
        self.assertNotIn("Ghost", got["product_facts"])          # not live, never read
        self.assertEqual(got["products"], ["Alpha Tool", "Beta Kit"])

    def test_a_no_files_says_so(self):
        root = workspace(files={})
        self.assertEqual(brand_facts(BRAND, root=root)["product_facts"],
                         "(no product files on file for this brand)")
        self.assertEqual(BF.catalogue_facts(BRAND, root),
                         "(no product files on file for this brand)")

    def test_b_no_rulings_no_verified_section(self):
        root = workspace()
        got = brand_facts(BRAND, root=root)
        self.assertEqual((got["verified_facts"], got["not_ours"]), ([], []))
        self.assertEqual(BF.catalogue_facts(BRAND, root), EXPECTED)
        self.assertEqual(BF.catalogue_facts(BRAND, root, limit=40), EXPECTED[:40])
        self.assertNotIn(BF.VERIFIED_TITLE, BF.catalogue_facts(BRAND, root))


class Rulings(unittest.TestCase):
    def test_c_true_fact_reaches_both(self):
        root = workspace()
        plant(root, "aaa111", "true", fact="The kit ships in a tin.")
        got = brand_facts(BRAND, root=root)
        self.assertEqual([v["fact"] for v in got["verified_facts"]], ["The kit ships in a tin."])
        text = BF.catalogue_facts(BRAND, root)
        self.assertEqual(text, EXPECTED + "\n\n----- " + BF.VERIFIED_TITLE + " -----\n"
                         "- The kit ships in a tin.")
        self.assertEqual(BF.catalogue_facts(BRAND, root, limit=len(EXPECTED) + 5),
                         text[:len(EXPECTED) + 5])         # the limit is on the whole text

    def test_d_a_ruled_price_reaches_neither_and_price_check_is_unmoved(self):
        root = workspace()
        bank = "## core — Core offer\nOne for $49.\n"
        said = "Only $29 today."
        before = Q.price_check(said, Q.offer_block(bank, "core"), "core")
        plant(root, "bbb222", "true", fact="The kit is $29 now.")
        got = brand_facts(BRAND, root=root)
        self.assertEqual(got["verified_facts"], [])
        self.assertNotIn("$29", BF.catalogue_facts(BRAND, root))
        self.assertNotIn(BF.VERIFIED_TITLE, BF.catalogue_facts(BRAND, root))
        self.assertEqual(Q.price_check(said, Q.offer_block(bank, "core"), "core"), before)
        self.assertTrue(before)                              # and it still flags the $29

    def test_e_not_ours(self):
        root = workspace()
        plant(root, "ccc333", "not-ours")
        got = brand_facts(BRAND, root=root)
        self.assertEqual([n["id"] for n in got["not_ours"]], ["ccc333"])
        self.assertEqual(got["verified_facts"], [])

    def test_other_brands_rulings_stay_theirs(self):
        root = workspace()
        plant(root, "ddd444", "true", fact="Another brand's fact.", brand="otherbrand")
        self.assertEqual(brand_facts(BRAND, root=root)["verified_facts"], [])


class Dictionary(unittest.TestCase):
    def test_f_no_dictionary_overlays_names_and_stays_unseeded(self):
        root = workspace()
        plant(root, "eee555", "true", fact="A ruled fact.")
        dic = tc.load_dictionary(BRAND, root=root)
        self.assertFalse(dic["found"])
        self.assertEqual(dic["path"], str(tc.dict_path(BRAND, root=root)))
        self.assertFalse(Path(dic["path"]).exists())
        self.assertEqual(dic["status"], "")
        self.assertEqual([r["canonical"] for r in dic["names"]], ["Alpha Tool", "Beta Kit"])
        self.assertTrue(all(r["prices"] == [] and r["wrong"] == [] for r in dic["names"]))
        self.assertEqual(dic["never_prices"], [])
        _, report = tc.run_checks(tc.units_from_text("Alpha Tool at $29, Alpa Tool."),
                                  dic=dic, grammar=False)
        for name in ("dictionary-name", "dictionary-price"):
            self.assertEqual(report["checks"][name],
                             {"ran": False, "why": "no dictionary for this brand"})
        self.assertFalse(report["dictionary"]["found"])
        self.assertEqual(tc.truth_from_dictionary(dic, root=root), [])

    def test_g_dictionary_rows_first_overlay_adds_only_missing(self):
        root = workspace()
        doc = {"schema": 1, "kind": "qc-dictionary", "brand": BRAND, "status": "provisional",
               "names": [{"canonical": "alpha tool", "wrong": ["Alfa Tool"], "comment": "x"}],
               "never_prices": [], "checks_off": []}
        p = tc.dict_path(BRAND, root=root)
        p.write_text(json.dumps(doc))
        plain = tc.load_dictionary(path=str(p))
        dic = tc.load_dictionary(BRAND, root=root)
        for k in ("found", "status", "path", "brand", "never_prices", "banned", "checks_off"):
            self.assertEqual(dic[k], plain[k], k)
        self.assertTrue(dic["found"])
        self.assertEqual(dic["names"][:1], plain["names"])
        self.assertEqual([r["canonical"] for r in dic["names"]], ["alpha tool", "Beta Kit"])
        self.assertEqual(dic["names"][1]["prices"], [])
        _, report = tc.run_checks(tc.units_from_text("Beta Kit and the Alfa Tool."),
                                  dic=dic, grammar=False)
        self.assertEqual(report["checks"]["dictionary-name"], {"ran": True, "found": 1})

    def test_h_path_gets_no_overlay(self):
        root = workspace()
        p = root / "elsewhere.json"
        p.write_text(json.dumps({"schema": 1, "status": "draft",
                                 "names": [{"canonical": "Zed"}]}))
        self.assertEqual([r["canonical"] for r in tc.load_dictionary(path=str(p))["names"]], ["Zed"])
        self.assertEqual(tc.load_dictionary(BRAND, path=os.devnull, root=root)["names"], [])
        self.assertEqual(tc.load_dictionary(path=str(root / "missing.json"))["names"], [])


class Invariants(unittest.TestCase):
    def test_no_brand_name_in_the_shared_read(self):
        src = (HERE / "marketing_chain_checks" / "facts.py").read_text().lower()
        brands = [p.name for p in (REPO / "brands").iterdir()
                  if p.is_dir() and not p.name.startswith((".", "_"))]
        self.assertTrue(brands)
        for b in brands:
            self.assertNotIn(b.lower(), src, b)


if __name__ == "__main__":
    unittest.main()
