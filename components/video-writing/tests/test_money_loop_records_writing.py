"""v2 writing passes record the prompt version from the filename, not the constant 2."""
import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import writing_v2 as W  # noqa: E402


class PromptVersion(unittest.TestCase):
    def test_version_from_filename(self):
        self.assertEqual(W.prompt_version("stage4v2a-readhooks-v8-owner.md"), 8)
        self.assertEqual(W.prompt_version("x/stage5-ai-brief-v11-owner.md"), 11)
        self.assertEqual(W.prompt_version("stage9-nover.md"), 2)

    def test_plan_records_real_versions(self):
        by = {s["key"]: s for s in W.plan("brand_a", "creator", "paid")}
        for s in by.values():
            self.assertEqual(s["version"], W.prompt_version(s["prompt"]))
        self.assertIn(by["stage4v2a"]["version"], (8, 9, 10, 11))   # 10: V57 hooks prompt (2026-11-16) · 11: each opening a different customer angle (owner approved 2026-11-19)


if __name__ == "__main__":
    unittest.main()
