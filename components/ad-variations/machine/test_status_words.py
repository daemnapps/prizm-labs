"""python3 machine/test_status_words.py — no key, no network, no model, no media.

SI-78 (variations entry status): elements, gates and routes carry a rule-6
status on every entry, and the readers price, gate and prompt as before.
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import assemble  # noqa: E402
import run  # noqa: E402

COMP = HERE.parent
RULE6 = {"draft", "approved", "deprecated"}
FILES = {"elements.json": "elements", "gates.json": "gates", "routes.json": "routes"}


def load(name):
    return json.loads((COMP / "definitions" / name).read_text(encoding="utf-8"))


class T(unittest.TestCase):
    def test_every_entry_carries_a_rule6_status(self):
        total = 0
        for name, key in FILES.items():
            d = load(name)
            self.assertNotIn("status", d, f"{name}: a file-level status is not an entry's status")
            for e in d[key]:
                self.assertIn(e.get("status"), RULE6, f"{name}: {e.get('id') or e.get('key')}")
                total += 1
        self.assertGreaterEqual(total, 46)

    def test_routes_table_status_column_is_the_lock_flag(self):
        routes = load("routes.json")["routes"]
        rows = [l for l in run.routes_table().splitlines() if l.startswith("| ") and not l.startswith("| id ")]
        self.assertEqual(len(rows), len(routes))
        for row, x in zip(rows, routes):
            self.assertTrue(row.startswith(f"| {x['id']} | "), row)
            flag = "TEST" if x.get("test") else "locked" if x.get("locked") else "not locked"
            self.assertTrue(row.endswith(f"| {flag} |"), row)

    def test_gates_table_one_line_per_gate(self):
        gates = load("gates.json")["gates"]
        lines = run.gates_table().splitlines()
        self.assertEqual(len(lines), len(gates))
        for line, g in zip(lines, gates):
            self.assertTrue(line.startswith(f"- {g['id']} · {g['name']} — passes: "), line)

    def test_costs_and_forced_gates_unchanged(self):
        for x in load("routes.json")["routes"]:
            usd = assemble.item_cost(x["id"], 2)["usd"]
            self.assertEqual(usd is None, x["usd_per_unit"] is None, x["id"])
        every = {g["id"] for g in load("gates.json")["gates"] if "*" in (g.get("forced_by") or [])}
        self.assertTrue(every)
        self.assertEqual(set(assemble.forced_for({"id": "v1", "make": []}, [])), every)


if __name__ == "__main__":
    unittest.main()
