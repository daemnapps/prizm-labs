"""A new story makes a new script, and the new script is audited: the old script's "repairs spent" mark must not skip
the new audit (a two-part drama's part 2 stayed unaccepted because the REPAIRS SPENT branch kept skipping it). The spent
repair count stays, so changing the story never buys more repair rounds."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

MACHINE = Path(__file__).resolve().parents[1] / "machine"
sys.path.insert(0, str(MACHINE))
spec = importlib.util.spec_from_file_location("vw_wv2_budget", str(MACHINE / "writing_v2.py"))
W = importlib.util.module_from_spec(spec)
spec.loader.exec_module(W)


def spent_run():
    return {"stages": {"stage4e": {"status": "done", "audit_spent": True, "audit_note": {"x": 1}},
                       "stage5": {"status": "done"}},
            "writing_retry_budget": {"limit": 2, "used": 2, "pending": [], "history": [{"round": 1}]}}


class NewStoryIsAudited(unittest.TestCase):
    def test_the_spent_mark_goes_and_the_count_stays(self):
        st = spent_run()
        W.invalidate_written(st, "story changed through --story")
        a = st["stages"]["stage4e"]
        self.assertEqual(a["status"], "stale")
        self.assertNotIn("audit_spent", a)
        self.assertNotIn("audit_note", a)
        self.assertEqual(st["writing_retry_budget"]["used"], 2)
        self.assertEqual(st["stages"]["stage5"]["status"], "stale")

    def test_lock_story_clears_the_mark_only_when_the_story_changes(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            story = d / "story-in.md"
            story.write_text("first story\n")
            (d / "run.json").write_text(json.dumps(spent_run()))
            W.lock_story(d, story)
            self.assertNotIn("audit_spent", json.loads((d / "run.json").read_text())["stages"]["stage4e"])
            st = json.loads((d / "run.json").read_text())
            st["stages"]["stage4e"].update(status="done", audit_spent=True)
            (d / "run.json").write_text(json.dumps(st))
            W.lock_story(d, story)                                       # the same story again: a resume, nothing cleared
            self.assertTrue(json.loads((d / "run.json").read_text())["stages"]["stage4e"].get("audit_spent"))


if __name__ == "__main__":
    unittest.main()
