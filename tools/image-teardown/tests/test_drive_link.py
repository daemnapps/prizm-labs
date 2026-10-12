#!/usr/bin/env python3
"""drive_link's Drive mirror — finals only, through gdrive-creator, into the
same Drive folder the lab script fed (SI-36 (teardown lab mirror)).

    python3 tests/test_drive_link.py

No key, no network, no PIL. The Google client is stubbed and Drive is a fake
held in memory; the fakes are COPIED from
new-workflow-design/builds/drive-pipe/test_gdrive_creator.py, not imported,
because that file runs its fakes inside subprocess scripts.
"""
import os
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

LANE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LANE / "tools"))

# ---- the Google client, stubbed BEFORE any engine call ----------------------
UPLOADS = []


class MediaFileUpload(object):
    """What upload_file builds; it records the file name and nothing else."""

    def __init__(self, path, mimetype=None, resumable=None):
        UPLOADS.append(os.path.basename(path))


_gac = types.ModuleType("googleapiclient")
_gac.__path__ = []
_http = types.ModuleType("googleapiclient.http")
_http.MediaFileUpload = MediaFileUpload
_gac.http = _http
sys.modules["googleapiclient"] = _gac
sys.modules["googleapiclient.http"] = _http

import paths as P                               # noqa: E402
import drive_link as DL                         # noqa: E402
from gdrive_creator import engine as E          # noqa: E402


# ---- the fake Drive ----------------------------------------------------------
def parse(q):
    """Enough of the Drive query language to answer honestly."""
    nm = re.search(r"name = '((?:[^'\\]|\\.)*)'", q)
    parent = re.search(r"'([^']+)' in parents", q)
    mime = re.search(r"mimeType = '([^']+)'", q)
    name = None
    if nm:
        name = nm.group(1).replace("\\'", "'").replace("\\\\", "\\")
    return (name, parent.group(1) if parent else None,
            mime.group(1) if mime else None)


class Exec(object):
    def __init__(self, log, call, result):
        self.log, self.call, self.result = log, call, result

    def execute(self):
        self.log.append(self.call)
        return self.result


class Files(object):
    """list / create / update — and NO delete: a call to one is an error."""

    def __init__(self, d):
        self.d = d

    def list(self, **kw):
        name, parent, mime = parse(kw["q"])
        hits = []
        for fid in sorted(self.d.store):
            f = self.d.store[fid]
            if parent is not None and f["parent"] != parent:
                continue
            if mime is not None and f["mime"] != mime:
                continue
            if name is not None and f["name"] != name:
                continue
            hits.append({"id": fid, "name": f["name"], "size": "1"})
        return Exec(self.d.log, {"op": "files.list", "q": kw["q"]},
                    {"files": hits[:kw.get("pageSize", 100)]})

    def create(self, body=None, fields=None, media_body=None, **kw):
        fid = "id-%d" % (len(self.d.store) + 1)
        self.d.store[fid] = {"parent": (body.get("parents") or [""])[0],
                             "name": body["name"],
                             "mime": body.get("mimeType", "")}
        return Exec(self.d.log, {"op": "files.create", "name": body["name"],
                                 "mime": body.get("mimeType")}, {"id": fid})

    def update(self, fileId=None, fields=None, media_body=None, **kw):
        return Exec(self.d.log, {"op": "files.update", "fileId": fileId},
                    {"id": fileId})


class Drives(object):
    def __init__(self, d):
        self.d = d

    def list(self, **kw):
        return Exec(self.d.log, {"op": "drives.list"}, {"drives": list(self.d.shared)})


class Drive(object):
    def __init__(self):
        self.store, self.log = {}, []
        self.shared = [{"id": "drive-sa", "name": "Team Drive"}]

    def drives(self):
        return Drives(self)

    def files(self):
        return Files(self)

    def seed(self, fid, name, parent, folder=True):
        self.store[fid] = {"parent": parent, "name": name,
                           "mime": E.FOLDER_MIME if folder else "image/png"}
        return fid


