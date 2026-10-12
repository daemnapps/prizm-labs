#!/usr/bin/env python3
"""The used lane, awareness and the query — a fixture tree, no network, no real brand.

    python3 -m unittest discover -s tests          # from tools/language-layer
    python3 tools/language-layer/tests/test_used_lane.py
"""
import json, os, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from language_layer import engine as E  # noqa: E402


def fixture(root):
    """One brand `fx`, one avatar `a1`, a lead bank and one used-lane record."""
    lang = Path(root) / "brands" / "fx" / "core-avatars" / "a1" / "language"
    (lang / "used").mkdir(parents=True)
    rows = [dict(id="r1", text="first line", use="hook", status="active"),
            dict(id="r2", text="second line", use="hook", status="active"),
            dict(id="r3", text="burned line", use="hook", status="burned"),
            dict(id="r4", text="retired line", use="hook", status="retired"),
            dict(id="r5", text="labelled problem line", use="problem-language",
                 awareness={"level": "problem-aware", "by": "model"}),
            dict(id="r6", text="labelled product line", use="why-bought",
                 awareness={"level": "product-aware", "by": "model"})]
    (lang / "leads.json").write_text(json.dumps({"schema": 1, "avatar": "a1", "funnel": "lead", "entries": rows}))
    (lang / "used" / "run1--h0.json").write_text(json.dumps({
        "schema": 1, "kind": "language-used", "asset": "run1--h0", "chain": "new-video",
        "used": [{"row_id": "r1", "text": "first line", "where": "4b", "how": "cited"}]}))
    return lang


class UsedLane(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        self.lang = fixture(self.root)
        self.before = (self.lang / "leads.json").read_text()

    def tearDown(self):
        self._t.cleanup()

    def test_used_lane_is_not_read_as_bank_rows(self):
        self.assertEqual(len(E.load("fx", root=self.root)), 6)

    def test_used_ids(self):
        self.assertEqual(E.used_ids("fx", root=self.root), {"r1"})
        self.assertEqual(E.load_used("fx", root=self.root)[0]["asset"], "run1--h0")

    def test_burned_and_retired_never_come_back(self):
        got = {r["id"] for r in E.query(E.load("fx", root=self.root))}
        self.assertEqual(got, {"r1", "r2", "r5", "r6"})

    def test_used_no_and_yes(self):
        rows, spent = E.load("fx", root=self.root), E.used_ids("fx", root=self.root)
        self.assertEqual({r["id"] for r in E.query(rows, use=["hook"], used="no", spent=spent)}, {"r2"})
        self.assertEqual({r["id"] for r in E.query(rows, use=["hook"], used="yes", spent=spent)}, {"r1"})

    def test_for_stage_holds_back_used_rows_and_says_so(self):
        out = E.for_stage("fx", "hooks", root=self.root, stage_use={"hooks": ["hook"]}, used="no")
        self.assertIn("[r2]", out)
        self.assertNotIn("[r1]", out)
        self.assertIn("never used before", out)
        out2 = E.for_stage("fx", "hooks", root=self.root, stage_use={"hooks": ["hook"]})
        self.assertIn("[r1]", out2)
        self.assertIn("[r2]", out2)

    def test_no_bank_file_is_edited(self):
        E.for_stage("fx", "hooks", root=self.root, stage_use={"hooks": ["hook"]}, used="no")
        self.assertEqual((self.lang / "leads.json").read_text(), self.before)


class Awareness(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        fixture(self.root)
        self.rows = E.load("fx", root=self.root)

    def tearDown(self):
        self._t.cleanup()

    def test_other_labelled_levels_are_dropped(self):
        got = [r["id"] for r in E.query(self.rows, use=["hook"], awareness="problem-aware")]
        self.assertNotIn("r6", got)

    def test_a_labelled_match_leads_and_stands_in_for_a_tag(self):
        got = [r["id"] for r in E.query(self.rows, use=["hook"], awareness="problem-aware")]
        self.assertEqual(got[0], "r5")                   # tagged problem-language, not hook: the label admits it
        self.assertEqual(set(got), {"r5", "r1", "r2"})   # unlabelled rows still answer, after

    def test_for_stage_header_names_the_level(self):
        out = E.for_stage("fx", "hooks", root=self.root, stage_use={"hooks": ["hook"]},
                          awareness="problem-aware")
        self.assertIn("spoken at the problem-aware level first", out)
        self.assertLess(out.index("[r5]"), out.index("[r2]"))


class Repeats(unittest.TestCase):
    def test_identical_lines_collapse_and_count(self):
        rows = [dict(id="a", text="Recipe!", use="hook"), dict(id="b", text="recipe", use="hook"),
                dict(id="c", text="other", use="hook")]
        got = E.query(rows, use=["hook"])
        self.assertEqual([r["id"] for r in got], ["a", "c"])
        self.assertEqual(got[0]["_repeats"], 2)
        self.assertIn("said 2×", E.render(got))


class Workspace(unittest.TestCase):
    def test_default_workspace_is_this_checkout_not_a_home_guess(self):
        if os.environ.get("AI_WORKSPACE"):
            self.skipTest("AI_WORKSPACE is set; the default is the named tree")
        here = Path(E.__file__).resolve().parents[3]
        self.assertEqual(E._default_workspace(), here)
        self.assertTrue((here / "tools" / "language-layer").is_dir())

    def test_ai_workspace_names_the_tree(self):
        old = os.environ.get("AI_WORKSPACE")
        os.environ["AI_WORKSPACE"] = "/tmp/some-ws"
        try:
            self.assertEqual(E._default_workspace(), Path("/tmp/some-ws"))
        finally:
            if old is None:
                del os.environ["AI_WORKSPACE"]
            else:
                os.environ["AI_WORKSPACE"] = old


if __name__ == "__main__":
    unittest.main()
