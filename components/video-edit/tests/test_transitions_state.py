"""SI-80 (transitions install state): a transitions row's `status` holds only rule 6's
words; "not installed" lives in `state`, beside `drawn: false` — and the gate
(cutsheet.check_elements, which reads `drawn`) still refuses every one of those rows
and still draws every drawn one. Imports cutsheet only; nothing renders."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import cutsheet as CS  # noqa: E402

RULE6 = {"draft", "approved", "deprecated"}


def rows_with_status(node, out):
    if isinstance(node, dict):
        if "id" in node and isinstance(node.get("status"), str):
            out.append(node)
        for v in node.values():
            rows_with_status(v, out)
    elif isinstance(node, list):
        for v in node:
            rows_with_status(v, out)
    return out


def sheet_with(kind: str) -> dict:
    return {"picture": [{"id": "S1", "start": 0, "duration": 2}, {"id": "S2", "start": 2, "duration": 2}],
            "layers": {"transitions": [{"after_scene": "S1", "kind": kind}]}}


def gate_red(kind: str) -> list:
    sheet = sheet_with(kind)
    with tempfile.TemporaryDirectory() as tmp:
        red = CS.check_elements(sheet, Path(tmp), lambda p: 30.0, CS.end_of(sheet))
    return [x for x in red if x.startswith("layers.transitions[0]")]


class TestTransitionsState(unittest.TestCase):
    def setUp(self):
        self.rows = CS.load("looks/transitions.json")["transitions"]

    def test_every_looks_status_is_a_rule6_word(self):
        seen = []
        for f in sorted((CS.TOOL / "looks").glob("*.json")):
            for r in rows_with_status(json.loads(f.read_text(encoding="utf-8")), []):
                self.assertIn(r["status"], RULE6, f"{f.name}: row {r['id']} has status {r['status']!r}")
                seen.append(r)
        self.assertGreaterEqual(len(seen), 150)

    def test_not_installed_is_state_not_status(self):
        self.assertFalse([r["id"] for r in self.rows if r.get("status") == "catalogue"])
        for r in self.rows:
            if "state" in r:
                self.assertEqual(r["state"], "not installed", r["id"])
        not_installed = {r["id"] for r in self.rows if r.get("state") == "not installed"}
        undrawn = {r["id"] for r in self.rows if r.get("drawn") is False}
        self.assertEqual(not_installed, undrawn)
        self.assertEqual(len(not_installed), 13)
        for r in self.rows:
            if r["id"] in not_installed:
                self.assertEqual(r["status"], "draft", r["id"])
                self.assertTrue(str(r.get("registry") or "").strip(), r["id"])

    def test_the_gate_still_refuses_every_not_installed_row(self):
        for r in self.rows:
            if r.get("state") == "not installed":
                red = gate_red(r["id"])
                self.assertEqual(len(red), 1, (r["id"], red))
                self.assertIn("not installed", red[0])

    def test_the_gate_still_draws_every_drawn_transition(self):
        drawn = [r for r in self.rows if r.get("drawn") is True and r.get("type") == "transition"]
        self.assertTrue(drawn)
        for r in drawn:
            self.assertEqual(gate_red(r["id"]), [], r["id"])
        red = gate_red("punch-in")
        self.assertEqual(len(red), 1, red)
        self.assertIn("move inside one shot", red[0])


if __name__ == "__main__":
    unittest.main()
