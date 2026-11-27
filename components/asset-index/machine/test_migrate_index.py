"""migrate_index (LD-56 (footage index in git)): pass 1 sorts a fixture work/ (three clips, one empty dir)
against a fake Drive; pass 2 writes runs/<brand>/<collection>/<drive-id>/ + map.json + old-ids.json,
text and the frame picture only, and touches nothing outside its runs folder. No Drive, no network."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import migrate_index as M  # noqa: E402
import shared_paths as SP  # noqa: E402

LAB = "Shared Assets/brands/acme/content-creators/raw/"


class FakeDrive:
    def __init__(self, files):
        self.files = files                    # {label: {"id", "size", "md5"}}

    def find(self, label, size=None):
        return self.files.get(label)

    def by_name(self, brand, name, size=None):
        hits = [dict(v, label=k) for k, v in self.files.items() if k.endswith("/" + name)]
        return hits[0] if len(hits) == 1 else None


class Migrate(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        work = self.tmp / "work"
        col = work / "acme-creators"
        for cid, name in (("aaa111", "a.mov"), ("bbb222", "b.mov"), ("ccc333", "c.mov")):
            (col / cid).mkdir(parents=True)
            (col / cid / "clip.json").write_text(json.dumps({"clip_id": cid, "filename": name, "transcript": "hi",
                                                             "meta": {"bytes": 10, "duration_s": 3.0}}))
            (col / cid / "breakdown.json").write_text(json.dumps({"subject": "a man"}))
            (col / cid / "frame_01.jpg").write_bytes(b"jpg")
        (col / "ddd444").mkdir()                                       # empty: an unfinished run
        (work / "_maps").mkdir()
        (work / "_maps" / "acme-creators.json").write_text(json.dumps({
            "aaa111": {"path": "/x/Shared drives/" + LAB + "a.mov"},
            "bbb222": {"path": None}}))                                  # only findable by name
        self.work, self.col = work, col
        self.drive = FakeDrive({LAB + "a.mov": {"id": "DRIVE_A", "size": 10, "md5": "m1"},
                                "Shared Assets/brands/acme/other/b.mov": {"id": "DRIVE_B", "size": 10, "md5": "m2"}})
        p = mock.patch.object(M, "WORK", work)
        p.start()
        self.addCleanup(p.stop)

    def test_pass1_sorts_every_record(self):
        rep = M.pass1(self.col, self.drive, self.tmp / "reports")
        self.assertEqual(rep["tally"], {"matched": 2, "nowhere": 1, "empty": 1})
        rows = {r["old_id"]: r for r in rep["rows"]}
        self.assertEqual((rows["aaa111"]["drive_id"], rows["aaa111"]["found_by"]), ("DRIVE_A", "map"))
        self.assertEqual((rows["bbb222"]["drive_id"], rows["bbb222"]["found_by"]), ("DRIVE_B", "name"))
        self.assertTrue((self.tmp / "reports" / "pass1-acme-creators.json").is_file())

    def test_pass2_writes_the_tree_map_and_table_and_nothing_else(self):
        rep = M.pass1(self.col, self.drive, self.tmp / "reports")
        before = sorted(str(p) for p in self.work.rglob("*"))
        runs = self.tmp / "runs"
        dry = M.pass2(self.col, rep, runs, go=False)
        self.assertEqual(dry["records"], 2)
        self.assertFalse(runs.exists())                                  # dry: nothing written
        M.pass2(self.col, rep, runs, go=True)
        d = runs / "acme" / "creators"
        self.assertEqual(sorted(p.name for p in d.iterdir()), ["DRIVE_A", "DRIVE_B", "map.json", "old-ids.json"])
        rec = json.loads((d / "DRIVE_A" / "clip.json").read_text())
        self.assertEqual((rec["drive_id"], rec["label"], rec["old_id"], rec["transcript"]),
                         ("DRIVE_A", LAB + "a.mov", "aaa111", "hi"))
        self.assertIsNone(rec["path"])                                   # no mount path is stored
        self.assertTrue((d / "DRIVE_A" / "breakdown.json").is_file())
        self.assertTrue((d / "DRIVE_A" / "frame_01.jpg").is_file())
        self.assertEqual(json.loads((d / "old-ids.json").read_text()), {"aaa111": "DRIVE_A", "bbb222": "DRIVE_B"})
        self.assertEqual(json.loads((d / "map.json").read_text())["DRIVE_B"]["label"],
                         "Shared Assets/brands/acme/other/b.mov")
        self.assertEqual(sorted(str(p) for p in self.work.rglob("*")), before)    # work/ untouched
        # the readers take the new collection's own map, keyed by Drive id, as a label
        self.assertEqual(SP.shared_path(d, "DRIVE_A"), LAB + "a.mov")


if __name__ == "__main__":
    unittest.main()
