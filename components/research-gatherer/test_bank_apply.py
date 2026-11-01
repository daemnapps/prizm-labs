#!/usr/bin/env python3
"""Tests for bank_apply.py — the gatherer's apply step for a language-bank
proposal. No network, no model, temp folders only (the component's test
rule). Every gate: what is refused whole, what is skipped row by row."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from research_gatherer import bank_apply as BA   # noqa: E402

LANG = "brands/b/core-avatars/a/language"


def sha(t):
    return hashlib.sha1(t.encode()).hexdigest()[:12]


ROWS = [
    {"id": "language_b_a_lead_0001", "text": "link?", "source": {"name": "ad comment", "ref": "https://x.test/c/1"}},
    {"id": "language_b_a_lead_0002", "text": "price?", "source": {"name": "ad comment", "ref": "https://x.test/c/2"},
     "awareness": {"level": "most-aware", "by": "a person"}},
]


class Apply(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        f = self.root / LANG / "leads.json"
        f.parent.mkdir(parents=True)
        f.write_text(json.dumps({"entries": ROWS}, indent=2) + "\n")
        self.bank = f
        self.before = f.read_text()

    def tearDown(self):
        self.t.cleanup()

    def prop(self, rows=(), used=(), write=(), brand="b"):
        p = self.root / "runs" / "language-layer" / brand / "x" / "proposal.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"kind": "language-bank-proposal", "version": 1, "brand": brand,
                                 "tool": "test", "rows": list(rows), "used": list(used), "write": list(write)}))
        return p

    def row(self, i, **fields):
        r = ROWS[i]
        return {"file": f"{LANG}/leads.json", "id": r["id"], "index": i, "text_sha": sha(r["text"]), "set": fields}

    def refused(self, p):
        with self.assertRaises(BA.Refused):
            BA.apply(p, root=self.root)
        self.assertEqual(self.bank.read_text(), self.before, "a refused proposal wrote into the bank")

    def test_applies_fields_and_keeps_the_file_format(self):
        rep = BA.apply(self.prop([self.row(0, origin="internal", use=["keyword-cta"])]), root=self.root)
        self.assertEqual((rep["applied"], rep["skipped"]), (1, 0))
        got = json.loads(self.bank.read_text())["entries"][0]
        self.assertEqual((got["origin"], got["use"], got["text"]), ("internal", ["keyword-cta"], "link?"))
        self.assertIn('\n  "entries"', self.bank.read_text())   # indent kept
        self.assertTrue((self.root / "runs/language-layer/b/x/applied.md").is_file())

    def test_dry_run_writes_nothing(self):
        rep = BA.apply(self.prop([self.row(0, origin="internal")]), root=self.root, dry_run=True)
        self.assertEqual(rep["applied"], 1)
        self.assertEqual(self.bank.read_text(), self.before)

    def test_a_person_label_is_never_overwritten(self):
        rep = BA.apply(self.prop([self.row(1, awareness={"level": "unaware", "by": "model"})]), root=self.root)
        self.assertEqual((rep["applied"], rep["skipped"]), (0, 1))
        self.assertEqual(self.bank.read_text(), self.before)

    def test_changed_words_are_skipped(self):
        r = self.row(0, origin="internal")
        r["text_sha"] = sha("other words")
        self.assertEqual(BA.apply(self.prop([r]), root=self.root)["skipped"], 1)

    def test_refusals_write_nothing(self):
        self.refused(self.prop([dict(self.row(0, origin="internal"), file="brands/b/products/heroes.json")]))
        self.refused(self.prop([dict(self.row(0, origin="internal"), file="brands/other/core-avatars/a/language/leads.json")]))
        self.refused(self.prop([self.row(0, text="new words")]))
        self.refused(self.prop([self.row(0, id="lead-1")]))
        self.refused(self.prop([self.row(0, source={"name": "ad comment"})]))           # drops the link
        self.refused(self.prop([self.row(0, id="language_b_a_lead_0002")]))             # two rows, one id
        self.refused(self.prop(write=[{"file": f"{LANG}/leads.json", "content": {}}]))
        self.refused(self.prop(write=[{"file": "brands/b/core-avatars/language-sources.json",
                                       "content": {"brand": "other", "sources": []}}]))

    def test_registry_and_used_marks(self):
        u = self.root / LANG / "used" / "u.json"
        u.parent.mkdir()
        u.write_text(json.dumps({"used": [{"row_id": "old-1"}]}))
        BA.apply(self.prop([self.row(0, id="language_b_a_lead_0003")],
                           used=[{"file": f"{LANG}/used/u.json", "index": 0, "row_id": "old-1",
                                  "new_row_id": "language_b_a_lead_0003"}],
                           write=[{"file": "brands/b/core-avatars/language-sources.json",
                                   "content": {"brand": "b", "sources": [{"id": "post_x_y_1"}]}}]), root=self.root)
        self.assertEqual(json.loads(u.read_text())["used"][0]["row_id"], "language_b_a_lead_0003")
        self.assertEqual(json.loads((self.root / "brands/b/core-avatars/language-sources.json").read_text())["brand"], "b")
        self.assertEqual(json.loads(self.bank.read_text())["entries"][0]["id"], "language_b_a_lead_0003")


if __name__ == "__main__":
    unittest.main(verbosity=1)
