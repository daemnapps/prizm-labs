#!/usr/bin/env python3
"""feedback-forms language pass — `--write` files a proposal under runs/ and
never writes the brand's feedback-questions.json (K2 (brands write wall)).
No network; temp folders only.

    python3 components/feedback-forms/tests/test_language_pass.py
"""
import json, shutil, sys, tempfile, unittest
from pathlib import Path

COMP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COMP))
import language_pass as LP  # noqa: E402  (configures the language layer read-only)


class Propose(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_propose_leaves_the_brand_file_alone(self):
        cfg_path = self.tmp / "brands/fx/operations/feedback-questions.json"
        cfg_path.parent.mkdir(parents=True)
        cfg_path.write_text(json.dumps({"brand": "fx", "form_version": "v1"}, indent=1) + "\n")
        before = cfg_path.read_bytes()
        cfg = dict(json.loads(before), form_version="v2")
        out = self.tmp / "runs/feedback-forms/fx/lp"
        path, diff = LP.propose("fx", cfg_path, cfg, out, root=self.tmp)
        self.assertEqual(cfg_path.read_bytes(), before)
        self.assertEqual(path, out / "deliverable/feedback-questions.json")
        self.assertEqual(json.loads(path.read_text())["form_version"], "v2")
        self.assertIn("v2", diff)
        note = (out / "PROPOSAL.md").read_text()
        self.assertIn("brands/fx/operations/feedback-questions.json", note)
        self.assertIn("shasum -a 256", note)

    def test_source_never_writes_the_brand_file(self):
        self.assertNotIn("cfg_path.write_text", (COMP / "language_pass.py").read_text())


if __name__ == "__main__":
    unittest.main()
