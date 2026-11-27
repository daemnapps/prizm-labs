"""One run, two shelves (owner, 2026-09-30): what was read off the swipe is
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

    def test_writing_recovery_inputs_keep_exact_bytes_on_writing_shelf(self):
        repo, run = self.make(["1b-audience.md", "3-injection.md"])
        files = {
            "language-exposure.json": '{"queries": {"q": ["source-7", "source-2"]}}\n',
            "owner-controls.json": '{"schema": 1, "constraints": {"humor": {"source": "owner-script.md", "quote": "Keep it straight"}}}\n',
            "story.md": "# Signed story\nThe unchanged source words.\n",
            "owner-script.md": "Keep it straight\n",
            "RULINGS.md": "The owner's source ruling.\n",
            "verbatim-sources.md": "Exact customer source records.\n",
            "execution-decisions.md": "Current scope and continuation records.\n",
            "claim-execution-2026-11-19.md": "Formula claims only.\n",
            "factual-copy-execution-2026-11-19.md": "Source-supported method.\n",
            "casting-continuity-2026-11-19.sources.json": '{"sha256": "source-hash"}\n',
        }
        for name, body in files.items():
            (run / name).write_text(body)
        (run / "source.mp4").write_bytes(b"media stays out")
        (run / "unrelated-note.md").write_text("not an input")
        _, copied, left = FR.file_run(run, repo=repo)
        self.assertEqual(left, [])
        for name, body in files.items():
            self.assertIn(name, copied)
            self.assertEqual((repo / "runs/video-writing/zz/a-run" / name).read_bytes(), (run / name).read_bytes())
            self.assertFalse((repo / "runs/video-teardown/zz/a-run" / name).exists())
        self.assertFalse(any(p.name in ("source.mp4", "unrelated-note.md") for p in repo.rglob("*")))

    def test_new_writing_inputs_keep_text_size_and_run_boundary(self):
        repo, run = self.make(["3-injection.md"])
        (run / "language-exposure.json").write_text("x" * (FR.MAX_BYTES + 1))
        (run / "owner-controls.json").write_bytes(b"\xff\xfe")
        external = run.parent / "external.md";external.write_text("outside source")
        (run / "owner-script.md").symlink_to(external)
        (run / "factual-copy-execution-2026-11-19.md").symlink_to(external)
        _, copied, left = FR.file_run(run, repo=repo)
        self.assertIn("language-exposure.json (over 1 MB)", left)
        self.assertIn("owner-controls.json (not text)", left)
        self.assertIn("owner-script.md (outside run)", left)
        self.assertIn("factual-copy-execution-2026-11-19.md (outside run)", left)
        self.assertFalse(set(FR.WRITING_INPUTS).intersection(copied))

    def test_a_teardown_only_run_has_no_writing_shelf(self):
        repo, run = self.make(["0-triage.md", "1-teardown.md"])
        (run / "manifest.json").unlink()
        FR.file_run(run, repo=repo)
        self.assertFalse((repo / "runs/video-writing").exists())


if __name__ == "__main__":
    unittest.main()