def creates(fake):
    return [c for c in fake.log if c["op"] == "files.create"]


# ---- the tests ---------------------------------------------------------------
class Source(unittest.TestCase):
    def test_no_lab_script_and_no_mount(self):
        src = Path(DL.__file__).read_text()
        for bad in ("mirror.py", "subprocess", "P.LAB", "P.DRIVE", "xattr",
                    "CloudStorage", "GoogleDrive-"):
            self.assertNotIn(bad, src, f"drive_link.py holds {bad!r}")


class Mirror(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        runs = Path(self.tmp.name)
        finals = runs / "r1" / "finals"
        (finals / ".web").mkdir(parents=True)
        (finals / ".compose-tmp").mkdir()
        (finals / "a.png").write_bytes(b"a")
        (finals / "b.jpg").write_bytes(b"b")
        (finals / ".web" / "x.jpg").write_bytes(b"x")
        (finals / ".compose-tmp" / "el.png").write_bytes(b"e")
        (finals / "notes.txt").write_text("not a picture\n")
        self.runs = runs

    def tearDown(self):
        self.tmp.cleanup()

    def test_mirror_lands_in_todays_drive_folder(self):
        fake = Drive()
        node = "drive-sa"
        for fid, name in [*((f"f-{x}", x) for x in P.DRIVE_SUBDIR),
                          ("f-it", "image-teardown"), ("f-runs", "runs"),
                          ("f-r1", "r1"), ("f-fin", "finals")]:
            node = fake.seed(fid, name, node)
        fake.seed("x-a", "a.png", "f-fin", folder=False)

        with mock.patch.object(P, "RUNS", self.runs):
            fid, ids = DL.mirror("r1", E, fake)

        self.assertEqual(fid, "f-fin")
        self.assertEqual(set(ids), {"a.png", "b.jpg"})
        self.assertEqual(ids["a.png"], "x-a")
        made = creates(fake)
        self.assertFalse([c for c in made if c["mime"] == E.FOLDER_MIME], made)
        self.assertFalse([c for c in made
                          if c["name"] in ("x.jpg", "el.png", "notes.txt")], made)
        ops = {c["op"] for c in fake.log}
        self.assertLessEqual(ops, {"drives.list", "files.list",
                                   "files.create", "files.update"}, ops)


class Service(unittest.TestCase):
    def test_no_key_is_a_loud_skip(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("GDRIVE_SA_KEY", None)
            with mock.patch.object(DL.DV, "service",
                                   side_effect=SystemExit("No GDRIVE_SA_KEY yet")):
                engine, svc, note = DL._service()
        self.assertIsNone(engine)
        self.assertIsNone(svc)
        self.assertTrue(note.startswith("SKIP the Drive mirror — no GDRIVE_SA_KEY"), note)

    def test_a_key_with_a_missing_package_is_a_failure(self):
        with mock.patch.dict(os.environ, {"GDRIVE_SA_KEY": "x"}):
            with mock.patch.object(DL.DV, "service", side_effect=SystemExit(
                    "gdrive-creator could not import googleapiclient.discovery")):
                with self.assertRaises(SystemExit):
                    DL._service()


class Shim(unittest.TestCase):
    def test_carry_over_goes_when_the_shim_goes(self):
        self.assertIn("REMOVE WITH THE SHIM", Path(P.__file__).read_text())
        if P.OLD_LANE.is_dir():
            self.skipTest("lab shim still present — carry_over stays until it is deleted")
        self.assertFalse(hasattr(P, "carry_over"))


if __name__ == "__main__":
    print(f"python {sys.version_info[:2]}")
    r = unittest.main(exit=False, verbosity=2).result
    print(f"\n{r.testsRun - len(r.failures) - len(r.errors) - len(r.skipped)}"
          f"/{r.testsRun} passed, {len(r.skipped)} skipped "
          f"on python {sys.version_info[:2]}")
    sys.exit(0 if r.wasSuccessful() else 1)
