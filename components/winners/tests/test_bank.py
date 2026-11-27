import json, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import bank  # noqa: E402

TEARDOWN = """# Teardown — 01-script-30

## 2. Hook

- **First spoken words (verbatim):** "Why did no one tell me this causes dark spots?" (0:00–0:02)
- **On-screen text (verbatim):** "Why did no one tell me / THIS causes dark spots?"

## 4. Core message

Dark spots come from too much **melanin**.

## 9. Offer

- Guarantee: "60-day money-back guarantee"
- Scarcity: "selling fast"
"""


def w(root, rel, obj):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(obj if isinstance(obj, str) else json.dumps(obj))


def row(rank, name, ids, spend, purch, value, variants=None):
    return {"rank": rank, "name": name, "ids": ids, "spend": spend, "purchases": purch, "value": value,
            "first": "2025-01", "last": "2026-01", "variants": variants or [name], "format": "Video",
            "headline": f"H{rank}", "body": "b"}


row_ = row


def audit(root, folder, since, until, rows, core=1):
    a = Path(root) / "runs" / "winners" / "acme" / "audit" / folder
    w(a, "window.json", {"brand": "acme", "since": since, "until": until, "pulled_at": until + "T09:00:00"})
    w(a, "ranked.json", {"total_purchases": 100, "total_spend": 1000, "creatives": 9, "core": core, "rows": rows})
    return a


