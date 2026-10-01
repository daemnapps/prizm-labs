#!/usr/bin/env python3
"""The rollout's promises, as tests. No network, no model, nothing spent.

    python3 test_rollout.py

Every run these tests make files under a temp folder (both run homes are
pointed there before anything runs), so no real run is ever touched. No brand
is named here: the chain tests pick whichever brand on file has a signed angle,
an avatar, a product card and an offer bank, and skip if none does.
"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import page_paths as P                                     # noqa: E402
import page_gates as G                                     # noqa: E402
import run as R                                            # noqa: E402
import deliver as D                                        # noqa: E402

WAS = {  # the hand-kept table this rollout replaced — the tiers must land on the same models
    "stage0": "claude-sonnet-5", "stage1": "claude-sonnet-5", "stage2": "claude-opus-5",
    "stage2b": "claude-sonnet-5", "stage3": "claude-opus-5", "stage4": "claude-opus-5",
    "stage5": "claude-opus-5", "stage6": "claude-sonnet-5", "stage7": "claude-opus-5",
}
CANNED = """# THE PAGE

[1 · hero]

The one that works. Only $999,999.00 today. [UNFILLED: the guarantee]

# THE CHECK

clean

**SECTIONS CARRIED**

- [1 · hero] — `hook`
- [2 · why] — `made-up-section`
"""


def a_brand():
    """(brand, avatar, angle, product) from whatever is on file — never named here."""
    for b in sorted((P.WORKSPACE / "brands").iterdir()):
        angles = b / "strategy" / "angles.json"
        if not angles.is_file() or not (b / "offers" / "offer-bank.md").is_file():
            continue
        try:
            active = [x["id"] for x in json.loads(angles.read_text()).get("angles", []) if x.get("status") == "active"]
        except ValueError:
            continue
        avatars = sorted(d.name for d in (b / "core-avatars").glob("*") if (d / "profile.md").is_file())
        products = sorted((b / "products").glob("*.md"))
        if active and avatars and products:
            return b.name, avatars[0], active[0], str(products[0].relative_to(P.WORKSPACE))
    return None


class Homes(unittest.TestCase):
    """Every test files into a temp folder: both run homes are re-pointed."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.new, self.old = root / "runs" / P.TOOL, root / "old-runs"
        self.new.mkdir(parents=True); self.old.mkdir()
        self.patches = [mock.patch.object(P, "RUNS", self.new), mock.patch.object(P, "OLD_RUNS", self.old)]
        for p in self.patches:
            p.start()
        self.source = root / "swipe" / "page.txt"
        self.source.parent.mkdir()
        self.source.write_text("A page about a thing.\n\nBuy it now for a price.\n")

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def argv(self, label, *extra):
        found = a_brand()
        if not found:
            self.skipTest("no brand on file has a signed angle, an avatar, a product card and an offer bank")
        brand, avatar, angle, product = found
        self.brand = brand
        return [str(self.source), "--brand", brand, "--avatar", avatar, "--angle", angle, "--funnel", "test",
                "--next", "select", "--label", label, "--source-url", "https://example.com/x",
                "--product", product, *extra]


class DryRun(Homes):
    def test_dry_makes_zero_calls_and_files_at_the_repo_root_home(self):
        calls = []

        def no_subprocess(cmd, *a, **k):
            calls.append(cmd)
            if cmd and cmd[0] == "claude":
                raise AssertionError("a dry run called the model")
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(R, "claude", side_effect=AssertionError("a dry run called the model")), \
                mock.patch.object(R.subprocess, "run", side_effect=no_subprocess), redirect_stdout(io.StringIO()):
            R.main(self.argv("dry-test", "--dry"))
        self.assertFalse([c for c in calls if c and c[0] == "claude"])
        run = self.new / self.brand / "dry-test"                  # runs/page-machine/<brand>/<label>/
        state = json.loads((run / "run.json").read_text())
        self.assertTrue(state["stages"])
        self.assertTrue(all(s["status"] == "dry" for s in state["stages"].values()))
        self.assertTrue((run / "stage3--sent.md").is_file())       # the prompt as it would be sent
        self.assertFalse((run / "check.json").exists())            # no words, so no gate
        self.assertEqual(state["elements"]["format/page"]["id"], state["format"])


class Elements(Homes):
    def test_unknown_page_format_is_refused_naming_the_real_ids(self):
        with mock.patch.object(R, "classify", return_value="made-up-format"), \
                mock.patch.object(R, "claude", side_effect=AssertionError("called the model")), \
                redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as e:
            R.main(self.argv("bad-format", "--dry"))
        msg = str(e.exception)
        self.assertIn("made-up-format", msg)
        self.assertIn("salespage", msg)                             # the library's real ids are named
        self.assertFalse(list(self.new.rglob("run.json")))          # refused before a run folder exists

    def test_sections_are_recorded_known_and_unknown(self):
        known, unknown = G.sections_carried(CANNED)
        self.assertEqual(known, ["hook"])
        self.assertEqual(unknown, ["made-up-section"])
        self.assertEqual(G.sections_carried("no such block"), ([], []))


