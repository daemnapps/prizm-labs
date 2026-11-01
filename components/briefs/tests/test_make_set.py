#!/usr/bin/env python3
"""make.py on a set change: no flat picture call, the set request's own steps, the request saved for filing.

    /usr/bin/python3 components/briefs/tests/test_make_set.py
"""
import importlib.util, json, shutil, sys, tempfile, unittest
from pathlib import Path

HOME = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("make_under_test", HOME / "make.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


class SetPlan(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        M.REPO, self.was = self.tmp, M.REPO
        self.folder = self.tmp / "runs/handoffs/graphic-designer/acme/acme_widget_brief-0001"
        (self.folder / "refs").mkdir(parents=True)
        (self.folder / "refs/kept.png").write_text("x")
        self.step = {"n": 2, "asset": "acme_widget_brief-0001_asset-02.png", "what": "variation v1", "job": "set-change",
                     "medium": "image", "prompt": "Print this.", "higgsfield_model": None, "words_on_top": [],
                     "references": [{"n": 1, "kind": "image", "local": "refs/kept.png", "file": "x", "exists": True}],
                     "set_request": {"set": "one--v1", "change": "a bigger sign", "credits": 2.5, "steps": ["Copy it."], "flags": []}}
        (self.folder / "run.json").write_text(json.dumps({"brief_key": self.folder.name, "steps": [self.step]}))

    def tearDown(self):
        M.REPO = self.was
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_set_change_plans_the_set_never_a_picture_call(self):
        got = M.plan(self.folder, 2)
        self.assertTrue(got["no_flat_picture"])
        self.assertNotIn("tool", got)
        self.assertEqual(got["steps"], ["Copy it."])
        self.assertEqual(got["print_words"], "Print this.")
        saved = json.loads((self.tmp / got["request"]).read_text())
        self.assertEqual(saved["set"], "one--v1")
        self.assertIn("put-change", got["then"])


if __name__ == "__main__":
    unittest.main()
