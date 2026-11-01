#!/usr/bin/env python3
"""The gatherer's gates — stdlib unittest, no network, no model, no Apify.

    python3 components/research-gatherer/test_gates.py

Every pull here runs against a TEMP workspace (`engine.configure(tmp)`), so
nothing is ever written into the real `runs/` or `brands/`. The Reddit door is
a stub. Proves: a pull that files nothing leaves a gate-keyed check.json that
reads HELD; a clean pull reads pass on all three gates and files what it filed
before; an unknown doctrine technique is refused with the real ids named, before
anything is spent; "record" mode puts the old behaviour back; a dry run writes
nothing.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import research_gatherer.engine as R   # noqa: E402
from research_gatherer import gates as G   # noqa: E402

SUB = """# sub x

### desire words
- stubborn marks
- even tone

### demographics
- age: 40–55
- gender: female
- skin tone / ethnicity: lighter-skinned
- region: United States
- language: English

### rooms
- r/GoodRoom
confirmed by: a test
"""


class _Door:
    @staticmethod
    def score(r):
        return r.get("ups") or 0

    @staticmethod
    def when(r):
        return "2026-09-01"


def _rows(*rows):
    def fake(rooms, queries, cap, out_dir, **kw):
        return list(rows), "", 0.0
    return fake


GOOD = {"title": "kept", "body": "b", "communityName": "GoodRoom", "ups": 5,
        "url": "https://reddit.com/r/GoodRoom/1", "dataType": "post"}
NO_LINK = {"title": "no receipt", "body": "b", "communityName": "GoodRoom", "ups": 3,
           "dataType": "post"}
WRONG_ROOM = {"title": "someone else", "body": "b", "communityName": "teenagers", "ups": 9,
              "url": "https://reddit.com/r/teenagers/2", "dataType": "post"}


class GateCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        sub_dir = self.tmp / "brands" / "b" / "core-avatars" / "a" / "sub-avatars"
        sub_dir.mkdir(parents=True)
        (sub_dir / "sub-01-x.md").write_text(SUB)
        self._saved = {k: getattr(R, k) for k in
                       ("WORKSPACE", "_run_reddit", "reddit_door", "schwartz_questions", "_config")}
        R.configure(self.tmp)
        R.reddit_door = lambda: _Door
        self.sub = R.all_sub_avatars(self.tmp)[0]["sub"]

    def tearDown(self):
        for k, v in self._saved.items():
            setattr(R, k, v)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _check(self, res):
        return json.loads((Path(res["out"]) / "check.json").read_text())

    # ------------------------------------------------------------ the workspace
    def test_the_pull_is_in_the_temp_tree(self):
        self.assertEqual(R.WORKSPACE, self.tmp)
        self.assertTrue(str(R._deep_runs_root()).startswith(str(self.tmp)))

    # ------------------------------------------------------------ delivery
    def test_clean_pull_passes_every_gate_and_files_as_before(self):
        R._run_reddit = _rows(GOOD, NO_LINK)
        res = R.deep_for("b", "a", self.sub, 20)
        self.assertTrue(res["ok"])
        self.assertEqual(res["rows_written"], 1)
        self.assertNotIn("held", res)
        self.assertTrue(Path(res["bank_file"]).is_file())
        check = self._check(res)
        self.assertEqual({g: check[g]["result"] for g in check},
                         {"inputs": "pass", "elements": "pass", "delivery": "pass"})

    def test_a_pull_that_files_nothing_is_held_at_delivery(self):
        R._run_reddit = _rows(NO_LINK, WRONG_ROOM)
        res = R.deep_for("b", "a", self.sub, 20)
        self.assertTrue(res["ok"])                       # unchanged: ok, 0 rows
        self.assertEqual(res["rows_written"], 0)
        self.assertEqual(res["held"], "delivery")
        check = self._check(res)
        self.assertEqual(check["delivery"]["result"], "HELD")
        self.assertIn("no permalink", check["delivery"]["problems"][0])
        self.assertIn("demographics", check["delivery"]["problems"][0])
        bank = R.sub_home("b", "a", self.sub) / "language"
        self.assertFalse(bank.exists() and any(bank.iterdir()))

    def test_a_bad_row_that_slipped_through_is_named(self):
        bad = [{"id": "r1", "source": {"ref": ""}, "fit": {"verdict": "yes"}},
               {"id": "r2", "source": {"ref": "u"}, "fit": {"verdict": "no", "room": "r/x"}}]
        problems = G.delivery_problems(bad)
        self.assertEqual(len(problems), 2)
        self.assertIn("r1", problems[0])
        self.assertIn("r/x", problems[1])
        self.assertEqual(G.delivery_problems(
            [{"id": "ok", "source": {"ref": "u"}, "fit": {"verdict": "unknown"}}]), [])

    # ------------------------------------------------------------ inputs
    def test_no_rooms_is_held_at_inputs(self):
        f = R.sub_file("b", "a", self.sub)
        f.write_text(SUB.split("### rooms")[0])
        orig = R.resolve_rooms
        R.resolve_rooms = lambda *a, **k: ([], ["stubborn"], None)
        try:
            R._run_reddit = lambda *a, **k: self.fail("nothing may be pulled")
            res = R.deep_for("b", "a", self.sub, 20)
        finally:
            R.resolve_rooms = orig
        self.assertFalse(res["ok"])
        self.assertIn("no rooms on file", res["why"])     # the same words as before
        self.assertEqual(res["held"], "inputs")
        self.assertEqual(self._check(res)["inputs"]["result"], "HELD")

    def test_a_mistyped_brand_leaves_no_folder_behind(self):
        res = R.deep_for("nobrand", "a", "nosub", 20)
        self.assertFalse(res["ok"])
        self.assertEqual(res["held"], "inputs")
        self.assertFalse((self.tmp / "runs").exists())

    # ------------------------------------------------------------ elements
    def test_the_live_question_bank_is_all_real(self):
        live = G._repo() / "components" / "marketing-doctrine" / "frameworks.json"   # read only
        questions = json.loads(live.read_text())["research_questions"]
        self.assertTrue(any(G.question_labels(questions)))
        problems, checked = G.question_problems(questions)
        self.assertTrue(checked, "the element library should be reachable from the repo")
        self.assertEqual(problems, [])
        problems, _ = G.question_problems(R.FALLBACK_QUESTIONS)
        self.assertEqual(problems, [])

    def test_an_unknown_technique_is_refused_with_the_real_ids_named(self):
        bad = [dict(id="RQ-99", framework="techniques.hypnosis", question="?", tags=["mechanism"]),
               dict(id="RQ-98", framework="delivery.volume", question="?", tags=["hook"]),
               dict(id="RQ-01", framework="desire", question="?", tags=["why-bought"])]
        problems, checked = G.question_problems(bad)
        self.assertTrue(checked)
        self.assertEqual(len(problems), 2)
        self.assertIn("hypnosis", problems[0])
        self.assertIn("camouflage", problems[0])          # a real id, named
        self.assertIn("delivery/volume", problems[1])

        R.schwartz_questions = lambda: (bad, False)
        R._run_reddit = lambda *a, **k: self.fail("held before anything is pulled")
        res = R.deep_for("b", "a", self.sub, 20)
        self.assertFalse(res["ok"])
        self.assertEqual(res["held"], "elements")
        self.assertEqual(res["spend"], 0.0)
        self.assertEqual(self._check(res)["elements"]["result"], "HELD")

    def test_record_mode_is_the_old_behaviour(self):
        bad = [dict(id="RQ-99", framework="techniques.hypnosis", question="?", tags=["mechanism"])]
        R.schwartz_questions = lambda: (bad, False)
        R._config = lambda: {"gates": {"elements": "record"}}
        R._run_reddit = _rows(GOOD)
        res = R.deep_for("b", "a", self.sub, 20)
        self.assertTrue(res["ok"])
        self.assertEqual(res["rows_written"], 1)
        check = self._check(res)
        self.assertEqual(check["elements"]["result"], "HELD")
        self.assertIn("recorded only", check["elements"]["problems"][0])

    # ------------------------------------------------------------ dry run
    def test_a_dry_run_writes_nothing_and_reports_the_elements_gate(self):
        R._run_reddit = lambda *a, **k: self.fail("a dry run never pulls")
        res = R.deep_for("b", "a", self.sub, 20, dry_run=True)
        self.assertTrue(res["dry_run"])
        self.assertIn("elements_problems", res)
        self.assertFalse((self.tmp / "runs").exists())

    # ------------------------------------------------------------ the hold itself
    def test_record_goes_through_the_shared_hold(self):
        Q = G.marketing_chain_checks()
        self.assertIsNotNone(Q)
        for g in G.GATE_NAMES:
            self.assertIn(g, {x[0] for x in Q.GATES})
        out = self.tmp / "somewhere"
        self.assertEqual(G.record("delivery", [], out), [])
        self.assertEqual(G.record("inputs", ["missing"], out), ["missing"])
        state = json.loads((out / "check.json").read_text())
        self.assertEqual(state["delivery"], {"result": "pass", "problems": []})
        self.assertEqual(state["inputs"], {"result": "HELD", "problems": ["missing"]})

    def test_sys_path_is_appended_never_put_first(self):
        G.marketing_chain_checks(), G.element_library()
        self.assertNotIn("marketing-chain-checks", sys.path[0])
        self.assertNotIn("elements", sys.path[0])


if __name__ == "__main__":
    unittest.main(verbosity=1)
