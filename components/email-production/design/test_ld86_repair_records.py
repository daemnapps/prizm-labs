#!/usr/bin/env python3
"""LD-86 (old records repaired): repair_records.py turns an old picture record's machine paths into LD-81 (portable
picture records)'s refs by the form of each path, and touches nothing else — proven offline.

    python3 tools/email-production/design/test_ld86_repair_records.py

A fixture workspace in a temp folder: a fake brandpath drive index row, a run with a fake media/drive.json and the
picture it lists, and one old record holding one reference of each form, an unknown form and a pin. No key, no
network, no Google package. Stdlib only, 3.9.

  1  forms 1-3 map exactly to LD-81's shape: the cache path to the index row's {drive_id, label, bytes}; the mount
     path to {label} (with the row's id only when it IS that row's drive path); the run media path to its drive.json
     row, else the mirror label; the record's file gains file_ref from drive.json; every new ref is an LD-79 ref
  2  the unknown form and the pin are byte-identical after, and the unknown is listed (record, kind, path)
  3  a second run changes nothing and reports 0 records changed
  4  --dry-run prints every mapping and writes nothing
  5  a cache path the index cannot place (no row, or a different name) is left and listed, never guessed
"""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))      # design/ FIRST; never tools/email-production (its email.py shadows the stdlib's)
import repair_records as RR        # noqa: E402

sys.path.append(str(HERE.parents[1] / "gdrive-creator"))
from gdrive_creator import refs as REFS   # noqa: E402

BRAND, RUN, PIC = "acme", "acme-nov-09", "acme-nov-09-p1-01.png"
ROW = {"drive_id": "IDPACK", "name": "acme_pack.png", "bytes": 1234, "old_path": None,
       "drive_path": "brands/acme/products/pack/packshot/acme_pack.png"}
CACHE = "/var/folders/ab/cd123/T/brandpath-drive-cache/acme/IDPACK/acme_pack.png"
MOUNT = "~/Library/CloudStorage/GoogleDrive-someone@example.com/Shared drives/Shared Assets/"
CLONE = "~/Projects/workspace/runs/email-production/acme/acme-nov-09/media/"
PIN = {"path": "/private/tmp/wt/runs/email-production/acme/acme-nov-09/media/pins/p1/pin-00.jpg",
       "kind": "Pinterest pin (mood only)", "pinterest": {"pin": "https://example.com/pin/1", "title": "mood"}}
UNKNOWN = {"path": "/Volumes/stick/odd.png", "kind": "brand asset"}


def fixture(tmp, refs, file="media/" + PIC):
    repo = Path(tmp)
    idx = repo / "brands" / BRAND / "products" / "DRIVE-INDEX.json"
    idx.parent.mkdir(parents=True)
    idx.write_text(json.dumps({"files": [ROW]}))
    run = repo / "runs" / "email-production" / BRAND / RUN
    (run / "media").mkdir(parents=True)
    (run / "media" / PIC).write_bytes(b"x" * 77)
    (run / "media" / "drive.json").write_text(json.dumps({
        "schema": 1, "folder": "Shared Assets/runs/image-production/acme/acme-nov-09-p1", "folder_id": "F",
        "route": "api", "files": [{"path": PIC, "id": "IDPIC", "kind": "image"}]}))
    rec = run / "media" / "records" / "acme-nov-09-p1" / "record.json"
    rec.parent.mkdir(parents=True)
    rec.write_text(json.dumps({"label": "acme-nov-09-p1", "file": file, "purpose": "hero", "references": refs},
                              indent=1, ensure_ascii=False) + "\n")
    return repo, rec


def run(repo, rec, *extra):
    out = io.StringIO()
    RR.main([str(rec), "--repo", str(repo)] + list(extra), out=out)
    return out.getvalue()


def entry(rec, i):
    return json.loads(Path(rec).read_text())["references"][i]


