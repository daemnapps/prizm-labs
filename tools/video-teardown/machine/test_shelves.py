"""One run, two shelves (the owner, 2026-09-30): what was read off the swipe is
filed under runs/video-teardown/, everything written for a brand under
runs/video-writing/ — same brand, same slug."""
import json, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import file_run as FR                                        # noqa: E402


class Shelves(unittest.TestCase):
    def make(self, stages):
        t = Path(tempfile.mkdtemp())
        run = t / "a-run"
        (run / "stages").mkdir(parents=True)
        (run / "run.json").write_text(json.dumps({"slug": "a-run", "brand": "zz"}))
        (run / "doctrine.json").write_text("{}")
        (run / "manifest.json").write_text("{}")
        for s in stages:
            (run / "stages" / s).write_text(s)
        return t / "repo", run

    def files(self, base):
        return sorted(str(p.relative_to(base)) for p in base.rglob("*") if p.is_file()) if base.exists() else []

    def test_teardown_and_writing_go_to_their_own_shelf(self):
        repo, run = self.make(["0-triage.md", "1-teardown.md", "1c-doctrine.md", "2-spec.md",
                               "1b-audience.md", "3-injection.md", "4b-hooks.md", "5-brief.md"])
        FR.file_run(run, repo=repo)
        td = repo / "runs/video-teardown/zz/a-run"
        wr = repo / "runs/video-writing/zz/a-run"
        self.assertEqual(self.files(td), ["doctrine.json", "run.json", "stages/0-triage.md",
                                          "stages/1-teardown.md", "stages/1c-doctrine.md", "stages/2-spec.md"])
        self.assertEqual(self.files(wr), ["deliverable/5-brief.md", "manifest.json", "run.json", "stages/1b-audience.md",
                                          "stages/3-injection.md", "stages/4b-hooks.md", "stages/5-brief.md"])

    def test_a_teardown_only_run_has_no_writing_shelf(self):
        repo, run = self.make(["0-triage.md", "1-teardown.md"])
        (run / "manifest.json").unlink()
        FR.file_run(run, repo=repo)
        self.assertFalse((repo / "runs/video-writing").exists())


if __name__ == "__main__":
    unittest.main()
