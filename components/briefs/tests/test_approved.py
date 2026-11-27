"""A maker's list shows only briefs the owner approved."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import approved as A  # noqa: E402


class Approved(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.repo = Path(self.t.name)

    def put(self, rel, text):
        f = self.repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)

    def test_no_record_or_a_broken_one_approves_nothing(self):
        self.assertEqual(A.keys(self.repo), set())
        self.put("runs/briefs/approved.json", "{oops")
        self.assertEqual(A.keys(self.repo), set())

    def test_a_held_brief_shows_on_its_day_and_a_revoked_one_never(self):
        A.add(["a_w_brief-0001"], "said so", repo=self.repo)
        A.add(["a_w_brief-0002"], "said so", hold="2026-12-21", repo=self.repo)
        doc = A.add(["a_w_brief-0003"], "said so", repo=self.repo)
        doc["approved"]["a_w_brief-0003"]["revoked"] = "2026-11-25"
        A._save(doc, self.repo)
        self.assertEqual(A.keys(self.repo, "2026-12-20"), {"a_w_brief-0001"})
        self.assertEqual(A.keys(self.repo, "2026-12-21"), {"a_w_brief-0001", "a_w_brief-0002"})

    def test_approved_as_a_run_is_approved_as_its_number_unless_held(self):
        self.put("components/image-teardown/briefs.json", json.dumps({"briefs": {
            "a_w_brief-0009": {"brand": "a", "run": "the-run"}, "a_w_brief-0010": {"brand": "a", "run": "other"},
            "a_w_brief-0011": {"brand": "a", "run": "the-run"}}}))
        A.add(["a_idea_the-run"], "clicked", repo=self.repo)
        A.add(["a_w_brief-0011"], "said so", hold="2099-01-01", repo=self.repo)
        self.assertEqual(A.keys(self.repo), {"a_idea_the-run", "a_w_brief-0009"})

    def test_both_makers_are_locked_and_another_role_is_not(self):
        for role in ("video-editor", "video-producer", "graphic-designer"):
            self.assertNotIn("a_w_brief-0001", A.readable(role, self.repo))
        self.assertIn("a_w_brief-0001", A.readable("copywriter", self.repo))



if __name__ == "__main__":
    unittest.main()