class Repair(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        RR.DI._CACHE.clear()
        self.refs = [
            {"path": CACHE, "kind": "brand asset"},                                                    # 0 form 1
            {"path": MOUNT + ROW["drive_path"], "kind": "real product photo"},                        # 1 form 2, index row
            {"path": MOUNT + "brands/acme/products/other/x.png", "kind": "real product picture"},     # 2 form 2, label only
            {"path": CLONE + PIC, "kind": "earlier version of this picture"},                         # 3 form 3, drive.json
            {"path": CLONE + "acme-nov-09-p1-v2-01.png", "kind": "earlier version of this picture"},  # 4 form 3, mirror label
            dict(UNKNOWN),                                                                            # 5 unknown
            json.loads(json.dumps(PIN)),                                                              # 6 pin
        ]
        self.repo, self.rec = fixture(self.tmp.name, self.refs)

    def tearDown(self):
        self.tmp.cleanup()

    def test_1_forms_map_to_ld81_shape(self):
        run(self.repo, self.rec)
        d = json.loads(self.rec.read_text())
        pack = {"drive_id": "IDPACK", "label": "Shared Assets/" + ROW["drive_path"], "bytes": 1234}
        pic = {"drive_id": "IDPIC", "label": "Shared Assets/runs/image-production/acme/acme-nov-09-p1/" + PIC, "bytes": 77}
        mirror = {"label": "Shared Assets/runs/email-production/acme/acme-nov-09/media/acme-nov-09-p1-v2-01.png"}
        other = {"label": "Shared Assets/brands/acme/products/other/x.png"}
        want = [
            {"path": pack["label"], "ref": pack, "kind": "brand asset"},
            {"path": pack["label"], "ref": pack, "kind": "real product photo"},
            {"path": other["label"], "ref": other, "kind": "real product picture"},
            {"path": pic["label"], "ref": pic, "kind": "earlier version of this picture"},
            {"path": mirror["label"], "ref": mirror, "kind": "earlier version of this picture"},
        ]
        self.assertEqual(d["references"][:5], want)
        self.assertEqual(list(d)[:3], ["label", "file", "file_ref"])        # file_ref beside file, as keep() writes it
        self.assertEqual(d["file_ref"], pic)
        for e in d["references"][:5]:
            self.assertTrue(REFS.is_ref(e["ref"]), e)
            self.assertFalse(e["path"].startswith("/"), e)

    def test_2_unknown_and_pin_untouched_and_listed(self):
        out = run(self.repo, self.rec)
        d = json.loads(self.rec.read_text())
        self.assertEqual(json.dumps(d["references"][5]), json.dumps(UNKNOWN))
        self.assertEqual(json.dumps(d["references"][6]), json.dumps(PIN))
        listed = [x for x in out.splitlines() if x.startswith("LEFT AS IT IS:")]
        self.assertEqual(len(listed), 1, out)
        self.assertIn("record.json · brand asset · /Volumes/stick/odd.png", listed[0])
        self.assertNotIn("pin-00.jpg", "\n".join(listed))
        self.assertIn("1 pin untouched", out)
        self.assertIn("5 references repaired (form 1: 1, form 2: 2, form 3: 2) · 1 file_ref added", out)

    def test_3_second_run_changes_nothing(self):
        run(self.repo, self.rec)
        first = self.rec.read_bytes()
        out = run(self.repo, self.rec)
        self.assertEqual(self.rec.read_bytes(), first)
        self.assertIn("0 references repaired", out)
        self.assertIn("0 file_ref added", out)
        self.assertIn("5 already LD-81", out)
        self.assertIn("0 records changed", out)
        self.assertIn("=> unchanged", out)

    def test_4_dry_run_writes_nothing(self):
        before = self.rec.read_bytes()
        out = run(self.repo, self.rec, "--dry-run")
        self.assertEqual(self.rec.read_bytes(), before)
        self.assertIn("would change (dry run)", out)
        self.assertIn("nothing written", out)
        for r in self.refs[:5]:
            self.assertIn(r["path"], out)                 # every mapping printed
        self.assertIn('-> {"drive_id": "IDPACK"', out)
        self.assertIn("-> file_ref", out)
        self.assertIn("the picture is not on this Mac", out)      # why the v2 picture took the mirror label

    def test_5_unplaceable_cache_path_left_and_listed(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        RR.DI._CACHE.clear()
        refs = [{"path": "/var/folders/ab/cd/T/brandpath-drive-cache/acme/NOROW/a.png", "kind": "brand asset"},
                {"path": "/var/folders/ab/cd/T/brandpath-drive-cache/acme/IDPACK/not-the-name.png", "kind": "brand asset"}]
        repo, rec = fixture(tmp.name, refs, file=None)
        before = rec.read_bytes()
        out = run(repo, rec)
        self.assertEqual(rec.read_bytes(), before)
        self.assertEqual(len([x for x in out.splitlines() if x.startswith("LEFT AS IT IS:")]), 2, out)
        self.assertIn("no row for NOROW", out)
        self.assertIn("not not-the-name.png", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