class CopyGate(Homes):
    def test_gate_holds_an_unfilled_note_flags_a_price_and_deliver_refuses(self):
        run = self.new / "anybrand" / "held-run"
        run.mkdir(parents=True)
        (run / "run.json").write_text(json.dumps({"label": "held-run", "brand": "anybrand", "stages": {}}))
        offer = Path(self.tmp.name) / "offer.md"
        offer.write_text("| The thing | $49.00 | $37.00 every 30 days |\n")
        Q = G.quality()
        with self.assertRaises(Q.Held) as e:
            G.copy_gate(run, [("the base page", "# THE PAGE\n\nOnly $58 today. [UNFILLED: the guarantee]\n\n# THE CHECK\n\nthe source said $12")],
                        "anybrand", [str(offer)])
        self.assertTrue(any("UNFILLED" in p for p in e.exception.problems))
        flags = json.loads((run / "check.json").read_text())["copy"]["flags"]
        self.assertTrue(any("$58.00" in p for p in flags))               # a price is flagged, never a hold
        self.assertFalse(any("$12" in p for p in flags))                  # the check's notes are not the page
        self.assertEqual(json.loads((run / "check.json").read_text())["copy"]["result"], "HELD")
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as refused:
            D.main(["held-run"])
        self.assertIn("refused", str(refused.exception))

    def test_a_listed_price_passes_and_an_unfilled_note_holds(self):
        offer = Path(self.tmp.name) / "offer.md"
        offer.write_text("$49.00 once, $37.00 on subscription")
        text = G.offer_text("anybrand", [str(offer)])
        self.assertEqual(G.copy_problems([("base", "# THE PAGE\n\nJust $49 today.")], text), [])
        self.assertTrue(G.copy_problems([("base", "# THE PAGE\n\n[UNFILLED: the guarantee]")], text))

    def test_a_held_chain_saves_everything_and_exits_2(self):
        argv = self.argv("held-chain")
        with mock.patch.object(R, "claude", return_value=CANNED), \
                mock.patch.object(R.subprocess, "run", return_value=mock.Mock(returncode=0, stdout="", stderr="")), \
                redirect_stdout(io.StringIO()) as out, self.assertRaises(SystemExit) as e:
            R.main(argv)
        self.assertEqual(e.exception.code, 2)
        self.assertIn("HELD at the copy gate", out.getvalue())
        run = self.new / self.brand / "held-chain"
        state = json.loads((run / "run.json").read_text())
        self.assertTrue((run / "stage6--brief.md").is_file())          # the brief was still written
        self.assertEqual(state["gate"]["copy"], "HELD")
        self.assertEqual(state["elements"]["doctrine/section"], {"carried": ["hook"], "unknown": ["made-up-section"]})
        self.assertIn("copy", G.held(run))
        # --no-gate: same words, no hold
        with mock.patch.object(R, "claude", return_value=CANNED), \
                mock.patch.object(R.subprocess, "run", return_value=mock.Mock(returncode=0, stdout="", stderr="")), \
                redirect_stdout(io.StringIO()):
            R.main(self.argv("ungated", "--no-gate"))
        self.assertFalse((self.new / self.brand / "ungated" / "check.json").exists())


class BothHomes(Homes):
    def test_runs_are_found_in_both_homes(self):
        for d in (self.new / "brand-a" / "new-run", self.old / "old-run"):
            d.mkdir(parents=True)
            (d / "run.json").write_text("{}")
        self.assertEqual({d.name for d in P.all_runs()}, {"new-run", "old-run"})
        self.assertEqual(P.find_run("new-run"), self.new / "brand-a" / "new-run")
        self.assertEqual(P.find_run("old-run"), self.old / "old-run")
        self.assertIsNone(P.find_run("nowhere"))
        self.assertEqual(P.run_dir("brand-b", "x"), self.new / "brand-b" / "x")


class Models(unittest.TestCase):
    def test_tiers_map_to_the_same_models_as_before(self):
        self.assertEqual(R.MODELS, WAS)
        for stage, model in WAS.items():
            self.assertEqual(R.model_for(stage, 1000)[0], model)

    def test_every_stage_carries_a_tier(self):
        for s in R.STAGES:
            self.assertIn(s["tier"], R.KIT.TIERS)

    def test_a_forced_model_wins(self):
        with mock.patch.object(R, "FORCED_MODEL", "some-model"):
            self.assertEqual(R.model_for("stage0")[0], "some-model")

    def test_a_prompt_without_a_version_number_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "stage9-thing-vfinal-damon.md").write_text("x")
            with mock.patch.object(R, "PROMPTS", Path(t)), self.assertRaises(SystemExit) as e:
                R.latest_prompt("stage9")
            self.assertIn("version number", str(e.exception))

    def test_out_of_usage_stops_at_once(self):
        calls = []

        def refused(*a, **k):
            calls.append(1)
            return mock.Mock(returncode=1, stdout="Claude usage limit reached — resets 3pm", stderr="")

        with mock.patch.object(R.subprocess, "run", side_effect=refused), \
                mock.patch.object(R.time, "sleep", side_effect=AssertionError("waited to retry")), \
                redirect_stdout(io.StringIO()), self.assertRaises(R.UsageLimit):
            R.claude("a prompt", "a-model")
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
