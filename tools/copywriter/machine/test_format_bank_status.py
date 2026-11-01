#!/usr/bin/env python3
"""format-bank.json is a manifest — SI-77 (format-bank status).

    python3 test_format_bank_status.py

the team, triage page 15 (2026-10-07, Option A): a file any program reads per
entry is a manifest, so every entry carries a components rule-6 `status`.
The element library builds `placement/all` from this file, row by row.

Proves: every entry carries draft / approved / deprecated; `provenance`
(where the spec came from) is kept and is not the status; the element
library's placement rows carry the bank's status; and the channel map page
is the same with and without the field. No key, no network; every write
goes to a temp folder.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(COMPONENT.parent / "elements" / "machine"))
import channel_map_page as CM  # noqa: E402
import elements as E  # noqa: E402

BANK = COMPONENT / "bank" / "format-bank.json"
RULE6 = {"draft", "approved", "deprecated"}
PROVENANCE = ("proven", "evidenced", "drafted")


def formats():
    return json.loads(BANK.read_text(encoding="utf-8"))["formats"]


class FormatBankStatus(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        E._cache.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_every_entry_carries_a_rule_6_status(self):
        rows = formats()
        self.assertTrue(rows)
        for entry in rows:
            self.assertIn(entry.get("status"), RULE6, entry["key"])

    def test_provenance_is_kept_and_is_not_the_status(self):
        for entry in formats():
            self.assertIn(entry["provenance"].split()[0], PROVENANCE, entry["key"])
            self.assertNotIn(entry["status"], PROVENANCE, entry["key"])

    def test_placement_rows_carry_the_banks_status(self):
        lib = self.tmp / "library"
        lib.mkdir()
        with mock.patch.object(E, "LIBRARY", lib):
            E._cache.clear()
            E.build()
            rows = E.rows("placement", "all")
        got = {r["id"]: r["status"] for r in rows}
        self.assertEqual(got, {entry["key"]: entry["status"] for entry in formats()})
        for r in rows:
            self.assertEqual(r["approved"], r["status"] == "approved", r["id"])

    def test_channel_map_is_the_same_without_the_status_field(self):
        root = self.tmp / "component"
        (root / "bank").mkdir(parents=True)
        (root / "library").mkdir()
        for name in ("channel-map.json", "format-bank.json"):
            shutil.copyfile(COMPONENT / "bank" / name, root / "bank" / name)
        index = COMPONENT / "library" / "index.json"
        if index.is_file():
            shutil.copyfile(index, root / "library" / "index.json")
        page = self.tmp / "out" / "page.html"
        page.parent.mkdir()

        with mock.patch.object(CM, "HERE", root), mock.patch.object(CM, "OUT", page):
            CM.build()
            with_status = page.read_text(encoding="utf-8")
            bank = root / "bank" / "format-bank.json"
            d = json.loads(bank.read_text(encoding="utf-8"))
            for entry in d["formats"]:
                entry.pop("status", None)
            bank.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            CM.build()
            without_status = page.read_text(encoding="utf-8")

        self.assertEqual(with_status, without_status)
        self.assertIn("Primary text", with_status)


if __name__ == "__main__":
    unittest.main()
