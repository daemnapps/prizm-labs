"""Run records that read the same on every Mac (SI-67 (edit record paths), triage page 12):
status.json names the Drive as "Shared Assets/…", run.json's kit is written from the repo
root, and an old record's absolute kit is still read as written. Nothing renders."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import handoff_run as H  # noqa: E402

MACHINE = Path(__file__).resolve().parents[1] / "machine"


class RunRecordPaths(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.shared = self.tmp / "CloudStorage" / "GoogleDrive-zz@example.com" / "Shared drives" / "Shared Assets"
        self.shared.mkdir(parents=True)
        old_shared, old_link = H.drive_shared, H.drive_link
        H.drive_shared = lambda: self.shared
        H.drive_link = lambda p: None

        def restore():
            H.drive_shared, H.drive_link = old_shared, old_link
            shutil.rmtree(self.tmp, ignore_errors=True)
        self.addCleanup(restore)

    def test_drive_rel(self):
        self.assertEqual(H.drive_rel(self.shared / "runs/video-edit/b/l"), "Shared Assets/runs/video-edit/b/l")
        off = self.tmp / "elsewhere" / "l"
        self.assertEqual(H.drive_rel(off), str(off))
        self.assertIsNone(H.drive_rel(None))

    def test_status_names_the_drive_relatively(self):
        root = self.tmp / "ws"
        run = root / "runs" / "video-edit" / "b" / "l"
        (run / "work").mkdir(parents=True)
        (run / "work" / "rough-cut.mp4").write_bytes(b"x")
        drive_dir = self.shared / "runs" / "video-edit" / "b" / "l"
        (drive_dir / "work").mkdir(parents=True)
        (drive_dir / "work" / "rough-cut.mp4").write_bytes(b"x")
        h = {"folder": root / "handoff" / "video-editor-handoff_b_2026-10-01", "brief": "brief-0999", "brand": "b"}
        state = {"stops": {"timeline": "waiting"}, "steps": {}}
        st = H.write_status(run, h, state, None, drive_dir, None, root)
        self.assertEqual(st["drive"], "Shared Assets/runs/video-edit/b/l")
        self.assertEqual(st["drive_preview"], "Shared Assets/runs/video-edit/b/l/work/rough-cut.mp4")
        on_disk = json.loads((run / "status.json").read_text())
        self.assertEqual(on_disk["drive"], st["drive"])
        self.assertEqual(on_disk["drive_preview"], st["drive_preview"])
        for k in ("run", "drive", "drive_preview"):
            self.assertNotIn(str(self.tmp), on_disk[k], k)

    def test_kit_round_trip_and_history(self):
        root = self.tmp / "ws"
        kit = root / "runs" / "video-edit" / "b" / "l" / "kit"
        written = H.kit_rel(kit, root)
        self.assertEqual(written, "runs/video-edit/b/l/kit")
        self.assertEqual(H.kit_dir_of({"kit": written}, root), kit)
        old = "/old/mac/runs/video-edit/b/l/kit"
        self.assertEqual(H.kit_dir_of({"kit": old}, root), Path(old))
        outside = self.tmp / "outside" / "kit"
        self.assertEqual(H.kit_rel(outside, root), str(outside))

    def test_both_writers_and_the_reader_go_through_the_helpers(self):
        # a source check: run.py does not import under /usr/bin/python3 3.9.6 at HEAD (compose.py)
        hr = (MACHINE / "handoff_run.py").read_text()
        self.assertIn('state["kit"] = kit_rel(kit_dir, root)', hr)
        self.assertNotIn('state["kit"] = str(kit_dir)', hr)
        rp = (MACHINE / "run.py").read_text()
        self.assertIn("H.kit_rel(kit_dir, repo_root())", rp)
        self.assertIn("kit_dir = H.kit_dir_of(state, repo_root())", rp)
        self.assertNotIn('"kit": str(kit_dir)', rp)
        self.assertNotIn('kit_dir = Path(state["kit"])', rp)


if __name__ == "__main__":
    unittest.main()
