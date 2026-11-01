"""LD-64 (records Drive ids): every station push leaves <run>/drive.json — the real Drive folder (the
door's label, never the request's out) and each pushed file's Drive id — and copy_to/drive.json, the
same bytes, for the door's $OUT. Fake reaches only: no Drive, no network, no key.

    /usr/bin/python3 test_ld64_drive_json.py      (from components/run-kit/)
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_kit import station  # noqa: E402

LABEL = "creator-a-kzn03-counter-kitchen"
OUT = "ve-creator-a-kzn03-counter-kitchen-2-20261020"


class IdReach:
    """put_ids answers ids "id-<sub>/<name>" and a per-call folder id, and records every file it is
    handed. `how` sets the route it answers."""
    def __init__(self, how="api"):
        self.how, self.calls = how, []

    def put_ids(self, files, parts):
        sub = parts[4:]
        self.calls.append((list(parts), [Path(f).name for f in files]))
        if self.how == "none":
            return {"how": "none", "placed": [], "note": "SKIP the rest of the Drive mirror — NoDrive: x",
                    "folder": "Shared Assets/" + "/".join(parts), "folder_id": None, "files": []}
        api = self.how == "api"
        rows = [{"name": Path(f).name,
                 "id": ("id-" + "/".join(sub + [Path(f).name])) if api else None}
                for f in files]
        return {"how": self.how, "note": None,
                "placed": ["Shared Assets/" + "/".join(parts + [Path(f).name]) for f in files],
                "folder": "Shared Assets/" + "/".join(parts),
                "folder_id": ("fid-" + ("/".join(sub) or ".")) if api else None, "files": rows}


class FakeReach:
    """Shared Assets as a local folder — put only (copied from test_station.py)."""
    def __init__(self, root):
        self.root = Path(root)

    def put(self, files, parts):
        dest = self.root.joinpath(*parts)
        dest.mkdir(parents=True, exist_ok=True)
        for f in files:
            shutil.copy2(str(f), str(dest / Path(f).name))
        return "api", [str(dest / Path(f).name) for f in files], None


class Base(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("GDRIVE_SA_KEY", None)
        os.environ["KEYS_NO_FALLBACK"] = "1"
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.tmp = Path(t.name)
        self.run_dir = self.tmp / "run"
        for rel in ("run.json", "a.png", "x.bin", "media/s1.mp4", "vo/l1.mp3"):
            (self.run_dir / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.run_dir / rel).write_text("x")

    def rec(self, where=None):
        return json.loads(((where or self.run_dir) / "drive.json").read_text(encoding="utf-8"))


class TestLabelTrap(Base):
    def test_the_record_names_the_door_label_and_the_uploads_ids(self):
        fake = IdReach()
        copy_to = self.tmp / OUT / LABEL
        res = station.push(self.run_dir, "video-edit", "brand-a", LABEL, reach=fake, copy_to=copy_to)
        self.assertEqual((self.run_dir / "drive.json").read_bytes(), (copy_to / "drive.json").read_bytes())
        rec = self.rec()
        self.assertEqual(rec["folder"], "Shared Assets/runs/video-edit/brand-a/" + LABEL)
        self.assertNotIn("ve-creator-a", rec["folder"])
        self.assertEqual(rec["schema"], 1)
        self.assertEqual(rec["route"], "api")
        self.assertEqual(rec["folder_id"], "fid-.")
        by = {f["path"]: f for f in rec["files"]}
        self.assertEqual(sorted(by), ["a.png", "media/s1.mp4", "run.json", "vo/l1.mp3", "x.bin"])
        for path, row in by.items():
            self.assertEqual(row["id"], "id-" + path)
        self.assertEqual({p: r["kind"] for p, r in by.items()},
                         {"run.json": "text", "media/s1.mp4": "video", "vo/l1.mp3": "audio",
                          "a.png": "image", "x.bin": "other"})
        self.assertEqual(res["placed"], 5)
        self.assertEqual(res["notes"], [])
        self.assertEqual(res["to"], "Shared Assets/runs/video-edit/brand-a/" + LABEL)
        self.assertEqual(res["drive"], rec)
        self.assertEqual(res["record"], str(self.run_dir / "drive.json"))


class TestStaleRecord(Base):
    def test_a_stale_record_is_never_uploaded_and_is_replaced(self):
        (self.run_dir / "drive.json").write_text('{"stale": true}')
        (self.run_dir / "framemap" / "frames").mkdir(parents=True)
        (self.run_dir / "framemap" / "frames" / "f1.jpg").write_text("x")
        (self.run_dir / "framemap" / "map.json").write_text("{}")
        fake = IdReach()
        station.push(self.run_dir, "video-teardown", "brand-a", LABEL, reach=fake,
                     skip=("framemap/frames",))
        for _parts, names in fake.calls:
            self.assertNotIn("drive.json", names)
        rec = self.rec()
        self.assertNotIn("stale", rec)
        paths = [f["path"] for f in rec["files"]]
        self.assertNotIn("drive.json", paths)
        self.assertIn("framemap/map.json", paths)
        self.assertFalse(any(p.startswith("framemap/frames") for p in paths))


class TestOtherRoutes(Base):
    def test_a_put_only_reach_records_null_ids(self):
        res = station.push(self.run_dir, "video-writing", "brand-a", LABEL, reach=FakeReach(self.tmp / "drive"))
        rec = self.rec()
        self.assertEqual(res["placed"], 5)
        self.assertEqual(len(rec["files"]), 5)
        self.assertTrue(all(f["id"] is None for f in rec["files"]))
        self.assertIsNone(rec["folder_id"])
        self.assertEqual(rec["folder"], "Shared Assets/runs/video-writing/brand-a/" + LABEL)

    def test_the_mount_records_null_ids(self):
        station.push(self.run_dir, "video-production", "brand-a", LABEL, reach=IdReach("mount"))
        rec = self.rec()
        self.assertEqual(rec["route"], "mount")
        self.assertIsNone(rec["folder_id"])
        self.assertEqual(len(rec["files"]), 5)
        self.assertTrue(all(f["id"] is None for f in rec["files"]))

    def test_no_route_writes_an_empty_record(self):
        copy_to = self.tmp / "out"
        res = station.push(self.run_dir, "video-edit", "brand-a", LABEL, reach=IdReach("none"), copy_to=copy_to)
        rec = self.rec()
        self.assertEqual((rec["route"], rec["files"], rec["folder_id"]), ("none", [], None))
        self.assertEqual(rec, self.rec(copy_to))
        self.assertEqual(res["placed"], 0)
        self.assertEqual(len(res["notes"]), 1)


class TestSameFilesAsToday(Base):
    def test_each_call_gets_exactly_todays_files(self):
        (self.run_dir / "drive.json").write_text("{}")
        today = {}
        for rel, files in station._groups(self.run_dir).items():
            sub = [] if str(rel) == "." else list(rel.parts)
            names = [Path(f).name for f in files if not (not sub and Path(f).name == "drive.json")]
            today[tuple(station.parts("video-edit", "brand-a", LABEL) + sub)] = names
        fake = IdReach()
        station.push(self.run_dir, "video-edit", "brand-a", LABEL, reach=fake)
        self.assertEqual({tuple(p): n for p, n in fake.calls}, today)
        self.assertEqual(sorted(n for _p, ns in fake.calls for n in ns),
                         ["a.png", "l1.mp3", "run.json", "s1.mp4", "x.bin"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
