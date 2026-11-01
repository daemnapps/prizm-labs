#!/usr/bin/env python3
"""python3 test_marketing_chain_checks.py — stdlib unittest, no network, no model."""
import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import marketing_chain_checks as Q   # noqa: E402

BANK = "## the-set — The Set\n- Price: **$49.99**, was $59.99\n\n## other — Other\n- Price: **$10.00**\n"


class Checks(unittest.TestCase):
    def test_a_price_the_bank_does_not_sell_is_caught(self):
        block = Q.offer_block(BANK, "the-set")
        self.assertEqual(Q.price_check("Two for $99.99", block, "the-set")[0][:7], "$99.99 ")
        self.assertEqual(Q.price_check("Just $49.99, was $59.99", block), [])
        self.assertNotIn("$10.00", block, "one offer's block never leaks the next offer's price")

    def test_49_and_49_00_are_one_price(self):
        self.assertEqual(Q.price_check("only $49", "## x — X\n- Price: **$49.00**"), [])

    def test_a_price_with_no_offer_is_caught(self):
        self.assertTrue(Q.price_check("only $5", ""))

    def test_unfilled(self):
        self.assertTrue(Q.unfilled_check("hello [the handoff — UNFILLED: x]"))
        self.assertEqual(Q.unfilled_check("clean"), [])

    def test_check_block(self):
        t = '```CHECK\n{"facts":[{"quote":"scrub","problem":"WRONG","files_say":"serum"}],"chops":[],"typos":[{"quote":"uy","fix":"Buy"}]}\n```'
        self.assertEqual(len(Q.read_check_block(t)), 2)
        self.assertTrue(Q.read_check_block("no block"))

    def test_elements(self):
        self.assertEqual(Q.elements_check({("framework", "all"): "pas"}), [])
        self.assertTrue(Q.elements_check({("format", "video"): "not-a-real-format"}))

    def test_hold_writes_and_stops(self):
        d = Path(tempfile.mkdtemp())
        self.assertTrue(Q.hold("copy", [], d))
        with self.assertRaises(Q.Held):
            Q.hold("delivery", ["wrong price"], d)
        state = json.loads((d / "check.json").read_text())
        self.assertEqual(state["copy"]["result"], "pass")
        self.assertEqual(state["delivery"]["result"], "HELD")


class CreativeQcLoop(unittest.TestCase):
    """The creative QC loop, for every tool and stage (2026-10-02)."""

    def test_every_tool_has_a_definition(self):
        from marketing_chain_checks import review
        d = review.definitions()["tools"]
        for tool in ("video-teardown", "video-production", "video-edit", "image-edit", "copywriter",
                     "email-production", "ad-variations", "meta-upload", "marketing-calendar", "intake"):
            self.assertIn(tool, d)
        self.assertIn("reference", " ".join(review.stage_def("video-production", "pictures")["hard_bars"]))
        self.assertEqual(review.stage_def("video-teardown", "stage4g")["fix_at"], "this stage")   # prefix match

    def test_after_stage_reviews_and_files_a_round(self):
        from marketing_chain_checks import review
        d = Path(tempfile.mkdtemp()); out = d / "stage3--x.md"; out.write_text("our script")
        seen = {}
        def caller(parts):
            seen["text"] = " ".join(p.get("text", "") for p in parts)
            return {"stage3": {"ok": False, "severity": "FIX", "problems": ["a price not in the offer bank"]}}
        f = review.after_stage("copywriter", "stage3", d, output=out, sources=["the source"], caller=caller)
        self.assertEqual(f["stage3"]["severity"], "FIX")
        self.assertIn("our script", seen["text"])
        self.assertIn("the source", seen["text"])
        log = (d / "qc-log" / "QC-LOG.md").read_text()
        self.assertIn("copywriter · stage3", log)
        self.assertIn("a price not in the offer bank", log)

    def test_a_review_that_cannot_run_is_filed_not_hidden(self):
        from marketing_chain_checks import review
        d = Path(tempfile.mkdtemp())
        def caller(parts):
            raise RuntimeError("no network")
        f = review.after_stage("intake", "record", d, output="x", caller=caller)
        self.assertEqual(f["record"]["severity"], "UNCHECKED")
        self.assertIn("did not run", (d / "qc-log" / "QC-LOG.md").read_text())

    def test_a_blocker_holds_when_asked(self):
        from marketing_chain_checks import review
        d = Path(tempfile.mkdtemp())
        caller = lambda parts: {"S1": {"ok": False, "severity": "BLOCKER", "problems": ["a different person"]}}
        with self.assertRaises(Q.Held):
            review.after_stage("video-production", "pictures", d, items=[{"id": "S1", "output": ["x"]}],
                               hold=True, caller=caller)


class OldName(unittest.TestCase):
    def test_import_quality_checks_still_works(self):
        import quality_checks
        self.assertIs(quality_checks.hold, Q.hold)
        from quality_checks import review   # noqa: F401  the submodules forward too


class PictureInventory(unittest.TestCase):
    """Every picture review answers the full fourteen-line inventory (2026-10-02)."""

    def test_checklist_is_asked_for_every_picture(self):
        from marketing_chain_checks import review
        seen = {}
        def caller(parts):
            seen["t"] = " ".join(p.get("text", "") for p in parts)
            return {"S1": {"ok": True, "severity": "none"}}
        review.review("video-production", "pictures", [{"id": "S1", "output": ["x"]}], caller=caller)
        for key in ("framing", "moment", "people", "skin_marks", "hands_bodies", "light_shadow", "fits_the_look",
                    "outfit", "place", "product_props", "continuity", "nothing_added", "frame_zone", "cards"):
            self.assertIn(key, seen["t"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
