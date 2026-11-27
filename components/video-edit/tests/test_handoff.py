"""The video editor's front door (machine/handoff_run.py): reading a hand-off,
finding its media, and a run that moved between checkouts. Nothing renders."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import handoff_run as H  # noqa: E402


def make(root: Path, with_media: bool = True) -> Path:
    f = root / "video-editor" / "b" / "video-editor-handoff_b_2026-10-01"
    k = f / "assets" / "kit" / "kit"
    (k / "scenes").mkdir(parents=True)
    (k / "edit-kit.json").write_text(json.dumps({"clips": [{"id": "s01", "src": "scenes/a.mp4", "roll": "a", "approved": True, "talks": True}], "voice": None}))
    if with_media:
        (k / "scenes" / "a.mp4").write_bytes(b"x")
    (f / "manifest.json").write_text(json.dumps({"role": "video-editor", "brand": "b", "date": "2026-10-01",
                                                 "briefs": [{"id": "brief-0999", "product_id": "product_b_thing"}], "drive": {}}))
    return f


class TestHandoff(unittest.TestCase):
    def test_reads_the_handoff(self):
        with tempfile.TemporaryDirectory() as d:
            h = H.read_handoff(make(Path(d)))
            self.assertEqual((h["brand"], h["brief"], h["product"], h["label"]), ("b", "brief-0999", "thing", "brief-0999_2026-10-01"))
            self.assertEqual(str(h["kit_rel"]), "assets/kit/kit")

    def test_refuses_another_role(self):
        with tempfile.TemporaryDirectory() as d:
            f = make(Path(d))
            m = json.loads((f / "manifest.json").read_text()); m["role"] = "ad-uploader"
            (f / "manifest.json").write_text(json.dumps(m))
            with self.assertRaises(SystemExit):
                H.read_handoff(f)

    def test_missing_media_is_named(self):
        with tempfile.TemporaryDirectory() as d:
            h = H.read_handoff(make(Path(d), with_media=False))
            h["drive"] = None
            _, missing = H.find_kit(h)
            self.assertEqual(missing, ["scenes/a.mp4"])

    def test_media_found(self):
        with tempfile.TemporaryDirectory() as d:
            h = H.read_handoff(make(Path(d)))
            h["drive"] = None
            where, missing = H.find_kit(h)
            self.assertEqual(missing, [])
            self.assertTrue((where / "edit-kit.json").is_file())

    def test_relocate_points_moved_files_into_this_run(self):
        with tempfile.TemporaryDirectory() as d:
            run = Path(d) / "runs" / "video-edit" / "b" / "L"
            (run / "work").mkdir(parents=True)
            (run / "work" / "a.level.mp4").write_bytes(b"x")
            (run / "cutsheet-v1.json").write_text(json.dumps({"picture": [{"src": "/gone/checkout/runs/video-edit/b/L/work/a.level.mp4"},
                                                                          {"src": "scenes/keep.mp4"}]}))
            H.relocate(run, "b", "L")
            pic = json.loads((run / "cutsheet-v1.json").read_text())["picture"]
            self.assertEqual(pic[0]["src"], str(run / "work" / "a.level.mp4"))
            self.assertEqual(pic[1]["src"], "scenes/keep.mp4")


if __name__ == "__main__":
    unittest.main()