class T(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        rows = [row(1, "Script 30", ["111", "112"], 1000, 50, 1500),
                row(2, "Touch Face", ["221"], 800, 20, 900),
                row(3, "Plain", ["331"], 600, 10, 500),
                row(4, "Dud", ["441"], 900, 5, 300),
                row(5, "Tiny", ["551"], 50, 1, 40)]
        self.a1 = audit(self.root, "2025", "2025-01-01", "2026-11-02", rows)
        w(self.a1, "teardowns/01-script-30/teardown.md", TEARDOWN)
        self.bank_path = self.root / "runs/winners/acme/bank.json"

    def tearDown(self):
        self._t.cleanup()

    def run_bank(self, *args):
        return bank.main(["--brand", "acme", "--root", str(self.root), *args])

    def load(self):
        return json.loads(self.bank_path.read_text())

    def test_audit_rows_words_and_idempotent(self):
        self.assertEqual(self.run_bank("--audit", str(self.a1)), 0)
        first = self.bank_path.read_text()
        b = self.load()
        self.assertEqual(b["bar"], {"min_spend": None, "max_cpa": None, "min_roas": None})
        r = {x["id"]: x for x in b["rows"]}
        self.assertEqual(set(r), {"acme-111", "acme-221", "acme-331", "acme-441", "acme-551"})
        top = r["acme-111"]
        self.assertTrue(top["core"])
        self.assertFalse(r["acme-221"]["core"])
        self.assertEqual(top["state"], "candidate")
        self.assertNotIn("status", top)
        self.assertIn('"Why did no one tell me this causes dark spots?"', top["words"]["hook"])
        self.assertIn("THIS causes dark spots", top["words"]["hook"])
        self.assertEqual(top["words"]["core_message"], "Dark spots come from too much melanin.")
        self.assertIn('"60-day money-back guarantee"', top["words"]["offer"])
        self.assertEqual(top["source"]["teardown"], "audit/2025/teardowns/01-script-30/teardown.md")
        self.assertEqual(top["source"]["audit"], "audit/2025")
        s = top["snapshots"][0]
        self.assertEqual((s["since"], s["until"], s["rank"], s["cpa"], s["roas"]), ("2025-01-01", "2026-11-02", 1, 20.0, 1.5))
        self.assertEqual(self.run_bank("--audit", str(self.a1)), 0)
        self.assertEqual(self.bank_path.read_text(), first)

    def test_new_window_appends_and_ids_stay(self):
        self.run_bank("--audit", str(self.a1))
        a2 = audit(self.root, "2026", "2026-01-01", "2026-12-01",
                   [row(1, "Script 30", ["999", "112"], 2000, 80, 3000)])
        self.assertEqual(self.run_bank("--audit", str(a2)), 0)
        r = {x["id"]: x for x in self.load()["rows"]}
        self.assertNotIn("acme-999", r)
        self.assertEqual(len(r["acme-111"]["snapshots"]), 2)
        self.assertIn("999", r["acme-111"]["ad_ids"])
        self.assertEqual(r["acme-111"]["words"]["core_message"], "Dark spots come from too much melanin.")

    def test_a_rebank_never_drops_words_already_in_a_row(self):
        self.run_bank("--audit", str(self.a1))
        b = self.load()
        row = {x["id"]: x for x in b["rows"]}["acme-221"]
        row["words"] = {"hook": "Touch your face.", "core_message": "Hands carry dirt.", "offer": "90 days."}
        row["source"]["registry"] = "elsewhere#02"
        self.bank_path.write_text(json.dumps(b))
        self.assertEqual(self.run_bank("--audit", str(self.a1)), 0)
        r = {x["id"]: x for x in self.load()["rows"]}["acme-221"]
        self.assertEqual(r["words"]["hook"], "Touch your face.")
        self.assertEqual(r["source"]["registry"], "elsewhere#02")
        a2 = audit(self.root, "2026", "2026-01-01", "2026-12-01", [row_(1, "Touch Face", ["221"], 100, 9, 200)])
        self.assertEqual(self.run_bank("--audit", str(a2)), 0)
        r = {x["id"]: x for x in self.load()["rows"]}["acme-221"]
        self.assertEqual(r["words"]["core_message"], "Hands carry dirt.")

    def test_core_is_counted_from_the_widest_window(self):
        self.run_bank("--audit", str(self.a1))
        r = {x["id"]: x for x in self.load()["rows"]}
        self.assertTrue(r["acme-111"]["core"])
        a2 = audit(self.root, "2024", "2024-01-01", "2026-12-01", [row_(1, "Touch Face", ["221"], 100, 9, 200),
                                                                   row_(2, "Script 30", ["111"], 100, 1, 200)])
        self.run_bank("--audit", str(a2))
        r = {x["id"]: x for x in self.load()["rows"]}
        self.assertTrue(r["acme-221"]["core"])
        self.assertFalse(r["acme-111"]["core"])
        self.assertFalse(r["acme-331"]["core"])

    def test_bar_marks_state_from_the_newest_snapshot(self):
        self.run_bank("--audit", str(self.a1))
        b = bank.load_bank(self.bank_path, "acme")
        b["bar"]["max_cpa"] = 25
        bank.write(self.root, b)
        d = self.load()
        r = {x["id"]: x for x in d["rows"]}
        self.assertEqual(r["acme-111"]["state"], "winner")      # CPA 20
        self.assertEqual(r["acme-221"]["state"], "candidate")   # CPA 40
        self.assertIn("clears the bar", d["note"])
        self.assertTrue(bank.clears({"min_spend": 500, "min_roas": 1.0}, {"spend": 600, "roas": 1.0}))
        self.assertFalse(bank.clears({"min_spend": 500}, {"spend": 499}))
        self.assertFalse(bank.clears({"max_cpa": 50}, {"cpa": None}))
        a2 = audit(self.root, "2026", "2026-01-01", "2026-12-01", [row_(1, "Script 30", ["111"], 900, 9, 200)])
        self.run_bank("--audit", str(a2))
        self.assertEqual({x["id"]: x for x in self.load()["rows"]}["acme-111"]["state"], "candidate")  # now CPA 100

    def test_an_audit_row_keeps_its_name_when_the_score_finds_it(self):
        self.run_bank("--audit", str(self.a1))
        w(self.root, "runs/winners/acme/score/2026-10-20/score.json", {
            "brand": "acme", "asof": "2026-10-20", "data_through": "2026-10-19", "matched": [
                {"ad_id": "111", "ad_name": "acme_x_brief-0001_batch-a", "spend": 10.0, "purchases": 1.0, "value": 30.0,
                 "run": "runs/video-writing/acme/r1"}]})
        self.assertEqual(self.run_bank("--score", "runs/winners/acme/score/2026-10-20/score.json"), 0)
        r = {x["id"]: x for x in self.load()["rows"]}["acme-111"]
        self.assertEqual(r["name"], "Script 30")
        sn = [x for x in r["snapshots"] if x["kind"] == "score"]
        self.assertEqual(sn[0]["value"], 30.0)
        self.assertEqual(r["source"]["score"], "score/2026-10-20/score.json")

    def test_score_rows(self):
        self.run_bank("--audit", str(self.a1))
        w(self.root, "runs/video-writing/acme/r1/stages/4b-hooks.md",
          "THUMB V1: x\nBORROWED_FROM V1: acme-111 · the question hook\nBORROWED_FROM V2: none\n")
        w(self.root, "runs/winners/acme/score/2026-10-20/score.json", {
            "brand": "acme", "asof": "2026-10-20", "data_through": "2026-10-19", "matched": [
                {"ad_id": "777", "ad_name": "acme_x_brief-0001_batch-a", "spend": 100.0, "purchases": 4.0, "cpa": 25.0,
                 "roas": 2.0, "brief_key": "acme_x_brief-0001", "run": "runs/video-writing/acme/r1",
                 "hook_prompt": {"name": "stage4b-hook", "version": 26, "label": "stage4b-hook v26"},
                 "brief_prompt": {"name": "stage5-ai-brief", "version": 35, "label": "stage5-ai-brief v35"}}]})
        args = ("--score", "runs/winners/acme/score/2026-10-20/score.json")
        self.assertEqual(self.run_bank(*args), 0)
        first = self.bank_path.read_text()
        self.assertEqual(self.run_bank(*args), 0)
        self.assertEqual(self.bank_path.read_text(), first)
        r = {x["id"]: x for x in self.load()["rows"]}["acme-777"]
        self.assertEqual(r["brief_key"], "acme_x_brief-0001")
        self.assertEqual(r["hook_prompt"]["version"], 26)
        self.assertEqual(r["borrowed_from"], [{"variation": "V1", "id": "acme-111"}])
        self.assertEqual(r["snapshots"][0]["value"], 200.0)
        self.assertEqual(r["state"], "candidate")

    def test_bad_input(self):
        self.assertEqual(self.run_bank(), 2)
        self.assertEqual(self.run_bank("--audit", str(self.root / "nope")), 2)
        w(self.a1, "window.json", {"brand": "other", "since": "a", "until": "b", "pulled_at": "c"})
        self.assertEqual(self.run_bank("--audit", str(self.a1)), 2)
        self.assertFalse(self.bank_path.exists())


if __name__ == "__main__":
    unittest.main()
