"""The one model table (run_kit/tiers.json): every chain asks for exactly what it asked for on 2026-11-26.

    python3 test_tiers.py

TODAY is the snapshot taken before the table existed. When owner answers the build-week worksheet (A1-A3) and a
chain's models change on purpose, change TODAY in the same commit, so the change is visible in review.
"""
import json
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_kit import claude_flags, model, tiers   # noqa: E402

TODAY = {
    "shared": {"reads": "claude-haiku-4-5-20251001", "checks": "claude-sonnet-5", "designs": "claude-opus-5"},
    "marketing-calendar": {"reads": "claude-haiku-4-5-20251001", "checks": "claude-sonnet-5", "designs": "claude-opus-5"},
    "copywriter": {"reads": "claude-haiku-4-5-20251001", "checks": "claude-sonnet-5", "designs": "claude-opus-5"},
    "copywriter-formats": {"reads": "claude-haiku-4-5-20251001", "checks": "claude-sonnet-5-5", "designs": "claude-opus-5-5"},
    "session-teardown": {"reads": "claude-haiku-5-5", "checks": "claude-sonnet-5-5", "designs": "claude-opus-5-5"},
    "email-production": {"reads": "claude-haiku-4-5-20251001", "checks": "claude-sonnet-5", "designs": "claude-opus-5"},
}
# Ids the table names that the model registry (components/models/models.json) does not list. Flagged, not changed:
# the registry has "claude-haiku-4-5"; run-kit has always asked for the dated id (session-teardown's CLAUDE.md, proposal).
NOT_IN_REGISTRY = {"claude-haiku-4-5-20251001"}


class Table(unittest.TestCase):
    def setUp(self):
        self.saved = os.environ.pop("CHAIN_MODEL", None)

    def tearDown(self):
        if self.saved is not None:
            os.environ["CHAIN_MODEL"] = self.saved

    def test_shared_is_what_run_kit_asked_for(self):
        self.assertEqual(tiers.shared(), TODAY["shared"])
        self.assertEqual(model.TIERS, TODAY["shared"])

    def test_every_chain_is_pinned_to_today(self):
        for chain in tiers.chains():
            with self.subTest(chain=chain):
                self.assertIn(chain, TODAY, f"{chain} is in the table but not in TODAY")
                self.assertEqual(tiers.for_chain(chain), TODAY[chain])

    def test_a_chain_the_table_does_not_name_gets_shared(self):
        self.assertEqual(tiers.for_chain("no-such-chain"), TODAY["shared"])

    def test_default_follows_the_chains_one_model(self):
        os.environ["CHAIN_MODEL"] = "claude-sonnet-5-5"
        try:
            self.assertEqual(tiers.model("session-teardown", "designs"), claude_flags.model())
            self.assertEqual(tiers.model("session-teardown", "designs"), "claude-sonnet-5-5")
        finally:
            del os.environ["CHAIN_MODEL"]

    def test_lean_only_for_email(self):
        self.assertEqual([c for c in tiers.chains() if tiers.lean(c)], ["email-production"])

    def test_every_id_is_in_the_registry_or_flagged(self):
        reg = {m["id"] for m in json.loads((HERE.parent / "models" / "models.json").read_text())["models"]}
        t = tiers.table()
        named = set(t["shared"].values())
        for e in t["chains"].values():
            named |= set((e.get("tiers") or {}).values())
        named.discard("default")
        self.assertEqual(sorted(named - reg - NOT_IN_REGISTRY), [])

    def test_every_entry_carries_a_status(self):
        for chain, e in tiers.table()["chains"].items():
            with self.subTest(chain=chain):
                self.assertIn(e.get("status"), ("draft", "approved", "deprecated"))
                self.assertTrue(set(e.get("tiers") or {}) <= set(tiers.JOBS))

    def test_the_chains_point_at_the_table(self):
        ws = HERE.parent
        want = {
            "copywriter/machine/copy_writer.py": 'for_chain("copywriter")',
            "copywriter/machine/google_copy.py": '"copywriter-formats"',
            "copywriter/machine/format_copy.py": '"copywriter-formats"',
            "copywriter/machine/copy_set.py": '"copywriter-formats"',
            "copywriter/machine/real_formats.py": '"copywriter-formats"',
            "session-teardown/machine/run.py": 'for_chain("session-teardown")',
            "marketing-calendar/machine/runner.py": 'for_chain("marketing-calendar")',
        }
        for f, needle in want.items():
            with self.subTest(file=f):
                self.assertIn(needle, (ws / f).read_text())


if __name__ == "__main__":
    unittest.main()
