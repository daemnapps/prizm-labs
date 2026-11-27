"""A problem-side scene (problem, failed-solutions, agitation) shows no brand product: our product is never the thing
that fails. Run: python3 -m unittest test_problem_scene_products"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import clip_refs as CF  # noqa: E402


class ProblemSceneProducts(unittest.TestCase):
    def setUp(self):
        self.run = Path(tempfile.mkdtemp(prefix="problemscene_"))
        (self.run / "plan.json").write_text(json.dumps({"scenes": [
            {"id": "S3", "section": "failed-solutions"}, {"id": "S14", "section": "solution"}]}))
        (self.run / "elements.json").write_text(json.dumps({"items": [
            {"kind": "product", "bank_id": "war-face-wash", "scenes": ["S3", "S14"]}]}))
        (self.run / "run.json").write_text(json.dumps({}))

    def test_problem_scene_gets_no_product(self):
        self.assertEqual(CF.product_ids(self.run, {"scenes": ["S3"]}, self.run), [])

    def test_solution_scene_keeps_product(self):
        self.assertIn("war-face-wash", CF.product_ids(self.run, {"scenes": ["S14"]}, self.run))

    def test_mixed_clip_keeps_product(self):
        self.assertIn("war-face-wash", CF.product_ids(self.run, {"scenes": ["S3", "S14"]}, self.run))


if __name__ == "__main__":
    unittest.main()
