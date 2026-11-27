"""An approval on the brief's checklist is KEPT for that brief (2026-10-19).

Found on the mini check: 5 of 7 v2 briefs on disk were refused by production with
"MANIFEST: MISSING — E…" although writing had passed them. Approvals lived only in one process's
environment, so production's own re-check read MISSING again. No network: the judge's answer is
already on file for the brief, so it is never asked.

    /usr/bin/python3 -m unittest discover -s components/video-writing/tests
"""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MACHINE = Path(__file__).resolve().parent.parent / "machine"
sys.path.insert(0, str(MACHINE))
import manifest as M        # noqa: E402
import swipe_match as SM    # noqa: E402

BRAND = next(p.name for p in sorted((MACHINE.parents[2] / "brands").iterdir())
             if p.is_dir() and not p.name.startswith("_") and (p / "products").is_dir())


class ApprovalsAreKept(unittest.TestCase):
    def setUp(self):
        self.prev = os.environ.pop("DAEMN_STRUCTURE_APPROVALS", None)
        self.tmp = tempfile.TemporaryDirectory()
        d = self.d = Path(self.tmp.name)
        (d / "stages").mkdir()
        (d / "run.json").write_text(json.dumps({"brand": BRAND}))
        (d / "stages" / "2-spec.md").write_text("spec")
        body = "# Brief\n\nA scene with nothing priced.\n"
        stamped = "<!-- swipe-match: PASSED · %s -->\n%s" % (SM.brief_hash(M.strip(body)), body)
        (d / "stages" / "5-brief.md").write_text(stamped)
        self.h = SM.brief_hash(M.strip(stamped))
        self.write_rec({})

    def write_rec(self, extra):
        brief = M.strip((self.d / "stages/5-brief.md").read_text())
        request = M.judge_request(self.d, {"brand": BRAND}, brief)
        rec = {"brief_hash": self.h, "model": M.MODEL,
               "request_sha256": hashlib.sha256(request.encode()).hexdigest(),
               "judge": {"elements": [{"id": "E1", "carried": False, "element": "the core beat"}], "load_bearing": []}}
        rec.update(extra)
        (self.d / "manifest.json").write_text(json.dumps(rec))

    def tearDown(self):
        os.environ.pop("DAEMN_STRUCTURE_APPROVALS", None)
        if self.prev is not None:
            os.environ["DAEMN_STRUCTURE_APPROVALS"] = self.prev
        self.tmp.cleanup()

    def last_line(self):
        return [l for l in (self.d / "stages" / "5-brief.md").read_text().splitlines() if l.startswith("MANIFEST:")][-1]

    def test_missing_without_an_approval(self):
        self.assertEqual(M.check(self.d, BRAND), (True, []))
        self.assertTrue(self.last_line().startswith("MANIFEST: COMPLETE"))     # V57: E1 is noted, not missing
        self.assertEqual(json.loads((self.d / "manifest.json").read_text())["swipe_notes"], ["E1"])

    def test_an_approval_survives_the_next_check(self):
        os.environ["DAEMN_STRUCTURE_APPROVALS"] = "E1"
        self.assertEqual(M.check(self.d, BRAND), (True, []))
        os.environ.pop("DAEMN_STRUCTURE_APPROVALS")
        self.assertEqual(M.check(self.d, BRAND), (True, []))            # production's re-check
        self.assertTrue(self.last_line().startswith("MANIFEST: COMPLETE"))
        self.assertEqual(M.status_of((self.d / "stages" / "5-brief.md").read_text()), "COMPLETE")

    def test_all_with_v_approves_everything(self):
        """"all,V" (Outlier's "Looks good", the batch script approval) is all, not the codes {all, V}."""
        os.environ["DAEMN_STRUCTURE_APPROVALS"] = "all,V"
        self.assertEqual(M.check(self.d, BRAND), (True, []))

    def test_an_approval_for_another_brief_does_not_count(self):
        self.write_rec({"approved": {"brief_hash": "0" * 16, "all": False, "ids": ["E1"]}})
        self.assertEqual(M.check(self.d, BRAND), (True, []))

    def test_current_sources_reach_judge_and_changes_invalidate_cache(self):
        source_files = ["stages/2-spec.md", "stages/1-teardown.md", "RULINGS.md",
                        "verbatim-sources.json", "verbatim-sources.md"]
        for filename in source_files:
            data = (filename + "\r\n" + "evidence " * 12000 + "final line — {brief}\r\n").encode()
            (self.d / filename).write_bytes(data)
        record = self.d / "manifest.json"
        prev = json.loads(record.read_text())
        del prev["request_sha256"]
        record.write_text(json.dumps(prev))  # Legacy result has no evidence of current context.
        original = record.read_bytes()
        with patch.object(M, "ask_judge", return_value=prev["judge"]) as judge:
            self.assertEqual(M.check(self.d, BRAND), (True, []))
            sent = judge.call_args.args[0].encode()
            current = json.loads(record.read_text())
            self.assertEqual(hashlib.sha256(sent).hexdigest(), current["request_sha256"])
            self.assertEqual((self.d / current["request_file"]).read_bytes(), sent)
            for filename in source_files:
                self.assertIn((self.d / filename).read_bytes(), sent)
            previous = self.d / "manifest-reviews" / (hashlib.sha256(original).hexdigest() + ".previous.json")
            self.assertEqual(previous.read_bytes(), original)
            self.assertEqual(M.check(self.d, BRAND), (True, []))
            judge.assert_called_once()
            for i, filename in enumerate(source_files, start=2):
                with (self.d / filename).open("ab") as f:
                    f.write(b"new tail")
                self.assertEqual(M.check(self.d, BRAND), (True, []))
                self.assertEqual(judge.call_count, i)
                self.assertIn((self.d / filename).read_bytes(), judge.call_args.args[0].encode())

    def test_declared_swipe_story_uses_writing_contract_without_approving_missing_job(self):
        import writing_v2 as W
        st = {"brand": BRAND, "lane": "swipe", "story": {"file": "story.md"}}
        (self.d / "run.json").write_text(json.dumps(st))
        (self.d / "story.md").write_text("Our signed story with its own people and facts.\n")
        expected = W.story_block(self.d, st)
        request = M.judge_request(self.d, st, "Final scene")
        self.assertIn(expected, request)
        self.assertIn("## stages/2-spec.md\n\nspec", request)
        self.assertIn("report a missing function", request)
        self.assertNotIn("Original scratch concept", request)
        missing = {"elements": [{"id": "E1", "carried": False, "element": "the core beat"}], "load_bearing": []}
        with patch.object(M, "ask_judge", return_value=missing) as judge:
            # V57: the missing swipe job is NOTED on the manifest, never held, and never approved
            self.assertEqual(M.check(self.d, BRAND), (True, []))
            rec = json.loads((self.d / "manifest.json").read_text())
            self.assertNotIn("approved", rec)
            self.assertEqual(rec["swipe_notes"], ["E1"])
            self.assertIn(expected, judge.call_args.args[0])
            (self.d / "story.md").write_text("Changed signed story.\n")
            self.assertEqual(M.check(self.d, BRAND), (True, []))
            self.assertEqual(judge.call_count, 2)
            self.assertIn("Changed signed story.", judge.call_args.args[0])

    def test_undeclared_story_file_does_not_activate_own_story_route(self):
        (self.d / "story.md").write_text("An unrelated draft.")
        request = M.judge_request(self.d, {"brand": BRAND, "lane": "swipe"}, "Final scene")
        self.assertNotIn("OUR STORY", request)
        self.assertNotIn("An unrelated draft.", request)

    def test_locked_scratch_concept_survives_numbered_spec(self):
        (self.d / "stages/2-spec.md").write_text("**1. ELEMENT INVENTORY** one\n**2. LOAD-BEARING** two\n**3. NEXT** other")
        concept = "Full concept — after structured spec\n"
        (self.d / "story.md").write_text(concept)
        st = {"brand": BRAND, "lane": "scratch", "stages": {"stage1": {"from": "scratch"}},
              "story": {"sha": hashlib.sha256(concept.encode()).hexdigest()[:16]}}
        request = M.judge_request(self.d, st, "Final scene")
        self.assertIn(concept, request)
        self.assertNotIn("OUR STORY", request)
        self.assertIn("**3. NEXT** other", request)
        self.assertIn("Final scene", request)


if __name__ == "__main__":
    unittest.main()
