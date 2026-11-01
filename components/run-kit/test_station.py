"""run_kit.station: a station's run folder goes up to Shared Assets runs/<machine>/<brand>/<label>/,
subfolders kept, and comes back by the same label. A fake reach only — no Drive, no network.

    /usr/bin/python3 test_station.py      (from components/run-kit/)
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_kit import station  # noqa: E402


class FakeReach:
    """Shared Assets as a local folder."""
    def __init__(self, root):
        self.root = Path(root)

    def put(self, files, parts):
        dest = self.root.joinpath(*parts)
        dest.mkdir(parents=True, exist_ok=True)
        for f in files:
            shutil.copy2(str(f), str(dest / Path(f).name))
        return "api", [str(dest / Path(f).name) for f in files], None

    def fetch_folder(self, parts, dest_dir, recursive=False):
        src = self.root.joinpath(*parts)
        if not src.is_dir():
            return None
        shutil.copytree(str(src), str(dest_dir), dirs_exist_ok=True)
        return Path(dest_dir)

    def get(self, parts, name, dest_dir):
        src = self.root.joinpath(*parts) / name
        if not src.is_file():
            return None
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(Path(dest_dir) / name))
        return str(Path(dest_dir) / name)


class Station(unittest.TestCase):
    def test_push_then_pull_by_label(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            run = t / "run"
            (run / "stages").mkdir(parents=True)
            (run / "run.json").write_text("{}")
            (run / "stages" / "5-brief.md").write_text("brief")
            (run / "__pycache__").mkdir()
            (run / "__pycache__" / "x.pyc").write_text("skip me")
            reach = FakeReach(t / "drive")
            res = station.push(run, "video-writing", "brand-a", "lab-1", reach=reach)
            self.assertEqual(res["placed"], 2)
            self.assertEqual(res["to"], "Shared Assets/runs/video-writing/brand-a/lab-1")
            got = station.pull("video-writing", "brand-a", "lab-1", t / "back", reach=reach)
            self.assertEqual((got / "stages" / "5-brief.md").read_text(), "brief")
            self.assertFalse((got / "__pycache__").exists())
            self.assertIsNone(station.pull("video-writing", "brand-a", "nope", t / "none", reach=reach))

    def test_skip_keeps_folders_on_this_machine(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            run = t / "run"
            for rel in ("run.json", "framemap/framemap.json", "framemap/shots/K01.mp4",
                        "framemap/frames/K01/a.jpg", "framemap/elements/person-x/best.jpg"):
                (run / rel).parent.mkdir(parents=True, exist_ok=True)
                (run / rel).write_text("x")
            reach = FakeReach(t / "drive")
            res = station.push(run, "video-teardown", "brand-a", "lab-1", reach=reach,
                               skip=("framemap/frames", "framemap/elements"))
            self.assertEqual(res["placed"], 3)
            up = t / "drive" / "runs" / "video-teardown" / "brand-a" / "lab-1"
            self.assertTrue((up / "framemap" / "shots" / "K01.mp4").is_file())
            self.assertFalse((up / "framemap" / "frames").exists())
            self.assertFalse((up / "framemap" / "elements").exists())

    def test_a_teardown_pull_falls_back_to_the_old_mirror_and_says_so(self):
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            old = t / "drive" / "tools" / "video-teardown" / "runs" / "swipes" / "lab-1"
            old.mkdir(parents=True)
            (old / "run.json").write_text("{}")
            reach = FakeReach(t / "drive")
            out = io.StringIO()
            with redirect_stdout(out):
                got = station.pull("video-teardown", "brand-a", "lab-1", t / "back", reach=reach)
            self.assertTrue((got / "run.json").is_file())
            self.assertIn("pulled from Shared Assets/tools/video-teardown/runs/swipes/lab-1, modified", out.getvalue())
            self.assertIsNone(station.pull("video-writing", "brand-a", "lab-1", t / "w", reach=reach))

    # LD-53 (station-path runner), widened: working folder → repo copy → Shared Assets media → old mirror.
    def a_repo(self, t, stages):
        import json
        rc = t / "repo" / "runs" / "video-teardown" / "brand-a" / "lab-1"
        (rc / "stages").mkdir(parents=True)
        (rc / "run.json").write_text(json.dumps({"brand": "brand-a", "stages": {k: {"status": "done"} for k in stages}}))
        (rc / "stages" / "1-teardown.md").write_text("read")
        return rc

    def test_resolve_takes_the_repo_copy_first_and_resets_later_stages(self):
        import io, json
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            rc = self.a_repo(t, ["stage0", "stage1", "stage2", "stage3", "stage5"])
            before = (rc / "run.json").read_text()
            drive = t / "drive" / "runs" / "video-teardown" / "brand-a" / "lab-1"
            drive.mkdir(parents=True)
            (drive / "source.mp4").write_text("video")
            out = io.StringIO()
            with redirect_stdout(out):
                work, lines = station.resolve("video-teardown", "brand-a", "lab-1", t / "work", want=("source.mp4",),
                                              keep_stage=lambda k: k in ("stage0", "stage1", "stage2"),
                                              repo=t / "repo", reach=FakeReach(t / "drive"))
            st = json.loads((work / "run.json").read_text())
            self.assertEqual(sorted(st["stages"]), ["stage0", "stage1", "stage2"])
            self.assertEqual((work / "source.mp4").read_text(), "video")
            self.assertEqual((rc / "run.json").read_text(), before)                  # the repo file is never edited
            self.assertTrue(lines[0].startswith("repo runs/video-teardown/brand-a/lab-1 @ "), lines)
            self.assertTrue(any(ln.startswith("Shared Assets runs/video-teardown/brand-a/lab-1/source.mp4") for ln in lines))
            self.assertTrue(any("stage3, stage5 dropped" in ln for ln in lines))
            self.assertEqual(st["sources"], lines)
            self.assertIn("source: repo runs/video-teardown", out.getvalue())

    def test_resolve_keeps_a_working_folder_and_says_so(self):
        import io, json
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            self.a_repo(t, ["stage0"])
            work = t / "work"
            work.mkdir()
            (work / "run.json").write_text(json.dumps({"stages": {"stage5": {"status": "done"}}}))
            with redirect_stdout(io.StringIO()):
                _, lines = station.resolve("video-teardown", "brand-a", "lab-1", work, keep_stage=lambda k: False,
                                           repo=t / "repo", reach=FakeReach(t / "drive"))
            self.assertEqual(lines[0], "working folder %s" % work)
            self.assertIn("stage5", json.loads((work / "run.json").read_text())["stages"])   # a working run is never reset

    def test_resolve_names_every_place_when_nothing_is_found(self):
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as c:
                station.resolve("video-writing", "brand-a", "nope", t / "work", repo=t / "repo", reach=FakeReach(t / "drive"))
            self.assertIn("the repo runs/video-writing/brand-a/nope", str(c.exception))
            self.assertIn("Shared Assets runs/video-writing/brand-a/nope", str(c.exception))

    def test_a_media_folder_holding_only_text_is_fetched(self):
        # 2026-10-20, the second edit run: the repo's vo/ held manifest.json only, so 'want vo' was
        # satisfied and the voice mp3s on Shared Assets never came down.
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            work = t / "work"
            (work / "vo").mkdir(parents=True)
            (work / "run.json").write_text("{}")
            (work / "vo" / "manifest.json").write_text("{}")
            drive = t / "drive" / "runs" / "video-production" / "brand-a" / "lab-1" / "vo"
            drive.mkdir(parents=True)
            (drive / "S1.mp3").write_text("voice")
            with redirect_stdout(io.StringIO()):
                _, lines = station.resolve("video-production", "brand-a", "lab-1", work, want=("vo",),
                                           repo=t / "repo", reach=FakeReach(t / "drive"))
            self.assertEqual((work / "vo" / "S1.mp3").read_text(), "voice")
            self.assertTrue((work / "vo" / "manifest.json").is_file())
            self.assertTrue(any(ln.startswith("Shared Assets runs/video-production/brand-a/lab-1/vo") for ln in lines), lines)

    def test_a_label_with_a_slash_is_refused(self):
        with self.assertRaises(ValueError):
            station.parts("video-writing", "brand-a", "../x")


if __name__ == "__main__":
    unittest.main()
